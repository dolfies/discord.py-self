"""
The MIT License (MIT)

Copyright (c) 2015-present Rapptz

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, List, Literal, Optional, Tuple, Union, overload

from .enums import ButtonStyle, ComponentType, InteractionType, TextStyle, try_enum
from .interactions import _wrapped_interaction
from .partial_emoji import PartialEmoji, _EmojiTag
from .utils import MISSING, _generate_nonce, get_slots

if TYPE_CHECKING:
    from typing_extensions import Self

    from .emoji import Emoji
    from .interactions import Interaction
    from .message import Message
    from .types.components import (
        ActionRow as ActionRowPayload,
        ActionRowChildComponent,
        ButtonComponent as ButtonComponentPayload,
        Component as ComponentPayload,
        MessageChildComponent,
        ModalChildComponent,
        SelectMenu as SelectMenuPayload,
        SelectOption as SelectOptionPayload,
        TextInput as TextInputPayload,
    )
    from .types.interactions import (
        ActionRowInteractionData,
        ButtonInteractionData,
        ComponentInteractionData,
        SelectInteractionData,
        TextInputInteractionData,
    )

    MessageChildComponentType = Union['Button', 'SelectMenu']
    ActionRowChildComponentType = Union[MessageChildComponentType, 'TextInput']


__all__ = (
    'Component',
    'ActionRow',
    'Button',
    'SelectMenu',
    'SelectOption',
    'TextInput',
    'TextDisplay',
    'Container',
    'Section',
    'Thumbnail',
    'MediaGallery',
    'FileComponent',
    'Separator',
)


class Component:
    """Represents a Discord Bot UI Kit Component.

    Currently, the only components supported by Discord are:

    - :class:`ActionRow`
    - :class:`Button`
    - :class:`SelectMenu`
    - :class:`TextInput`

    .. versionadded:: 2.0
    """

    __slots__ = ('message',)

    __repr_info__: ClassVar[Tuple[str, ...]]
    message: Message

    def __repr__(self) -> str:
        attrs = ' '.join(f'{key}={getattr(self, key)!r}' for key in self.__repr_info__)
        return f'<{self.__class__.__name__} {attrs}>'

    @property
    def type(self) -> ComponentType:
        """:class:`ComponentType`: The type of component."""
        raise NotImplementedError

    @classmethod
    def _raw_construct(cls, **kwargs) -> Self:
        self = cls.__new__(cls)
        for slot in get_slots(cls):
            try:
                value = kwargs[slot]
            except KeyError:
                pass
            else:
                setattr(self, slot, value)
        return self

    def to_dict(self) -> Union[ActionRowInteractionData, ComponentInteractionData]:
        raise NotImplementedError


class ActionRow(Component):
    """Represents a Discord Bot UI Kit Action Row.

    This is a component that holds up to 5 children components in a row.

    This inherits from :class:`Component`.

    .. versionadded:: 2.0

    Attributes
    ------------
    children: List[Union[:class:`Button`, :class:`SelectMenu`, :class:`TextInput`]]
        The children components that this holds, if any.
    message: :class:`Message`
        The originating message.
    """

    __slots__ = ('children', 'id')

    __repr_info__: ClassVar[Tuple[str, ...]] = __slots__

    def __init__(self, data: ActionRowPayload, message: Message):
        self.message = message
        self.children: List[ActionRowChildComponentType] = []
        self.id: Optional[int] = data.get('id')

        for component_data in data.get('components', []):
            component = _component_factory(component_data, message)
            if component is not None:
                self.children.append(component)

    @property
    def type(self) -> Literal[ComponentType.action_row]:
        """:class:`ComponentType`: The type of component."""
        return ComponentType.action_row

    def to_dict(self) -> ActionRowInteractionData:
        payload = {
            'type': ComponentType.action_row.value,
            'components': [c.to_dict() for c in self.children],
        }  # type: ignore
        if self.id is not None:
            payload['id'] = self.id
        return payload


class TextDisplay(Component):
    """Represents a v2 Text Display component (type 10).

    This is a content component used in messages and modals.

    Attributes
    -----------
    content: :class:`str`
        The markdown content for this component.
    message: :class:`Message`
        The originating message, if any.
    """

    __slots__ = ('content', 'id')

    __repr_info__: ClassVar[Tuple[str, ...]] = __slots__

    def __init__(self, data: 'ComponentPayload', message: 'Message'):
        self.message = message
        self.content: str = data.get('content', '')
        self.id: Optional[int] = data.get('id')

    @property
    def type(self) -> int:
        """int: The raw component type value (10)."""
        return 10

    def to_dict(self) -> 'ComponentInteractionData':  # type: ignore[override]
        # TextDisplay is a non-interactive content component
        payload = {
            'type': 10,
            'content': self.content,
        }
        if self.id is not None:
            payload['id'] = self.id
        return payload


class Container(Component):
    """Represents a v2 Container layout component (type 17).

    Containers visually group a set of components and can include an accent color
    and spoiler state. Children can include layout, content, and interactive components.

    Attributes
    -----------
    children: List[:class:`Component`]
        The child components encapsulated within this container.
    accent_color: Optional[:class:`int`]
        Optional RGB color (0x000000 to 0xFFFFFF) for the container accent bar.
    spoiler: :class:`bool`
        Whether the container is marked as a spoiler.
    id: Optional[:class:`int`]
        Optional identifier for the component.
    message: :class:`Message`
        The originating message, if any.
    """

    __slots__ = ('children', 'accent_color', 'spoiler', 'id', 'data')

    __repr_info__: ClassVar[Tuple[str, ...]] = ('accent_color', 'spoiler', 'id')

    def __init__(self, data: 'ComponentPayload', message: 'Message'):
        self.message = message
        # Preserve raw data for forward-compatibility
        self.data: dict = dict(data)
        self.children: List[Component] = []
        for component_data in data.get('components', []) or []:
            component = _component_factory(component_data, message)
            if component is not None:
                self.children.append(component)

        self.accent_color: Optional[int] = data.get('accent_color')
        self.spoiler: bool = data.get('spoiler', False)
        self.id: Optional[int] = data.get('id')

    @property
    def type(self) -> int:
        """int: The raw component type value (17)."""
        return 17

    def to_dict(self) -> 'ComponentInteractionData':  # type: ignore[override]
        payload: dict = {
            'type': 17,
            'components': [c.to_dict() for c in self.children],
        }
        if self.accent_color is not None:
            payload['accent_color'] = self.accent_color
        if self.spoiler:
            payload['spoiler'] = True
        if self.id is not None:
            payload['id'] = self.id
        # Merge any unknown original fields (excluding ones we already set)
        for k, v in self.data.items():
            if k not in payload and k not in {'type'}:
                payload[k] = v
        return payload

    @property
    def buttons(self) -> List['Button']:
        """List[:class:`Button`]: All button components contained in this container.

        This searches inside rows, sections, accessories, and nested children.
        """
        out: List[Button] = []
        for comp in _walk_component_tree(self.children):
            if isinstance(comp, Button):
                out.append(comp)
        return out

    @property
    def select_menus(self) -> List['SelectMenu']:
        """List[:class:`SelectMenu`]: All select menus contained in this container."""
        out: List[SelectMenu] = []
        for comp in _walk_component_tree(self.children):
            if isinstance(comp, SelectMenu):
                out.append(comp)
        return out

    @property
    def text_displays(self) -> List['TextDisplay']:
        """List[:class:`TextDisplay`]: All text display components within this container."""
        out: List[TextDisplay] = []
        for comp in _walk_component_tree(self.children):
            if isinstance(comp, TextDisplay):
                out.append(comp)
        return out

    @property
    def text_content(self) -> str:
        """str: Concatenated text content from all nested :class:`TextDisplay` components.

        Blocks are separated by a blank line to preserve intent.
        """
        return '\n\n'.join(td.content for td in self.text_displays if td.content)

    @property
    def sections(self) -> List['Section']:
        """List[:class:`Section`]: All sections within this container."""
        out: List[Section] = []
        for comp in _walk_component_tree(self.children):
            if isinstance(comp, Section):
                out.append(comp)
        return out

    @property
    def thumbnails(self) -> List['Thumbnail']:
        """List[:class:`Thumbnail`]: All thumbnails contained in sections and accessories."""
        out: List[Thumbnail] = []
        for comp in _walk_component_tree(self.children):
            if isinstance(comp, Thumbnail):
                out.append(comp)
        return out

    @property
    def media_galleries(self) -> List['MediaGallery']:
        out: List[MediaGallery] = []
        for comp in _walk_component_tree(self.children):
            if isinstance(comp, MediaGallery):
                out.append(comp)
        return out

    @property
    def files(self) -> List['FileComponent']:
        out: List[FileComponent] = []
        for comp in _walk_component_tree(self.children):
            if isinstance(comp, FileComponent):
                out.append(comp)
        return out

    @property
    def raw_children(self) -> List[Component]:
        return list(self.children)


class Section(Component):
    """Represents a v2 Section layout component (type 9)."""

    __slots__ = ('components', 'accessory', 'id')

    __repr_info__: ClassVar[Tuple[str, ...]] = ('id',)

    def __init__(self, data: 'ComponentPayload', message: 'Message'):
        self.message = message
        self.id: Optional[int] = data.get('id')
        self.components: List[Component] = []
        for component_data in data.get('components', []) or []:
            component = _component_factory(component_data, message)
            if component is not None:
                self.components.append(component)
        accessory = data.get('accessory')
        self.accessory: Optional[Component] = _component_factory(accessory, message) if accessory else None

    @property
    def type(self) -> int:
        return 9

    def to_dict(self) -> 'ComponentInteractionData':  # type: ignore[override]
        payload: dict = {
            'type': 9,
            'components': [c.to_dict() for c in self.components],
        }
        if self.id is not None:
            payload['id'] = self.id
        if self.accessory is not None:
            payload['accessory'] = self.accessory.to_dict()
        return payload

    @property
    def text_displays(self) -> List['TextDisplay']:
        """List[:class:`TextDisplay`]: The section's text display children (1-3)."""
        return [c for c in self.components if isinstance(c, TextDisplay)]

    @property
    def text_content(self) -> str:
        """str: Concatenated text from the section's :class:`TextDisplay` children."""
        return '\n\n'.join(td.content for td in self.text_displays if td.content)

    @property
    def buttons(self) -> List['Button']:
        """List[:class:`Button`]: Any buttons found either as children or as accessory."""
        out: List[Button] = []
        for comp in _walk_component_tree(self.components):
            if isinstance(comp, Button):
                out.append(comp)
        if isinstance(self.accessory, Button):
            out.append(self.accessory)
        return out

    @property
    def thumbnail(self) -> Optional['Thumbnail']:
        """Optional[:class:`Thumbnail`]: The section's thumbnail accessory, if present."""
        if isinstance(self.accessory, Thumbnail):
            return self.accessory
        return None


class Thumbnail(Component):
    """Represents a v2 Thumbnail accessory component (type 11).

    This is typically used as a Section accessory to display an image.

    Attributes
    -----------
    url: Optional[:class:`str`]
        The URL of the image for this thumbnail, if provided by Discord.
    width: Optional[:class:`int`]
        The width of the image, when available.
    height: Optional[:class:`int`]
        The height of the image, when available.
    id: Optional[:class:`int`]
        Optional identifier for the component.
    data: :class:`dict`
        Raw payload preserved for forward-compatibility with additional fields.
    """

    __slots__ = ('url', 'width', 'height', 'id', 'data')

    __repr_info__: ClassVar[Tuple[str, ...]] = ('url', 'width', 'height', 'id')

    def __init__(self, data: 'ComponentPayload', message: 'Message'):
        self.message = message
        # Preserve raw to avoid losing future fields we don't explicitly model
        self.data: dict = dict(data)
        self.id: Optional[int] = data.get('id')
        # Known common fields
        self.url: Optional[str] = data.get('url') or data.get('image_url')
        self.width: Optional[int] = data.get('width')
        self.height: Optional[int] = data.get('height')

    @property
    def type(self) -> int:
        # Discord assigns 11 for image/thumbnail accessory in Components v2
        return 11

    def to_dict(self) -> 'ComponentInteractionData':  # type: ignore[override]
        payload: dict = {'type': 11}
        if self.id is not None:
            payload['id'] = self.id
        # Only include known fields if present; retain any unknowns from original
        if self.url is not None:
            payload['url'] = self.url
        if self.width is not None:
            payload['width'] = self.width
        if self.height is not None:
            payload['height'] = self.height
        # Merge any extra fields that were present originally but not modeled
        for k, v in self.data.items():
            if k not in payload and k not in {'type'}:
                payload[k] = v
        return payload


class MediaGallery(Component):
    """Represents a v2 Media Gallery content component (type 12)."""

    __slots__ = ('items', 'id')

    __repr_info__: ClassVar[Tuple[str, ...]] = ('id',)

    def __init__(self, data: 'ComponentPayload', message: 'Message'):
        self.message = message
        self.id: Optional[int] = data.get('id')
        self.items: List[dict] = list(data.get('items', []) or [])

    @property
    def type(self) -> int:
        return 12

    def to_dict(self) -> 'ComponentInteractionData':  # type: ignore[override]
        payload: dict = {
            'type': 12,
            'items': list(self.items),
        }
        if self.id is not None:
            payload['id'] = self.id
        return payload


class FileComponent(Component):
    """Represents a v2 File content component (type 13)."""

    __slots__ = ('file', 'spoiler', 'name', 'size', 'id')

    __repr_info__: ClassVar[Tuple[str, ...]] = ('name', 'size', 'spoiler', 'id')

    def __init__(self, data: 'ComponentPayload', message: 'Message'):
        self.message = message
        self.id: Optional[int] = data.get('id')
        self.file: Any = data.get('file')
        self.spoiler: bool = data.get('spoiler', False)
        self.name: Optional[str] = data.get('name')
        self.size: Optional[int] = data.get('size')

    @property
    def type(self) -> int:
        return 13

    def to_dict(self) -> 'ComponentInteractionData':  # type: ignore[override]
        payload: dict = {
            'type': 13,
            'file': self.file,
            'spoiler': self.spoiler,
        }
        if self.name is not None:
            payload['name'] = self.name
        if self.size is not None:
            payload['size'] = self.size
        if self.id is not None:
            payload['id'] = self.id
        return payload


class Separator(Component):
    """Represents a v2 Separator layout component (type 14)."""

    __slots__ = ('divider', 'spacing', 'id')

    __repr_info__: ClassVar[Tuple[str, ...]] = ('divider', 'spacing', 'id')

    def __init__(self, data: 'ComponentPayload', message: 'Message'):
        self.message = message
        self.id: Optional[int] = data.get('id')
        self.divider: bool = data.get('divider', True)
        self.spacing: int = data.get('spacing', 1)

    @property
    def type(self) -> int:
        return 14

    def to_dict(self) -> 'ComponentInteractionData':  # type: ignore[override]
        payload: dict = {
            'type': 14,
            'divider': self.divider,
            'spacing': self.spacing,
        }
        if self.id is not None:
            payload['id'] = self.id
        return payload


# ---- Traversal utilities ----------------------------------------------------

def _iter_component_children(component: Any) -> List[Component]:
    """Returns a best-effort list of child components for recursive traversal.

    This inspects common attributes used by v2 components such as
    `children`, `components`, and `accessory`.
    """
    out: List[Component] = []
    children = getattr(component, 'children', None)
    if isinstance(children, list):
        out.extend(children)
    components = getattr(component, 'components', None)
    if isinstance(components, list):
        out.extend(components)
    accessory = getattr(component, 'accessory', None)
    if isinstance(accessory, Component):
        out.append(accessory)
    return out


def _walk_component_tree(roots: List[Component]) -> List[Component]:
    """Depth-first traversal returning every component starting from roots.

    The order follows the payload order for deterministic iteration.
    """
    result: List[Component] = []

    def _walk(nodes: List[Component]) -> None:
        for node in nodes:
            result.append(node)
            kids = _iter_component_children(node)
            if kids:
                _walk(kids)

    _walk(roots)
    return result


class Button(Component):
    """Represents a button from the Discord Bot UI Kit.

    This inherits from :class:`Component`.

    .. versionadded:: 2.0

    Attributes
    -----------
    style: :class:`.ButtonStyle`
        The style of the button.
    custom_id: Optional[:class:`str`]
        The ID of the button that gets received during an interaction.
        If this button is for a URL, it does not have a custom ID.
    url: Optional[:class:`str`]
        The URL this button sends you to.
    disabled: :class:`bool`
        Whether the button is disabled or not.
    label: Optional[:class:`str`]
        The label of the button, if any.
    emoji: Optional[:class:`PartialEmoji`]
        The emoji of the button, if available.
    message: :class:`Message`
        The originating message.
    """

    __slots__ = (
        'style',
        'custom_id',
        'url',
        'disabled',
        'label',
        'emoji',
    )

    __repr_info__: ClassVar[Tuple[str, ...]] = __slots__

    def __init__(self, data: ButtonComponentPayload, message: Message):
        self.message = message
        self.style: ButtonStyle = try_enum(ButtonStyle, data['style'])
        self.custom_id: Optional[str] = data.get('custom_id')
        self.url: Optional[str] = data.get('url')
        self.disabled: bool = data.get('disabled', False)
        self.label: Optional[str] = data.get('label')
        self.emoji: Optional[PartialEmoji]
        try:
            self.emoji = PartialEmoji.from_dict(data['emoji'])  # pyright: ignore[reportTypedDictNotRequiredAccess]
        except KeyError:
            self.emoji = None

    @property
    def type(self) -> Literal[ComponentType.button]:
        """:class:`ComponentType`: The type of component."""
        return ComponentType.button

    def to_dict(self) -> ButtonInteractionData:
        return {
            'component_type': self.type.value,
            'custom_id': self.custom_id or '',
        }

    async def click(self) -> Union[str, Interaction]:
        """|coro|

        Clicks the button.

        Raises
        -------
        InvalidData
            Didn't receive a response from Discord
            (doesn't mean the interaction failed).
        NotFound
            The originating message was not found.
        HTTPException
            Clicking the button failed.

        Returns
        --------
        Union[:class:`str`, :class:`Interaction`]
            The button's URL or the interaction that was created.
        """
        if self.url:
            return self.url

        message = self.message
        return await _wrapped_interaction(
            message._state,
            _generate_nonce(),
            InteractionType.component,
            None,
            message.channel,  # type: ignore # channel is always correct here
            self.to_dict(),
            message=message,
        )


class SelectMenu(Component):
    """Represents a select menu from the Discord Bot UI Kit.

    A select menu is functionally the same as a dropdown, however
    on mobile it renders a bit differently.

    .. versionadded:: 2.0

    Attributes
    ------------
    custom_id: Optional[:class:`str`]
        The ID of the select menu that gets received during an interaction.
    placeholder: Optional[:class:`str`]
        The placeholder text that is shown if nothing is selected, if any.
    min_values: :class:`int`
        The minimum number of items that must be chosen for this select menu.
    max_values: :class:`int`
        The maximum number of items that must be chosen for this select menu.
    options: List[:class:`SelectOption`]
        A list of options that can be selected in this menu.
    disabled: :class:`bool`
        Whether the select is disabled or not.
    message: :class:`Message`
        The originating message, if any.
    """

    __slots__ = (
        'custom_id',
        'placeholder',
        'min_values',
        'max_values',
        'options',
        'disabled',
        'hash',
    )

    __repr_info__: ClassVar[Tuple[str, ...]] = __slots__

    def __init__(self, data: SelectMenuPayload, message: Message):
        self.message = message
        self.custom_id: str = data['custom_id']
        self.placeholder: Optional[str] = data.get('placeholder')
        self.min_values: int = data.get('min_values', 1)
        self.max_values: int = data.get('max_values', 1)
        self.options: List[SelectOption] = [SelectOption.from_dict(option) for option in data.get('options', [])]
        self.disabled: bool = data.get('disabled', False)
        self.hash: str = data.get('hash', '')

    @property
    def type(self) -> Literal[ComponentType.select]:
        """:class:`ComponentType`: The type of component."""
        return ComponentType.select

    def to_dict(self, options: Optional[Tuple[SelectOption, ...]] = None) -> SelectInteractionData:
        return {
            'component_type': self.type.value,
            'custom_id': self.custom_id,
            'values': [option.value for option in options] if options else [],
        }

    async def choose(self, *options: SelectOption) -> Interaction:
        """|coro|

        Chooses the given options from the select menu.

        Raises
        -------
        InvalidData
            Didn't receive a response from Discord
            (doesn't mean the interaction failed).
        NotFound
            The originating message was not found.
        HTTPException
            Choosing the options failed.

        Returns
        --------
        :class:`Interaction`
            The interaction that was created.
        """
        message = self.message
        return await _wrapped_interaction(
            message._state,
            _generate_nonce(),
            InteractionType.component,
            None,
            message.channel,  # type: ignore # acc_channel is always correct here
            self.to_dict(options),
            message=message,
        )


class SelectOption:
    """Represents a select menu's option.

    .. versionadded:: 2.0

    Attributes
    -----------
    label: :class:`str`
        The label of the option. This is displayed to users.
        Can only be up to 100 characters.
    value: :class:`str`
        The value of the option. This is not displayed to users.
        If not provided when constructed then it defaults to the
        label. Can only be up to 100 characters.
    description: Optional[:class:`str`]
        An additional description of the option, if any.
        Can only be up to 100 characters.
    emoji: Optional[:class:`PartialEmoji`]
        The emoji of the option, if available.
    default: :class:`bool`
        Whether this option is selected by default.
    """

    __slots__ = (
        'label',
        'value',
        'description',
        'emoji',
        'default',
    )

    def __init__(
        self,
        *,
        label: str,
        value: str = MISSING,
        description: Optional[str] = None,
        emoji: Optional[Union[str, Emoji, PartialEmoji]] = None,
        default: bool = False,
    ) -> None:
        self.label: str = label
        self.value: str = label if value is MISSING else value
        self.description: Optional[str] = description

        if emoji is not None:
            if isinstance(emoji, str):
                emoji = PartialEmoji.from_str(emoji)
            elif isinstance(emoji, _EmojiTag):
                emoji = emoji._to_partial()
            else:
                raise TypeError(f'expected emoji to be str, Emoji, or PartialEmoji not {emoji.__class__}')

        self.emoji: Optional[PartialEmoji] = emoji
        self.default: bool = default

    def __repr__(self) -> str:
        return (
            f'<SelectOption label={self.label!r} value={self.value!r} description={self.description!r} '
            f'emoji={self.emoji!r} default={self.default!r}>'
        )

    def __str__(self) -> str:
        if self.emoji:
            base = f'{self.emoji} {self.label}'
        else:
            base = self.label

        if self.description:
            return f'{base}\n{self.description}'
        return base

    @classmethod
    def from_dict(cls, data: SelectOptionPayload) -> SelectOption:
        try:
            emoji = PartialEmoji.from_dict(data['emoji'])  # pyright: ignore[reportTypedDictNotRequiredAccess]
        except KeyError:
            emoji = None

        return cls(
            label=data['label'],
            value=data['value'],
            description=data.get('description'),
            emoji=emoji,
            default=data.get('default', False),
        )


class TextInput(Component):
    """Represents a text input from the Discord Bot UI Kit.

    .. versionadded:: 2.0

    Attributes
    ------------
    custom_id: Optional[:class:`str`]
        The ID of the text input that gets received during an interaction.
    label: :class:`str`
        The label to display above the text input.
    style: :class:`TextStyle`
        The style of the text input.
    placeholder: Optional[:class:`str`]
        The placeholder text to display when the text input is empty.
    required: :class:`bool`
        Whether the text input is required.
    min_length: Optional[:class:`int`]
        The minimum length of the text input.
    max_length: Optional[:class:`int`]
        The maximum length of the text input.
    """

    __slots__ = (
        'style',
        'label',
        'custom_id',
        'placeholder',
        '_value',
        '_answer',
        'required',
        'min_length',
        'max_length',
    )

    __repr_info__: ClassVar[Tuple[str, ...]] = (
        'style',
        'label',
        'custom_id',
        'placeholder',
        'required',
        'min_length',
        'max_length',
        'default',
    )

    def __init__(self, data: TextInputPayload, *args) -> None:
        self.style: TextStyle = try_enum(TextStyle, data['style'])
        self.label: str = data['label']
        self.custom_id: str = data['custom_id']
        self.placeholder: Optional[str] = data.get('placeholder')
        self._value: Optional[str] = data.get('value')
        self.required: bool = data.get('required', True)
        self.min_length: Optional[int] = data.get('min_length')
        self.max_length: Optional[int] = data.get('max_length')

    @property
    def type(self) -> Literal[ComponentType.text_input]:
        """:class:`ComponentType`: The type of component."""
        return ComponentType.text_input

    @property
    def value(self) -> Optional[str]:
        """Optional[:class:`str`]: The current value of the text input. Defaults to :attr:`default`.

        This can be set to change the answer to the text input.
        """
        return getattr(self, '_answer', self._value)

    @value.setter
    def value(self, value: Optional[str]) -> None:
        length = len(value) if value is not None else 0
        if (self.required or value is not None) and (
            (self.min_length is not None and length < self.min_length)
            or (self.max_length is not None and length > self.max_length)
        ):
            raise ValueError(
                f'value cannot be shorter than {self.min_length or 0} or longer than {self.max_length or "infinity"}'
            )

        self._answer = value

    @property
    def default(self) -> Optional[str]:
        """Optional[:class:`str`]: The default value of the text input."""
        return self._value

    def answer(self, value: Optional[str], /) -> None:
        """A shorthand method to answer the text input.

        Parameters
        ----------
        value: Optional[:class:`str`]
            The value to set the answer to.

        Raises
        ------
        ValueError
            The answer is shorter than :attr:`min_length` or longer than :attr:`max_length`.
        """
        self.value = value

    def to_dict(self) -> TextInputInteractionData:
        return {
            'type': self.type.value,
            'custom_id': self.custom_id,
            'value': self.value or '',
        }


@overload
def _component_factory(data: ActionRowPayload, message: Message = ...) -> ActionRow: ...


@overload
def _component_factory(data: MessageChildComponent, message: Message = ...) -> Optional[MessageChildComponentType]: ...


@overload
def _component_factory(data: ModalChildComponent, message: Message = ...) -> Optional[TextInput]: ...


@overload
def _component_factory(data: ActionRowChildComponent, message: Message = ...) -> Optional[ActionRowChildComponentType]: ...


@overload
def _component_factory(data: ComponentPayload, message: Message = ...) -> Optional[Component]: ...


def _component_factory(data: ComponentPayload, message: Message = MISSING) -> Optional[Component]:
    if data['type'] == 1:
        return ActionRow(data, message)
    elif data['type'] == 2:
        return Button(data, message)
    elif data['type'] == 3:
        return SelectMenu(data, message)
    elif data['type'] == 4:
        return TextInput(data, message)
    elif data['type'] == 9:  # Section (v2)
        return Section(data, message)
    elif data['type'] == 10:  # Text Display (v2)
        return TextDisplay(data, message)
    elif data['type'] == 11:  # Thumbnail (v2)
        return Thumbnail(data, message)
    elif data['type'] == 12:  # Media Gallery (v2)
        return MediaGallery(data, message)
    elif data['type'] == 13:  # File (v2)
        return FileComponent(data, message)
    elif data['type'] == 14:  # Separator (v2)
        return Separator(data, message)
    elif data['type'] == 17:  # Container (v2)
        return Container(data, message)
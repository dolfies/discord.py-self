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

from typing import TYPE_CHECKING, Any, ClassVar, Iterable, List, Literal, Optional, Tuple, Union, overload

from .asset import AssetMixin
from .colour import Colour
from .enums import (
    ButtonStyle,
    ChannelType,
    ComponentType,
    InteractionType,
    MediaItemLoadingState,
    SelectDefaultValueType,
    SeparatorSpacing,
    TextStyle,
    try_enum,
)
from .file import CloudFile, File, _FileBase
from .flags import AttachmentFlags
from .interactions import _wrapped_interaction
from .partial_emoji import PartialEmoji, _EmojiTag
from .utils import MISSING, _generate_nonce, _get_as_snowflake, get_slots

if TYPE_CHECKING:
    from typing_extensions import Self

    from .abc import Snowflake
    from .emoji import Emoji
    from .message import Message
    from .state import ConnectionState
    from .types.components import (
        ActionRow as ActionRowPayload,
        ActionRowChildComponent,
        ButtonComponent as ButtonComponentPayload,
        CheckboxComponent as CheckboxComponentPayload,
        CheckboxGroupComponent as CheckboxGroupComponentPayload,
        CheckboxGroupOption as CheckboxGroupOptionPayload,
        Component as ComponentPayload,
        ContainerComponent as ContainerComponentPayload,
        FileComponent as FileComponentPayload,
        FileUploadComponent as FileUploadComponentPayload,
        LabelComponent as LabelComponentPayload,
        MediaGalleryComponent as MediaGalleryComponentPayload,
        MediaGalleryItem as MediaGalleryItemPayload,
        ModalChildComponent,
        RadioGroupComponent as RadioGroupComponentPayload,
        RadioGroupOption as RadioGroupOptionPayload,
        SectionComponent as SectionComponentPayload,
        SelectDefaultValues as SelectDefaultValuesPayload,
        SelectMenu as SelectMenuPayload,
        SelectOption as SelectOptionPayload,
        SeparatorComponent as SeparatorComponentPayload,
        TextComponent as TextComponentPayload,
        TextInput as TextInputPayload,
        ThumbnailComponent as ThumbnailComponentPayload,
        UnfurledMediaItem as UnfurledMediaItemPayload,
    )
    from .types.interactions import ButtonInteractionData, SelectInteractionData
    from .types.message import PartialAttachment as PartialAttachmentPayload

    MessageChildComponentType = Union['Button', 'SelectMenu']
    ActionRowChildComponentType = Union[
        MessageChildComponentType,
        'TextInput',
        'FileUploadComponent',
        'RadioGroupComponent',
        'CheckboxGroupComponent',
        'CheckboxComponent',
    ]
    ModalChildComponentType = Union[
        'TextInput',
        'SelectMenu',
        'FileUploadComponent',
        'RadioGroupComponent',
        'CheckboxGroupComponent',
        'CheckboxComponent',
    ]
    OptionPayload = Union[SelectOptionPayload, RadioGroupOptionPayload, CheckboxGroupOptionPayload]
    ComponentWithMessage = Optional[Message]


__all__ = (
    'Component',
    'ActionRow',
    'Button',
    'SelectMenu',
    'SelectOption',
    'TextInput',
    'SelectDefaultValue',
    'SectionComponent',
    'TextDisplay',
    'UnfurledMediaItem',
    'ThumbnailComponent',
    'MediaGalleryItem',
    'MediaGalleryComponent',
    'FileComponent',
    'SeparatorComponent',
    'Container',
    'LabelComponent',
    'FileUploadComponent',
    'RadioGroupComponent',
    'RadioGroupOption',
    'CheckboxGroupComponent',
    'CheckboxGroupOption',
    'CheckboxComponent',
)


class Component:
    """Represents a Discord Bot UI Kit Component.

    The components supported by Discord are:

    - :class:`ActionRow`
    - :class:`Button`
    - :class:`SelectMenu`
    - :class:`TextInput`
    - :class:`SectionComponent`
    - :class:`TextDisplay`
    - :class:`ThumbnailComponent`
    - :class:`MediaGalleryComponent`
    - :class:`FileComponent`
    - :class:`SeparatorComponent`
    - :class:`Container`
    - :class:`LabelComponent`
    - :class:`FileUploadComponent`

    This class is abstract and cannot be instantiated.

    .. versionadded:: 2.0
    """

    __slots__ = ()

    __repr_info__: ClassVar[Tuple[str, ...]]

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

    def to_dict(self) -> ComponentPayload:
        raise NotImplementedError

    @staticmethod
    def _validate_answer_count(count: int, min_values: int, max_values: int, required: bool, name: str) -> None:
        if count == 0 and not required:
            return

        min_required = max(min_values, 1) if required else min_values
        if count < min_required:
            raise ValueError(f'{name} must contain at least {min_required} item(s)')
        if count > max_values:
            raise ValueError(f'{name} must contain at most {max_values} item(s)')

    def to_submit_dict(
        self,
        files: Optional[List[_FileBase]] = None,
        attachments: Optional[List[PartialAttachmentPayload]] = None,
    ) -> ComponentPayload:
        return self.to_dict()


class BaseOption:
    """Represents a base option for components that have options.

    This currently implements:

    - :class:`SelectOption`
    - :class:`RadioGroupOption`
    - :class:`CheckboxGroupOption`

    .. versionadded:: 2.2
    """

    __slots__ = ('label', 'value', 'description', 'default')
    __repr_info__: ClassVar[Tuple[str, ...]] = __slots__

    def __init__(
        self,
        *,
        label: str,
        value: str = MISSING,
        description: Optional[str] = None,
        default: bool = False,
    ) -> None:
        self.label = label
        self.value = label if value is MISSING else value
        self.description = description
        self.default = default

    def __repr__(self) -> str:
        attrs = ' '.join(f'{key}={getattr(self, key)!r}' for key in self.__repr_info__)
        return f'<{self.__class__.__name__} {attrs}>'

    def __str__(self) -> str:
        if self.description:
            return f'{self.label}\n{self.description}'
        return self.label

    @staticmethod
    def _validate_options(options: Iterable[BaseOption], selected: Iterable[BaseOption], name: str) -> None:
        allowed = {option.value for option in options}
        if allowed and any(option.value not in allowed for option in selected):
            raise ValueError(f'{name} must belong to this component')

    @classmethod
    def from_dict(cls, data: OptionPayload) -> Self:
        return cls(
            label=data['label'],
            value=data['value'],
            description=data.get('description'),
            default=data.get('default', False),
        )

    def to_dict(self) -> OptionPayload:
        payload: OptionPayload = {
            'label': self.label,
            'value': self.value,
            'default': self.default,
        }
        if self.description:
            payload['description'] = self.description
        return payload

    def copy(self) -> Self:
        return self.__class__.from_dict(self.to_dict())


class ActionRow(Component):
    """Represents a Discord action row component.

    Action rows group interactive child components such as buttons, select
    menus, and text inputs.

    Attributes
    ----------
    children: List[:class:`Component`]
        The child components in this row.
    id: Optional[:class:`int`]
        The component ID, if Discord provided one.
    """

    __slots__ = ('children', 'id')
    __repr_info__: ClassVar[Tuple[str, ...]] = ('children', 'id')

    def __init__(self, data: ActionRowPayload, message: ComponentWithMessage = MISSING):
        self.id = data.get('id')
        self.children: List[ActionRowChildComponentType] = []

        for component_data in data.get('components', []):
            component = _component_factory(component_data, message)
            if component is not None:
                self.children.append(component)

    @property
    def type(self) -> Literal[ComponentType.action_row]:
        """:class:`ComponentType`: The type of component."""
        return ComponentType.action_row

    def to_dict(self) -> ActionRowPayload:
        payload: ActionRowPayload = {
            'type': self.type.value,
            'components': [c.to_dict() for c in self.children],
        }
        if self.id is not None:
            payload['id'] = self.id
        return payload

    def to_submit_dict(
        self,
        files: Optional[List[_FileBase]] = None,
        attachments: Optional[List[PartialAttachmentPayload]] = None,
    ) -> ActionRowPayload:
        payload = {
            'type': self.type.value,
            'components': [c.to_submit_dict(files, attachments) for c in self.children],
        }
        if self.id is not None:
            payload['id'] = self.id
        return payload  # type: ignore


class Button(Component):
    """Represents a Discord button component.

    Buttons can be clicked when they belong to a message. Link and premium
    buttons do not create component interactions.

    Attributes
    ----------
    style: :class:`ButtonStyle`
        The button style.
    custom_id: Optional[:class:`str`]
        The custom ID used for interaction callbacks, if any.
    url: Optional[:class:`str`]
        The link URL for link buttons.
    disabled: :class:`bool`
        Whether the button is disabled.
    label: Optional[:class:`str`]
        The button label.
    emoji: Optional[:class:`PartialEmoji`]
        The button emoji.
    sku_id: Optional[:class:`int`]
        The SKU ID for premium buttons.
    id: Optional[:class:`int`]
        The component ID, if Discord provided one.
    message: Optional[:class:`Message`]
        The originating message, if this component came from a message.
    """

    __slots__ = ('style', 'custom_id', 'url', 'disabled', 'label', 'emoji', 'sku_id', 'id', 'message')
    __repr_info__: ClassVar[Tuple[str, ...]] = (
        'style',
        'custom_id',
        'url',
        'disabled',
        'label',
        'emoji',
        'sku_id',
        'id',
    )

    def __init__(self, data: ButtonComponentPayload, message: ComponentWithMessage = MISSING):
        self.message = None if message is MISSING else message
        self.id = data.get('id')
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

        try:
            self.sku_id: Optional[int] = int(data['sku_id'])  # pyright: ignore[reportTypedDictNotRequiredAccess]
        except KeyError:
            self.sku_id = None

    @property
    def type(self) -> Literal[ComponentType.button]:
        """:class:`ComponentType`: The type of component."""
        return ComponentType.button

    def to_interaction_dict(self) -> ButtonInteractionData:
        return {
            'component_type': self.type.value,
            'custom_id': self.custom_id or '',
        }

    def to_dict(self) -> ButtonComponentPayload:
        payload: ButtonComponentPayload = {
            'type': self.type.value,
            'style': self.style.value,
            'disabled': self.disabled,
        }
        if self.id is not None:
            payload['id'] = self.id
        if self.sku_id is not None:
            payload['sku_id'] = str(self.sku_id)
        if self.label:
            payload['label'] = self.label
        if self.custom_id:
            payload['custom_id'] = self.custom_id
        if self.url:
            payload['url'] = self.url
        if self.emoji:
            payload['emoji'] = self.emoji.to_dict()
        return payload

    async def click(self) -> Optional[str]:
        """|coro|

        Clicks the button.

        Link buttons return their URL and do not create an interaction.
        Premium buttons cannot be clicked and return ``None``.

        .. versionchanged:: 2.2

            This no longer returns the created interaction.

        Raises
        -------
        TypeError
            The button is not attached to a message.
        NotFound
            The originating message was not found.
        HTTPException
            Clicking the button failed.

        Returns
        --------
        Optional[:class:`str`]
            The button's URL for link buttons, or ``None`` otherwise.
        """
        if self.url:
            return self.url
        if self.sku_id is not None:
            return None
        if self.message is None:
            raise TypeError('Button is not attached to a message')

        message = self.message
        await _wrapped_interaction(
            message._state,
            _generate_nonce(),
            InteractionType.component,
            None,
            message.channel,  # type: ignore # channel is always correct here
            self.to_interaction_dict(),
            message=message,
        )
        return None


class SelectMenu(Component):
    """Represents a select menu from the Discord Bot UI Kit.

    A select menu is functionally the same as a dropdown, however
    on mobile it renders a bit differently.

    Attributes
    ------------
    custom_id: Optional[:class:`str`]
        The ID of the select menu that gets received during an interaction.
    placeholder: Optional[:class:`str`]
        The placeholder text that is shown if nothing is selected, if any.
    min_values: :class:`int`
        The minimum number of items that must be chosen for this select menu.
        Defaults to 1 and must be between 0 and 25.
    max_values: :class:`int`
        The maximum number of items that must be chosen for this select menu.
        Defaults to 1 and must be between 1 and 25.
    options: List[:class:`SelectOption`]
        A list of options that can be selected in this menu.
    disabled: :class:`bool`
        Whether the select is disabled or not.
    channel_types: List[:class:`ChannelType`]
        A list of channel types that are allowed to be chosen in this select menu.
    default_values: List[:class:`SelectDefaultValue`]
        A list of default values for auto-populated select menus.
    id: Optional[:class:`int`]
        The ID of this component.
    required: :class:`bool`
        Whether the select is required. Only applicable within modals.
    """

    __slots__ = (
        '_type',
        'custom_id',
        'placeholder',
        'min_values',
        'max_values',
        'options',
        'disabled',
        'channel_types',
        'default_values',
        'required',
        '_values',
        'id',
        'message',
    )
    __repr_info__: ClassVar[Tuple[str, ...]] = (
        'type',
        'custom_id',
        'placeholder',
        'min_values',
        'max_values',
        'options',
        'disabled',
        'channel_types',
        'default_values',
        'required',
        'id',
    )

    def __init__(self, data: SelectMenuPayload, message: ComponentWithMessage = MISSING):
        self.message = None if message is MISSING else message
        self.id = data.get('id')
        self._type: ComponentType = try_enum(ComponentType, data['type'])
        self.custom_id: str = data['custom_id']
        self.placeholder: Optional[str] = data.get('placeholder')
        self.min_values: int = data.get('min_values', 1)
        self.max_values: int = data.get('max_values', 1)
        self.options: List[SelectOption] = [SelectOption.from_dict(option) for option in data.get('options', [])]
        self.disabled: bool = data.get('disabled', False)
        self.channel_types: List[ChannelType] = [try_enum(ChannelType, t) for t in data.get('channel_types', [])]
        self.default_values: List[SelectDefaultValue] = [
            SelectDefaultValue.from_dict(value) for value in data.get('default_values', [])
        ]
        self.required: bool = data.get('required', True)

    @property
    def type(self) -> ComponentType:
        """:class:`ComponentType`: The concrete select component type."""
        return self._type

    @property
    def values(self) -> List[SelectOption]:
        """List[:class:`SelectOption`]: The options currently selected for modal submission.
        Defaults to the options selected by default.

        This can be set to change the answer to the select menu.
        """
        try:
            return self._values
        except AttributeError:
            return [option for option in self.options if option.default]

    @values.setter
    def values(self, values: Iterable[SelectOption]) -> None:
        values = list(values)
        BaseOption._validate_options(self.options, values, 'values')
        self._validate_answer_count(len(values), self.min_values, self.max_values, self.required, 'values')
        self._values = values

    def answer(self, *values: SelectOption) -> None:
        """Answers this select menu for modal submission.

        Parameters
        ----------
        \\*values: :class:`SelectOption`
            The options to select.

        Raises
        -------
        ValueError
            The number of selected options is outside the select menu's allowed range.
        """
        self.values = values

    def to_interaction_dict(self, options: Optional[Tuple[SelectOption, ...]] = None) -> SelectInteractionData:
        selected = list(options) if options else []
        BaseOption._validate_options(self.options, selected, 'options')
        self._validate_answer_count(len(selected), self.min_values, self.max_values, self.required, 'options')
        values = [option.value for option in selected]
        payload: SelectInteractionData = {
            'component_type': self.type.value,  # type: ignore[typeddict-item]
            'custom_id': self.custom_id,
            'values': values,
        }
        return payload

    def to_dict(self) -> SelectMenuPayload:
        payload: SelectMenuPayload = {
            'type': self.type.value,  # type: ignore
            'custom_id': self.custom_id,
            'min_values': self.min_values,
            'max_values': self.max_values,
            'disabled': self.disabled,
        }
        if self.id is not None:
            payload['id'] = self.id
        if self.placeholder:
            payload['placeholder'] = self.placeholder
        if self.required is not True:
            payload['required'] = self.required
        if self.options:
            payload['options'] = [option.to_dict() for option in self.options]
        if self.channel_types:
            payload['channel_types'] = [channel_type.value for channel_type in self.channel_types]
        if self.default_values:
            payload['default_values'] = [value.to_dict() for value in self.default_values]
        return payload

    def to_submit_dict(
        self,
        files: Optional[List[_FileBase]] = None,
        attachments: Optional[List[PartialAttachmentPayload]] = None,
    ) -> Any:
        values = [option.value for option in self.values]
        return {
            'type': self.type.value,
            'custom_id': self.custom_id,
            'values': values,
        }

    async def choose(self, *options: SelectOption) -> None:
        """|coro|

        Chooses the given options from the select menu.

        If this select menu belongs to a modal, this calls :func:`answer` to
        record the selected values for later submission instead of creating an interaction.

        .. versionchanged:: 2.2

            This no longer returns the created interaction.

        Parameters
        ----------
        \\*options: :class:`SelectOption`
            The options to choose.

        Raises
        -------
        ValueError
            The number of selected options is outside the select menu's allowed
            range when answering a modal select.
        NotFound
            The originating message was not found.
        HTTPException
            Choosing the options failed.
        """
        if self.message is None:
            self.answer(*options)
            return

        message = self.message
        await _wrapped_interaction(
            message._state,
            _generate_nonce(),
            InteractionType.component,
            None,
            message.channel,  # type: ignore # channel is always correct here
            self.to_interaction_dict(options),
            message=message,
        )


class SelectOption(BaseOption):
    """Represents an option in a string select menu.

    Attributes
    ----------
    label: :class:`str`
        The displayed option label.
    value: :class:`str`
        The submitted option value.
    description: Optional[:class:`str`]
        Additional option text.
    default: :class:`bool`
        Whether this option is selected by default.
    """

    __slots__ = BaseOption.__slots__ + ('_emoji',)
    __repr_info__ = BaseOption.__repr_info__ + ('emoji',)

    def __init__(
        self,
        *,
        label: str,
        value: str = MISSING,
        description: Optional[str] = None,
        emoji: Optional[Union[str, Emoji, PartialEmoji]] = None,
        default: bool = False,
    ) -> None:
        super().__init__(label=label, value=value, description=description, default=default)
        self.emoji = emoji

    def __str__(self) -> str:
        base = f'{self.emoji} {self.label}' if self.emoji else self.label
        if self.description:
            return f'{base}\n{self.description}'
        return base

    @property
    def emoji(self) -> Optional[PartialEmoji]:
        """Optional[:class:`.PartialEmoji`]: The emoji of the option, if available."""
        return self._emoji

    @emoji.setter
    def emoji(self, value: Optional[Union[str, Emoji, PartialEmoji]]) -> None:
        if value is None:
            self._emoji = None
        elif isinstance(value, str):
            self._emoji = PartialEmoji.from_str(value)
        elif isinstance(value, _EmojiTag):
            self._emoji = value._to_partial()
        else:
            raise TypeError(f'expected emoji to be str, Emoji, or PartialEmoji not {value.__class__}')

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

    def to_dict(self) -> SelectOptionPayload:
        payload: SelectOptionPayload = super().to_dict()  # type: ignore
        if self.emoji:
            payload['emoji'] = self.emoji.to_dict()
        return payload


class TextInput(Component):
    """Represents a text input from the Discord Bot UI Kit.

    Attributes
    ------------
    custom_id: :class:`str`
        The ID of the text input that gets received during an interaction.
    label: Optional[:class:`str`]
        The label to display above the text input.
    style: :class:`TextStyle`
        The style of the text input.
    placeholder: Optional[:class:`str`]
        The placeholder text to display when the text input is empty.
    default: Optional[:class:`str`]
        The default value of the text input.
    required: :class:`bool`
        Whether the text input is required.
    min_length: Optional[:class:`int`]
        The minimum length of the text input.
    max_length: Optional[:class:`int`]
        The maximum length of the text input.
    id: Optional[:class:`int`]
        The ID of this component.
    """

    __slots__ = (
        'style',
        'label',
        'custom_id',
        'placeholder',
        'default',
        '_answer',
        'required',
        'min_length',
        'max_length',
        'id',
        'message',
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
        'id',
    )

    def __init__(self, data: TextInputPayload, message: ComponentWithMessage = MISSING) -> None:
        self.message = None if message is MISSING else message
        self.id = data.get('id')
        self.style: TextStyle = try_enum(TextStyle, data['style'])
        self.label: Optional[str] = data.get('label')
        self.custom_id: str = data['custom_id']
        self.placeholder: Optional[str] = data.get('placeholder')
        self.default: Optional[str] = data.get('value')
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
        return getattr(self, '_answer', self.default)

    @value.setter
    def value(self, value: Optional[str]) -> None:
        if value is not None and (value or self.required):
            if self.min_length is not None and len(value) < self.min_length:
                raise ValueError(f'value must be at least {self.min_length} characters long')
            if self.max_length is not None and len(value) > self.max_length:
                raise ValueError(f'value must be at most {self.max_length} characters long')
        self._answer = value

    def answer(self, value: Optional[str], /) -> None:
        """Answers this text input for modal submission.

        Parameters
        ----------
        value: Optional[:class:`str`]
            The value to submit.
        """
        self.value = value

    def to_dict(self) -> TextInputPayload:
        payload: TextInputPayload = {
            'type': self.type.value,
            'custom_id': self.custom_id,
            'style': self.style.value,
            'label': self.label,
            'required': self.required,
        }
        if self.id is not None:
            payload['id'] = self.id
        if self.placeholder:
            payload['placeholder'] = self.placeholder
        if self.default:
            payload['value'] = self.default
        if self.min_length is not None:
            payload['min_length'] = self.min_length
        if self.max_length is not None:
            payload['max_length'] = self.max_length
        return payload

    def to_submit_dict(
        self,
        files: Optional[List[_FileBase]] = None,
        attachments: Optional[List[PartialAttachmentPayload]] = None,
    ) -> TextInputPayload:
        value = self.value
        if self.required and not value:
            raise ValueError('value is required')

        payload = {
            'type': self.type.value,
            'custom_id': self.custom_id,
            'value': value or '',
        }
        if self.id is not None:
            payload['id'] = self.id
        return payload  # type: ignore


class SelectDefaultValue:
    """Represents a select menu's default value.

    .. versionadded:: 2.2
    """

    def __init__(self, *, id: int, type: SelectDefaultValueType) -> None:
        self.id = id
        self.type = type

    @property
    def type(self) -> SelectDefaultValueType:
        """:class:`SelectDefaultValueType`: The type of value that ``id`` represents."""
        return self._type

    @type.setter
    def type(self, value: SelectDefaultValueType) -> None:
        if not isinstance(value, SelectDefaultValueType):
            raise TypeError(f'expected SelectDefaultValueType, received {value.__class__.__name__} instead')
        self._type = value

    def __repr__(self) -> str:
        return f'<SelectDefaultValue id={self.id!r} type={self.type!r}>'

    @classmethod
    def from_dict(cls, data: SelectDefaultValuesPayload) -> SelectDefaultValue:
        return cls(id=int(data['id']), type=try_enum(SelectDefaultValueType, data['type']))

    def to_dict(self) -> SelectDefaultValuesPayload:
        return {'id': self.id, 'type': self.type.value}

    @classmethod
    def from_channel(cls, channel: Snowflake, /) -> Self:
        """Creates a :class:`SelectDefaultValue` with the type set to :attr:`~SelectDefaultValueType.channel`.

        Parameters
        -----------
        channel: :class:`~selfcord.abc.Snowflake`
            The channel to create the default value for.

        Returns
        --------
        :class:`SelectDefaultValue`
            The default value created with the channel.
        """
        return cls(id=channel.id, type=SelectDefaultValueType.channel)

    @classmethod
    def from_role(cls, role: Snowflake, /) -> Self:
        """Creates a :class:`SelectDefaultValue` with the type set to :attr:`~SelectDefaultValueType.role`.

        Parameters
        -----------
        role: :class:`~selfcord.abc.Snowflake`
            The role to create the default value for.

        Returns
        --------
        :class:`SelectDefaultValue`
            The default value created with the role.
        """
        return cls(id=role.id, type=SelectDefaultValueType.role)

    @classmethod
    def from_user(cls, user: Snowflake, /) -> Self:
        """Creates a :class:`SelectDefaultValue` with the type set to :attr:`~SelectDefaultValueType.user`.

        Parameters
        -----------
        user: :class:`~selfcord.abc.Snowflake`
            The user to create the default value for.

        Returns
        --------
        :class:`SelectDefaultValue`
            The default value created with the user.
        """
        return cls(id=user.id, type=SelectDefaultValueType.user)


class SectionComponent(Component):
    """Represents a Components v2 section component.

    Sections contain text display children and a single accessory component,
    such as a button or thumbnail.

    Attributes
    ----------
    children: List[:class:`Component`]
        The section's text display children.
    accessory: :class:`Component`
        The accessory component.
    id: Optional[:class:`int`]
        The component ID, if Discord provided one.
    """

    __slots__ = ('children', 'accessory', 'id', 'message')
    __repr_info__ = ('children', 'accessory', 'id')

    def __init__(self, data: SectionComponentPayload, message: ComponentWithMessage = MISSING) -> None:
        self.message = None if message is MISSING else message
        self.id = data.get('id')
        self.children: List[Component] = []
        self.accessory: Component = _component_factory(data['accessory'], message)  # type: ignore[assignment]
        for component_data in data['components']:
            component = _component_factory(component_data, message)
            if component is not None:
                self.children.append(component)

    @property
    def type(self) -> Literal[ComponentType.section]:
        return ComponentType.section

    def to_dict(self) -> SectionComponentPayload:
        payload = {
            'type': self.type.value,
            'components': [component.to_dict() for component in self.children],
            'accessory': self.accessory.to_dict(),
        }
        if self.id is not None:
            payload['id'] = self.id
        return payload  # type: ignore[return-value]


class TextDisplay(Component):
    """Represents a Components v2 text display component.

    Attributes
    ----------
    content: :class:`str`
        The displayed markdown text.
    id: Optional[:class:`int`]
        The component ID, if Discord provided one.
    """

    __slots__ = ('content', 'id', 'message')
    __repr_info__ = ('content', 'id')

    def __init__(self, data: TextComponentPayload, message: ComponentWithMessage = MISSING) -> None:
        self.message = None if message is MISSING else message
        self.id = data.get('id')
        self.content = data['content']

    @property
    def type(self) -> Literal[ComponentType.text_display]:
        return ComponentType.text_display

    def to_dict(self) -> TextComponentPayload:
        payload = {'type': self.type.value, 'content': self.content}
        if self.id is not None:
            payload['id'] = self.id
        return payload  # type: ignore

    def to_submit_dict(
        self,
        files: Optional[List[_FileBase]] = None,
        attachments: Optional[List[PartialAttachmentPayload]] = None,
    ) -> TextComponentPayload:
        return self.to_dict()


class UnfurledMediaItem(AssetMixin):
    """Represents an unfurled media item.

    .. versionadded:: 2.2

    Parameters
    ----------
    url: :class:`str`
        The URL of this media item. This can be an arbitrary URL or a reference
        to a local file uploaded as an attachment within the message, which can
        be accessed with the ``attachment://<filename>`` format.

    Attributes
    ----------
    url: :class:`str`
        The media URL.
    proxy_url: Optional[:class:`str`]
        Discord's proxied URL, if present.
    height: Optional[:class:`int`]
        The media height in pixels.
    width: Optional[:class:`int`]
        The media width in pixels.
    content_type: Optional[:class:`str`]
        The media content type.
    placeholder: Optional[:class:`str`]
        A placeholder representation, if present.
    loading_state: Optional[:class:`MediaItemLoadingState`]
        The loading state reported by Discord.
    attachment_id: Optional[:class:`int`]
        The backing attachment ID for attachment-backed media.
    """

    __slots__ = (
        'url',
        'proxy_url',
        'height',
        'width',
        'content_type',
        '_flags',
        'placeholder',
        'loading_state',
        'attachment_id',
        '_state',
    )

    def __init__(self, url: str) -> None:
        self.url = url
        self.proxy_url: Optional[str] = None
        self.height: Optional[int] = None
        self.width: Optional[int] = None
        self.content_type: Optional[str] = None
        self.placeholder: Optional[str] = None
        self.loading_state: Optional[MediaItemLoadingState] = None
        self.attachment_id: Optional[int] = None
        self._flags = 0
        self._state = None

    @property
    def flags(self) -> AttachmentFlags:
        """:class:`AttachmentFlags`: This media item's flags."""
        return AttachmentFlags._from_value(self._flags)

    def __repr__(self) -> str:
        return f'<UnfurledMediaItem url={self.url!r}>'

    @classmethod
    def _from_data(cls, data: UnfurledMediaItemPayload, state: Optional[ConnectionState] = None) -> UnfurledMediaItem:
        self = cls(data['url'])
        self.proxy_url = data.get('proxy_url')
        self.height = data.get('height')
        self.width = data.get('width')
        self.content_type = data.get('content_type')
        self.placeholder = data.get('placeholder')
        loading_state = data.get('loading_state')
        if loading_state is not None:
            self.loading_state = try_enum(MediaItemLoadingState, loading_state)
        self.attachment_id = _get_as_snowflake(data, 'attachment_id')
        self._flags = data.get('flags', 0)
        self._state = state
        return self

    def to_dict(self) -> UnfurledMediaItemPayload:
        payload: UnfurledMediaItemPayload = {'url': self.url}
        if self.proxy_url:
            payload['proxy_url'] = self.proxy_url
        if self.height is not None:
            payload['height'] = self.height
        if self.width is not None:
            payload['width'] = self.width
        if self.content_type:
            payload['content_type'] = self.content_type
        if self.placeholder:
            payload['placeholder'] = self.placeholder
        if self.loading_state is not None:
            payload['loading_state'] = self.loading_state.value
        if self.attachment_id is not None:
            payload['attachment_id'] = self.attachment_id
        if self._flags:
            payload['flags'] = self._flags
        return payload


class ThumbnailComponent(Component):
    """Represents a Thumbnail from the Discord Bot UI Kit.

    This inherits from :class:`Component`.

    .. versionadded:: 2.2

    Attributes
    ----------
    media: :class:`UnfurledMediaItem`
        The media for this thumbnail.
    description: Optional[:class:`str`]
        The description shown within this thumbnail.
    spoiler: :class:`bool`
        Whether this thumbnail is flagged as a spoiler.
    id: Optional[:class:`int`]
        The ID of this component.
    """

    __slots__ = ('media', 'description', 'spoiler', 'id', 'message')
    __repr_info__ = ('media', 'description', 'spoiler', 'id')

    def __init__(self, data: ThumbnailComponentPayload, message: ComponentWithMessage = MISSING) -> None:
        self.message = None if message is MISSING else message
        self.id = data.get('id')
        self.media = UnfurledMediaItem._from_data(data['media'], getattr(self.message, '_state', None))
        self.description = data.get('description')
        self.spoiler = data.get('spoiler', False)

    @property
    def type(self) -> Literal[ComponentType.thumbnail]:
        return ComponentType.thumbnail

    def to_dict(self) -> ThumbnailComponentPayload:
        payload = {'type': self.type.value, 'media': self.media.to_dict(), 'spoiler': self.spoiler}
        if self.description:
            payload['description'] = self.description
        if self.id is not None:
            payload['id'] = self.id
        return payload  # type: ignore


class MediaGalleryItem:
    """Represents a :class:`MediaGalleryComponent` media item.

    .. versionadded:: 2.2

    Parameters
    ----------
    media: Union[:class:`str`, :class:`selfcord.File`, :class:`UnfurledMediaItem`]
        The media item data. This can be a string representing a local
        file uploaded as an attachment in the message, which can be accessed
        using the ``attachment://<filename>`` format, or an arbitrary URL.
    description: Optional[:class:`str`]
        The description to show within this item. Up to 256 characters.
    spoiler: :class:`bool`
        Whether this item should be flagged as a spoiler.

    Attributes
    ----------
    media: :class:`UnfurledMediaItem`
        The gallery item's media.
    description: Optional[:class:`str`]
        The item description.
    spoiler: :class:`bool`
        Whether the item is marked as a spoiler.
    """

    __slots__ = ('_media', 'description', 'spoiler')

    def __init__(
        self,
        media: Union[str, File, UnfurledMediaItem],
        *,
        description: Optional[str] = MISSING,
        spoiler: bool = MISSING,
    ) -> None:
        self.media = media

        if isinstance(media, File):
            if description is MISSING:
                description = media.description
            if spoiler is MISSING:
                spoiler = media.spoiler

        self.description: Optional[str] = None if description is MISSING else description
        self.spoiler: bool = bool(spoiler)

    def __repr__(self) -> str:
        return f'<MediaGalleryItem media={self.media!r}>'

    @property
    def media(self) -> UnfurledMediaItem:
        """:class:`UnfurledMediaItem`: This item's media data."""
        return self._media

    @media.setter
    def media(self, value: Union[str, File, UnfurledMediaItem]) -> None:
        if isinstance(value, str):
            self._media = UnfurledMediaItem(value)
        elif isinstance(value, UnfurledMediaItem):
            self._media = value
        elif isinstance(value, File):
            self._media = UnfurledMediaItem(f'attachment://{value.filename}')
        else:
            raise TypeError(f'Expected a str or UnfurledMediaItem, not {value.__class__.__name__}')

    @classmethod
    def _from_data(cls, data: MediaGalleryItemPayload) -> MediaGalleryItem:
        self = cls(
            UnfurledMediaItem._from_data(data['media']),
            description=data.get('description'),
            spoiler=data.get('spoiler', False),
        )
        return self

    @classmethod
    def _from_gallery(
        cls,
        items: List[MediaGalleryItemPayload],
    ) -> List[MediaGalleryItem]:
        return [cls._from_data(item) for item in items]

    def to_dict(self) -> MediaGalleryItemPayload:
        payload: MediaGalleryItemPayload = {'media': self.media.to_dict(), 'spoiler': self.spoiler}
        if self.description:
            payload['description'] = self.description
        return payload


class MediaGalleryComponent(Component):
    """Represents a Media Gallery component from the Discord Bot UI Kit.

    This inherits from :class:`Component`.

    .. versionadded:: 2.2

    Attributes
    ----------
    items: List[:class:`MediaGalleryItem`]
        The items this gallery has.
    id: Optional[:class:`int`]
        The ID of this component.
    """

    __slots__ = ('items', 'id', 'message')
    __repr_info__ = ('items', 'id')

    def __init__(self, data: MediaGalleryComponentPayload, message: ComponentWithMessage = MISSING) -> None:
        self.message = None if message is MISSING else message
        self.id = data.get('id')
        self.items = MediaGalleryItem._from_gallery(data['items'])

    @property
    def type(self) -> Literal[ComponentType.media_gallery]:
        return ComponentType.media_gallery

    def to_dict(self) -> MediaGalleryComponentPayload:
        payload = {'type': self.type.value, 'items': [item.to_dict() for item in self.items]}
        if self.id is not None:
            payload['id'] = self.id
        return payload  # type: ignore


class FileComponent(Component):
    """Represents a File component from the Discord Bot UI Kit.

    This inherits from :class:`Component`.

    .. versionadded:: 2.2

    Attributes
    ----------
    media: :class:`UnfurledMediaItem`
        The unfurled attachment contents of the file.
    spoiler: :class:`bool`
        Whether the file is marked as a spoiler.
    id: Optional[:class:`int`]
        The ID of this component.
    name: Optional[:class:`str`]
        The displayed file name, only available when received from the API.
    size: Optional[:class:`int`]
        The file size in MiB, only available when received from the API.
    """

    __slots__ = ('media', 'spoiler', 'name', 'size', 'id', 'message')
    __repr_info__ = ('media', 'spoiler', 'name', 'size', 'id')

    def __init__(self, data: FileComponentPayload, message: ComponentWithMessage = MISSING) -> None:
        self.message = None if message is MISSING else message
        self.id = data.get('id')
        self.media = UnfurledMediaItem._from_data(data['file'], getattr(self.message, '_state', None))
        self.spoiler = data.get('spoiler', False)
        self.name = data.get('name')
        self.size = data.get('size')

    @property
    def type(self) -> Literal[ComponentType.file]:
        return ComponentType.file

    def to_dict(self) -> FileComponentPayload:
        payload = {'type': self.type.value, 'file': self.media.to_dict(), 'spoiler': self.spoiler}
        if self.id is not None:
            payload['id'] = self.id
        if self.name:
            payload['name'] = self.name
        if self.size is not None:
            payload['size'] = self.size
        return payload  # type: ignore


class SeparatorComponent(Component):
    """Represents a Separator from the Discord Bot UI Kit.

    This inherits from :class:`Component`.

    .. versionadded:: 2.2

    Attributes
    ----------
    spacing: :class:`SeparatorSpacing`
        The spacing size of the separator.
    visible: :class:`bool`
        Whether this separator is visible and shows a divider.
    id: Optional[:class:`int`]
        The ID of this component.
    """

    __slots__ = ('spacing', 'visible', 'id', 'message')
    __repr_info__ = ('spacing', 'visible', 'id')

    def __init__(self, data: SeparatorComponentPayload, message: ComponentWithMessage = MISSING) -> None:
        self.message = None if message is MISSING else message
        self.id = data.get('id')
        self.spacing = try_enum(SeparatorSpacing, data.get('spacing', 1))
        self.visible = data.get('divider', True)

    @property
    def type(self) -> Literal[ComponentType.separator]:
        return ComponentType.separator

    def to_dict(self) -> SeparatorComponentPayload:
        payload = {'type': self.type.value, 'divider': self.visible, 'spacing': self.spacing.value}
        if self.id is not None:
            payload['id'] = self.id
        return payload  # type: ignore


class Container(Component):
    """Represents a Container from the Discord Bot UI Kit.

    This inherits from :class:`Component`.

    .. versionadded:: 2.2

    Attributes
    ----------
    children: :class:`Component`
        This container's children.
    spoiler: :class:`bool`
        Whether this container is flagged as a spoiler.
    id: Optional[:class:`int`]
        The ID of this component.
    """

    __slots__ = ('children', 'spoiler', '_colour', 'id', 'message')
    __repr_info__ = ('children', 'spoiler', 'accent_colour', 'id')

    def __init__(self, data: ContainerComponentPayload, message: ComponentWithMessage = MISSING) -> None:
        self.message = None if message is MISSING else message
        self.id = data.get('id')
        self.children: List[Component] = []
        for child in data['components']:
            component = _component_factory(child, message)
            if component is not None:
                self.children.append(component)
        self.spoiler = data.get('spoiler', False)
        colour = data.get('accent_color')
        self._colour = Colour(colour) if colour is not None else None

    @property
    def accent_colour(self) -> Optional[Colour]:
        """Optional[:class:`Colour`]: The container's accent colour."""
        return self._colour

    accent_color = accent_colour

    @property
    def type(self) -> Literal[ComponentType.container]:
        return ComponentType.container

    def to_dict(self) -> ContainerComponentPayload:
        payload = {
            'type': self.type.value,
            'spoiler': self.spoiler,
            'components': [child.to_dict() for child in self.children],
        }
        if self.id is not None:
            payload['id'] = self.id
        if self._colour is not None:
            payload['accent_color'] = self._colour.value
        return payload  # type: ignore


class LabelComponent(Component):
    """Represents a label component from the Discord Bot UI Kit.

    This inherits from :class:`Component`.

    .. versionadded:: 2.2

    Attributes
    ----------
    label: :class:`str`
        The label text to display.
    description: Optional[:class:`str`]
        The description text to display below the label, if any.
    component: :class:`Component`
        The component that this label is associated with.
    id: Optional[:class:`int`]
        The ID of this component.
    """

    __slots__ = ('label', 'description', 'component', 'id', 'message')
    __repr_info__ = ('label', 'description', 'component', 'id')

    def __init__(self, data: LabelComponentPayload, message: ComponentWithMessage = MISSING) -> None:
        self.message = None if message is MISSING else message
        self.id = data.get('id')
        self.label = data['label']
        self.description = data.get('description')
        self.component: Component = _component_factory(data['component'], message)  # type: ignore

    @property
    def type(self) -> Literal[ComponentType.label]:
        return ComponentType.label

    def to_dict(self) -> LabelComponentPayload:
        payload = {'type': self.type.value, 'label': self.label, 'component': self.component.to_dict()}
        if self.description:
            payload['description'] = self.description
        if self.id is not None:
            payload['id'] = self.id
        return payload  # type: ignore

    def to_submit_dict(
        self,
        files: Optional[List[_FileBase]] = None,
        attachments: Optional[List[PartialAttachmentPayload]] = None,
    ) -> LabelComponentPayload:
        payload = {'type': self.type.value, 'component': self.component.to_submit_dict(files, attachments)}
        if self.id is not None:
            payload['id'] = self.id
        return payload  # type: ignore


class FileUploadComponent(Component):
    """Represents a file upload component from the Discord Bot UI Kit.

    This inherits from :class:`Component`.

    .. versionadded:: 2.2

    Attributes
    ------------
    custom_id: Optional[:class:`str`]
        The ID of the component that gets received during an interaction.
    min_values: :class:`int`
        The minimum number of files that must be uploaded for this component.
        Defaults to 0 and must be between 0 and 10.
    max_values: :class:`int`
        The maximum number of files that must be uploaded for this component.
        Defaults to 10 and must be between 1 and 10.
    id: Optional[:class:`int`]
        The ID of this component.
    required: :class:`bool`
        Whether the component is required.
        Defaults to ``False``.
    """

    __slots__ = ('custom_id', 'min_values', 'max_values', 'required', '_values', 'id', 'message')
    __repr_info__ = ('custom_id', 'min_values', 'max_values', 'required', 'id')

    def __init__(self, data: FileUploadComponentPayload, message: ComponentWithMessage = MISSING) -> None:
        self.message = None if message is MISSING else message
        self.id = data.get('id')
        self.custom_id = data['custom_id']
        self.min_values = data.get('min_values', 0)
        self.max_values = data.get('max_values', 10)
        self.required = data.get('required', False)
        self._values: List[Union[File, CloudFile]] = []

    @property
    def type(self) -> Literal[ComponentType.file_upload]:
        """:class:`ComponentType`: The type of component."""
        return ComponentType.file_upload

    @property
    def values(self) -> List[Union[File, CloudFile]]:
        """List[Union[:class:`File`, :class:`CloudFile`]]: The files selected for modal submission.

        This can be set to change the answer to the file upload.
        """
        return self._values

    @values.setter
    def values(self, values: Iterable[Union[File, CloudFile]]) -> None:
        values = list(values)
        if any(not isinstance(value, _FileBase) for value in values):
            raise TypeError('values must be File or CloudFile')

        self._validate_answer_count(len(values), self.min_values, self.max_values, self.required, 'values')
        self._values = values

    def answer(self, *files: Union[File, CloudFile]) -> None:
        """Answers this file upload for modal submission.

        Parameters
        ----------
        \\*files: Union[:class:`File`, :class:`CloudFile`]
            The files to submit.

        Raises
        -------
        TypeError
            A value is not a :class:`File` or :class:`CloudFile`.
        ValueError
            The number of selected files is outside the component's allowed range.
        """
        self.values = files

    def to_dict(self) -> FileUploadComponentPayload:
        payload = {
            'type': self.type.value,
            'custom_id': self.custom_id,
            'min_values': self.min_values,
            'max_values': self.max_values,
            'required': self.required,
        }
        if self.id is not None:
            payload['id'] = self.id
        return payload  # type: ignore

    def to_submit_dict(
        self,
        files: Optional[List[_FileBase]] = None,
        attachments: Optional[List[PartialAttachmentPayload]] = None,
    ) -> FileUploadComponentPayload:
        if self.values and (files is None or attachments is None):
            raise TypeError('File uploads can only be serialized during modal submission')

        values: List[str] = []
        if files is not None and attachments is not None:
            for file in self.values:
                index = len(attachments)
                attachments.append(file.to_dict(index))
                files.append(file)
                values.append(str(index))

        payload = {'type': self.type.value, 'custom_id': self.custom_id, 'values': values}
        if self.id is not None:
            payload['id'] = self.id
        return payload  # type: ignore


class RadioGroupComponent(Component):
    """Represents a radio group component from the Discord Bot UI Kit.

    This inherits from :class:`Component`.

    .. versionadded:: 2.2

    Attributes
    ------------
    custom_id: Optional[:class:`str`]
        The ID of the component that gets received during an interaction.
    id: Optional[:class:`int`]
        The ID of this component.
    required: :class:`bool`
        Whether the component is required.
        Defaults to ``True``.
    options: List[:class:`RadioGroupOption`]
        A list of options that can be selected in this group.
    """

    __slots__ = ('custom_id', 'required', 'options', '_value', 'id', 'message')
    __repr_info__ = ('custom_id', 'required', 'options', 'id')

    def __init__(self, data: RadioGroupComponentPayload, message: ComponentWithMessage = MISSING) -> None:
        self.message = None if message is MISSING else message
        self.id = data.get('id')
        self.custom_id = data['custom_id']
        self.required = data.get('required', True)
        self.options: List[RadioGroupOption] = [RadioGroupOption.from_dict(option) for option in data.get('options', [])]

    @property
    def type(self) -> Literal[ComponentType.radio_group]:
        """:class:`ComponentType`: The type of component."""
        return ComponentType.radio_group

    @property
    def value(self) -> Optional[RadioGroupOption]:
        """Optional[:class:`RadioGroupOption`]: The selected option for modal submission.
        Defaults to the option selected by default.

        This can be set to change the answer to the radio group.
        """
        try:
            return self._value
        except AttributeError:
            return next((option for option in self.options if option.default), None)

    @value.setter
    def value(self, value: Optional[RadioGroupOption]) -> None:
        if value is None:
            self._value = None
            return

        BaseOption._validate_options(self.options, (value,), 'value')
        self._value = value

    def answer(self, value: Optional[RadioGroupOption]) -> None:
        """Answers this radio group for modal submission.

        Parameters
        ----------
        value: Optional[:class:`RadioGroupOption`]
            The option to select.

        Raises
        -------
        ValueError
            The option does not belong to this component.
        """
        self.value = value

    def to_dict(self) -> RadioGroupComponentPayload:
        payload = {'type': self.type.value, 'custom_id': self.custom_id, 'required': self.required}
        if self.id is not None:
            payload['id'] = self.id
        if self.options:
            payload['options'] = [option.to_dict() for option in self.options]
        return payload  # type: ignore

    def to_submit_dict(
        self,
        files: Optional[List[_FileBase]] = None,
        attachments: Optional[List[PartialAttachmentPayload]] = None,
    ) -> RadioGroupComponentPayload:
        if self.required and self.value is None:
            raise ValueError('value is required')

        payload = {
            'type': self.type.value,
            'custom_id': self.custom_id,
            'value': None if self.value is None else self.value.value,
        }
        if self.id is not None:
            payload['id'] = self.id
        return payload  # type: ignore


class RadioGroupOption(BaseOption):
    """Represents a radio group's option

    .. versionadded:: 2.2

    Attributes
    -----------
    label: :class:`str`
        The label of the option. This is displayed to users.
    value: :class:`str`
        The value of this option. This is not displayed to users.
        If not provided when constructed then it defaults to the
        label.
    description: Optional[:class:`str`]
        An additional description of the option, if any.
    default: :class:`bool`
        Whether this option is selected by default.
    """

    pass


class CheckboxGroupComponent(Component):
    """Represents a checkbox group component from the Discord Bot UI Kit.

    This inherits from :class:`Component`.

    .. versionadded:: 2.2

    Attributes
    ------------
    custom_id: Optional[:class:`str`]
        The ID of the component that gets received during an interaction.
    id: Optional[:class:`int`]
        The ID of this component.
    required: :class:`bool`
        Whether the component is required.
        Defaults to ``True``.
    min_values: :class:`int`
        The minimum number of options that must be selected in this component.
        Must be between 0 and 10. Defaults to 0.
    max_values: :class:`int`
        The maximum number of options that can be selected in this component.
        Must be between 1 and 10. Defaults to 1.
    options: List[:class:`CheckboxGroupOption`]
        A list of options that can be selected in this group.
    """

    __slots__ = ('custom_id', 'required', 'min_values', 'max_values', 'options', '_values', 'id', 'message')
    __repr_info__ = ('custom_id', 'required', 'min_values', 'max_values', 'options', 'id')

    def __init__(self, data: CheckboxGroupComponentPayload, message: ComponentWithMessage = MISSING) -> None:
        self.message = None if message is MISSING else message
        self.id = data.get('id')
        self.custom_id = data['custom_id']
        self.required = data.get('required', True)
        self.min_values = data.get('min_values', 0)
        self.max_values = data.get('max_values', 1)
        self.options: List[CheckboxGroupOption] = [
            CheckboxGroupOption.from_dict(option) for option in data.get('options', [])
        ]

    @property
    def type(self) -> Literal[ComponentType.checkbox_group]:
        """:class:`ComponentType`: The type of component."""
        return ComponentType.checkbox_group

    @property
    def values(self) -> List[CheckboxGroupOption]:
        """List[:class:`CheckboxGroupOption`]: The selected options for modal submission.
        Defaults to the options selected by default.

        This can be set to change the answer to the checkbox group.
        """
        try:
            return self._values
        except AttributeError:
            return [option for option in self.options if option.default]

    @values.setter
    def values(self, values: Iterable[CheckboxGroupOption]) -> None:
        values = list(values)
        BaseOption._validate_options(self.options, values, 'values')
        self._validate_answer_count(len(values), self.min_values, self.max_values, self.required, 'values')
        self._values = values

    def answer(self, *values: CheckboxGroupOption) -> None:
        """Answers this checkbox group for modal submission.

        Parameters
        ----------
        \\*values: :class:`CheckboxGroupOption`
            The options to select.

        Raises
        -------
        ValueError
            The number of selected options is outside the component's allowed range.
        """
        self.values = values

    def to_dict(self) -> CheckboxGroupComponentPayload:
        payload = {
            'type': self.type.value,
            'custom_id': self.custom_id,
            'min_values': self.min_values,
            'max_values': self.max_values,
            'required': self.required,
        }
        if self.id is not None:
            payload['id'] = self.id
        if self.options:
            payload['options'] = [option.to_dict() for option in self.options]
        return payload  # type: ignore

    def to_submit_dict(
        self,
        files: Optional[List[_FileBase]] = None,
        attachments: Optional[List[PartialAttachmentPayload]] = None,
    ) -> CheckboxGroupComponentPayload:
        payload = {
            'type': self.type.value,
            'custom_id': self.custom_id,
            'values': [option.value for option in self.values],
        }
        if self.id is not None:
            payload['id'] = self.id
        return payload  # type: ignore


class CheckboxGroupOption(BaseOption):
    """Represents a checkbox group's option

    .. versionadded:: 2.2

    Attributes
    -----------
    label: :class:`str`
        The label of the option. This is displayed to users.
    value: :class:`str`
        The value of the option. This is not displayed to users.
        If not provided when constructed then it defaults to the
        label.
    description: Optional[:class:`str`]
        An additional description of the option, if any.
    default: :class:`bool`
        Whether this option is selected by default.
    """

    pass


class CheckboxComponent(Component):
    """Represents a checkbox component from the Discord Bot UI Kit.

    This inherits from :class:`Component`.

    .. versionadded:: 2.2

    Attributes
    ------------
    custom_id: Optional[:class:`str`]
        The ID of the component that gets received during an interaction.
    id: Optional[:class:`int`]
        The ID of this component.
    default: :class:`bool`
        Whether this checkbox is selected by default.
    """

    __slots__ = ('custom_id', 'default', '_value', 'id', 'message')
    __repr_info__ = ('custom_id', 'default', 'value', 'id')

    def __init__(self, data: CheckboxComponentPayload, message: ComponentWithMessage = MISSING) -> None:
        self.message = None if message is MISSING else message
        self.id = data.get('id')
        self.custom_id = data['custom_id']
        self.default = data.get('default', False)
        self._value: Optional[bool] = None

    @property
    def type(self) -> Literal[ComponentType.checkbox]:
        """:class:`ComponentType`: The type of component."""
        return ComponentType.checkbox

    @property
    def value(self) -> bool:
        """:class:`bool`: The checked state submitted with the modal. Defaults to :attr:`default`.

        This can be set to change the state of the checkbox.
        """
        return self.default if self._value is None else self._value

    @value.setter
    def value(self, value: bool) -> None:
        self._value = bool(value)

    def answer(self, value: bool) -> None:
        """Answers this checkbox for modal submission.

        Parameters
        ----------
        value: :class:`bool`
            Whether the checkbox should be checked.
        """
        self.value = value

    def to_dict(self) -> CheckboxComponentPayload:
        payload = {'type': self.type.value, 'custom_id': self.custom_id, 'default': self.default}
        if self.id is not None:
            payload['id'] = self.id
        return payload  # type: ignore

    def to_submit_dict(
        self,
        files: Optional[List[_FileBase]] = None,
        attachments: Optional[List[PartialAttachmentPayload]] = None,
    ) -> CheckboxComponentPayload:
        payload = {'type': self.type.value, 'custom_id': self.custom_id, 'value': self.value}
        if self.id is not None:
            payload['id'] = self.id
        return payload  # type: ignore


@overload
def _component_factory(data: ActionRowPayload, message: ComponentWithMessage = ...) -> ActionRow: ...


@overload
def _component_factory(
    data: ModalChildComponent, message: ComponentWithMessage = ...
) -> Optional[ModalChildComponentType]: ...


@overload
def _component_factory(
    data: ActionRowChildComponent, message: ComponentWithMessage = ...
) -> Optional[ActionRowChildComponentType]: ...


@overload
def _component_factory(data: ComponentPayload, message: ComponentWithMessage = ...) -> Optional[Component]: ...


def _component_factory(data: ComponentPayload, message: ComponentWithMessage = MISSING) -> Optional[Component]:
    if data['type'] == 1:
        return ActionRow(data, message)
    elif data['type'] == 2:
        return Button(data, message)
    elif data['type'] == 4:
        return TextInput(data, message)
    elif data['type'] in (3, 5, 6, 7, 8):
        return SelectMenu(data, message)  # type: ignore
    elif data['type'] == 9:
        return SectionComponent(data, message)
    elif data['type'] == 10:
        return TextDisplay(data, message)
    elif data['type'] == 11:
        return ThumbnailComponent(data, message)
    elif data['type'] == 12:
        return MediaGalleryComponent(data, message)
    elif data['type'] == 13:
        return FileComponent(data, message)
    elif data['type'] == 14:
        return SeparatorComponent(data, message)
    elif data['type'] == 17:
        return Container(data, message)
    elif data['type'] == 18:
        return LabelComponent(data, message)
    elif data['type'] == 19:
        return FileUploadComponent(data, message)
    elif data['type'] == 21:
        return RadioGroupComponent(data, message)
    elif data['type'] == 22:
        return CheckboxGroupComponent(data, message)
    elif data['type'] == 23:
        return CheckboxComponent(data, message)
    return None

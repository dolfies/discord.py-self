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

import asyncio
import datetime
import re
import io
from os import PathLike
from typing import (
    AsyncIterator,
    Dict,
    Collection,
    TYPE_CHECKING,
    Literal,
    Sequence,
    Union,
    List,
    Optional,
    Any,
    Callable,
    Tuple,
    ClassVar,
    Type,
    overload,
)

from . import utils
from .reaction import Reaction
from .emoji import Emoji
from .partial_emoji import PartialEmoji
from .calls import CallMessage
from .enums import (
    MessageType,
    ChannelType,
    ApplicationCommandType,
    PurchaseNotificationType,
    MessageReferenceType,
    try_enum,
)
from .errors import HTTPException
from .components import _component_factory
from .embeds import Embed
from .member import Member
from .flags import MessageFlags, AttachmentFlags
from .file import File
from .utils import escape_mentions, MISSING
from .http import handle_message_parameters
from .guild import Guild
from .mixins import Hashable
from .sticker import StickerItem, GuildSticker
from .threads import Thread
from .channel import PartialMessageable
from .interactions import Interaction
from .commands import MessageCommand
from .abc import _handle_commands
from .application import IntegrationApplication, PartialApplication
from .poll import Poll

if TYPE_CHECKING:
    from typing_extensions import Self

    from .types.message import (
        Message as MessagePayload,
        Attachment as AttachmentPayload,
        BaseApplication as MessageApplicationPayload,
        Call as CallPayload,
        MessageReference as MessageReferencePayload,
        MessageSnapshot as MessageSnapshotPayload,
        MessageActivity as MessageActivityPayload,
        RoleSubscriptionData as RoleSubscriptionDataPayload,
        MessageSearchResult as MessageSearchResultPayload,
        PurchaseNotificationResponse as PurchaseNotificationResponsePayload,
        GuildProductPurchase as GuildProductPurchasePayload,
    )

    from .types.interactions import MessageInteraction as MessageInteractionPayload

    from .types.components import MessageActionRow as ComponentPayload
    from .types.threads import ThreadArchiveDuration
    from .types.member import (
        Member as MemberPayload,
        UserWithMember as UserWithMemberPayload,
    )
    from .types.user import User as UserPayload
    from .types.embed import Embed as EmbedPayload
    from .types.gateway import MessageReactionRemoveEvent, MessageUpdateEvent
    from .abc import Snowflake
    from .abc import GuildChannel, MessageableChannel
    from .components import ActionRow
    from .file import _FileBase
    from .state import ConnectionState
    from .mentions import AllowedMentions
    from .sticker import GuildSticker
    from .user import User
    from .role import Role

    EmojiInputType = Union[Emoji, PartialEmoji, str]


__all__ = (
    'Attachment',
    'Message',
    'PartialMessage',
    'MessageReference',
    'MessageSnapshot',
    'DeletedReferencedMessage',
    'RoleSubscriptionInfo',
    'GuildProductPurchase',
    'PurchaseNotification',
)


def convert_emoji_reaction(emoji: Union[EmojiInputType, Reaction]) -> str:
    if isinstance(emoji, Reaction):
        emoji = emoji.emoji

    if isinstance(emoji, Emoji):
        return f'{emoji.name}:{emoji.id}'
    if isinstance(emoji, PartialEmoji):
        return emoji._as_reaction()
    if isinstance(emoji, str):
        # Reactions can be in :name:id format, but not <:name:id>
        # Emojis can't have <> in them, so this should be okay
        return emoji.strip('<>')

    raise TypeError(f'emoji argument must be str, Emoji, or Reaction not {emoji.__class__.__name__}.')


class Attachment(Hashable):
    """Represents an attachment from Discord.

    .. container:: operations

        .. describe:: str(x)

            Returns the URL of the attachment.

        .. describe:: x == y

            Checks if the attachment is equal to another attachment.

        .. describe:: x != y

            Checks if the attachment is not equal to another attachment.

        .. describe:: hash(x)

            Returns the hash of the attachment.

    .. versionchanged:: 1.7
        Attachment can now be casted to :class:`str` and is hashable.

    Attributes
    ------------
    id: :class:`int`
        The attachment ID.
    size: :class:`int`
        The attachment size in bytes.
    height: Optional[:class:`int`]
        The attachment's height, in pixels. Only applicable to images and videos.
    width: Optional[:class:`int`]
        The attachment's width, in pixels. Only applicable to images and videos.
    filename: :class:`str`
        The attachment's filename.
    url: :class:`str`
        The attachment URL. If the message this attachment was attached
        to is deleted, then this will 404.
    proxy_url: :class:`str`
        The proxy URL. This is a cached version of the :attr:`~Attachment.url` in the
        case of images.
    content_type: Optional[:class:`str`]
        The attachment's `media type <https://en.wikipedia.org/wiki/Media_type>`_

        .. versionadded:: 1.7
    description: Optional[:class:`str`]
        The attachment's description. Only applicable to images.

        .. versionadded:: 2.0
    ephemeral: :class:`bool`
        Whether the attachment is ephemeral.

        .. versionadded:: 2.0
    duration: Optional[:class:`float`]
        The duration of the audio file in seconds. Returns ``None`` if it's not a voice message.

        .. versionadded:: 2.1
    waveform: Optional[:class:`bytes`]
        The waveform (amplitudes) of the audio in bytes. Returns ``None`` if it's not a voice message.

        .. versionadded:: 2.1
    title: Optional[:class:`str`]
        The normalised version of the attachment's filename.

        .. versionadded:: 2.1
    clip_created_at: Optional[:class:`datetime.datetime`]
        When the clip this attachment represents was created.

        .. versionadded:: 2.1
    clip_participants: List[:class:`User`]
        The participants in the clip this attachment represents.

        .. versionadded:: 2.1
    application: Optional[:class:`PartialApplication`]
        The application of the game this clip was taken from.

        .. versionadded:: 2.1
    """

    __slots__ = (
        'id',
        'size',
        'height',
        'width',
        'filename',
        'url',
        'proxy_url',
        '_http',
        'content_type',
        'description',
        'ephemeral',
        'duration',
        'waveform',
        '_flags',
        'title',
        'clip_created_at',
        'clip_participants',
        'application',
    )

    def __init__(self, *, data: AttachmentPayload, state: ConnectionState):
        self.id: int = int(data['id'])
        self.size: int = data['size']
        self.height: Optional[int] = data.get('height')
        self.width: Optional[int] = data.get('width')
        self.filename: str = data['filename']
        self.url: str = data['url']
        self.proxy_url: str = data['proxy_url']
        self._http = state.http
        self.content_type: Optional[str] = data.get('content_type')
        self.description: Optional[str] = data.get('description')
        self.ephemeral: bool = data.get('ephemeral', False)
        self.duration: Optional[float] = data.get('duration_secs')
        self.title: Optional[str] = data.get('title')
        self.clip_created_at: Optional[datetime.datetime] = utils.parse_time(data.get('clip_created_at'))
        self.clip_participants: List[User] = [state.create_user(d) for d in data.get('clip_participants', [])]
        self.application: Optional[PartialApplication] = (
            PartialApplication(data=data['application'], state=state) if data.get('application') else None  # type: ignore
        )

        waveform = data.get('waveform')
        self.waveform: Optional[bytes] = utils._base64_to_bytes(waveform) if waveform is not None else None

        self._flags: int = data.get('flags', 0)

    @property
    def flags(self) -> AttachmentFlags:
        """:class:`AttachmentFlags`: The attachment's flags."""
        return AttachmentFlags._from_value(self._flags)

    def is_spoiler(self) -> bool:
        """:class:`bool`: Whether this attachment contains a spoiler."""
        # The flag is technically always present but no harm to check both
        return self.filename.startswith('SPOILER_') or self.flags.spoiler

    def is_voice_message(self) -> bool:
        """:class:`bool`: Whether this attachment is a voice message."""
        return self.duration is not None and self.waveform is not None

    def __repr__(self) -> str:
        return f'<Attachment id={self.id} filename={self.filename!r} url={self.url!r}>'

    def __str__(self) -> str:
        return self.url or ''

    async def save(
        self,
        fp: Union[io.BufferedIOBase, PathLike[Any]],
        *,
        seek_begin: bool = True,
        use_cached: bool = False,
    ) -> int:
        """|coro|

        Saves this attachment into a file-like object.

        Parameters
        -----------
        fp: Union[:class:`io.BufferedIOBase`, :class:`os.PathLike`]
            The file-like object to save this attachment to or the filename
            to use. If a filename is passed then a file is created with that
            filename and used instead.
        seek_begin: :class:`bool`
            Whether to seek to the beginning of the file after saving is
            successfully done.
        use_cached: :class:`bool`
            Whether to use :attr:`proxy_url` rather than :attr:`url` when downloading
            the attachment. This will allow attachments to be saved after deletion
            more often, compared to the regular URL which is generally deleted right
            after the message is deleted. Note that this can still fail to download
            deleted attachments if too much time has passed and it does not work
            on some types of attachments.

        Raises
        --------
        HTTPException
            Saving the attachment failed.
        NotFound
            The attachment was deleted.

        Returns
        --------
        :class:`int`
            The number of bytes written.
        """
        data = await self.read(use_cached=use_cached)
        if isinstance(fp, io.BufferedIOBase):
            written = fp.write(data)
            if seek_begin:
                fp.seek(0)
            return written
        else:
            with open(fp, 'wb') as f:
                return f.write(data)

    async def read(self, *, use_cached: bool = False) -> bytes:
        """|coro|

        Retrieves the content of this attachment as a :class:`bytes` object.

        .. versionadded:: 1.1

        Parameters
        -----------
        use_cached: :class:`bool`
            Whether to use :attr:`proxy_url` rather than :attr:`url` when downloading
            the attachment. This will allow attachments to be saved after deletion
            more often, compared to the regular URL which is generally deleted right
            after the message is deleted. Note that this can still fail to download
            deleted attachments if too much time has passed and it does not work
            on some types of attachments.

        Raises
        ------
        HTTPException
            Downloading the attachment failed.
        Forbidden
            You do not have permissions to access this attachment
        NotFound
            The attachment was deleted.

        Returns
        -------
        :class:`bytes`
            The contents of the attachment.
        """
        url = self.proxy_url if use_cached else self.url
        data = await self._http.get_from_cdn(url)
        return data

    async def to_file(
        self,
        *,
        filename: Optional[str] = MISSING,
        description: Optional[str] = MISSING,
        use_cached: bool = False,
        spoiler: bool = False,
    ) -> File:
        """|coro|

        Converts the attachment into a :class:`File` suitable for sending via
        :meth:`abc.Messageable.send`.

        .. versionadded:: 1.3

        Parameters
        -----------
        filename: Optional[:class:`str`]
            The filename to use for the file. If not specified then the filename
            of the attachment is used instead.

            .. versionadded:: 2.0
        description: Optional[:class:`str`]
            The description to use for the file. If not specified then the
            description of the attachment is used instead.

            .. versionadded:: 2.0
        use_cached: :class:`bool`
            Whether to use :attr:`proxy_url` rather than :attr:`url` when downloading
            the attachment. This will allow attachments to be saved after deletion
            more often, compared to the regular URL which is generally deleted right
            after the message is deleted. Note that this can still fail to download
            deleted attachments if too much time has passed and it does not work
            on some types of attachments.

            .. versionadded:: 1.4
        spoiler: :class:`bool`
            Whether the file is a spoiler.

            .. versionadded:: 1.4

        Raises
        ------
        HTTPException
            Downloading the attachment failed.
        Forbidden
            You do not have permissions to access this attachment
        NotFound
            The attachment was deleted.

        Returns
        -------
        :class:`File`
            The attachment as a file suitable for sending.
        """

        data = await self.read(use_cached=use_cached)
        file_filename = filename if filename is not MISSING else self.filename
        file_description = description if description is not MISSING else self.description
        return File(io.BytesIO(data), filename=file_filename, description=file_description, spoiler=spoiler)

    def to_dict(self) -> AttachmentPayload:
        result: AttachmentPayload = {
            'filename': self.filename,
            'flags': self._flags,
            'id': self.id,
            'proxy_url': self.proxy_url,
            'size': self.size,
            'url': self.url,
        }
        if self.height:
            result['height'] = self.height
        if self.width:
            result['width'] = self.width
        if self.content_type:
            result['content_type'] = self.content_type
        if self.description is not None:
            result['description'] = self.description
        if self.title is not None:
            result['title'] = self.title
        return result


class DeletedReferencedMessage:
    """A special sentinel type given when the resolved message reference
    points to a deleted message.

    The purpose of this class is to separate referenced messages that could not be
    fetched and those that were previously fetched but have since been deleted.

    .. versionadded:: 1.6
    """

    __slots__ = ('_parent',)

    def __init__(self, parent: MessageReference):
        self._parent: MessageReference = parent

    def __repr__(self) -> str:
        return f"<DeletedReferencedMessage id={self.id} channel_id={self.channel_id} guild_id={self.guild_id!r}>"

    @property
    def id(self) -> int:
        """:class:`int`: The message ID of the deleted referenced message."""
        # The parent's message id won't be None here
        return self._parent.message_id  # type: ignore

    @property
    def channel_id(self) -> int:
        """:class:`int`: The channel ID of the deleted referenced message."""
        return self._parent.channel_id

    @property
    def guild_id(self) -> Optional[int]:
        """Optional[:class:`int`]: The guild ID of the deleted referenced message."""
        return self._parent.guild_id


class MessageSnapshot(Hashable):
    """Represents a message snapshot attached to a forwarded message.

    .. container:: operations

        .. describe:: x == y

            Checks if the message snapshot is equal to another message snapshot.

        .. describe:: x != y

            Checks if the message snapshot is not equal to another message snapshot.

        .. describe:: hash(x)

            Returns the hash of the message snapshot.

    .. versionadded:: 2.1

    Attributes
    -----------
    id: :class:`int`
        The ID of the forwarded message.
    type: :class:`MessageType`
        The type of the forwarded message.
    content: :class:`str`
        The actual contents of the forwarded message.
    embeds: List[:class:`Embed`]
        A list of embeds the forwarded message has.
    attachments: List[:class:`Attachment`]
        A list of attachments given to the forwarded message.
    created_at: :class:`datetime.datetime`
        The forwarded message's time of creation.
    flags: :class:`MessageFlags`
        Extra features of the the message snapshot.
    stickers: List[:class:`StickerItem`]
        A list of sticker items given to the message.
    components: List[Union[:class:`ActionRow`, :class:`Button`, :class:`SelectMenu`]]
        A list of components in the message.
    """

    __slots__ = (
        '_cs_raw_channel_mentions',
        '_cs_cached_message',
        '_cs_raw_mentions',
        '_cs_raw_role_mentions',
        '_edited_timestamp',
        'id',
        'attachments',
        'content',
        'embeds',
        'flags',
        'created_at',
        'type',
        'stickers',
        'components',
        '_state',
    )

    @classmethod
    def _from_value(
        cls,
        state: ConnectionState,
        message_snapshots: Optional[List[Dict[Literal['message'], MessageSnapshotPayload]]],
        reference: MessageReference,
    ) -> List[Self]:
        if not message_snapshots:
            return []

        return [cls(state, snapshot['message'], reference) for snapshot in message_snapshots]

    def __init__(self, state: ConnectionState, data: MessageSnapshotPayload, reference: MessageReference):
        self.type: MessageType = try_enum(MessageType, data['type'])
        self.id: int = reference.message_id  # type: ignore
        self.content: str = data['content']
        self.embeds: List[Embed] = [Embed.from_dict(a) for a in data['embeds']]
        self.attachments: List[Attachment] = [Attachment(data=a, state=state) for a in data['attachments']]
        self.created_at: datetime.datetime = utils.parse_time(data['timestamp'])
        self._edited_timestamp: Optional[datetime.datetime] = utils.parse_time(data['edited_timestamp'])
        self.flags: MessageFlags = MessageFlags._from_value(data.get('flags', 0))
        self.stickers: List[StickerItem] = [StickerItem(data=d, state=state) for d in data.get('sticker_items', [])]

        self.components: List[ComponentPayload] = []
        for component_data in data.get('components', []):
            component = _component_factory(component_data)
            if component is not None:
                self.components.append(component)  # type: ignore

        self._state: ConnectionState = state

    def __repr__(self) -> str:
        name = self.__class__.__name__
        return f'<{name} type={self.type!r} created_at={self.created_at!r} flags={self.flags!r}>'

    @utils.cached_slot_property('_cs_raw_mentions')
    def raw_mentions(self) -> List[int]:
        """List[:class:`int`]: A property that returns an array of user IDs matched with
        the syntax of ``<@user_id>`` in the message content.

        This allows you to receive the user IDs of mentioned users
        even in a private message context.
        """
        return [int(x) for x in re.findall(r'<@!?([0-9]{15,20})>', self.content)]

    @utils.cached_slot_property('_cs_raw_channel_mentions')
    def raw_channel_mentions(self) -> List[int]:
        """List[:class:`int`]: A property that returns an array of channel IDs matched with
        the syntax of ``<#channel_id>`` in the message content.
        """
        return [int(x) for x in re.findall(r'<#([0-9]{15,20})>', self.content)]

    @utils.cached_slot_property('_cs_raw_role_mentions')
    def raw_role_mentions(self) -> List[int]:
        """List[:class:`int`]: A property that returns an array of role IDs matched with
        the syntax of ``<@&role_id>`` in the message content.
        """
        return [int(x) for x in re.findall(r'<@&([0-9]{15,20})>', self.content)]

    @utils.cached_slot_property('_cs_cached_message')
    def cached_message(self) -> Optional[Message]:
        """Optional[:class:`Message`]: Returns the cached message this snapshot points to, if any."""
        state = self._state
        return (
            utils.find(
                lambda m: m.id == self.id,
                reversed(state._messages),
            )
            if state._messages
            else None
        )

    @property
    def edited_at(self) -> Optional[datetime.datetime]:
        """Optional[:class:`datetime.datetime`]: An aware UTC datetime object containing the edited time of the forwarded message."""
        return self._edited_timestamp


class MessageReference:
    """Represents a reference to a :class:`~discord.Message`.

    .. versionadded:: 1.5

    .. versionchanged:: 1.6
        This class can now be constructed by users.

    Attributes
    -----------
    type: :class:`MessageReferenceType`
        The type of message reference.

        .. versionadded:: 2.1
    message_id: Optional[:class:`int`]
        The id of the message referenced.
        This can be ``None`` when this message reference was retrieved from
        a system message of one of the following types:

        - :attr:`MessageType.channel_follow_add`
        - :attr:`MessageType.thread_created`
    channel_id: :class:`int`
        The channel id of the message referenced.
    guild_id: Optional[:class:`int`]
        The guild id of the message referenced.
    fail_if_not_exists: :class:`bool`
        Whether the referenced message should raise :class:`HTTPException`
        if the message no longer exists or Discord could not fetch the message.

        .. versionadded:: 1.7

    resolved: Optional[Union[:class:`Message`, :class:`DeletedReferencedMessage`]]
        The message that this reference resolved to. If this is ``None``
        then the original message was not fetched either due to the Discord API
        not attempting to resolve it or it not being available at the time of creation.
        If the message was resolved at a prior point but has since been deleted then
        this will be of type :class:`DeletedReferencedMessage`.

        .. versionadded:: 1.6
    """

    __slots__ = ('type', 'message_id', 'channel_id', 'guild_id', 'fail_if_not_exists', 'resolved', '_state')

    def __init__(
        self,
        *,
        message_id: int,
        channel_id: int,
        guild_id: Optional[int] = None,
        fail_if_not_exists: bool = True,
        type: MessageReferenceType = MessageReferenceType.reply,
    ):
        self._state: Optional[ConnectionState] = None
        self.type: MessageReferenceType = type
        self.resolved: Optional[Union[Message, DeletedReferencedMessage]] = None
        self.message_id: Optional[int] = message_id
        self.channel_id: int = channel_id
        self.guild_id: Optional[int] = guild_id
        self.fail_if_not_exists: bool = fail_if_not_exists

    @classmethod
    def with_state(cls, state: ConnectionState, data: MessageReferencePayload) -> Self:
        self = cls.__new__(cls)
        self.type = try_enum(MessageReferenceType, data.get('type', 0))
        self.message_id = utils._get_as_snowflake(data, 'message_id')
        self.channel_id = int(data['channel_id'])
        self.guild_id = utils._get_as_snowflake(data, 'guild_id')
        self.fail_if_not_exists = data.get('fail_if_not_exists', True)
        self._state = state
        self.resolved = None
        return self

    @classmethod
    def from_message(
        cls,
        message: PartialMessage,
        *,
        fail_if_not_exists: bool = True,
        type: MessageReferenceType = MessageReferenceType.reply,
    ) -> Self:
        """Creates a :class:`MessageReference` from an existing :class:`~discord.Message`.

        .. versionadded:: 1.6

        Parameters
        ----------
        message: :class:`~discord.Message`
            The message to be converted into a reference.
        fail_if_not_exists: :class:`bool`
            Whether the referenced message should raise :class:`HTTPException`
            if the message no longer exists or Discord could not fetch the message.

            .. versionadded:: 1.7
        type: :class:`~discord.MessageReferenceType`
            The type of message reference this is.

            .. versionadded:: 2.1

        Returns
        -------
        :class:`MessageReference`
            A reference to the message.
        """
        self = cls(
            message_id=message.id,
            channel_id=message.channel.id,
            guild_id=getattr(message.guild, 'id', None),
            fail_if_not_exists=fail_if_not_exists,
            type=type,
        )
        self._state = message._state
        return self

    @property
    def cached_message(self) -> Optional[Message]:
        """Optional[:class:`~discord.Message`]: The cached message, if found in the internal message cache."""
        return self._state and self._state._get_message(self.message_id)

    @property
    def jump_url(self) -> str:
        """:class:`str`: Returns a URL that allows the client to jump to the referenced message.

        .. versionadded:: 1.7
        """
        guild_id = self.guild_id if self.guild_id is not None else '@me'
        return f'https://discord.com/channels/{guild_id}/{self.channel_id}/{self.message_id}'

    def __repr__(self) -> str:
        return f'<MessageReference message_id={self.message_id!r} channel_id={self.channel_id!r} guild_id={self.guild_id!r}>'

    def to_dict(self) -> MessageReferencePayload:
        result: Dict[str, Any] = (
            {'type': self.type.value, 'message_id': self.message_id} if self.message_id is not None else {}
        )
        result['channel_id'] = self.channel_id
        if self.guild_id is not None:
            result['guild_id'] = self.guild_id
        if self.fail_if_not_exists is not None:
            result['fail_if_not_exists'] = self.fail_if_not_exists
        return result  # type: ignore # Type checker doesn't understand these are the same

    to_message_reference_dict = to_dict


def flatten_handlers(cls: Type[Message]) -> Type[Message]:
    prefix = len('_handle_')
    handlers = [
        (key[prefix:], value)
        for key, value in cls.__dict__.items()
        if key.startswith('_handle_') and key != '_handle_member'
    ]

    # Store _handle_member last
    handlers.append(('member', cls._handle_member))
    cls._HANDLERS = handlers
    cls._CACHED_SLOTS = [attr for attr in cls.__slots__ if attr.startswith('_cs_')]
    return cls


class RoleSubscriptionInfo:
    """Represents a message's role subscription information.

    This is currently only attached to messages of type :attr:`MessageType.role_subscription_purchase`.

    .. versionadded:: 2.0

    Attributes
    -----------
    role_subscription_listing_id: :class:`int`
        The ID of the SKU and listing that the user is subscribed to.
    tier_name: :class:`str`
        The name of the tier that the user is subscribed to.
    total_months_subscribed: :class:`int`
        The cumulative number of months that the user has been subscribed for.
    is_renewal: :class:`bool`
        Whether this notification is for a renewal rather than a new purchase.
    """

    __slots__ = (
        'role_subscription_listing_id',
        'tier_name',
        'total_months_subscribed',
        'is_renewal',
    )

    def __init__(self, data: RoleSubscriptionDataPayload) -> None:
        self.role_subscription_listing_id: int = int(data['role_subscription_listing_id'])
        self.tier_name: str = data['tier_name']
        self.total_months_subscribed: int = data['total_months_subscribed']
        self.is_renewal: bool = data['is_renewal']


class GuildProductPurchase:
    """Represents a message's guild product that the user has purchased.

    .. versionadded:: 2.1

    Attributes
    -----------
    listing_id: :class:`int`
        The ID of the listing that the user has purchased.
    product_name: :class:`str`
        The name of the product that the user has purchased.
    """

    __slots__ = ('listing_id', 'product_name')

    def __init__(self, data: GuildProductPurchasePayload) -> None:
        self.listing_id: int = int(data['listing_id'])
        self.product_name: str = data['product_name']

    def __hash__(self) -> int:
        return self.listing_id >> 22

    def __eq__(self, other: object) -> bool:
        return isinstance(other, GuildProductPurchase) and other.listing_id == self.listing_id

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)


class PurchaseNotification:
    """Represents a message's purchase notification data.

    This is currently only attached to messages of type :attr:`MessageType.purchase_notification`.

    .. versionadded:: 2.1

    Attributes
    -----------
    guild_product_purchase: Optional[:class:`GuildProductPurchase`]
        The guild product purchase that prompted the message.
    """

    __slots__ = ('_type', 'guild_product_purchase')

    def __init__(self, data: PurchaseNotificationResponsePayload) -> None:
        self._type: int = data['type']

        self.guild_product_purchase: Optional[GuildProductPurchase] = None
        guild_product_purchase = data.get('guild_product_purchase')
        if guild_product_purchase is not None:
            self.guild_product_purchase = GuildProductPurchase(guild_product_purchase)

    @property
    def type(self) -> PurchaseNotificationType:
        """:class:`PurchaseNotificationType`: The type of purchase notification."""
        return try_enum(PurchaseNotificationType, self._type)


class PartialMessage(Hashable):
    """Represents a partial message to aid with working messages when only
    a message and channel ID are present.

    There are two ways to construct this class. The first one is through
    the constructor itself, and the second is via the following:

    - :meth:`TextChannel.get_partial_message`
    - :meth:`VoiceChannel.get_partial_message`
    - :meth:`StageChannel.get_partial_message`
    - :meth:`Thread.get_partial_message`
    - :meth:`DMChannel.get_partial_message`

    Note that this class is trimmed down and has no rich attributes.

    .. versionadded:: 1.6

    .. container:: operations

        .. describe:: x == y

            Checks if two partial messages are equal.

        .. describe:: x != y

            Checks if two partial messages are not equal.

        .. describe:: hash(x)

            Returns the partial message's hash.

    Attributes
    -----------
    channel: Union[:class:`PartialMessageable`, :class:`TextChannel`, :class:`StageChannel`, :class:`VoiceChannel`, :class:`Thread`, :class:`DMChannel`]
        The channel associated with this partial message.
    id: :class:`int`
        The message ID.
    guild_id: Optional[:class:`int`]
        The ID of the guild that the partial message belongs to, if applicable.

        .. versionadded:: 2.1
    guild: Optional[:class:`Guild`]
        The guild that the partial message belongs to, if applicable.
    """

    __slots__ = ('channel', 'id', '_state', 'guild_id', 'guild')

    def __init__(self, *, channel: MessageableChannel, id: int) -> None:
        if not isinstance(channel, PartialMessageable) and channel.type not in (
            ChannelType.text,
            ChannelType.voice,
            ChannelType.stage_voice,
            ChannelType.news,
            ChannelType.private,
            ChannelType.news_thread,
            ChannelType.public_thread,
            ChannelType.private_thread,
        ):
            raise TypeError(
                f'expected PartialMessageable, TextChannel, StageChannel, VoiceChannel, DMChannel or Thread not {type(channel)!r}'
            )

        self.channel: MessageableChannel = channel
        self._state: ConnectionState = channel._state
        self.id: int = id

        self.guild: Optional[Guild] = getattr(channel, 'guild', None)
        self.guild_id: Optional[int] = self.guild.id if self.guild else None
        if hasattr(channel, 'guild_id'):
            if self.guild_id is not None:
                channel.guild_id = self.guild_id  # type: ignore
            else:
                self.guild_id = channel.guild_id  # type: ignore

    def _update(self, data: MessageUpdateEvent) -> None:
        # This is used for duck typing purposes.
        # Just do nothing with the data.
        pass

    # Also needed for duck typing purposes
    # n.b. not exposed
    pinned: Any = property(None, lambda x, y: None)

    def __repr__(self) -> str:
        return f'<PartialMessage id={self.id} channel={self.channel!r}>'

    @property
    def created_at(self) -> datetime.datetime:
        """:class:`datetime.datetime`: The partial message's creation time in UTC."""
        return utils.snowflake_time(self.id)

    @property
    def jump_url(self) -> str:
        """:class:`str`: Returns a URL that allows the client to jump to this message."""
        guild_id = getattr(self.guild, 'id', '@me')
        return f'https://discord.com/channels/{guild_id}/{self.channel.id}/{self.id}'

    @property
    def thread(self) -> Optional[Thread]:
        """Optional[:class:`Thread`]: The public thread created from this message, if it exists.

        .. note::

            This does not retrieve archived threads, as they are not retained in the internal
            cache. Use :meth:`fetch_thread` instead.

        .. versionadded:: 2.1
        """
        if self.guild is not None:
            return self.guild.get_thread(self.id)

    async def fetch(self) -> Message:
        """|coro|

        Fetches the partial message to a full :class:`Message`.

        Raises
        --------
        NotFound
            The message was not found.
        Forbidden
            You do not have the permissions required to get a message.
        HTTPException
            Retrieving the message failed.

        Returns
        --------
        :class:`Message`
            The full message.
        """
        data = await self._state.http.get_message(self.channel.id, self.id)
        return self._state.create_message(channel=self.channel, data=data)

    async def delete(self, *, delay: Optional[float] = None) -> None:
        """|coro|

        Deletes the message.

        Your own messages could be deleted without any proper permissions. However to
        delete other people's messages, you must have :attr:`~Permissions.manage_messages`.

        .. versionchanged:: 1.1
            Added the new ``delay`` keyword-only parameter.

        Parameters
        -----------
        delay: Optional[:class:`float`]
            If provided, the number of seconds to wait in the background
            before deleting the message. If the deletion fails then it is silently ignored.

        Raises
        ------
        Forbidden
            You do not have proper permissions to delete the message.
        NotFound
            The message was deleted already
        HTTPException
            Deleting the message failed.
        """
        if delay is not None:

            async def delete(delay: float):
                await asyncio.sleep(delay)
                try:
                    await self._state.http.delete_message(self.channel.id, self.id)
                except HTTPException:
                    pass

            asyncio.create_task(delete(delay))
        else:
            await self._state.http.delete_message(self.channel.id, self.id)

    @overload
    async def edit(
        self,
        *,
        content: Optional[str] = ...,
        attachments: Sequence[Union[Attachment, _FileBase]] = ...,
        delete_after: Optional[float] = ...,
        allowed_mentions: Optional[AllowedMentions] = ...,
    ) -> Message:
        ...

    @overload
    async def edit(
        self,
        *,
        content: Optional[str] = ...,
        attachments: Sequence[Union[Attachment, _FileBase]] = ...,
        delete_after: Optional[float] = ...,
        allowed_mentions: Optional[AllowedMentions] = ...,
    ) -> Message:
        ...

    async def edit(
        self,
        content: Optional[str] = MISSING,
        attachments: Sequence[Union[Attachment, _FileBase]] = MISSING,
        delete_after: Optional[float] = None,
        allowed_mentions: Optional[AllowedMentions] = MISSING,
    ) -> Message:
        """|coro|

        Edits the message.

        The content must be able to be transformed into a string via ``str(content)``.

        .. versionchanged:: 2.0
            Edits are no longer in-place, the newly edited message is returned instead.

        .. versionchanged:: 2.0
            This function will now raise :exc:`TypeError` instead of
            ``InvalidArgument``.

        Parameters
        -----------
        content: Optional[:class:`str`]
            The new content to replace the message with.
            Could be ``None`` to remove the content.
        attachments: List[Union[:class:`Attachment`, :class:`File`, :class:`CloudFile`]]
            A list of attachments to keep in the message as well as new files to upload. If ``[]`` is passed
            then all attachments are removed.

            .. note::

                New files will always appear after current attachments.

            .. versionadded:: 2.0
        delete_after: Optional[:class:`float`]
            If provided, the number of seconds to wait in the background
            before deleting the message we just edited. If the deletion fails,
            then it is silently ignored.
        allowed_mentions: Optional[:class:`~discord.AllowedMentions`]
            Controls the mentions being processed in this message. If this is
            passed, then the object is merged with :attr:`~discord.Client.allowed_mentions`.
            The merging behaviour only overrides attributes that have been explicitly passed
            to the object, otherwise it uses the attributes set in :attr:`~discord.Client.allowed_mentions`.
            If no object is passed at all then the defaults given by :attr:`~discord.Client.allowed_mentions`
            are used instead.

            .. versionadded:: 1.4

        Raises
        -------
        HTTPException
            Editing the message failed.
        Forbidden
            Tried to suppress a message without permissions or
            edited a message's content or embed that isn't yours.
        NotFound
            This message does not exist.
        TypeError
            You specified both ``embed`` and ``embeds``

        Returns
        --------
        :class:`Message`
            The newly edited message.
        """
        if content is not MISSING:
            previous_allowed_mentions = self._state.allowed_mentions
        else:
            previous_allowed_mentions = None

        with handle_message_parameters(
            content=content,
            attachments=attachments,
            allowed_mentions=allowed_mentions,
            previous_allowed_mentions=previous_allowed_mentions,
        ) as params:
            data = await self._state.http.edit_message(self.channel.id, self.id, params=params)
            message = Message(state=self._state, channel=self.channel, data=data)

        if delete_after is not None:
            await self.delete(delay=delete_after)

        return message

    async def publish(self) -> None:
        """|coro|

        Publishes this message to the channel's followers.

        The message must have been sent in a news channel.
        You must have :attr:`~Permissions.send_messages` to do this.

        If the message is not your own then :attr:`~Permissions.manage_messages`
        is also needed.

        Raises
        -------
        Forbidden
            You do not have the proper permissions to publish this message
            or the channel is not a news channel.
        HTTPException
            Publishing the message failed.
        """
        await self._state.http.publish_message(self.channel.id, self.id)

    async def pin(self, *, reason: Optional[str] = None) -> None:
        """|coro|

        Pins the message.

        You must have :attr:`~Permissions.manage_messages` to do
        this in a non-private channel context.

        Parameters
        -----------
        reason: Optional[:class:`str`]
            The reason for pinning the message. Shows up on the audit log.

            .. versionadded:: 1.4

        Raises
        -------
        Forbidden
            You do not have permissions to pin the message.
        NotFound
            The message or channel was not found or deleted.
        HTTPException
            Pinning the message failed, probably due to the channel
            having more than 50 pinned messages.
        """
        await self._state.http.pin_message(self.channel.id, self.id, reason=reason)
        # pinned exists on PartialMessage for duck typing purposes
        self.pinned = True

    async def unpin(self, *, reason: Optional[str] = None) -> None:
        """|coro|

        Unpins the message.

        You must have :attr:`~Permissions.manage_messages` to do
        this in a non-private channel context.

        Parameters
        -----------
        reason: Optional[:class:`str`]
            The reason for unpinning the message. Shows up on the audit log.

            .. versionadded:: 1.4

        Raises
        -------
        Forbidden
            You do not have permissions to unpin the message.
        NotFound
            The message or channel was not found or deleted.
        HTTPException
            Unpinning the message failed.
        """
        await self._state.http.unpin_message(self.channel.id, self.id, reason=reason)
        # pinned exists on PartialMessage for duck typing purposes
        self.pinned = False

    async def add_reaction(self, emoji: Union[EmojiInputType, Reaction], /, *, boost: bool = False) -> None:
        """|coro|

        Adds a reaction to the message.

        The emoji may be a unicode emoji or a custom guild :class:`Emoji`.

        You must have :attr:`~Permissions.read_message_history`
        to do this. If nobody else has reacted to the message using this
        emoji, :attr:`~Permissions.add_reactions` is required.

        .. versionchanged:: 2.0

            ``emoji`` parameter is now positional-only.

        .. versionchanged:: 2.0
            This function will now raise :exc:`TypeError` instead of
            ``InvalidArgument``.

        Parameters
        ------------
        emoji: Union[:class:`Emoji`, :class:`Reaction`, :class:`PartialEmoji`, :class:`str`]
            The emoji to react with.
        boost: :class:`bool`
            Whether to react with a super reaction.

            .. versionadded:: 2.1

        Raises
        --------
        HTTPException
            Adding the reaction failed.
        Forbidden
            You do not have the proper permissions to react to the message.
        NotFound
            The emoji you specified was not found.
        TypeError
            The emoji parameter is invalid.
        """
        emoji = convert_emoji_reaction(emoji)
        await self._state.http.add_reaction(self.channel.id, self.id, emoji, type=1 if boost else 0)

    async def remove_reaction(self, emoji: Union[EmojiInputType, Reaction], member: Snowflake, boost: bool = False) -> None:
        """|coro|

        Remove a reaction by the member from the message.

        The emoji may be a unicode emoji or a custom guild :class:`Emoji`.

        If the reaction is not your own (i.e. ``member`` parameter is not you) then
        :attr:`~Permissions.manage_messages` is needed.

        The ``member`` parameter must represent a member and meet
        the :class:`abc.Snowflake` abc.

        .. versionchanged:: 2.0
            This function will now raise :exc:`TypeError` instead of
            ``InvalidArgument``.

        Parameters
        ------------
        emoji: Union[:class:`Emoji`, :class:`Reaction`, :class:`PartialEmoji`, :class:`str`]
            The emoji to remove.
        member: :class:`abc.Snowflake`
            The member for which to remove the reaction.
        boost: :class:`bool`
            Whether to remove a super reaction.

            .. note::

                Keep in mind that members can both react and super react with the same emoji.

            .. versionadded:: 2.1

        Raises
        --------
        HTTPException
            Removing the reaction failed.
        Forbidden
            You do not have the proper permissions to remove the reaction.
        NotFound
            The member or emoji you specified was not found.
        TypeError
            The emoji parameter is invalid.
        """
        emoji = convert_emoji_reaction(emoji)

        if member.id == self._state.self_id:
            await self._state.http.remove_own_reaction(self.channel.id, self.id, emoji, type=1 if boost else 0)
        else:
            await self._state.http.remove_reaction(self.channel.id, self.id, emoji, member.id, type=1 if boost else 0)

    async def clear_reaction(self, emoji: Union[EmojiInputType, Reaction]) -> None:
        """|coro|

        Clears a specific reaction from the message.

        The emoji may be a unicode emoji or a custom guild :class:`Emoji`.

        You must have :attr:`~Permissions.manage_messages` to do this.

        .. versionadded:: 1.3

        .. versionchanged:: 2.0
            This function will now raise :exc:`TypeError` instead of
            ``InvalidArgument``.

        Parameters
        -----------
        emoji: Union[:class:`Emoji`, :class:`Reaction`, :class:`PartialEmoji`, :class:`str`]
            The emoji to clear.

        Raises
        --------
        HTTPException
            Clearing the reaction failed.
        Forbidden
            You do not have the proper permissions to clear the reaction.
        NotFound
            The emoji you specified was not found.
        TypeError
            The emoji parameter is invalid.
        """
        emoji = convert_emoji_reaction(emoji)
        await self._state.http.clear_single_reaction(self.channel.id, self.id, emoji)

    async def clear_reactions(self) -> None:
        """|coro|

        Removes all the reactions from the message.

        You must have :attr:`~Permissions.manage_messages` to do this.

        Raises
        --------
        HTTPException
            Removing the reactions failed.
        Forbidden
            You do not have the proper permissions to remove all the reactions.
        """
        await self._state.http.clear_reactions(self.channel.id, self.id)

    async def create_thread(
        self,
        *,
        name: str,
        auto_archive_duration: ThreadArchiveDuration = MISSING,
        slowmode_delay: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> Thread:
        """|coro|

        Creates a public thread from this message.

        You must have :attr:`~discord.Permissions.create_public_threads` in order to
        create a public thread from a message.

        The channel this message belongs in must be a :class:`TextChannel`.

        .. versionadded:: 2.0

        Parameters
        -----------
        name: :class:`str`
            The name of the thread.
        auto_archive_duration: :class:`int`
            The duration in minutes before a thread is automatically hidden from the channel list.
            If not provided, the channel's default auto archive duration is used.

            Must be one of ``60``, ``1440``, ``4320``, or ``10080``, if provided.
        slowmode_delay: Optional[:class:`int`]
            Specifies the slowmode rate limit for user in this channel, in seconds.
            The maximum value possible is ``21600``. By default no slowmode rate limit
            if this is ``None``.
        reason: Optional[:class:`str`]
            The reason for creating a new thread. Shows up on the audit log.

        Raises
        -------
        Forbidden
            You do not have permissions to create a thread.
        HTTPException
            Creating the thread failed.
        ValueError
            This message does not have guild info attached.

        Returns
        --------
        :class:`.Thread`
            The created thread.
        """
        if self.guild is None:
            raise ValueError('This message does not have guild info attached')

        default_auto_archive_duration: ThreadArchiveDuration = getattr(self.channel, 'default_auto_archive_duration', 1440)
        data = await self._state.http.start_thread_with_message(
            self.channel.id,
            self.id,
            name=name,
            auto_archive_duration=auto_archive_duration or default_auto_archive_duration,
            rate_limit_per_user=slowmode_delay,
            reason=reason,
            location='Message',
        )
        return Thread(guild=self.guild, state=self._state, data=data)

    async def ack(self, *, manual: bool = False, mention_count: Optional[int] = None) -> None:
        """|coro|

        Marks this message as read.

        .. note::

            This sets the last acknowledged message to this message,
            which will mark acknowledged messages created after this one as unread.

        Parameters
        -----------
        manual: :class:`bool`
            Whether to manually set the channel read state to this message.

            .. versionadded:: 2.1
        mention_count: Optional[:class:`int`]
            The mention count to set the channel read state to. Only applicable for
            manual acknowledgements.

            .. versionadded:: 2.1

        Raises
        -------
        HTTPException
            Acking failed.
        """
        await self.channel.read_state.ack(self.id, manual=manual, mention_count=mention_count)

    async def unack(self, *, mention_count: Optional[int] = None) -> None:
        """|coro|

        Marks this message as unread.
        This manually sets the read state to the current message's ID - 1.

        .. versionadded:: 2.1

        Parameters
        -----------
        mention_count: Optional[:class:`int`]
            The mention count to set the channel read state to.

        Raises
        -------
        HTTPException
            Unacking failed.
        """
        await self.channel.read_state.ack(self.id - 1, manual=True, mention_count=mention_count)

    async def fetch_thread(self) -> Thread:
        """|coro|

        Retrieves the public thread attached to this message.

        .. note::

            This method is an API call. For general usage, consider :attr:`thread` instead.

        .. versionadded:: 2.1

        Raises
        -------
        InvalidData
            An unknown channel type was received from Discord
            or the guild the thread belongs to is not the same
            as the one in this object points to.
        HTTPException
            Retrieving the thread failed.
        NotFound
            There is no thread attached to this message.
        Forbidden
            You do not have permission to fetch this channel.

        Returns
        --------
        :class:`.Thread`
            The public thread attached to this message.
        """
        if self.guild is None:
            raise ValueError('This message does not have guild info attached')

        return await self.guild.fetch_channel(self.id)  # type: ignore  # Can only be Thread in this case

    @overload
    async def reply(
        self,
        content: Optional[str] = ...,
        *,
        tts: bool = ...,
        file: _FileBase = ...,
        stickers: Sequence[Union[GuildSticker, StickerItem]] = ...,
        delete_after: float = ...,
        nonce: Union[str, int] = ...,
        allowed_mentions: AllowedMentions = ...,
        mention_author: bool = ...,
        suppress_embeds: bool = ...,
        silent: bool = ...,
        poll: Poll = ...,
    ) -> Message:
        ...

    @overload
    async def reply(
        self,
        content: Optional[str] = ...,
        *,
        tts: bool = ...,
        files: Sequence[_FileBase] = ...,
        stickers: Sequence[Union[GuildSticker, StickerItem]] = ...,
        delete_after: float = ...,
        nonce: Union[str, int] = ...,
        allowed_mentions: AllowedMentions = ...,
        mention_author: bool = ...,
        suppress_embeds: bool = ...,
        silent: bool = ...,
        poll: Poll = ...,
    ) -> Message:
        ...

    @overload
    async def reply(
        self,
        content: Optional[str] = ...,
        *,
        tts: bool = ...,
        file: _FileBase = ...,
        stickers: Sequence[Union[GuildSticker, StickerItem]] = ...,
        delete_after: float = ...,
        nonce: Union[str, int] = ...,
        allowed_mentions: AllowedMentions = ...,
        mention_author: bool = ...,
        suppress_embeds: bool = ...,
        silent: bool = ...,
        poll: Poll = ...,
    ) -> Message:
        ...

    @overload
    async def reply(
        self,
        content: Optional[str] = ...,
        *,
        tts: bool = ...,
        files: Sequence[_FileBase] = ...,
        stickers: Sequence[Union[GuildSticker, StickerItem]] = ...,
        delete_after: float = ...,
        nonce: Union[str, int] = ...,
        allowed_mentions: AllowedMentions = ...,
        mention_author: bool = ...,
        suppress_embeds: bool = ...,
        silent: bool = ...,
        poll: Poll = ...,
    ) -> Message:
        ...

    async def reply(self, content: Optional[str] = None, **kwargs: Any) -> Message:
        """|coro|

        A shortcut method to :meth:`.abc.Messageable.send` to reply to the
        :class:`.Message`.

        .. versionadded:: 1.6

        .. versionchanged:: 2.0
            This function will now raise :exc:`TypeError` or
            :exc:`ValueError` instead of ``InvalidArgument``.

        Raises
        --------
        ~discord.HTTPException
            Sending the message failed.
        ~discord.Forbidden
            You do not have the proper permissions to send the message.
        ValueError
            The ``files`` list is not of the appropriate size
        TypeError
            You specified both ``file`` and ``files``.

        Returns
        ---------
        :class:`.Message`
            The message that was sent.
        """
        return await self.channel.send(content, reference=self, **kwargs)

    @overload
    async def greet(
        self,
        sticker: Union[GuildSticker, StickerItem],
        *,
        allowed_mentions: AllowedMentions = ...,
        mention_author: bool = ...,
    ) -> Message:
        ...

    @overload
    async def greet(self, sticker: Union[GuildSticker, StickerItem]) -> Message:
        ...

    async def greet(self, sticker: Union[GuildSticker, StickerItem], **kwargs: Any) -> Message:
        """|coro|

        A shortcut method to :meth:`.abc.Messageable.greet` to reply to the
        :class:`.Message` with a sticker greeting.

        .. versionadded:: 2.0

        Raises
        --------
        ~discord.HTTPException
            Sending the message failed.
        ~discord.Forbidden
            You do not have the proper permissions to send the message, or this is not a valid greet context.

        Returns
        ---------
        :class:`.Message`
            The sticker greeting that was sent.
        """
        return await self.channel.greet(sticker, reference=self, **kwargs)

    async def end_poll(self) -> Message:
        """|coro|

        Ends the :class:`Poll` attached to this message.

        This can only be done if you are the message author.

        If the poll was successfully ended, then it returns the updated :class:`Message`.

        Raises
        ------
        ~discord.HTTPException
            Ending the poll failed.

        Returns
        -------
        :class:`.Message`
            The updated message.
        """

        data = await self._state.http.end_poll(self.channel.id, self.id)

        return Message(state=self._state, channel=self.channel, data=data)

    def to_reference(
        self,
        *,
        fail_if_not_exists: bool = True,
        type: MessageReferenceType = MessageReferenceType.reply,
    ) -> MessageReference:
        """Creates a :class:`~discord.MessageReference` from the current message.

        .. versionadded:: 1.6

        Parameters
        ----------
        fail_if_not_exists: :class:`bool`
            Whether the referenced message should raise :class:`HTTPException`
            if the message no longer exists or Discord could not fetch the message.

            .. versionadded:: 1.7
        type: :class:`MessageReferenceType`
            The type of message reference. Default :attr:`MessageReferenceType.reply`.

            .. versionadded:: 2.1

        Returns
        ---------
        :class:`~discord.MessageReference`
            The reference to this message.
        """

        return MessageReference.from_message(self, fail_if_not_exists=fail_if_not_exists, type=type)

    async def forward(
        self,
        destination: MessageableChannel,
        *,
        fail_if_not_exists: bool = True,
    ) -> Message:
        """|coro|

        Forwards this message to a channel.

        .. versionadded:: 2.1

        Parameters
        ----------
        destination: :class:`~discord.abc.Messageable`
            The channel to forward this message to.
        fail_if_not_exists: :class:`bool`
            Whether replying using the message reference should raise :class:`HTTPException`
            if the message no longer exists or Discord could not fetch the message.

        Raises
        ------
        ~discord.HTTPException
            Forwarding the message failed.

        Returns
        -------
        :class:`.Message`
            The message sent to the channel.
        """
        reference = self.to_reference(
            fail_if_not_exists=fail_if_not_exists,
            type=MessageReferenceType.forward,
        )
        ret = await destination.send(reference=reference)
        return ret

    def to_message_reference_dict(self) -> MessageReferencePayload:
        data: MessageReferencePayload = {
            'message_id': self.id,
            'channel_id': self.channel.id,
        }

        if self.guild is not None:
            data['guild_id'] = self.guild.id

        return data


@flatten_handlers
class Message(PartialMessage, Hashable):
    r"""Represents a message from Discord.

    .. container:: operations

        .. describe:: x == y

            Checks if two messages are equal.

        .. describe:: x != y

            Checks if two messages are not equal.

        .. describe:: hash(x)

            Returns the message's hash.

    Attributes
    -----------
    tts: :class:`bool`
        Specifies if the message was done with text-to-speech.
        This can only be accurately received in :func:`on_message` due to
        a discord limitation.
    type: :class:`MessageType`
        The type of message. In most cases this should not be checked, but it is helpful
        in cases where it might be a system message for :attr:`system_content`.
    author: Union[:class:`Member`, :class:`abc.User`]
        A :class:`Member` that sent the message. If :attr:`channel` is a
        private channel or the user has the left the guild, then it is a :class:`User` instead.
    content: :class:`str`
        The actual contents of the message.
    nonce: Optional[Union[:class:`str`, :class:`int`]]
        The value used by Discord clients to verify that the message is successfully sent.
        This is not stored long term within Discord's servers and is only used ephemerally.
    embeds: List[:class:`Embed`]
        A list of embeds the message has.
    channel: Union[:class:`TextChannel`, :class:`StageChannel`, :class:`VoiceChannel`, :class:`Thread`, :class:`DMChannel`, :class:`GroupChannel`, :class:`PartialMessageable`]
        The :class:`TextChannel` or :class:`Thread` that the message was sent from.
        Could be a :class:`DMChannel` or :class:`GroupChannel` if it's a private message.
    call: Optional[:class:`CallMessage`]
        The call that the message refers to. This is only applicable to messages of type
        :attr:`MessageType.call`.
    reference: Optional[:class:`~discord.MessageReference`]
        The message that this message references. This is only applicable to
        message replies (:attr:`MessageType.reply`), crossposted messages created by
        a followed channel integration, forwarded messages, and messages of type:

        - :attr:`MessageType.pins_add`
        - :attr:`MessageType.channel_follow_add`
        - :attr:`MessageType.thread_created`
        - :attr:`MessageType.thread_starter_message`
        - :attr:`MessageType.poll_result`
        - :attr:`MessageType.context_menu_command`

        .. versionadded:: 1.5

    mention_everyone: :class:`bool`
        Specifies if the message mentions everyone.

        .. note::

            This does not check if the ``@everyone`` or the ``@here`` text is in the message itself.
            Rather this boolean indicates if either the ``@everyone`` or the ``@here`` text is in the message
            **and** it did end up mentioning.
    mentions: List[:class:`abc.User`]
        A list of :class:`Member` that were mentioned. If the message is in a private message
        then the list will be of :class:`User` instead. For messages that are not of type
        :attr:`MessageType.default`\, this array can be used to aid in system messages.
        For more information, see :attr:`system_content`.

        .. warning::

            The order of the mentions list is not in any particular order so you should
            not rely on it. This is a Discord limitation, not one with the library.
    channel_mentions: List[Union[:class:`abc.GuildChannel`, :class:`Thread`]]
        A list of :class:`abc.GuildChannel` or :class:`Thread` that were mentioned. If the message is
        in a private message then the list is always empty.
    role_mentions: List[:class:`Role`]
        A list of :class:`Role` that were mentioned. If the message is in a private message
        then the list is always empty.
    id: :class:`int`
        The message ID.
    webhook_id: Optional[:class:`int`]
        If this message was sent by a webhook, then this is the webhook ID's that sent this
        message.
    attachments: List[:class:`Attachment`]
        A list of attachments given to a message.
    pinned: :class:`bool`
        Specifies if the message is currently pinned.
    flags: :class:`MessageFlags`
        Extra features of the message.

        .. versionadded:: 1.3

    reactions : List[:class:`Reaction`]
        Reactions to a message. Reactions can be either custom emoji or standard unicode emoji.
    activity: Optional[:class:`dict`]
        The activity associated with this message. Sent with Rich-Presence related messages that for
        example, request joining, spectating, or listening to or with another member.

        It is a dictionary with the following optional keys:

        - ``type``: An integer denoting the type of message activity being requested.
        - ``party_id``: The party ID associated with the party.
    application: Optional[:class:`IntegrationApplication`]
        The rich presence enabled application associated with this message.

        .. versionchanged:: 2.0

            Type is now :class:`IntegrationApplication` instead of :class:`dict`.
    stickers: List[:class:`StickerItem`]
        A list of sticker items given to the message.

        .. versionadded:: 1.6
    components: List[Union[:class:`ActionRow`, :class:`Button`, :class:`SelectMenu`]]
        A list of components in the message.

        .. versionadded:: 2.0
    role_subscription: Optional[:class:`RoleSubscriptionInfo`]
        The data of the role subscription purchase or renewal that prompted this
        :attr:`MessageType.role_subscription_purchase` message.

        .. versionadded:: 2.0
    application_id: Optional[:class:`int`]
        The application ID of the application that created this message if this
        message was sent by an application-owned webhook or an interaction.

        .. versionadded:: 2.0
    position: Optional[:class:`int`]
        A generally increasing integer with potentially gaps or duplicates that represents
        the approximate position of the message in a thread.

        .. versionadded:: 2.0
    guild_id: Optional[:class:`int`]
        The ID of the guild that the partial message belongs to, if applicable.

        .. versionadded:: 2.1
    guild: Optional[:class:`Guild`]
        The guild that the message belongs to, if applicable.
    interaction: Optional[:class:`Interaction`]
        The interaction that this message is a response to.

        .. versionadded:: 2.0
    poll: Optional[:class:`Poll`]
        The poll attached to this message.

        .. versionadded:: 2.1
    purchase_notification: Optional[:class:`PurchaseNotification`]
        The data of the purchase notification that prompted this :attr:`MessageType.purchase_notification` message.

        .. versionadded:: 2.1
    message_snapshots: List[:class:`MessageSnapshot`]
        The message snapshots attached to this message.

        .. versionadded:: 2.1
    hit: :class:`bool`
        Whether the message was a hit in a search result. As surrounding messages
        are no longer returned in search results, this is always ``True`` for search results.

        .. versionadded:: 2.1
    total_results: Optional[:class:`int`]
        The total number of results for the search query. This is only present in search results.

        .. versionadded:: 2.1
    analytics_id: Optional[:class:`str`]
        The search results analytics ID. This is only present in search results.

        .. versionadded:: 2.1
    doing_deep_historical_index: Optional[:class:`bool`]
        The status of the document's current deep historical indexing operation, if any.
        This is only present in search results.

        .. versionadded:: 2.1
    """

    __slots__ = (
        '_edited_timestamp',
        '_cs_channel_mentions',
        '_cs_raw_mentions',
        '_cs_clean_content',
        '_cs_raw_channel_mentions',
        '_cs_raw_role_mentions',
        '_cs_system_content',
        '_thread',
        'tts',
        'content',
        'webhook_id',
        'mention_everyone',
        'embeds',
        'mentions',
        'author',
        'attachments',
        'nonce',
        'pinned',
        'role_mentions',
        'type',
        'flags',
        'reactions',
        'reference',
        'application',
        'activity',
        'stickers',
        'components',
        'call',
        'interaction',
        'role_subscription',
        'application_id',
        'position',
        'poll',
        'purchase_notification',
        'message_snapshots',
        'hit',
        'total_results',
        'analytics_id',
        'doing_deep_historical_index',
    )

    if TYPE_CHECKING:
        _HANDLERS: ClassVar[List[Tuple[str, Callable[..., None]]]]
        _CACHED_SLOTS: ClassVar[List[str]]
        reference: Optional[MessageReference]
        mentions: List[Union[User, Member]]
        author: Union[User, Member]
        role_mentions: List[Role]
        components: List[ActionRow]

    def __init__(
        self,
        *,
        state: ConnectionState,
        channel: MessageableChannel,
        data: MessagePayload,
        search_result: Optional[MessageSearchResultPayload] = None,
    ) -> None:
        self.channel: MessageableChannel = channel
        self.id: int = int(data['id'])
        self._state: ConnectionState = state
        self.webhook_id: Optional[int] = utils._get_as_snowflake(data, 'webhook_id')
        self.reactions: List[Reaction] = [Reaction(message=self, data=d) for d in data.get('reactions', [])]
        self.attachments: List[Attachment] = [Attachment(data=a, state=self._state) for a in data.get('attachments', [])]
        self.embeds: List[Embed] = [Embed.from_dict(a) for a in data.get('embeds', [])]
        self.activity: Optional[MessageActivityPayload] = data.get('activity')
        self._edited_timestamp: Optional[datetime.datetime] = utils.parse_time(data.get('edited_timestamp'))
        self.type: MessageType = try_enum(MessageType, data['type'])
        self.pinned: bool = data.get('pinned', False)
        self.flags: MessageFlags = MessageFlags._from_value(data.get('flags', 0))
        self.mention_everyone: bool = data.get('mention_everyone', False)
        self.tts: bool = data.get('tts', False)
        self.content: str = data['content']
        self.nonce: Optional[Union[int, str]] = data.get('nonce')
        self.position: Optional[int] = data.get('position')
        self.application_id: Optional[int] = utils._get_as_snowflake(data, 'application_id')
        self.stickers: List[StickerItem] = [StickerItem(data=d, state=state) for d in data.get('sticker_items', [])]
        self.call: Optional[CallMessage] = None
        self.interaction: Optional[Interaction] = None

        self.poll: Optional[Poll] = None
        try:
            poll = data['poll']  # pyright: ignore[reportTypedDictNotRequiredAccess]
            self.poll = Poll._from_data(data=poll, message=self, state=state)
        except KeyError:
            pass

        try:
            # If the channel doesn't have a guild attribute, we handle that
            self.guild = channel.guild
        except AttributeError:
            guild_id = utils._get_as_snowflake(data, 'guild_id')
            if guild_id is not None:
                channel.guild_id = guild_id  # type: ignore
            else:
                guild_id = channel.guild_id  # type: ignore

            self.guild_id: Optional[int] = guild_id
            self.guild = state._get_guild(guild_id)

        self._thread: Optional[Thread] = None

        if self.guild is not None:
            try:
                thread = data['thread']  # pyright: ignore[reportTypedDictNotRequiredAccess]
            except KeyError:
                pass
            else:
                self._thread = self.guild.get_thread(int(thread['id']))

                if self._thread is not None:
                    self._thread._update(thread)
                else:
                    self._thread = Thread(guild=self.guild, state=state, data=thread)

        self.application: Optional[IntegrationApplication] = None
        try:
            application = data['application']  # pyright: ignore[reportTypedDictNotRequiredAccess]
        except KeyError:
            pass
        else:
            self.application = IntegrationApplication(state=self._state, data=application)

        try:
            ref = data['message_reference']  # pyright: ignore[reportTypedDictNotRequiredAccess]
        except KeyError:
            self.reference = None
        else:
            self.reference = ref = MessageReference.with_state(state, ref)
            try:
                resolved = data['referenced_message']  # pyright: ignore[reportTypedDictNotRequiredAccess]
            except KeyError:
                pass
            else:
                if resolved is None:
                    ref.resolved = DeletedReferencedMessage(ref)
                else:
                    # Right now the channel IDs match but maybe in the future they won't
                    if ref.channel_id == channel.id:
                        chan = channel
                    elif isinstance(channel, Thread) and channel.parent_id == ref.channel_id:
                        chan = channel
                    else:
                        chan, _ = state._get_guild_channel(resolved, ref.guild_id)

                    # The channel will be the correct type here
                    ref.resolved = self.__class__(channel=chan, data=resolved, state=state)  # type: ignore

            if self.type is MessageType.poll_result:
                if isinstance(self.reference.resolved, self.__class__):
                    self._state._update_poll_results(self, self.reference.resolved)
                else:
                    if self.reference.message_id:
                        self._state._update_poll_results(self, self.reference.message_id)

        self.message_snapshots: List[MessageSnapshot] = MessageSnapshot._from_value(state, data.get('message_snapshots'), self.reference)  # type: ignore

        self.role_subscription: Optional[RoleSubscriptionInfo] = None
        try:
            role_subscription = data['role_subscription_data']  # pyright: ignore[reportTypedDictNotRequiredAccess]
        except KeyError:
            pass
        else:
            self.role_subscription = RoleSubscriptionInfo(role_subscription)

        self.purchase_notification: Optional[PurchaseNotification] = None
        try:
            purchase_notification = data['purchase_notification']  # pyright: ignore[reportTypedDictNotRequiredAccess]
        except KeyError:
            pass
        else:
            self.purchase_notification = PurchaseNotification(purchase_notification)

        search_payload = search_result or {}
        self.hit: bool = data.get('hit', False)
        self.total_results: Optional[int] = search_payload.get('total_results')
        self.analytics_id: Optional[str] = search_payload.get('analytics_id')
        self.doing_deep_historical_index: Optional[bool] = search_payload.get('doing_deep_historical_index')

        for handler in ('author', 'member', 'mentions', 'mention_roles', 'call', 'interaction', 'components'):
            try:
                getattr(self, f'_handle_{handler}')(data[handler])  # type: ignore
            except KeyError:
                continue

    def __repr__(self) -> str:
        name = self.__class__.__name__
        return (
            f'<{name} id={self.id} channel={self.channel!r} type={self.type!r} author={self.author!r} flags={self.flags!r}>'
        )

    async def _get_channel(self) -> MessageableChannel:
        return self.channel

    def _try_patch(self, data, key, transform=None) -> None:
        try:
            value = data[key]
        except KeyError:
            pass
        else:
            if transform is None:
                setattr(self, key, value)
            else:
                setattr(self, key, transform(value))

    def _add_reaction(self, data, emoji, user_id) -> Reaction:
        reaction = utils.find(lambda r: r.emoji == emoji, self.reactions)
        is_me = data['me'] = user_id == self._state.self_id

        if reaction is None:
            reaction = Reaction(message=self, data=data, emoji=emoji)
            self.reactions.append(reaction)
        else:
            reaction.count += 1
            if is_me:
                reaction.me = is_me

        return reaction

    def _remove_reaction(self, data: MessageReactionRemoveEvent, emoji: EmojiInputType, user_id: int) -> Reaction:
        reaction = utils.find(lambda r: r.emoji == emoji, self.reactions)

        if reaction is None:
            # Already removed?
            raise ValueError('Emoji already removed?')

        # If reaction isn't in the list, we crash; this means Discord
        # sent bad data, or we stored improperly
        reaction.count -= 1

        if user_id == self._state.self_id:
            reaction.me = False
        if reaction.count == 0:
            # This raises ValueError if something went wrong as well
            self.reactions.remove(reaction)

        return reaction

    def _clear_emoji(self, emoji: PartialEmoji) -> Optional[Reaction]:
        to_check = str(emoji)
        for index, reaction in enumerate(self.reactions):
            if str(reaction.emoji) == to_check:
                break
        else:
            # Didn't find anything so just return
            return

        del self.reactions[index]
        return reaction

    def _update(self, data: MessageUpdateEvent) -> None:
        # In an update scheme, 'author' key has to be handled before 'member'
        # otherwise they overwrite each other which is undesirable
        # Since there's no good way to do this we have to iterate over every
        # handler rather than iterating over the keys which is a little slower
        for key, handler in self._HANDLERS:
            try:
                value = data[key]
            except KeyError:
                continue
            else:
                handler(self, value)

        # Clear the cached properties
        for attr in self._CACHED_SLOTS:
            try:
                delattr(self, attr)
            except AttributeError:
                pass

    def _handle_edited_timestamp(self, value: str) -> None:
        self._edited_timestamp = utils.parse_time(value)

    def _handle_pinned(self, value: bool) -> None:
        self.pinned = value

    def _handle_flags(self, value: int) -> None:
        self.flags = MessageFlags._from_value(value)

    def _handle_application(self, value: MessageApplicationPayload) -> None:
        application = IntegrationApplication(state=self._state, data=value)
        self.application = application

    def _handle_activity(self, value: MessageActivityPayload) -> None:
        self.activity = value

    def _handle_mention_everyone(self, value: bool) -> None:
        self.mention_everyone = value

    def _handle_tts(self, value: bool) -> None:
        self.tts = value

    def _handle_type(self, value: int) -> None:
        self.type = try_enum(MessageType, value)

    def _handle_content(self, value: str) -> None:
        self.content = value

    def _handle_attachments(self, value: List[AttachmentPayload]) -> None:
        self.attachments = [Attachment(data=a, state=self._state) for a in value]

    def _handle_embeds(self, value: List[EmbedPayload]) -> None:
        self.embeds = [Embed.from_dict(data) for data in value]

    def _handle_nonce(self, value: Union[str, int]) -> None:
        self.nonce = value

    def _handle_author(self, author: UserPayload) -> None:
        self.author = self._state.store_user(author, cache=self.webhook_id is None)
        if isinstance(self.guild, Guild):
            found = self.guild.get_member(self.author.id)
            if found is not None:
                self.author = found

    def _handle_member(self, member: MemberPayload) -> None:
        # The gateway now gives us full Member objects sometimes with the following keys
        # deaf, mute, joined_at, roles
        # For the sake of performance I'm going to assume that the only
        # field that needs *updating* would be the joined_at field
        # If there is no Member object (for some strange reason), then we can upgrade
        # ourselves to a more "partial" member object
        author = self.author
        try:
            # Update member reference
            author._update_from_message(member)  # type: ignore
        except AttributeError:
            # It's a user here
            # TODO: consider adding to cache here
            self.author = Member._from_message(message=self, data=member)

    def _handle_mentions(self, mentions: List[UserWithMemberPayload]) -> None:
        self.mentions = r = []
        guild = self.guild
        state = self._state
        if not isinstance(guild, Guild):
            self.mentions = [state.store_user(m) for m in mentions]
            return

        for mention in filter(None, mentions):
            id_search = int(mention['id'])
            member = guild.get_member(id_search)
            if member is not None:
                r.append(member)
            else:
                r.append(Member._try_upgrade(data=mention, guild=guild, state=state))

    def _handle_mention_roles(self, role_mentions: List[int]) -> None:
        self.role_mentions = r = []
        if isinstance(self.guild, Guild):
            for role_id in map(int, role_mentions):
                role = self.guild.get_role(role_id)
                if role is not None:
                    r.append(role)

    def _handle_call(self, call: Optional[CallPayload]) -> None:
        if call is None or self.type is not MessageType.call:
            self.call = None
            return

        participants = []
        for uid in map(int, call.get('participants', [])):
            if uid == self.author.id:
                participants.append(self.author)
            else:
                user = utils.find(lambda u: u.id == uid, self.mentions)
                if user is not None:
                    participants.append(user)

        self.call = CallMessage(message=self, ended_timestamp=call.get('ended_timestamp'), participants=participants)

    def _handle_components(self, data: List[ComponentPayload]) -> None:
        self.components = []
        for component_data in data:
            component = _component_factory(component_data, self)
            if component is not None:
                self.components.append(component)

    def _handle_interaction(self, data: MessageInteractionPayload):
        self.interaction = Interaction._from_message(self, **data)

    def _rebind_cached_references(
        self,
        new_guild: Guild,
        new_channel: Union[GuildChannel, Thread, PartialMessageable],
    ) -> None:
        self.guild = new_guild
        self.channel = new_channel  # type: ignore # Not all "GuildChannel" are messageable at the moment

    def _is_self_mentioned(self) -> bool:
        state = self._state
        guild = self.guild
        channel = self.channel
        settings = guild.notification_settings if guild else state.client.notification_settings

        if channel.type in (ChannelType.private, ChannelType.group) and not settings.muted and not channel.notification_settings.muted:  # type: ignore
            return True
        if state.user in self.mentions:
            return True
        if self.mention_everyone and not settings.suppress_everyone:
            return True
        if guild and guild.me and not settings.suppress_roles and guild.me.mentioned_in(self):
            return True
        return False

    @utils.cached_slot_property('_cs_raw_mentions')
    def raw_mentions(self) -> List[int]:
        """List[:class:`int`]: A property that returns an array of user IDs matched with
        the syntax of ``<@user_id>`` in the message content.

        This allows you to receive the user IDs of mentioned users
        even in a private message context.
        """
        return [int(x) for x in re.findall(r'<@!?([0-9]{15,20})>', self.content)]

    @utils.cached_slot_property('_cs_raw_channel_mentions')
    def raw_channel_mentions(self) -> List[int]:
        """List[:class:`int`]: A property that returns an array of channel IDs matched with
        the syntax of ``<#channel_id>`` in the message content.
        """
        return [int(x) for x in re.findall(r'<#([0-9]{15,20})>', self.content)]

    @utils.cached_slot_property('_cs_raw_role_mentions')
    def raw_role_mentions(self) -> List[int]:
        """List[:class:`int`]: A property that returns an array of role IDs matched with
        the syntax of ``<@&role_id>`` in the message content.
        """
        return [int(x) for x in re.findall(r'<@&([0-9]{15,20})>', self.content)]

    @utils.cached_slot_property('_cs_channel_mentions')
    def channel_mentions(self) -> List[Union[GuildChannel, Thread]]:
        if self.guild is None:
            return []
        it = filter(None, map(self.guild._resolve_channel, self.raw_channel_mentions))
        return utils._unique(it)

    @utils.cached_slot_property('_cs_clean_content')
    def clean_content(self) -> str:
        """:class:`str`: A property that returns the content in a "cleaned up"
        manner. This basically means that mentions are transformed
        into the way the client shows it. e.g. ``<#id>`` will transform
        into ``#name``.

        This will also transform @everyone and @here mentions into
        non-mentions.

        .. note::

            This *does not* affect markdown. If you want to escape
            or remove markdown then use :func:`utils.escape_markdown` or :func:`utils.remove_markdown`
            respectively, along with this function.
        """

        if self.guild:

            def resolve_member(id: int) -> str:
                m = self.guild.get_member(id) or utils.get(self.mentions, id=id)  # type: ignore
                return f'@{m.display_name}' if m else '@deleted-user'

            def resolve_role(id: int) -> str:
                r = self.guild.get_role(id) or utils.get(self.role_mentions, id=id)  # type: ignore
                return f'@{r.name}' if r else '@deleted-role'

            def resolve_channel(id: int) -> str:
                c = self.guild._resolve_channel(id)  # type: ignore
                return f'#{c.name}' if c else '#deleted-channel'

        else:

            def resolve_member(id: int) -> str:
                m = utils.get(self.mentions, id=id)
                return f'@{m.display_name}' if m else '@deleted-user'

            def resolve_role(id: int) -> str:
                return '@deleted-role'

            def resolve_channel(id: int) -> str:
                return '#deleted-channel'

        transforms = {
            '@': resolve_member,
            '@!': resolve_member,
            '#': resolve_channel,
            '@&': resolve_role,
        }

        def repl(match: re.Match) -> str:
            type = match[1]
            id = int(match[2])
            transformed = transforms[type](id)
            return transformed

        result = re.sub(r'<(@[!&]?|#)([0-9]{15,20})>', repl, self.content)

        return escape_mentions(result)

    @property
    def created_at(self) -> datetime.datetime:
        """:class:`datetime.datetime`: The message's creation time in UTC."""
        return utils.snowflake_time(self.id)

    @property
    def edited_at(self) -> Optional[datetime.datetime]:
        """Optional[:class:`datetime.datetime`]: An aware UTC datetime object containing the edited time of the message."""
        return self._edited_timestamp

    @property
    def thread(self) -> Optional[Thread]:
        """Optional[:class:`Thread`]: The public thread created from this message, if it exists.

        .. note::

            For messages received via the gateway this does not retrieve archived threads, as they
            are not retained in the internal cache. Use :meth:`fetch_thread` instead.

        .. versionadded:: 2.1
        """
        if self.guild is not None:
            # Fall back to guild threads in case one was created after the message
            return self._thread or self.guild.get_thread(self.id)

    def is_system(self) -> bool:
        """:class:`bool`: Whether the message is a system message.

        A system message is a message that is constructed entirely by the Discord API
        in response to something.

        .. versionadded:: 1.3
        """
        return self.type not in (
            MessageType.default,
            MessageType.reply,
            MessageType.chat_input_command,
            MessageType.context_menu_command,
            MessageType.thread_starter_message,
            MessageType.poll_result,
        )

    def is_acked(self) -> bool:
        """:class:`bool`: Whether the message has been marked as read.

        .. versionadded:: 2.1
        """
        read_state = self._state.get_read_state(self.channel.id)
        return read_state.last_acked_id >= self.id if read_state.last_acked_id else False

    @utils.cached_slot_property('_cs_system_content')
    def system_content(self) -> str:
        r""":class:`str`: A property that returns the content that is rendered
        regardless of the :attr:`Message.type`.

        In the case of :attr:`MessageType.default` and :attr:`MessageType.reply`\,
        this just returns the regular :attr:`Message.content`. Otherwise this
        returns an English message denoting the contents of the system message.
        """
        if self.type is MessageType.recipient_add:
            if self.channel.type is ChannelType.group:
                return f'{self.author.name} added {self.mentions[0].name} to the group.'
            else:
                return f'{self.author.name} added {self.mentions[0].name} to the thread.'

        if self.type is MessageType.recipient_remove:
            if self.channel.type is ChannelType.group:
                return f'{self.author.name} removed {self.mentions[0].name} from the group.'
            else:
                return f'{self.author.name} removed {self.mentions[0].name} from the thread.'

        if self.type is MessageType.channel_name_change:
            if getattr(self.channel, 'parent', self.channel).type is ChannelType.forum:
                return f'{self.author.name} changed the post title: **{self.content}**'
            else:
                return f'{self.author.name} changed the channel name: **{self.content}**'

        if self.type is MessageType.channel_icon_change:
            return f'{self.author.name} changed the group icon.'

        if self.type is MessageType.pins_add:
            return f'{self.author.name} pinned a message to this channel.'

        if self.type is MessageType.new_member:
            formats = [
                "{0} joined the party.",
                "{0} is here.",
                "Welcome, {0}. We hope you brought pizza.",
                "A wild {0} appeared.",
                "{0} just landed.",
                "{0} just slid into the server.",
                "{0} just showed up!",
                "Welcome {0}. Say hi!",
                "{0} hopped into the server.",
                "Everyone welcome {0}!",
                "Glad you're here, {0}.",
                "Good to see you, {0}.",
                "Yay you made it, {0}!",
            ]

            created_at_ms = int(self.created_at.timestamp() * 1000)
            return formats[created_at_ms % len(formats)].format(self.author.name)

        if self.type is MessageType.call:
            call_ended = self.call.ended_timestamp is not None  # type: ignore

            if self.channel.me in self.call.participants:  # type: ignore
                return f'{self.author.name} started a call.'
            elif call_ended:
                return f'You missed a call from {self.author.name} that lasted {int((utils.utcnow() - self.call.ended_timestamp).total_seconds())} seconds.'  # type: ignore
            else:
                return f'{self.author.name} started a call \N{EM DASH} Join the call.'

        if self.type is MessageType.premium_guild_subscription:
            if not self.content:
                return f'{self.author.name} just boosted the server!'
            else:
                return f'{self.author.name} just boosted the server **{self.content}** times!'

        if self.type is MessageType.premium_guild_tier_1:
            if not self.content:
                return f'{self.author.name} just boosted the server! {self.guild} has achieved **Level 1!**'
            else:
                return f'{self.author.name} just boosted the server **{self.content}** times! {self.guild} has achieved **Level 1!**'

        if self.type is MessageType.premium_guild_tier_2:
            if not self.content:
                return f'{self.author.name} just boosted the server! {self.guild} has achieved **Level 2!**'
            else:
                return f'{self.author.name} just boosted the server **{self.content}** times! {self.guild} has achieved **Level 2!**'

        if self.type is MessageType.premium_guild_tier_3:
            if not self.content:
                return f'{self.author.name} just boosted the server! {self.guild} has achieved **Level 3!**'
            else:
                return f'{self.author.name} just boosted the server **{self.content}** times! {self.guild} has achieved **Level 3!**'

        if self.type is MessageType.channel_follow_add:
            return (
                f'{self.author.name} has added {self.content} to this channel. Its most important updates will show up here.'
            )

        if self.type is MessageType.guild_discovery_disqualified:
            return 'This server has been removed from Server Discovery because it no longer passes all the requirements. Check Server Settings for more details.'

        if self.type is MessageType.guild_discovery_requalified:
            return 'This server is eligible for Server Discovery again and has been automatically relisted!'

        if self.type is MessageType.guild_discovery_grace_period_initial_warning:
            return 'This server has failed Discovery activity requirements for 1 week. If this server fails for 4 weeks in a row, it will be automatically removed from Discovery.'

        if self.type is MessageType.guild_discovery_grace_period_final_warning:
            return 'This server has failed Discovery activity requirements for 3 weeks in a row. If this server fails for 1 more week, it will be removed from Discovery.'

        if self.type is MessageType.thread_created:
            return f'{self.author.name} started a thread: **{self.content}**. See all threads.'

        if self.type is MessageType.thread_starter_message:
            if self.reference is None or self.reference.resolved is None:
                return 'Sorry, we couldn\'t load the first message in this thread'

            # The resolved message for the reference will be a Message
            return self.reference.resolved.content  # type: ignore

        if self.type is MessageType.guild_invite_reminder:
            return 'Wondering who to invite?\nStart by inviting anyone who can help you build the server!'

        if self.type is MessageType.role_subscription_purchase and self.role_subscription is not None:
            total_months = self.role_subscription.total_months_subscribed
            months = '1 month' if total_months == 1 else f'{total_months} months'
            action = 'renewed' if self.role_subscription.is_renewal else 'joined'
            return f'{self.author.name} {action} **{self.role_subscription.tier_name}** and has been a subscriber of {self.guild} for {months}!'

        if self.type is MessageType.stage_start:
            return f'{self.author.name} started **{self.content}**'

        if self.type is MessageType.stage_end:
            return f'{self.author.name} ended **{self.content}**'

        if self.type is MessageType.stage_speaker:
            return f'{self.author.name} is now a speaker.'

        if self.type is MessageType.stage_raise_hand:
            return f'{self.author.name} requested to speak.'

        if self.type is MessageType.stage_topic:
            return f'{self.author.name} changed the Stage topic: **{self.content}**'

        if self.type is MessageType.guild_application_premium_subscription:
            return f'{self.author.name} upgraded {self.application.name if self.application else "a deleted application"} to premium for this server!'

        if self.type is MessageType.guild_incident_alert_mode_enabled:
            dt = utils.parse_time(self.content)
            dt_content = utils.format_dt(dt)
            return f'{self.author.name} enabled security actions until {dt_content}.'

        if self.type is MessageType.guild_incident_alert_mode_disabled:
            return f'{self.author.name} disabled security actions.'

        if self.type is MessageType.guild_incident_report_raid:
            return f'{self.author.name} reported a raid in {self.guild}.'

        if self.type is MessageType.guild_incident_report_false_alarm:
            return f'{self.author.name} reported a false alarm in {self.guild}.'

        if self.type is MessageType.purchase_notification and self.purchase_notification is not None:
            guild_product_purchase = self.purchase_notification.guild_product_purchase
            if guild_product_purchase is not None:
                return f'{self.author.name} has purchased {guild_product_purchase.product_name}!'

        if self.type is MessageType.poll_result:
            embed = self.embeds[0]  # Will always have 1 embed
            poll_title = utils.get(
                embed.fields,
                name='poll_question_text',
            )
            return f'{self.author.display_name}\'s poll {poll_title.value} has closed.'  # type: ignore

        # Fallback for unknown message types
        return self.content

    @overload
    async def edit(
        self,
        *,
        content: Optional[str] = ...,
        attachments: Sequence[Union[Attachment, _FileBase]] = ...,
        suppress: bool = ...,
        delete_after: Optional[float] = ...,
        allowed_mentions: Optional[AllowedMentions] = ...,
    ) -> Message:
        ...

    @overload
    async def edit(
        self,
        *,
        content: Optional[str] = ...,
        attachments: Sequence[Union[Attachment, _FileBase]] = ...,
        suppress: bool = ...,
        delete_after: Optional[float] = ...,
        allowed_mentions: Optional[AllowedMentions] = ...,
    ) -> Message:
        ...

    async def edit(
        self,
        content: Optional[str] = MISSING,
        attachments: Sequence[Union[Attachment, _FileBase]] = MISSING,
        suppress: bool = False,
        delete_after: Optional[float] = None,
        allowed_mentions: Optional[AllowedMentions] = MISSING,
    ) -> Message:
        """|coro|

        Edits the message.

        The content must be able to be transformed into a string via ``str(content)``.

        .. versionchanged:: 1.3
            The ``suppress`` keyword-only parameter was added.

        .. versionchanged:: 2.0
            Edits are no longer in-place, the newly edited message is returned instead.

        .. versionchanged:: 2.0
            This function will now raise :exc:`TypeError` instead of
            ``InvalidArgument``.

        Parameters
        -----------
        content: Optional[:class:`str`]
            The new content to replace the message with.
            Could be ``None`` to remove the content.
        attachments: List[Union[:class:`Attachment`, :class:`File`, :class:`CloudFile`]]
            A list of attachments to keep in the message as well as new files to upload. If ``[]`` is passed
            then all attachments are removed.

            .. note::

                New files will always appear after current attachments.

            .. versionadded:: 2.0
        suppress: :class:`bool`
            Whether to suppress embeds for the message. This removes
            all the embeds if set to ``True``. If set to ``False``
            this brings the embeds back if they were suppressed.
            Using this parameter requires :attr:`~.Permissions.manage_messages`.
        delete_after: Optional[:class:`float`]
            If provided, the number of seconds to wait in the background
            before deleting the message we just edited. If the deletion fails,
            then it is silently ignored.
        allowed_mentions: Optional[:class:`~discord.AllowedMentions`]
            Controls the mentions being processed in this message. If this is
            passed, then the object is merged with :attr:`~discord.Client.allowed_mentions`.
            The merging behaviour only overrides attributes that have been explicitly passed
            to the object, otherwise it uses the attributes set in :attr:`~discord.Client.allowed_mentions`.
            If no object is passed at all then the defaults given by :attr:`~discord.Client.allowed_mentions`
            are used instead.

            .. versionadded:: 1.4

        Raises
        -------
        HTTPException
            Editing the message failed.
        Forbidden
            Tried to suppress a message without permissions or
            edit a message that isn't yours.
        NotFound
            This message does not exist.

        Returns
        --------
        :class:`Message`
            The newly edited message.
        """

        if content is not MISSING:
            previous_allowed_mentions = self._state.allowed_mentions
        else:
            previous_allowed_mentions = None

        if suppress is not MISSING:
            flags = MessageFlags._from_value(self.flags.value)
            flags.suppress_embeds = suppress
        else:
            flags = MISSING

        with handle_message_parameters(
            content=content,
            flags=flags,
            attachments=attachments,
            allowed_mentions=allowed_mentions,
            previous_allowed_mentions=previous_allowed_mentions,
        ) as params:
            data = await self._state.http.edit_message(self.channel.id, self.id, params=params)
            message = Message(state=self._state, channel=self.channel, data=data)

        if delete_after is not None:
            await self.delete(delay=delete_after)

        return message

    async def add_files(self, *files: _FileBase) -> Message:
        r"""|coro|

        Adds new files to the end of the message attachments.

        .. versionadded:: 2.0

        Parameters
        -----------
        \*files: Union[:class:`File`, :class:`CloudFile`]
            New files to add to the message.

        Raises
        -------
        HTTPException
            Editing the message failed.
        Forbidden
            Tried to edit a message that isn't yours.

        Returns
        --------
        :class:`Message`
            The newly edited message.
        """
        return await self.edit(attachments=[*self.attachments, *files])

    async def remove_attachments(self, *attachments: Attachment) -> Message:
        r"""|coro|

        Removes attachments from the message.

        .. versionadded:: 2.0

        Parameters
        -----------
        \*attachments: :class:`Attachment`
            Attachments to remove from the message.

        Raises
        -------
        HTTPException
            Editing the message failed.
        Forbidden
            Tried to edit a message that isn't yours.

        Returns
        --------
        :class:`Message`
            The newly edited message.
        """
        return await self.edit(attachments=[a for a in self.attachments if a not in attachments])

    @utils.deprecated("Message.channel.application_commands")
    def message_commands(
        self,
        query: Optional[str] = None,
        *,
        limit: Optional[int] = None,
        command_ids: Optional[Collection[int]] = None,
        application: Optional[Snowflake] = None,
        with_applications: bool = True,
    ) -> AsyncIterator[MessageCommand]:
        """Returns a :term:`asynchronous iterator` of the message commands available to use on the message.

        .. deprecated:: 2.1

        Examples
        ---------

        Usage ::

            async for command in message.message_commands():
                print(command.name)

        Flattening into a list ::

            commands = [command async for command in message.message_commands()]
            # commands is now a list of MessageCommand...

        All parameters are optional.

        Parameters
        ----------
        query: Optional[:class:`str`]
            The query to search for. Specifying this limits results to 25 commands max.
        limit: Optional[:class:`int`]
            The maximum number of commands to send back. If ``None``, returns all commands.
        command_ids: Optional[List[:class:`int`]]
            List of up to 100 command IDs to search for. If the command doesn't exist, it won't be returned.

            If ``limit`` is passed alongside this parameter, this parameter will serve as a "preferred commands" list.
            This means that the endpoint will return the found commands + up to ``limit`` more, if available.
        application: Optional[:class:`~discord.abc.Snowflake`]
            Whether to return this application's commands. Always set to DM recipient in a private channel context.
        with_applications: :class:`bool`
            Whether to include applications in the response.

        Raises
        ------
        TypeError
            Both query and command_ids are passed.
            Attempted to fetch commands in a DM with a non-bot user.
        ValueError
            The limit was not greater than or equal to 0.
        HTTPException
            Getting the commands failed.
        ~discord.Forbidden
            You do not have permissions to get the commands.
        ~discord.HTTPException
            The request to get the commands failed.

        Yields
        -------
        :class:`.MessageCommand`
            A message command.
        """
        return _handle_commands(
            self,
            ApplicationCommandType.message,
            query=query,
            limit=limit,
            command_ids=command_ids,
            application=application,
            target=self,
        )

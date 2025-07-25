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

import datetime
import inspect
import itertools
from operator import attrgetter
from typing import Any, Awaitable, Callable, Collection, Dict, List, Optional, TYPE_CHECKING, Tuple, TypeVar, Union

import discord.abc

from . import utils
from .asset import Asset
from .utils import MISSING
from .user import BaseUser, User, _UserTag
from .permissions import Permissions
from .enums import Status, try_enum
from .errors import ClientException
from .colour import Colour
from .object import Object
from .flags import MemberFlags
from .voice_client import VoiceClient

__all__ = (
    'VoiceState',
    'Member',
)

T = TypeVar('T', bound=type)

if TYPE_CHECKING:
    from typing_extensions import Self

    from .activity import ActivityTypes
    from .asset import Asset
    from .channel import DMChannel, VoiceChannel, StageChannel, GroupChannel
    from .client import Client
    from .flags import PublicUserFlags
    from .guild import Guild
    from .profile import MemberProfile
    from .types.activity import (
        BasePresenceUpdate,
    )
    from .types.member import (
        MemberWithUser as MemberWithUserPayload,
        Member as MemberPayload,
        UserWithMember as UserWithMemberPayload,
    )
    from .types.gateway import GuildMemberUpdateEvent
    from .types.user import AvatarDecorationData, PartialUser as PartialUserPayload
    from .abc import Snowflake
    from .state import ConnectionState, Presence
    from .message import Message
    from .role import Role
    from .types.voice import BaseVoiceState as VoiceStatePayload
    from .relationship import Relationship
    from .calls import PrivateCall
    from .primary_guild import PrimaryGuild

    VocalGuildChannel = Union[VoiceChannel, StageChannel]
    ConnectableChannel = Union[VocalGuildChannel, DMChannel, GroupChannel]


class VoiceState:
    """Represents a Discord user's voice state.

    Attributes
    ------------
    deaf: :class:`bool`
        Indicates if the user is currently deafened by the guild.

        Doesn't apply to private channels.
    mute: :class:`bool`
        Indicates if the user is currently muted by the guild.

        Doesn't apply to private channels.
    self_mute: :class:`bool`
        Indicates if the user is currently muted by their own accord.
    self_deaf: :class:`bool`
        Indicates if the user is currently deafened by their own accord.
    self_stream: :class:`bool`
        Indicates if the user is currently streaming via 'Go Live' feature.

        .. versionadded:: 1.3

    self_video: :class:`bool`
        Indicates if the user is currently broadcasting video.
    suppress: :class:`bool`
        Indicates if the user is suppressed from speaking.

        Only applicable to stage channels.

        .. versionadded:: 1.7

    requested_to_speak_at: Optional[:class:`datetime.datetime`]
        An aware datetime object that specifies the date and time in UTC that the member
        requested to speak. It will be ``None`` if they are not requesting to speak
        anymore or have been accepted to speak.

        Only applicable to stage channels.

        .. versionadded:: 1.7

    afk: :class:`bool`
        Indicates if the user is currently in the AFK channel in the guild.
    channel: Optional[Union[:class:`VoiceChannel`, :class:`StageChannel`, :class:`DMChannel`, :class:`GroupChannel`]]
        The voice channel that the user is currently connected to. ``None`` if the user
        is not currently in a voice channel.
    """

    __slots__ = (
        'session_id',
        'deaf',
        'mute',
        'self_mute',
        'self_stream',
        'self_video',
        'self_deaf',
        'afk',
        'channel',
        'requested_to_speak_at',
        'suppress',
    )

    def __init__(self, *, data: VoiceStatePayload, channel: Optional[ConnectableChannel] = None):
        self.session_id: Optional[str] = data.get('session_id')
        self._update(data, channel)

    def _update(self, data: VoiceStatePayload, channel: Optional[ConnectableChannel]):
        self.self_mute: bool = data.get('self_mute', False)
        self.self_deaf: bool = data.get('self_deaf', False)
        self.self_stream: bool = data.get('self_stream', False)
        self.self_video: bool = data.get('self_video', False)
        self.afk: bool = data.get('suppress', False)
        self.mute: bool = data.get('mute', False)
        self.deaf: bool = data.get('deaf', False)
        self.suppress: bool = data.get('suppress', False)
        self.requested_to_speak_at: Optional[datetime.datetime] = utils.parse_time(data.get('request_to_speak_timestamp'))
        self.channel: Optional[ConnectableChannel] = channel

    def __repr__(self) -> str:
        attrs = [
            ('self_mute', self.self_mute),
            ('self_deaf', self.self_deaf),
            ('self_stream', self.self_stream),
            ('suppress', self.suppress),
            ('requested_to_speak_at', self.requested_to_speak_at),
            ('channel', self.channel),
        ]
        inner = ' '.join('%s=%r' % t for t in attrs)
        return f'<{self.__class__.__name__} {inner}>'


def flatten_user(cls: T) -> T:
    for attr, value in itertools.chain(BaseUser.__dict__.items(), User.__dict__.items()):
        # Ignore private/special methods
        if attr.startswith('_'):
            continue

        # Don't override what we already have
        if attr in cls.__dict__:
            continue

        # If it's a slotted attribute or a property, redirect it
        # Slotted members are implemented as member_descriptors in Type.__dict__
        if not hasattr(value, '__annotations__') or isinstance(value, utils.CachedSlotProperty):
            getter = attrgetter('_user.' + attr)
            setattr(cls, attr, property(getter, doc=f'Equivalent to :attr:`User.{attr}`'))
        else:
            # Technically, this can also use attrgetter,
            # however I'm not sure how I feel about "functions" returning properties
            # It probably breaks something in Sphinx
            # Probably a member function by now
            def generate_function(x):
                # We want Sphinx to properly show coroutine functions as coroutines
                if inspect.iscoroutinefunction(value):

                    async def general(self, *args, **kwargs):  # type: ignore
                        return await getattr(self._user, x)(*args, **kwargs)

                else:

                    def general(self, *args, **kwargs):
                        return getattr(self._user, x)(*args, **kwargs)

                general.__name__ = x
                return general

            func = generate_function(attr)
            func = utils.copy_doc(value)(func)
            setattr(cls, attr, func)

    return cls


@flatten_user
class Member(discord.abc.Messageable, discord.abc.Connectable, _UserTag):
    """Represents a Discord member to a :class:`Guild`.

    This implements a lot of the functionality of :class:`User`.

    .. container:: operations

        .. describe:: x == y

            Checks if two members are equal.
            Note that this works with :class:`User` instances too.

        .. describe:: x != y

            Checks if two members are not equal.
            Note that this works with :class:`User` instances too.

        .. describe:: hash(x)

            Returns the member's hash.

        .. describe:: str(x)

            Returns the member's handle (e.g. ``name`` or ``name#discriminator``).

    Attributes
    ----------
    joined_at: Optional[:class:`datetime.datetime`]
        An aware datetime object that specifies the date and time in UTC that the member joined the guild.
        If the member left and rejoined the guild, this will be the latest date. In certain cases, this can be ``None``.
    guild: :class:`Guild`
        The guild that the member belongs to.
    nick: Optional[:class:`str`]
        The guild specific nickname of the user. Takes precedence over the global name.
    pending: :class:`bool`
        Whether the member is pending member verification.

        .. versionadded:: 1.6
    premium_since: Optional[:class:`datetime.datetime`]
        An aware datetime object that specifies the date and time in UTC when the member used their
        "Nitro boost" on the guild, if available. This could be ``None``.
    timed_out_until: Optional[:class:`datetime.datetime`]
        An aware datetime object that specifies the date and time in UTC that the member's time out will expire.
        This will be set to ``None`` or a time in the past if the user is not timed out.

        .. versionadded:: 2.0
    """

    __slots__ = (
        '_roles',
        'joined_at',
        'premium_since',
        'guild',
        'pending',
        'nick',
        'timed_out_until',
        '_presence',
        '_user',
        '_state',
        '_avatar',
        '_avatar_decoration_data',
        '_banner',
        '_flags',
    )

    if TYPE_CHECKING:
        name: str
        id: int
        discriminator: str
        global_name: Optional[str]
        bot: bool
        system: bool
        created_at: datetime.datetime
        default_avatar: Asset
        avatar: Optional[Asset]
        avatar_decoration: Optional[Asset]
        avatar_decoration_sku_id: Optional[int]
        avatar_decoration_expires_at: Optional[datetime.datetime]
        is_pomelo: Callable[[], bool]
        relationship: Optional[Relationship]
        is_friend: Callable[[], bool]
        is_blocked: Callable[[], bool]
        dm_channel: Optional[DMChannel]
        call: Optional[PrivateCall]
        create_dm: Callable[[], Awaitable[DMChannel]]
        block: Callable[[], Awaitable[None]]
        unblock: Callable[[], Awaitable[None]]
        remove_friend: Callable[[], Awaitable[None]]
        send_friend_request: Callable[[], Awaitable[None]]
        fetch_mutual_friends: Callable[[], Awaitable[List[User]]]
        fetch_note: Callable[[], Awaitable[Optional[str]]]
        set_note: Callable[[Optional[str]], Awaitable[None]]
        delete_note: Callable[[], Awaitable[None]]
        public_flags: PublicUserFlags
        banner: Optional[Asset]
        accent_color: Optional[Colour]
        accent_colour: Optional[Colour]
        primary_guild: PrimaryGuild

    def __init__(self, *, data: MemberWithUserPayload, guild: Guild, state: ConnectionState):
        self._state: ConnectionState = state
        self._user: User = state.store_user(data['user'])
        self.guild: Guild = guild
        self.joined_at: Optional[datetime.datetime] = utils.parse_time(data.get('joined_at'))
        self.premium_since: Optional[datetime.datetime] = utils.parse_time(data.get('premium_since'))
        self._roles: utils.SnowflakeList = utils.SnowflakeList(map(int, data['roles']))
        self._presence: Optional[Presence] = None
        self.nick: Optional[str] = data.get('nick', None)
        self.pending: bool = data.get('pending', False)
        self._avatar: Optional[str] = data.get('avatar')
        self._avatar_decoration_data: Optional[AvatarDecorationData] = data.get('avatar_decoration_data')
        self._banner: Optional[str] = data.get('banner')
        self._flags: int = data.get('flags', 0)
        self.timed_out_until: Optional[datetime.datetime] = utils.parse_time(data.get('communication_disabled_until'))

    def __str__(self) -> str:
        return str(self._user)

    def __repr__(self) -> str:
        return (
            f'<Member id={self._user.id} name={self._user.name!r} global_name={self._user.global_name!r}'
            f' bot={self._user.bot} nick={self.nick!r} guild={self.guild!r}>'
        )

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _UserTag) and other.id == self.id

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash(self._user)

    @classmethod
    def _from_message(cls, *, message: Message, data: MemberPayload) -> Self:
        author = message.author
        data['user'] = author._to_minimal_user_json()  # type: ignore
        return cls(data=data, guild=message.guild, state=message._state)  # type: ignore

    def _update_from_message(self, data: MemberPayload) -> None:
        self.joined_at = utils.parse_time(data.get('joined_at'))
        self.premium_since = utils.parse_time(data.get('premium_since'))
        self._roles = utils.SnowflakeList(map(int, data['roles']))
        self.nick = data.get('nick', None)
        self.pending = data.get('pending', False)
        self._avatar = data.get('avatar')
        self._avatar_decoration_data = data.get('avatar_decoration_data')
        self._banner = data.get('banner')
        self._flags = data.get('flags', 0)
        self.timed_out_until = utils.parse_time(data.get('communication_disabled_until'))

    @classmethod
    def _try_upgrade(cls, *, data: UserWithMemberPayload, guild: Guild, state: ConnectionState) -> Union[User, Self]:
        # A User object with a 'member' key
        try:
            member_data = data.pop('member')
        except KeyError:
            return state.create_user(data)
        else:
            member_data['user'] = data  # type: ignore
            return cls(data=member_data, guild=guild, state=state)  # type: ignore

    @classmethod
    def _copy(cls, member: Self) -> Self:
        self = cls.__new__(cls)  # to bypass __init__

        self._roles = utils.SnowflakeList(member._roles, is_sorted=True)
        self.joined_at = member.joined_at
        self.premium_since = member.premium_since
        self._presence = member._presence
        self.guild = member.guild
        self.nick = member.nick
        self.pending = member.pending
        self.timed_out_until = member.timed_out_until
        self._flags = member._flags
        self._state = member._state
        self._avatar = member._avatar
        self._avatar_decoration_data = member._avatar_decoration_data
        self._banner = member._banner

        # Reference will not be copied unless necessary by PRESENCE_UPDATE
        # See below
        self._user = member._user
        return self

    def _update(self, data: Union[GuildMemberUpdateEvent, MemberWithUserPayload]) -> Optional[Member]:
        old = Member._copy(self)

        # Some changes are optional
        # If they aren't in the payload then they didn't change
        try:
            self.nick = data['nick']  # pyright: ignore[reportTypedDictNotRequiredAccess]
        except KeyError:
            pass

        try:
            self.pending = data['pending']  # pyright: ignore[reportTypedDictNotRequiredAccess]
        except KeyError:
            pass

        self.premium_since = utils.parse_time(data.get('premium_since'))
        self.timed_out_until = utils.parse_time(data.get('communication_disabled_until'))
        self._roles = utils.SnowflakeList(map(int, data['roles']))
        self._avatar = data.get('avatar')
        self._banner = data.get('banner')
        self._flags = data.get('flags', 0)

        attrs = {'joined_at', 'premium_since', '_roles', '_avatar', '_banner', 'timed_out_until', 'nick', 'pending'}

        if any(getattr(self, attr) != getattr(old, attr) for attr in attrs):
            return old

    def _presence_update(
        self, data: BasePresenceUpdate, user: Union[PartialUserPayload, Tuple[()]]
    ) -> Optional[Tuple[User, User]]:
        self._presence = self._state.create_presence(data)
        return self._user._update_self(user)

    def _get_voice_client_key(self) -> Tuple[int, str]:
        return self._state.self_id, 'self_id'  # type: ignore # self_id is always set at this point

    def _get_voice_state_pair(self) -> Tuple[int, int]:
        return self._state.self_id, self.dm_channel.id  # type: ignore # self_id is always set at this point

    async def _get_channel(self) -> DMChannel:
        ch = await self.create_dm()
        return ch

    @utils.copy_doc(discord.abc.Connectable.connect)
    async def connect(
        self,
        *,
        timeout: float = 60.0,
        reconnect: bool = True,
        cls: Callable[[Client, discord.abc.VocalChannel], discord.abc.T] = VoiceClient,
        ring: bool = True,
    ) -> discord.abc.T:
        channel = await self._get_channel()
        ret = await super().connect(timeout=timeout, reconnect=reconnect, cls=cls, _channel=channel)

        if ring:
            await channel._initial_ring()
        return ret

    @property
    def presence(self) -> Presence:
        state = self._state
        return self._presence or state.get_presence(self._user.id, self.guild.id) or state.create_offline_presence()

    @property
    def status(self) -> Status:
        """:class:`Status`: The member's overall status."""
        return try_enum(Status, self.presence.client_status.status)

    @property
    def raw_status(self) -> str:
        """:class:`str`: The member's overall status as a string value.

        .. versionadded:: 1.5
        """
        return self.presence.client_status.status

    @property
    def mobile_status(self) -> Status:
        """:class:`Status`: The member's status on a mobile device, if applicable."""
        return try_enum(Status, self.presence.client_status.mobile or 'offline')

    @property
    def desktop_status(self) -> Status:
        """:class:`Status`: The member's status on the desktop client, if applicable."""
        return try_enum(Status, self.presence.client_status.desktop or 'offline')

    @property
    def web_status(self) -> Status:
        """:class:`Status`: The member's status on the web client, if applicable."""
        return try_enum(Status, self.presence.client_status.web or 'offline')

    @property
    def embedded_status(self) -> Status:
        """:class:`Status`: The member's status on an embedded client, if applicable.

        .. versionadded:: 2.1
        """
        return try_enum(Status, self.presence.client_status.embedded or 'offline')

    def is_on_mobile(self) -> bool:
        """:class:`bool`: A helper function that determines if a member is active on a mobile device."""
        return self.presence.client_status.mobile is not None

    @property
    def colour(self) -> Colour:
        """:class:`Colour`: A property that returns a colour denoting the rendered colour
        for the member. If the default colour is the one rendered then an instance
        of :meth:`Colour.default` is returned.

        There is an alias for this named :attr:`color`.
        """

        roles = self.roles[1:]  # Remove @everyone

        # Highest role with a colour is the one that's rendered
        for role in reversed(roles):
            if role.colour.value:
                return role.colour
        return Colour.default()

    @property
    def color(self) -> Colour:
        """:class:`Colour`: A property that returns a color denoting the rendered color for
        the member. If the default color is the one rendered then an instance of :meth:`Colour.default`
        is returned.

        There is an alias for this named :attr:`colour`.
        """
        return self.colour

    @property
    def roles(self) -> List[Role]:
        """List[:class:`Role`]: A :class:`list` of :class:`Role` that the member belongs to. Note
        that the first element of this list is always the default '@everyone'
        role.

        These roles are sorted by their position in the role hierarchy.
        """
        result = []
        g = self.guild
        for role_id in self._roles:
            role = g.get_role(role_id)
            if role:
                result.append(role)
        default_role = g.default_role
        if default_role:
            result.append(default_role)
        result.sort()
        return result

    @property
    def display_icon(self) -> Optional[Union[str, Asset]]:
        """Optional[Union[:class:`str`, :class:`Asset`]]: A property that returns the role icon that is rendered for
        this member. If no icon is shown then ``None`` is returned.

        .. versionadded:: 2.0
        """

        roles = self.roles[1:]  # remove @everyone
        for role in reversed(roles):
            icon = role.display_icon
            if icon:
                return icon

        return None

    @property
    def mention(self) -> str:
        """:class:`str`: Returns a string that allows you to mention the member."""
        return f'<@{self._user.id}>'

    @property
    def display_name(self) -> str:
        """:class:`str`: Returns the user's display name.

        For regular users this is just their global name or their username,
        but if they have a guild specific nickname then that
        is returned instead.
        """
        return self.nick or self.global_name or self.name

    @property
    def display_avatar(self) -> Asset:
        """:class:`Asset`: Returns the member's display avatar.

        For regular members this is just their avatar, but
        if they have a guild specific avatar then that
        is returned instead.

        .. versionadded:: 2.0
        """
        return self.guild_avatar or self._user.avatar or self._user.default_avatar

    @property
    def guild_avatar(self) -> Optional[Asset]:
        """Optional[:class:`Asset`]: Returns an :class:`Asset` for the guild avatar
        the member has. If unavailable, ``None`` is returned.

        .. versionadded:: 2.0
        """
        if self._avatar is None:
            return None
        return Asset._from_guild_avatar(self._state, self.guild.id, self.id, self._avatar)

    @property
    def display_avatar_decoration(self) -> Optional[Asset]:
        """Optional[:class:`Asset`]: Returns the member's display avatar decoration.

        If the user has a guild avatar decoration, that is returned.
        Otherwise, if they have a global avatar decoration, that is returned.
        If the user has no avatar decoration set, then ``None`` is returned.

        .. versionadded:: 2.1
        """
        return self.guild_avatar_decoration or self._user.avatar_decoration

    @property
    def display_avatar_decoration_sku_id(self) -> Optional[int]:
        """Optional[:class:`int`]: Returns the member's display avatar decoration's SKU ID.

        If the user has a guild avatar decoration, that is returned.
        Otherwise, if they have a global avatar decoration, that is returned.
        If the user has no avatar decoration set, then ``None`` is returned.

        .. versionadded:: 2.1
        """
        return self.guild_avatar_decoration_sku_id or self._user.avatar_decoration_sku_id

    @property
    def guild_avatar_decoration(self) -> Optional[Asset]:
        """Optional[:class:`Asset`]: Returns an :class:`Asset` for the guild avatar decoration the user has.

        If the user does not have a guild avatar decoration, ``None`` is returned.

        .. versionadded:: 2.1
        """
        if self._avatar_decoration_data is not None:
            return Asset._from_avatar_decoration(self._state, self._avatar_decoration_data['asset'])

    @property
    def guild_avatar_decoration_sku_id(self) -> Optional[int]:
        """Optional[:class:`int`]: Returns the guild avatar decoration's SKU ID.

        If the user does not have a guild avatar decoration, ``None`` is returned.

        .. versionadded:: 2.1
        """
        if self._avatar_decoration_data:
            return utils._get_as_snowflake(self._avatar_decoration_data, 'sku_id')

    @property
    def guild_avatar_decoration_expires_at(self) -> Optional[datetime.datetime]:
        """Optional[:class:`datetime.datetime`]: Returns the guild avatar decoration's expiration time.

        If the user does not have an expiring guild avatar decoration, ``None`` is returned.

        .. versionadded:: 2.1
        """
        if self._avatar_decoration_data:
            return utils.parse_timestamp(self._avatar_decoration_data.get('expires_at'), ms=False)

    @property
    def display_banner(self) -> Optional[Asset]:
        """Optional[:class:`Asset`]: Returns the member's displayed banner, if any.

        This is the member's guild banner if available, otherwise it's their
        global banner. If the member has no banner set then ``None`` is returned.

        .. versionadded:: 2.1
        """
        return self.guild_banner or self._user.banner

    @property
    def guild_banner(self) -> Optional[Asset]:
        """Optional[:class:`Asset`]: Returns an :class:`Asset` for the guild banner
        the member has. If unavailable, ``None`` is returned.

        .. versionadded:: 2.1
        """
        if self._banner is None:
            return None
        return Asset._from_guild_banner(self._state, self.guild.id, self.id, self._banner)

    @property
    def activities(self) -> Tuple[ActivityTypes, ...]:
        """Tuple[Union[:class:`BaseActivity`, :class:`Spotify`]]: Returns the activities that
        the user is currently doing.

        .. note::

            Due to a Discord API limitation, a user's Spotify activity may not appear
            if they are listening to a song with a title longer
            than 128 characters. See :issue:`1738` for more information.
        """
        return self.presence.activities

    @property
    def activity(self) -> Optional[ActivityTypes]:
        """Optional[Union[:class:`BaseActivity`, :class:`Spotify`]]: Returns the primary
        activity the user is currently doing. Could be ``None`` if no activity is being done.

        .. note::

            Due to a Discord API limitation, this may be ``None`` if
            the user is listening to a song on Spotify with a title longer
            than 128 characters. See :issue:`1738` for more information.

        .. note::

            A user may have multiple activities, these can be accessed under :attr:`activities`.
        """
        if self.activities:
            return self.activities[0]

    def mentioned_in(self, message: Message) -> bool:
        """Checks if the member is mentioned in the specified message.

        Parameters
        -----------
        message: :class:`Message`
            The message to check if you're mentioned in.

        Returns
        -------
        :class:`bool`
            Indicates if the member is mentioned in the message.
        """
        if message.guild is None or message.guild.id != self.guild.id:
            return False

        if self._user.mentioned_in(message):
            return True

        return any(self._roles.has(role.id) for role in message.role_mentions)

    @property
    def top_role(self) -> Role:
        """:class:`Role`: Returns the member's highest role.

        This is useful for figuring where a member stands in the role
        hierarchy chain.
        """
        guild = self.guild
        if len(self._roles) == 0:
            return guild.default_role

        return max(guild.get_role(rid) or guild.default_role for rid in self._roles)

    @property
    def guild_permissions(self) -> Permissions:
        """:class:`Permissions`: Returns the member's guild permissions.

        This only takes into consideration the guild permissions
        and not most of the implied permissions or any of the
        channel permission overwrites. For 100% accurate permission
        calculation, please use :meth:`abc.GuildChannel.permissions_for`.

        This does take into consideration guild ownership, the
        administrator implication, and whether the member is timed out.

        .. versionchanged:: 2.0
            Member timeouts are taken into consideration.
        """

        if self.guild.owner_id == self.id:
            return Permissions.all()

        base = Permissions.none()
        for r in self.roles:
            base.value |= r.permissions.value

        if base.administrator:
            return Permissions.all()

        if self.is_timed_out():
            base.value &= Permissions._timeout_mask()

        return base

    @property
    def voice(self) -> Optional[VoiceState]:
        """Optional[:class:`VoiceState`]: Returns the member's current voice state."""
        return self.guild._voice_state_for(self._user.id)

    @property
    def flags(self) -> MemberFlags:
        """:class:`MemberFlags`: Returns the member's flags.

        .. versionadded:: 2.0
        """
        return MemberFlags._from_value(self._flags)

    async def ban(
        self,
        *,
        delete_message_days: int = MISSING,
        delete_message_seconds: int = MISSING,
        reason: Optional[str] = None,
    ) -> None:
        """|coro|

        Bans this member. Equivalent to :meth:`Guild.ban`.
        """
        await self.guild.ban(
            self,
            reason=reason,
            delete_message_days=delete_message_days,
            delete_message_seconds=delete_message_seconds,
        )

    async def unban(self, *, reason: Optional[str] = None) -> None:
        """|coro|

        Unbans this member. Equivalent to :meth:`Guild.unban`.
        """
        await self.guild.unban(self, reason=reason)

    async def kick(self, *, reason: Optional[str] = None) -> None:
        """|coro|

        Kicks this member. Equivalent to :meth:`Guild.kick`.
        """
        await self.guild.kick(self, reason=reason)

    async def edit(
        self,
        *,
        nick: Optional[str] = MISSING,
        mute: bool = MISSING,
        deafen: bool = MISSING,
        suppress: bool = MISSING,
        roles: Collection[discord.abc.Snowflake] = MISSING,
        voice_channel: Optional[VocalGuildChannel] = MISSING,
        timed_out_until: Optional[datetime.datetime] = MISSING,
        avatar: Optional[bytes] = MISSING,
        banner: Optional[bytes] = MISSING,
        bio: Optional[str] = MISSING,
        bypass_verification: bool = MISSING,
        reason: Optional[str] = None,
    ) -> Optional[Member]:
        """|coro|

        Edits the member's data.

        Depending on the parameter passed, this requires different permissions listed below:

        +---------------------+---------------------------------------+
        |      Parameter      |              Permission               |
        +---------------------+---------------------------------------+
        | nick                | :attr:`Permissions.manage_nicknames`  |
        +---------------------+---------------------------------------+
        | mute                | :attr:`Permissions.mute_members`      |
        +---------------------+---------------------------------------+
        | deafen              | :attr:`Permissions.deafen_members`    |
        +---------------------+---------------------------------------+
        | roles               | :attr:`Permissions.manage_roles`      |
        +---------------------+---------------------------------------+
        | voice_channel       | :attr:`Permissions.move_members`      |
        +---------------------+---------------------------------------+
        | timed_out_until     | :attr:`Permissions.moderate_members`  |
        +---------------------+---------------------------------------+
        | bypass_verification | :attr:`Permissions.moderate_members`  |
        +---------------------+---------------------------------------+

        All parameters are optional.

        .. note::

            To upload an avatar or banner, a :term:`py:bytes-like object` must be passed in that
            represents the image being uploaded. If this is done through a file
            then the file must be opened via ``open('some_filename', 'rb')`` and
            the :term:`py:bytes-like object` is given through the use of ``fp.read()``.

        .. versionchanged:: 1.1
            Can now pass ``None`` to ``voice_channel`` to kick a member from voice.

        .. versionchanged:: 2.0
            The newly updated member is now optionally returned, if applicable.

        Parameters
        -----------
        nick: Optional[:class:`str`]
            The member's new nickname. Use ``None`` to remove the nickname.
        mute: :class:`bool`
            Indicates if the member should be guild muted or un-muted.
        deafen: :class:`bool`
            Indicates if the member should be guild deafened or un-deafened.
        suppress: :class:`bool`
            Indicates if the member should be suppressed in stage channels.

            .. versionadded:: 1.7
        roles: List[:class:`Role`]
            The member's new list of roles. This *replaces* the roles.
        voice_channel: Optional[Union[:class:`VoiceChannel`, :class:`StageChannel`]]
            The voice channel to move the member to.
            Pass ``None`` to kick them from voice.
        timed_out_until: Optional[:class:`datetime.datetime`]
            The date the member's timeout should expire, or ``None`` to remove the timeout.
            This must be a timezone-aware datetime object. Consider using :func:`utils.utcnow`.

            .. versionadded:: 2.0
        avatar: Optional[:class:`bytes`]
            The member's new guild avatar. Pass ``None`` to remove the avatar.
            You can only change your own guild avatar.

            .. versionadded:: 2.0
        banner: Optional[:class:`bytes`]
            The member's new guild banner. Pass ``None`` to remove the banner.
            You can only change your own guild banner.

            .. versionadded:: 2.0
        bio: Optional[:class:`str`]
            The member's new guild "about me". Pass ``None`` to remove the bio.
            You can only change your own guild bio.

            .. versionadded:: 2.0
        bypass_verification: :class:`bool`
            Indicates if the member should be allowed to bypass the guild verification requirements.

            .. versionadded:: 2.0
        reason: Optional[:class:`str`]
            The reason for editing this member. Shows up on the audit log.

        Raises
        -------
        Forbidden
            You do not have the proper permissions to do the action requested.
        HTTPException
            The operation failed.
        TypeError
            The datetime object passed to ``timed_out_until`` was not timezone-aware.

        Returns
        --------
        Optional[:class:`.Member`]
            The newly updated member, if applicable. This is not returned
            if certain fields are passed, such as ``suppress``.
        """
        http = self._state.http
        guild_id = self.guild.id
        me = self._user.id == self._state.self_id
        payload: Dict[str, Any] = {}
        data = None

        if nick is not MISSING:
            payload['nick'] = nick

        if avatar is not MISSING:
            payload['avatar'] = utils._bytes_to_base64_data(avatar) if avatar is not None else None

        if banner is not MISSING:
            payload['banner'] = utils._bytes_to_base64_data(banner) if banner is not None else None

        if bio is not MISSING:
            payload['bio'] = bio or ''

        if me and payload:
            data = await http.edit_me(self.guild.id, **payload)
            payload = {}

        if deafen is not MISSING:
            payload['deaf'] = deafen

        if mute is not MISSING:
            payload['mute'] = mute

        if suppress is not MISSING:
            voice_state_payload: Dict[str, Any] = {
                'suppress': suppress,
            }

            if self.voice is not None and self.voice.channel is not None:
                voice_state_payload['channel_id'] = self.voice.channel.id

            if suppress or self.bot:
                voice_state_payload['request_to_speak_timestamp'] = None

            if me:
                await http.edit_my_voice_state(guild_id, voice_state_payload)
            else:
                if not suppress:
                    voice_state_payload['request_to_speak_timestamp'] = datetime.datetime.utcnow().isoformat()
                await http.edit_voice_state(guild_id, self.id, voice_state_payload)

        if voice_channel is not MISSING:
            payload['channel_id'] = voice_channel and voice_channel.id

        if roles is not MISSING:
            payload['roles'] = tuple(r.id for r in roles)

        if timed_out_until is not MISSING:
            if timed_out_until is None:
                payload['communication_disabled_until'] = None
            else:
                if timed_out_until.tzinfo is None:
                    raise TypeError(
                        'timed_out_until must be an aware datetime. Consider using discord.utils.utcnow() or datetime.datetime.now().astimezone() for local time.'
                    )
                payload['communication_disabled_until'] = timed_out_until.isoformat()

        if bypass_verification is not MISSING:
            flags = MemberFlags._from_value(self._flags)
            flags.bypasses_verification = bypass_verification
            payload['flags'] = flags.value

        if payload:
            data = await http.edit_member(guild_id, self.id, reason=reason, **payload)

        if data:
            return Member(data=data, guild=self.guild, state=self._state)

    async def request_to_speak(self) -> None:
        """|coro|

        Request to speak in the connected channel.

        Only applies to stage channels.

        .. note::

            Requesting members that are not the client is equivalent
            to :attr:`.edit` providing ``suppress`` as ``False``.

        .. versionadded:: 1.7

        Raises
        -------
        ClientException
            You are not connected to a voice channel.
        Forbidden
            You do not have the proper permissions to do the action requested.
        HTTPException
            The operation failed.
        """
        if self.voice is None or self.voice.channel is None:
            raise ClientException('Cannot request to speak while not connected to a voice channel.')

        payload = {
            'channel_id': self.voice.channel.id,
            'request_to_speak_timestamp': datetime.datetime.utcnow().isoformat(),
        }

        if self._state.self_id != self.id:
            payload['suppress'] = False
            await self._state.http.edit_voice_state(self.guild.id, self.id, payload)
        else:
            await self._state.http.edit_my_voice_state(self.guild.id, payload)

    async def move_to(self, channel: Optional[VocalGuildChannel], *, reason: Optional[str] = None) -> None:
        """|coro|

        Moves a member to a new voice channel (they must be connected first).

        You must have :attr:`~Permissions.move_members` to do this.

        This raises the same exceptions as :meth:`edit`.

        .. versionchanged:: 1.1
            Can now pass ``None`` to kick a member from voice.

        Parameters
        -----------
        channel: Optional[Union[:class:`VoiceChannel`, :class:`StageChannel`]]
            The new voice channel to move the member to.
            Pass ``None`` to kick them from voice.
        reason: Optional[:class:`str`]
            The reason for doing this action. Shows up on the audit log.
        """
        await self.edit(voice_channel=channel, reason=reason)

    async def timeout(
        self, until: Optional[Union[datetime.timedelta, datetime.datetime]], /, *, reason: Optional[str] = None
    ) -> None:
        """|coro|

        Applies a time out to a member until the specified date time or for the
        given :class:`datetime.timedelta`.

        You must have :attr:`~Permissions.moderate_members` to do this.

        This raises the same exceptions as :meth:`edit`.

        Parameters
        -----------
        until: Optional[Union[:class:`datetime.timedelta`, :class:`datetime.datetime`]]
            If this is a :class:`datetime.timedelta` then it represents the amount of
            time the member should be timed out for. If this is a :class:`datetime.datetime`
            then it's when the member's timeout should expire. If ``None`` is passed then the
            timeout is removed. Note that the API only allows for timeouts up to 28 days.
        reason: Optional[:class:`str`]
            The reason for doing this action. Shows up on the audit log.

        Raises
        -------
        TypeError
            The ``until`` parameter was the wrong type or the datetime was not timezone-aware.
        """

        if until is None:
            timed_out_until = None
        elif isinstance(until, datetime.timedelta):
            timed_out_until = utils.utcnow() + until
        elif isinstance(until, datetime.datetime):
            timed_out_until = until
        else:
            raise TypeError(f'expected None, datetime.datetime, or datetime.timedelta not {until.__class__!r}')

        await self.edit(timed_out_until=timed_out_until, reason=reason)

    async def add_roles(self, *roles: Snowflake, reason: Optional[str] = None, atomic: bool = True) -> None:
        r"""|coro|

        Gives the member a number of :class:`Role`\s.

        You must have :attr:`~Permissions.manage_roles` to
        use this, and the added :class:`Role`\s must appear lower in the list
        of roles than the highest role of the client.

        Parameters
        -----------
        \*roles: :class:`abc.Snowflake`
            An argument list of :class:`abc.Snowflake` representing a :class:`Role`
            to give to the member.
        reason: Optional[:class:`str`]
            The reason for adding these roles. Shows up on the audit log.
        atomic: :class:`bool`
            Whether to atomically add roles. This will ensure that multiple
            operations will always be applied regardless of the current
            state of the cache.

        Raises
        -------
        Forbidden
            You do not have permissions to add these roles.
        HTTPException
            Adding roles failed.
        """

        if not atomic:
            new_roles = utils._unique(Object(id=r.id) for s in (self.roles[1:], roles) for r in s)
            await self.edit(roles=new_roles, reason=reason)
        else:
            req = self._state.http.add_role
            guild_id = self.guild.id
            user_id = self.id
            for role in roles:
                await req(guild_id, user_id, role.id, reason=reason)

    async def remove_roles(self, *roles: Snowflake, reason: Optional[str] = None, atomic: bool = True) -> None:
        r"""|coro|

        Removes :class:`Role`\s from this member.

        You must have :attr:`~Permissions.manage_roles` to
        use this, and the removed :class:`Role`\s must appear lower in the list
        of roles than the highest role of the client.

        Parameters
        -----------
        \*roles: :class:`abc.Snowflake`
            An argument list of :class:`abc.Snowflake` representing a :class:`Role`
            to remove from the member.
        reason: Optional[:class:`str`]
            The reason for removing these roles. Shows up on the audit log.
        atomic: :class:`bool`
            Whether to atomically remove roles. This will ensure that multiple
            operations will always be applied regardless of the current
            state of the cache.

        Raises
        -------
        Forbidden
            You do not have permissions to remove these roles.
        HTTPException
            Removing the roles failed.
        """

        if not atomic:
            new_roles = [Object(id=r.id) for r in self.roles[1:]]  # remove @everyone
            for role in roles:
                try:
                    new_roles.remove(Object(id=role.id))
                except ValueError:
                    pass

            await self.edit(roles=new_roles, reason=reason)
        else:
            req = self._state.http.remove_role
            guild_id = self.guild.id
            user_id = self.id
            for role in roles:
                await req(guild_id, user_id, role.id, reason=reason)

    def get_role(self, role_id: int, /) -> Optional[Role]:
        """Returns a role with the given ID from roles which the member has.

        .. versionadded:: 2.0

        Parameters
        -----------
        role_id: :class:`int`
            The ID to search for.

        Returns
        --------
        Optional[:class:`Role`]
            The role or ``None`` if not found in the member's roles.
        """
        return self.guild.get_role(role_id) if self._roles.has(role_id) else None

    def is_timed_out(self) -> bool:
        """Returns whether this member is timed out.

        .. versionadded:: 2.0

        Returns
        --------
        :class:`bool`
            ``True`` if the member is timed out. ``False`` otherwise.
        """
        if self.timed_out_until is not None:
            return utils.utcnow() < self.timed_out_until
        return False

    async def profile(
        self,
        *,
        with_mutual_guilds: bool = True,
        with_mutual_friends_count: bool = False,
        with_mutual_friends: bool = True,
    ) -> MemberProfile:
        """|coro|

        A shorthand method to retrieve a :class:`MemberProfile` for the member.

        Parameters
        ------------
        with_mutual_guilds: :class:`bool`
            Whether to fetch mutual guilds.
            This fills in :attr:`MemberProfile.mutual_guilds`.

            .. versionadded:: 2.0
        with_mutual_friends_count: :class:`bool`
            Whether to fetch the number of mutual friends.
            This fills in :attr:`MemberProfile.mutual_friends_count`.

            .. versionadded:: 2.0
        with_mutual_friends: :class:`bool`
            Whether to fetch mutual friends.
            This fills in :attr:`MemberProfile.mutual_friends` and :attr:`MemberProfile.mutual_friends_count`.

            .. versionadded:: 2.0

        Raises
        -------
        NotFound
            Not allowed to fetch this profile.
        HTTPException
            Fetching the profile failed.
        InvalidData
            The member is not in this guild or has blocked you.

        Returns
        --------
        :class:`MemberProfile`
            The profile of the member.
        """
        return await self.guild.fetch_member_profile(
            self._user.id,
            with_mutual_guilds=with_mutual_guilds,
            with_mutual_friends_count=with_mutual_friends_count,
            with_mutual_friends=with_mutual_friends,
        )

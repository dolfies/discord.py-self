"""
The MIT License (MIT)

Copyright (c) 2021-present Dolfies

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

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    List,
    Literal,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    Type,
    Union,
    runtime_checkable,
)

from .enums import (
    ApplicationCommandHandlerType,
    ApplicationCommandOptionType,
    ApplicationCommandPermissionType,
    ApplicationCommandType,
    ChannelType,
    InteractionType,
    Locale,
    try_enum,
)
from .flags import ApplicationCommandContext, ApplicationIntegrationType
from .interactions import _wrapped_interaction
from .mixins import Hashable
from .object import Object
from .permissions import Permissions
from .utils import _generate_nonce, _get_as_snowflake

if TYPE_CHECKING:
    from .abc import GuildChannel, Messageable, Snowflake, User as ABCUser
    from .application import CommandApplication, IntegrationApplication, PartialApplication
    from .file import _FileBase
    from .guild import Guild
    from .member import Member
    from .message import Message
    from .role import Role
    from .state import ConnectionState
    from .threads import Thread
    from .types.command import (
        ApplicationCommand as ApplicationCommandPayload,
        ApplicationCommandIndex as ApplicationCommandIndexPayload,
        ApplicationCommandIndexPermissions as ApplicationCommandIndexPermissionsPayload,
        ApplicationCommandOption,
        ApplicationCommandOptionChoice as OptionChoicePayload,
        ApplicationCommandPermissions as ApplicationCommandPermissionsPayload,
        GuildApplicationCommandPermissions as GuildApplicationCommandPermissionsPayload,
        SubCommand as SubCommandPayload,
        _ValueApplicationCommandOption as OptionPayload,
    )
    from .types.interactions import (
        ApplicationCommandInteractionData,
        ChatInputCommandInteractionData,
        MessageCommandInteractionData,
        PrimaryEntryPointCommandInteractionData,
        UserCommandInteractionData,
        ApplicationCommandInteractionDataOption as InteractionDataOption,
        _ValueApplicationCommandInteractionDataOption as InteractionDataValueOption,
    )
    from .types import gateway as gw
    from .types.gateway import ApplicationCommandAutocompleteChoice as ApplicationCommandAutocompleteChoicePayload
    from .types.message import PartialAttachment as PartialAttachmentPayload

    ApplicationCommandPermissionTarget = Union[
        'AllChannels',
        GuildChannel,
        Thread,
        Member,
        ABCUser,
        Role,
        Object,
    ]
    CommandApplicationTarget = Union[CommandApplication, IntegrationApplication, PartialApplication]

__all__ = (
    'BaseCommand',
    'UserCommand',
    'MessageCommand',
    'PrimaryEntryPointCommand',
    'SlashCommand',
    'SubCommand',
    'Option',
    'OptionChoice',
    'AllChannels',
    'ApplicationCommandPermissions',
    'GuildApplicationCommandPermissions',
    'ApplicationCommandAutocompleteChoice',
    'ApplicationCommandAutocomplete',
)


def _parse_localizations(data: Any, key: str, *, default: str = '') -> Tuple[str, Optional[str], Dict[Locale, str]]:
    value = data.get(key, default)
    if f'{key}_default' in data:
        # The evil command index rust service maps ``name`` -> ``name_default`` and throws the localized key in ``name``
        return data[f'{key}_default'], value, {}

    localizations = {try_enum(Locale, locale): value for locale, value in (data.get(f'{key}_localizations') or {}).items()}
    return value, data.get(f'{key}_localized'), localizations


def _commands_from_index(
    *,
    state: ConnectionState,
    data: ApplicationCommandIndexPayload,
    channel: Optional[Messageable] = None,
    guild: Optional[Guild] = None,
) -> List[Union[SlashCommand, UserCommand, MessageCommand, PrimaryEntryPointCommand]]:
    applications: Dict[int, Any] = {
        int(application['id']): state.create_command_application(application, guild=guild)
        for application in data.get('applications') or []
    }

    result = []
    for command in data['application_commands']:
        _, cls = _command_factory(command['type'])
        application = applications.get(int(command['application_id']))
        result.append(cls(state=state, data=command, channel=channel, guild=guild, application=application))
    return result


class AllChannels(Hashable):
    """Represents the special application command permission target for every channel in a guild.

    .. versionadded:: 2.2

    Attributes
    ----------
    guild: :class:`Guild`
        The guild the permission applies to.
    """

    __slots__ = ('guild',)

    def __init__(self, guild: Guild) -> None:
        self.guild: Guild = guild

    def __repr__(self) -> str:
        return f'<AllChannels guild={self.guild!r}>'

    @property
    def id(self) -> int:
        """:class:`int`: The special target ID, equivalent to ``guild.id - 1``."""
        return self.guild.id - 1


class ApplicationCommandPermissions:
    """Represents an application command permission overwrite for a guild.

    .. versionadded:: 2.2

    Parameters
    ----------
    target: Union[:class:`AllChannels`, :class:`abc.GuildChannel`, :class:`Thread`, :class:`Member`, :class:`abc.User`, :class:`Role`, :class:`Object`]
        The permission target. If this is an :class:`Object`, its ``type`` must be
        :class:`Role`, :class:`abc.User`, :class:`abc.GuildChannel`, or :class:`Thread`.
    permission: :class:`bool`
        Whether the command is allowed for the target.

    Attributes
    ----------
    id: :class:`int`
        The ID of the target role, user, or channel.
    type: :class:`ApplicationCommandPermissionType`
        The overwrite target type.
    permission: :class:`bool`
        Whether the command is allowed for the target.
    target: Union[:class:`AllChannels`, :class:`abc.GuildChannel`, :class:`Thread`, :class:`Member`, :class:`User`, :class:`Role`, :class:`Object`]
        The resolved target, or an :class:`Object` if it could not be resolved.
    guild: Optional[:class:`Guild`]
        The guild this overwrite applies to, if known.
    """

    __slots__ = ('id', 'type', 'permission', 'target', 'guild')

    def __init__(
        self,
        target: ApplicationCommandPermissionTarget,
        permission: bool = True,
        /,
    ) -> None:
        self.guild: Optional[Guild] = getattr(target, 'guild', None)
        self.id: int = target.id
        self.type: ApplicationCommandPermissionType = self._type_from_target(target)
        self.permission: bool = permission
        self.target: ApplicationCommandPermissionTarget = target

    def __repr__(self) -> str:
        return f'<ApplicationCommandPermissions id={self.id} type={self.type!r} permission={self.permission!r}>'

    @staticmethod
    def _type_from_target(target: ApplicationCommandPermissionTarget) -> ApplicationCommandPermissionType:
        from .abc import GuildChannel, User as ABCUser
        from .member import Member
        from .role import Role
        from .threads import Thread
        from .user import BaseUser

        if isinstance(target, AllChannels):
            return ApplicationCommandPermissionType.channel
        if isinstance(target, Role):
            return ApplicationCommandPermissionType.role
        if isinstance(target, (GuildChannel, Thread)):
            return ApplicationCommandPermissionType.channel
        if isinstance(target, ABCUser):
            return ApplicationCommandPermissionType.user
        if isinstance(target, Object):
            target_type = target.type
            if target_type is ABCUser:
                return ApplicationCommandPermissionType.user
            if target_type is GuildChannel:
                return ApplicationCommandPermissionType.channel
            try:
                if issubclass(target_type, Role):
                    return ApplicationCommandPermissionType.role
                if issubclass(target_type, (Thread, GuildChannel)):
                    return ApplicationCommandPermissionType.channel
                if issubclass(target_type, (Member, BaseUser)):
                    return ApplicationCommandPermissionType.user
            except TypeError:
                pass

        raise TypeError('target must be Role, Member, User, GuildChannel, Thread, AllChannels, or a typed Object')

    def _resolve_target(self, state: ConnectionState) -> ApplicationCommandPermissionTarget:
        guild = self.guild
        if self.type is ApplicationCommandPermissionType.role:
            from .role import Role

            return (guild.get_role(self.id) if guild is not None else None) or Object(id=self.id, type=Role)

        if self.type is ApplicationCommandPermissionType.user:
            from .member import Member

            return (
                (guild.get_member(self.id) if guild is not None else None)
                or state.get_user(self.id)
                or Object(id=self.id, type=Member)
            )

        if self.type is ApplicationCommandPermissionType.channel:
            from .abc import GuildChannel

            if guild is not None and self.id == guild.id - 1:
                return AllChannels(guild)

            return (guild.get_channel_or_thread(self.id) if guild is not None else None) or Object(
                id=self.id,
                type=GuildChannel,
            )

        return Object(id=self.id)

    @classmethod
    def with_state(
        cls,
        *,
        state: ConnectionState,
        data: ApplicationCommandPermissionsPayload,
        guild: Guild,
    ) -> ApplicationCommandPermissions:
        self = cls.__new__(cls)
        self.guild = guild
        self.id = int(data['id'])
        self.type = try_enum(ApplicationCommandPermissionType, data['type'])
        self.permission = data['permission']
        self.target = self._resolve_target(state)
        return self

    def to_dict(self) -> ApplicationCommandPermissionsPayload:
        return {
            'id': str(self.id),
            'type': self.type.value,
            'permission': self.permission,
        }

    @classmethod
    def _from_index(
        cls,
        *,
        state: ConnectionState,
        guild: Guild,
        data: ApplicationCommandIndexPermissionsPayload,
    ) -> List[ApplicationCommandPermissions]:
        permissions: List[ApplicationCommandPermissions] = []

        if 'user' in data:
            permissions.append(
                cls.with_state(
                    state=state,
                    guild=guild,
                    data={
                        'id': str(state.self_id),
                        'type': ApplicationCommandPermissionType.user.value,
                        'permission': data['user'],
                    },
                )
            )

        for role_id, permission in data.get('roles', {}).items():
            permissions.append(
                cls.with_state(
                    state=state,
                    guild=guild,
                    data={
                        'id': role_id,
                        'type': ApplicationCommandPermissionType.role.value,
                        'permission': permission,
                    },
                )
            )

        for channel_id, permission in data.get('channels', {}).items():
            permissions.append(
                cls.with_state(
                    state=state,
                    guild=guild,
                    data={
                        'id': channel_id,
                        'type': ApplicationCommandPermissionType.channel.value,
                        'permission': permission,
                    },
                )
            )

        return permissions


class GuildApplicationCommandPermissions:
    """Represents the configured application command permissions for a guild command.

    .. versionadded:: 2.2

    Attributes
    ----------
    id: :class:`int`
        The command ID, or the application ID for application-wide permissions.
    application_id: :class:`int`
        The ID of the application the permissions belong to.
    guild_id: :class:`int`
        The ID of the guild the permissions belong to.
    guild: :class:`Guild`
        The guild the permissions belong to.
    command: Optional[Union[:class:`~discord.SlashCommand`, :class:`~discord.UserCommand`, :class:`~discord.MessageCommand`, :class:`~discord.PrimaryEntryPointCommand`, :class:`~discord.Object`]]
        The command these permissions belong to, if known. ``None`` for application-wide permissions.
    permissions: List[:class:`ApplicationCommandPermissions`]
        The configured permission overwrites.
    """

    __slots__ = ('id', 'application_id', 'guild_id', 'guild', 'command', 'permissions', '_state')

    def __init__(
        self,
        *,
        state: ConnectionState,
        data: GuildApplicationCommandPermissionsPayload,
        guild: Guild,
        command: Optional[Union[ApplicationCommand, Object]] = None,
    ) -> None:
        self._state: ConnectionState = state
        self.id: int = int(data['id'])
        self.application_id: int = int(data['application_id'])
        self.guild_id: int = int(data['guild_id'])
        self.guild: Guild = guild
        self.command: Optional[Union[ApplicationCommand, Object]] = command
        if self.command is None and self.id != self.application_id:
            self.command = Object(id=self.id, type=BaseCommand)
        self.permissions: List[ApplicationCommandPermissions] = [
            ApplicationCommandPermissions.with_state(state=state, data=permission, guild=guild)
            for permission in data.get('permissions', [])
        ]

    @classmethod
    def _from_index(
        cls,
        *,
        state: ConnectionState,
        guild: Guild,
        application_id: int,
        id: int,
        data: Optional[ApplicationCommandIndexPermissionsPayload] = None,
        command: Optional[Union[ApplicationCommand, Object]] = None,
    ) -> GuildApplicationCommandPermissions:
        self = cls.__new__(cls)
        self._state = state
        self.id = id
        self.application_id = application_id
        self.guild_id = guild.id
        self.guild = guild
        self.command = command
        if self.command is None and self.id != self.application_id:
            self.command = Object(id=self.id, type=BaseCommand)
        self.permissions = (
            ApplicationCommandPermissions._from_index(state=state, guild=guild, data=data) if data is not None else []
        )
        return self

    def __repr__(self) -> str:
        return (
            f'<GuildApplicationCommandPermissions id={self.id} application_id={self.application_id} '
            f'guild_id={self.guild_id} permissions={len(self.permissions)}>'
        )

    def to_dict(self) -> GuildApplicationCommandPermissionsPayload:
        return {
            'id': str(self.id),
            'application_id': str(self.application_id),
            'guild_id': str(self.guild_id),
            'permissions': [permission.to_dict() for permission in self.permissions],
        }

    async def edit(
        self,
        *permissions: ApplicationCommandPermissions,
    ) -> GuildApplicationCommandPermissions:
        r"""|coro|

        Replaces the permissions for this command in the guild.

        .. versionadded:: 2.2

        Parameters
        ----------
        \*permissions: :class:`ApplicationCommandPermissions`
            The permission overwrites to replace the existing overwrites with.

        Raises
        ------
        Forbidden
            You do not have permission to edit the command permissions.
        HTTPException
            Editing the command permissions failed.

        Returns
        -------
        :class:`~discord.GuildApplicationCommandPermissions`
            The updated permissions.
        """
        data = await self._state.http.edit_application_command_permissions(
            self.application_id,
            self.guild_id,
            self.id,
            [permission.to_dict() for permission in permissions],
        )
        return GuildApplicationCommandPermissions(state=self._state, data=data, guild=self.guild, command=self.command)


@runtime_checkable
class ApplicationCommand(Protocol):
    """An ABC that represents a usable application command.

    The following implement this ABC:

    - :class:`~discord.UserCommand`
    - :class:`~discord.MessageCommand`
    - :class:`~discord.SlashCommand`
    - :class:`~discord.SubCommand`

    .. versionadded:: 2.0

    .. versionchanged:: 2.1

        Removed ``default_permission`` attribute.

    Attributes
    -----------
    name: :class:`str`
        The command's name.
    name_localized: Optional[:class:`str`]
        The localized name of the command, if available.

        .. versionadded:: 2.2
    name_localizations: Dict[:class:`~discord.Locale`, :class:`str`]
        The full name localization mapping, if available.

        .. versionadded:: 2.2
    description: :class:`str`
        The command's description, if any.
    description_localized: Optional[:class:`str`]
        The localized description of the command, if available.

        .. versionadded:: 2.2
    description_localizations: Dict[:class:`~discord.Locale`, :class:`str`]
        The full description localization mapping, if available.

        .. versionadded:: 2.2
    type: :class:`~discord.ApplicationCommandType`
        The type of application command.
    dm_permission: :class:`bool`
        Whether the command is enabled in DMs.

        .. deprecated:: 2.2
            Use :attr:`contexts` instead.
    nsfw: :class:`bool`
        Whether the command is marked NSFW and only available in NSFW channels.
    contexts: Optional[:class:`~discord.ApplicationCommandContext`]
        The contexts where the command can be used.

        .. versionadded:: 2.2
    integration_types: Optional[:class:`~discord.ApplicationIntegrationType`]
        The installation types where the command is available.

        .. versionadded:: 2.2
    permissions: Optional[:class:`~discord.GuildApplicationCommandPermissions`]
        The command's permission overwrites from an application command index
        response. User overwrite entries are only included
        for the current user.

        .. versionadded:: 2.2
    application: Optional[Union[:class:`~discord.CommandApplication`, :class:`~discord.IntegrationApplication`, :class:`~discord.PartialApplication`]]
        The application this command belongs to

        .. versionchanged:: 2.2

            Added :class:`~discord.CommandApplication` and :class:`~discord.PartialApplication` as possible types for this attribute.
    application_id: :class:`int`
        The ID of the application this command belongs to.
    guild_id: Optional[:class:`int`]
        The ID of the guild this command is registered in. A value of ``None``
        denotes that it is a global command.
    """

    __slots__ = ()

    if TYPE_CHECKING:
        _state: ConnectionState
        _channel: Optional[Messageable]
        _context_guild: Optional[Guild]
        _default_member_permissions: Optional[int]
        name: str
        name_localized: Optional[str]
        name_localizations: Dict[Locale, str]
        description: str
        description_localized: Optional[str]
        description_localizations: Dict[Locale, str]
        version: int
        type: ApplicationCommandType
        dm_permission: bool
        nsfw: bool
        application_id: int
        application: Optional[CommandApplicationTarget]
        mention: str
        guild_id: Optional[int]
        contexts: Optional[ApplicationCommandContext]
        integration_types: Optional[ApplicationIntegrationType]
        permissions: Optional[GuildApplicationCommandPermissions]

    def to_dict(self) -> Any: ...

    def __str__(self) -> str:
        return self.name

    async def __call__(
        self,
        data: ApplicationCommandInteractionData,
        files: Optional[List[_FileBase]] = None,
        channel: Optional[Messageable] = None,
    ) -> None:
        channel = channel or self.target_channel
        if channel is None:
            raise TypeError("__call__() missing 1 required argument: 'channel'")

        await _wrapped_interaction(
            self._state,
            _generate_nonce(),
            InteractionType.application_command,
            data['name'],
            await channel._get_channel(),  # type: ignore # acc_channel is always correct here
            data,
            files=files,
            application_id=self.application_id,
        )

    @property
    def guild(self) -> Optional[Guild]:
        """Optional[:class:`~discord.Guild`]: Returns the guild this command is registered to,
        if it exists.
        """
        return self._state._get_guild(self.guild_id)

    def _require_guild(self) -> Guild:
        guild = self._context_guild or self.guild
        if guild is None:
            raise ValueError('This command is not bound to a guild')
        return guild

    def is_group(self) -> bool:
        """:class:`bool`: Whether this command is a group."""
        return False

    @property
    def target_channel(self) -> Optional[Messageable]:
        """Optional[:class:`.abc.Messageable`]: The channel this application command will be used on.

        You can set this in order to use this command in a different channel without re-fetching it.
        """
        return self._channel

    @target_channel.setter
    def target_channel(self, value: Optional[Messageable]) -> None:
        from .abc import Messageable

        if not isinstance(value, Messageable) and value is not None:
            raise TypeError('channel must derive from Messageable')
        self._channel = value

    @property
    def default_member_permissions(self) -> Optional[Permissions]:
        """Optional[:class:`~discord.Permissions`]: The default permissions required to use this command.

        .. note::
            This may be overrided on a guild-by-guild basis.
        """
        perms = self._default_member_permissions
        return Permissions(perms) if perms is not None else None

    @staticmethod
    def _resolve_permission_overwrites(
        permissions: List[ApplicationCommandPermissions],
        member: Member,
        channel: Union[GuildChannel, Thread],
    ) -> Tuple[Optional[bool], Optional[bool]]:
        from .threads import Thread

        guild = channel.guild
        channel_id = channel.parent_id if isinstance(channel, Thread) else channel.id

        everyone = None
        role = None
        user = None
        all_channels = None
        specific_channel = None

        roles = member._roles
        for permission in permissions:
            if permission.type is ApplicationCommandPermissionType.user:
                if permission.id == member.id:
                    user = permission.permission
            elif permission.type is ApplicationCommandPermissionType.role:
                if permission.id == guild.id:
                    everyone = permission.permission
                elif roles.has(permission.id):
                    if permission.permission:
                        role = True
                    elif role is None:
                        role = False
            elif permission.type is ApplicationCommandPermissionType.channel:
                if permission.id == guild.id - 1:
                    all_channels = permission.permission
                elif permission.id == channel_id:
                    specific_channel = permission.permission

        target = everyone
        if role is not None:
            target = role
        if user is not None:
            target = user

        location = all_channels
        if specific_channel is not None:
            location = specific_channel

        return target, location

    def permission_for(self, channel: Union[GuildChannel, Thread], /) -> bool:
        """Returns whether this command can be used by the current user in the given guild channel.

        As this function requires that the command has attached guild context,
        it does not take into account the special behavior of user-installed apps.

        .. versionadded:: 2.2

        Parameters
        ----------
        channel: Union[:class:`~discord.abc.GuildChannel`, :class:`~discord.Thread`]
            The guild channel to resolve command permissions in.

        Returns
        -------
        :class:`bool`
            Whether the command is usable in the channel.
        """
        guild = channel.guild
        if self.guild_id is not None and self.guild_id != guild.id:
            return False

        if self.contexts is not None and not self.contexts.guild:
            return False

        if self.nsfw:
            if self._state.user is None or self._state.user.nsfw_allowed is not True:
                return False

            is_nsfw = getattr(channel, 'is_nsfw', None)
            if not callable(is_nsfw) or not is_nsfw():
                return False

        member = guild.me
        if member is None:
            return False

        from .threads import Thread

        channel_permissions = channel.permissions_for(member)
        if channel_permissions.administrator:
            return True

        if isinstance(channel, Thread):
            send_messages = channel_permissions.send_messages_in_threads
        else:
            send_messages = channel_permissions.send_messages

        if not channel_permissions.read_messages or not channel_permissions.use_application_commands or not send_messages:
            return False

        default_member_permissions = self._default_member_permissions
        if default_member_permissions is None:
            allowed = True
        elif default_member_permissions == 0:
            allowed = False
        else:
            allowed = (channel_permissions.value & default_member_permissions) == default_member_permissions

        location_allowed = True

        from .application import CommandApplication

        application = self.application
        if isinstance(application, CommandApplication):
            permissions = application.permissions
            if permissions is not None:
                target, location = self._resolve_permission_overwrites(permissions.permissions, member, channel)
                if target is False:
                    allowed = False
                if location is not None:
                    location_allowed = location

        permissions = self.permissions
        if permissions is not None:
            target, location = self._resolve_permission_overwrites(permissions.permissions, member, channel)
            if target is not None:
                allowed = target
            if location is not None:
                location_allowed = location

        return allowed and location_allowed


class BaseCommand(ApplicationCommand, Hashable):
    __slots__ = (
        'name',
        'description',
        'id',
        'version',
        'application',
        'application_id',
        'dm_permission',
        'nsfw',
        'guild_id',
        'name_localized',
        'name_localizations',
        'description_localized',
        'description_localizations',
        'contexts',
        'integration_types',
        'permissions',
        'global_popularity_rank',
        '_type',
        '_state',
        '_channel',
        '_context_guild',
        '_default_member_permissions',
    )

    def __init__(
        self,
        *,
        state: ConnectionState,
        data: ApplicationCommandPayload,
        channel: Optional[Messageable] = None,
        guild: Optional[Guild] = None,
        application: Optional[CommandApplicationTarget] = None,
        **kwargs,
    ) -> None:
        self._state = state
        self.application = application
        self._type: ApplicationCommandType = try_enum(ApplicationCommandType, data['type'])
        self.name, self.name_localized, self.name_localizations = _parse_localizations(data, 'name')
        self.description, self.description_localized, self.description_localizations = _parse_localizations(
            data, 'description'
        )
        self._channel = channel
        self._context_guild = guild
        self.application_id: int = int(data['application_id'])
        self.id: int = int(data['id'])
        self.version = int(data['version'])

        default_member_permissions = data.get('default_member_permissions')
        self._default_member_permissions = (
            int(default_member_permissions) if default_member_permissions is not None else None
        )
        dm_permission = data.get('dm_permission')  # Null means true?
        self.dm_permission = dm_permission if dm_permission is not None else True
        self.nsfw: bool = data.get('nsfw', False)
        contexts = data.get('contexts')
        self.contexts: Optional[ApplicationCommandContext] = (
            ApplicationCommandContext._from_value(contexts) if contexts is not None else None
        )
        integration_types = data.get('integration_types')
        self.integration_types: Optional[ApplicationIntegrationType] = (
            ApplicationIntegrationType._from_value(integration_types) if integration_types is not None else None
        )
        self.guild_id: Optional[int] = _get_as_snowflake(data, 'guild_id')
        index_permissions = data.get('permissions')
        self.permissions: Optional[GuildApplicationCommandPermissions] = (
            GuildApplicationCommandPermissions._from_index(
                state=state,
                guild=guild,
                application_id=self.application_id,
                id=self.id,
                data=index_permissions,
                command=self,
            )
            if guild is not None
            else None
        )
        global_popularity_rank = data.get('global_popularity_rank')
        self.global_popularity_rank: Optional[int] = (
            int(global_popularity_rank) if global_popularity_rank is not None else None
        )

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} id={self.id} name={self.name!r}>'

    @property
    def type(self) -> ApplicationCommandType:
        """:class:`ApplicationCommandType`: The type of application command."""
        return self._type

    @property
    def mention(self) -> str:
        """:class:`str`: Returns a string that allows you to mention the command."""
        return f'</{self.name}:{self.id}>'

    @property
    def display_name(self) -> str:
        """:class:`str`: The localized name if available, otherwise :attr:`name`.

        .. versionadded:: 2.2
        """
        return self.name_localized or self._state.parsed_locale._resolve_from(self.name_localizations) or self.name

    @property
    def display_description(self) -> str:
        """:class:`str`: The localized description if available, otherwise :attr:`description`.

        .. versionadded:: 2.2
        """
        return (
            self.description_localized
            or self._state.parsed_locale._resolve_from(self.description_localizations)
            or self.description
        )

    def to_dict(self) -> ApplicationCommandPayload:
        data = {
            'id': self.id,
            'application_id': self.application_id,
            'version': self.version,
            'type': self.type.value,
            'name': self.name,
            'description': self.description,
            'dm_permission': self.dm_permission,
            'nsfw': self.nsfw,
        }

        if self.name_localized is not None:
            data['name_localized'] = self.name_localized
        if self.name_localizations:
            data['name_localizations'] = {locale.value: value for locale, value in self.name_localizations.items()}
        if self.description_localized is not None:
            data['description_localized'] = self.description_localized
        if self.description_localizations:
            data['description_localizations'] = {
                locale.value: value for locale, value in self.description_localizations.items()
            }
        if self._default_member_permissions is not None:
            data['default_member_permissions'] = self._default_member_permissions
        if self.contexts is not None:
            data['contexts'] = self.contexts.to_array()
        if self.integration_types is not None:
            data['integration_types'] = self.integration_types.to_array()
        if self.guild_id is not None:
            data['guild_id'] = self.guild_id
        return data  # type: ignore

    async def fetch_permissions(self) -> GuildApplicationCommandPermissions:
        """|coro|

        Retrieves this command's permissions in its guild.

        .. versionadded:: 2.2

        This requires the command to be fetched from a guild or guild channel.

        Raises
        ------
        ValueError
            The command is not bound to a guild.
        NotFound
            The command does not exist in the guild.
        Forbidden
            You do not have access to the command permissions.
        HTTPException
            Retrieving the command permissions failed.

        Returns
        -------
        :class:`~discord.GuildApplicationCommandPermissions`
            The command permissions.
        """
        guild = self._require_guild()
        data = await self._state.http.get_application_command_permissions(self.application_id, guild.id, self.id)
        return GuildApplicationCommandPermissions(state=self._state, data=data, guild=guild, command=self)

    async def edit_permissions(
        self,
        *permissions: ApplicationCommandPermissions,
    ) -> GuildApplicationCommandPermissions:
        r"""|coro|

        Replaces this command's permissions in the guild.

        .. versionadded:: 2.2

        This requires the command to be fetched from a guild or guild channel.

        Parameters
        ----------
        \*permissions: :class:`ApplicationCommandPermissions`
            The permission overwrites to replace the existing overwrites with.

        Raises
        ------
        ValueError
            The command is not bound to a guild.
        Forbidden
            You do not have permission to edit the command permissions.
        HTTPException
            Editing the command permissions failed.

        Returns
        -------
        :class:`~discord.GuildApplicationCommandPermissions`
            The updated command permissions.
        """
        guild = self._require_guild()
        data = await self._state.http.edit_application_command_permissions(
            self.application_id,
            guild.id,
            self.id,
            [permission.to_dict() for permission in permissions],
        )
        return GuildApplicationCommandPermissions(state=self._state, data=data, guild=guild, command=self)


class SlashMixin(ApplicationCommand, Protocol):
    if TYPE_CHECKING:
        _parent: SlashCommand
        _type: Any
        name: str
        options: List[Option]
        children: List[SubCommand]

        def _walk_parents(self) -> Iterable[Any]: ...

    async def __call__(
        self,
        options: List[InteractionDataValueOption],
        files: Optional[List[_FileBase]],
        attachments: List[PartialAttachmentPayload],
        channel: Optional[Messageable] = None,
    ) -> None:
        obj = self._parent
        command = obj.to_dict()
        data: ChatInputCommandInteractionData = {
            'application_command': command,
            'attachments': attachments,
            'id': str(obj.id),
            'name': obj.name,
            'options': self._wrap_options(options),
            'type': ApplicationCommandType.chat_input.value,
            'version': str(obj.version),
        }
        if self.guild_id:
            data['guild_id'] = str(self.guild_id)
        await super().__call__(data, files, channel)

    def _wrap_options(self, options: List[InteractionDataValueOption]) -> List[InteractionDataOption]:
        wrapped_options: List[InteractionDataOption] = []
        wrapped_options.extend(options)
        if isinstance(self, SlashCommand):
            return wrapped_options

        wrapped: List[InteractionDataOption] = [
            {
                'type': self._type.value,
                'name': self.name,
                'options': wrapped_options,
            }
        ]
        for parent in self._walk_parents():
            wrapped = [
                {
                    'type': parent._type.value,
                    'name': parent.name,
                    'options': wrapped,
                }
            ]

        return wrapped

    def _get_option(self, option: Union[str, Option]) -> Option:
        if isinstance(option, Option):
            return option

        for candidate in self.options:
            if candidate.name == option:
                return candidate

        raise ValueError(f'Unknown option {option!r}')

    async def autocomplete(self, channel: Optional[Messageable] = None, /, **kwargs) -> None:
        r"""|coro|

        Requests autocomplete choices for an option.

        The last keyword argument is treated as the focused option. Earlier
        keyword arguments are sent as the current values of the other options.
        The response is dispatched through :func:`on_application_command_autocomplete_response`.

        Parameters
        ----------
        channel: Optional[:class:`abc.Messageable`]
            The channel to request autocomplete choices in. Overrides
            :attr:`target_channel`. Required if :attr:`target_channel` is not set.
        \*\*kwargs: Any
            The current option values. The final keyword argument must be the
            autocomplete-enabled option to request choices for.
            Options of type :attr:`ApplicationCommandOptionType.attachment` will be ignored.

        Raises
        ------
        TypeError
            No focused option was provided, the focused option is not a string,
            integer, or number option, or no channel was available.
        ValueError
            The focused option does not exist or is not autocomplete-enabled.
        """
        try:
            option_name = next(reversed(kwargs))
        except StopIteration:
            raise TypeError('autocomplete() missing 1 required keyword argument') from None

        option = self._get_option(option_name)
        if not option.autocomplete:
            raise ValueError(f'Option {option.name!r} does not autocomplete')

        channel = channel or self.target_channel
        if channel is None:
            raise TypeError("autocomplete() missing 1 required argument: 'channel'")

        options, _, attachments = self._parse_kwargs(kwargs, autocomplete=True)
        focused = options[-1]
        focused['focused'] = True
        # This guy MUST be sent as a string
        focused_val = focused['value']
        focused['value'] = str(focused_val)  # pyright: ignore[reportGeneralTypeIssues]

        obj = self._parent
        command = obj.to_dict()
        data: ChatInputCommandInteractionData = {
            'application_command': command,
            'attachments': attachments,
            'id': str(obj.id),
            'name': obj.name,
            'options': self._wrap_options(options),
            'type': ApplicationCommandType.chat_input.value,
            'version': str(obj.version),
        }
        if self.guild_id:
            data['guild_id'] = str(self.guild_id)

        state = self._state
        nonce = _generate_nonce()
        resolved_channel = await channel._get_channel()
        state._application_command_autocomplete_cache[nonce] = (resolved_channel, obj, option, focused_val)
        state._application_command_autocomplete_cache.move_to_end(nonce)
        if len(state._application_command_autocomplete_cache) > 50:
            state._application_command_autocomplete_cache.popitem(last=False)

        try:
            await state.http.interact(
                InteractionType.autocomplete,
                data,
                resolved_channel,  # pyright: ignore[reportArgumentType] # channel is resolved by Messageable._get_channel
                nonce=nonce,
                application_id=obj.application_id,
            )
        except Exception:
            state._application_command_autocomplete_cache.pop(nonce, None)
            raise

    def _parse_kwargs(
        self, kwargs: Dict[str, Any], *, autocomplete: bool = False
    ) -> Tuple[List[InteractionDataValueOption], List[_FileBase], List[PartialAttachmentPayload]]:
        possible_options = {o.name: o for o in self.options}
        kwargs = {k: v for k, v in kwargs.items() if k in possible_options}
        options = []
        files = []

        for k, v in kwargs.items():
            option = possible_options[k]
            type = option.type

            if type in {
                ApplicationCommandOptionType.user,
                ApplicationCommandOptionType.channel,
                ApplicationCommandOptionType.role,
                ApplicationCommandOptionType.mentionable,
            }:
                v = str(v.id)
            elif type is ApplicationCommandOptionType.boolean:
                v = bool(v)
            elif type is ApplicationCommandOptionType.attachment:
                if autocomplete:
                    continue
                files.append(v)
                v = len(files) - 1
            else:
                v = option._convert(v)

            if type is ApplicationCommandOptionType.string:
                v = str(v)
            elif type is ApplicationCommandOptionType.integer:
                v = int(v)
            elif type is ApplicationCommandOptionType.number:
                v = float(v)

            options.append({'name': k, 'value': v, 'type': type.value})

        attachments = []
        for index, file in enumerate(files):
            attachments.append(file.to_dict(index))

        return options, files, attachments

    def _unwrap_options(self, data: Sequence[ApplicationCommandOption]) -> None:
        state = self._state
        options = []
        children = []
        for option in data:
            type = try_enum(ApplicationCommandOptionType, option['type'])
            if type in (
                ApplicationCommandOptionType.sub_command,
                ApplicationCommandOptionType.sub_command_group,
            ):
                children.append(SubCommand(parent=self, data=option))  # type: ignore
            else:
                options.append(Option(data=option, state=state))  # type: ignore

        self.options = options
        self.children = children


class UserCommand(BaseCommand):
    """Represents a user command.

    .. container:: operations

        .. describe:: x == y

            Checks if two commands are equal.

        .. describe:: x != y

            Checks if two commands are not equal.

        .. describe:: hash(x)

            Return the command's hash.

        .. describe:: str(x)

            Returns the command's name.

    .. versionadded:: 2.0

    .. versionchanged:: 2.1

        Removed ``default_permission`` attribute.

    Attributes
    ----------
    id: :class:`int`
        The command's ID.
    version: :class:`int`
        The command's version.
    name: :class:`str`
        The command's name.
    name_localized: Optional[:class:`str`]
        The localized name of the command, if available.

        .. versionadded:: 2.2
    name_localizations: Dict[:class:`~discord.Locale`, :class:`str`]
        The full name localization mapping, if available.

        .. versionadded:: 2.2
    description: :class:`str`
        The command's description, if any.
    description_localized: Optional[:class:`str`]
        The localized description of the command, if available.

        .. versionadded:: 2.2
    description_localizations: Dict[:class:`~discord.Locale`, :class:`str`]
        The full description localization mapping, if available.

        .. versionadded:: 2.2
    dm_permission: :class:`bool`
        Whether the command is enabled in DMs.

        .. deprecated:: 2.2
            Use :attr:`contexts` instead.
    nsfw: :class:`bool`
        Whether the command is marked NSFW and only available in NSFW channels.
    contexts: Optional[:class:`~discord.ApplicationCommandContext`]
        The contexts where the command can be used.

        .. versionadded:: 2.2
    integration_types: Optional[:class:`~discord.ApplicationIntegrationType`]
        The installation types where the command is available.

        .. versionadded:: 2.2
    permissions: Optional[:class:`~discord.GuildApplicationCommandPermissions`]
        The command's permission overwrites from an application command index
        response. User overwrite entries are only included
        for the current user.

        .. versionadded:: 2.2
    global_popularity_rank: Optional[:class:`int`]
        The command's global popularity rank, if provided.

        .. versionadded:: 2.2
    application: Optional[Union[:class:`~discord.CommandApplication`, :class:`~discord.IntegrationApplication`, :class:`~discord.PartialApplication`]]
        The application this command belongs to

        .. versionchanged:: 2.2

            Added :class:`~discord.CommandApplication` and :class:`~discord.PartialApplication` as possible types for this attribute.
    application_id: :class:`int`
        The ID of the application this command belongs to.
    guild_id: Optional[:class:`int`]
        The ID of the guild this command is registered in. A value of ``None``
        denotes that it is a global command.
    """

    __slots__ = ('_user',)

    def __init__(self, *, target: Optional[Snowflake] = None, **kwargs):
        super().__init__(**kwargs)
        self._user = target

    async def __call__(
        self,
        user: Optional[Snowflake] = None,
        *,
        channel: Optional[Messageable] = None,
    ) -> None:
        """|coro|

        Use the user command.

        .. versionchanged:: 2.2

            This no longer returns the created interaction.

        Parameters
        ----------
        user: Optional[:class:`User`]
            The user to use the command on. Overrides :attr:`target_user`.
            Required if :attr:`target_user` is not set.
        channel: Optional[:class:`abc.Messageable`]
            The channel to use the command on. Overrides :attr:`target_channel`.
            Required if :attr:`target_channel` is not set.
        """
        user = user or self._user
        if user is None:
            raise TypeError("__call__() missing 1 required positional argument: 'user'")

        command = self.to_dict()
        data: UserCommandInteractionData = {
            'application_command': command,
            'attachments': [],
            'id': str(self.id),
            'name': self.name,
            'options': [],
            'target_id': str(user.id),
            'type': ApplicationCommandType.user.value,
            'version': str(self.version),
        }
        if self.guild_id:
            data['guild_id'] = str(self.guild_id)
        await super().__call__(data, None, channel)

    @property
    def type(self) -> Literal[ApplicationCommandType.user]:
        """:class:`ApplicationCommandType`: The type of application command. This is always :attr:`ApplicationCommandType.user`."""
        return ApplicationCommandType.user

    @property
    def target_user(self) -> Optional[Snowflake]:
        """Optional[:class:`~abc.Snowflake`]: The user this application command will be used on.

        You can set this in order to use this command on a different user without re-fetching it.
        """
        return self._user

    @target_user.setter
    def target_user(self, value: Optional[Snowflake]) -> None:
        from .abc import Snowflake

        if not isinstance(value, Snowflake) and value is not None:
            raise TypeError('user must be Snowflake')
        self._user = value


class MessageCommand(BaseCommand):
    """Represents a message command.

    .. container:: operations

        .. describe:: x == y

            Checks if two commands are equal.

        .. describe:: x != y

            Checks if two commands are not equal.

        .. describe:: hash(x)

            Return the command's hash.

        .. describe:: str(x)

            Returns the command's name.

    .. versionadded:: 2.0

    .. versionchanged:: 2.1

        Removed ``default_permission`` attribute.

    Attributes
    ----------
    id: :class:`int`
        The command's ID.
    version: :class:`int`
        The command's version.
    name: :class:`str`
        The command's name.
    name_localized: Optional[:class:`str`]
        The localized name of the command, if available.

        .. versionadded:: 2.2
    name_localizations: Dict[:class:`~discord.Locale`, :class:`str`]
        The full name localization mapping, if available.

        .. versionadded:: 2.2
    description: :class:`str`
        The command's description, if any.
    description_localized: Optional[:class:`str`]
        The localized description of the command, if available.

        .. versionadded:: 2.2
    description_localizations: Dict[:class:`~discord.Locale`, :class:`str`]
        The full description localization mapping, if available.

        .. versionadded:: 2.2
    dm_permission: :class:`bool`
        Whether the command is enabled in DMs.

        .. deprecated:: 2.2
            Use :attr:`contexts` instead.
    nsfw: :class:`bool`
        Whether the command is marked NSFW and only available in NSFW channels.
    contexts: Optional[:class:`~discord.ApplicationCommandContext`]
        The contexts where the command can be used.

        .. versionadded:: 2.2
    integration_types: Optional[:class:`~discord.ApplicationIntegrationType`]
        The installation types where the command is available.

        .. versionadded:: 2.2
    permissions: Optional[:class:`~discord.GuildApplicationCommandPermissions`]
        The command's permission overwrites from an application command index
        response. User overwrite entries are only included
        for the current user.

        .. versionadded:: 2.2
    global_popularity_rank: Optional[:class:`int`]
        The command's global popularity rank, if provided.

        .. versionadded:: 2.2
    application: Optional[Union[:class:`~discord.CommandApplication`, :class:`~discord.IntegrationApplication`, :class:`~discord.PartialApplication`]]
        The application this command belongs to

        .. versionchanged:: 2.2

            Added :class:`~discord.CommandApplication` and :class:`~discord.PartialApplication` as possible types for this attribute.
    application_id: :class:`int`
        The ID of the application this command belongs to.
    guild_id: Optional[:class:`int`]
        The ID of the guild this command is registered in. A value of ``None``
        denotes that it is a global command.
    """

    __slots__ = ('_message',)

    def __init__(self, *, target: Optional[Message] = None, **kwargs):
        super().__init__(**kwargs)
        self._message = target

    async def __call__(
        self,
        message: Optional[Message] = None,
        *,
        channel: Optional[Messageable] = None,
    ) -> None:
        """|coro|

        Use the message command.

        .. versionchanged:: 2.2

            This no longer returns the created interaction.

        Parameters
        ----------
        message: Optional[:class:`Message`]
            The message to use the command on. Overrides :attr:`target_message`.
            Required if :attr:`target_message` is not set.
        channel: Optional[:class:`abc.Messageable`]
            The channel to use the command on. Overrides :attr:`target_channel`.
            Required if :attr:`target_channel` is not set.
        """
        message = message or self._message
        if message is None:
            raise TypeError("__call__() missing 1 required positional argument: 'message'")

        command = self.to_dict()
        data: MessageCommandInteractionData = {
            'application_command': command,
            'attachments': [],
            'id': str(self.id),
            'name': self.name,
            'options': [],
            'target_id': str(message.id),
            'type': self.type.value,
            'version': str(self.version),
        }
        if self.guild_id:
            data['guild_id'] = str(self.guild_id)
        await super().__call__(data, None, channel)

    @property
    def type(self) -> Literal[ApplicationCommandType.message]:
        """:class:`ApplicationCommandType`: The type of application command. This is always :attr:`ApplicationCommandType.message`."""
        return ApplicationCommandType.message

    @property
    def target_message(self) -> Optional[Message]:
        """Optional[:class:`Message`]: The message this application command will be used on.

        You can set this in order to use this command on a different message without re-fetching it.
        """
        return self._message

    @target_message.setter
    def target_message(self, value: Optional[Message]) -> None:
        from .message import Message

        if not isinstance(value, Message) and value is not None:
            raise TypeError('message must be Message')
        self._message = value


class PrimaryEntryPointCommand(BaseCommand):
    """Represents a primary entry point application command.

    .. versionadded:: 2.2

    Attributes
    ----------
    id: :class:`int`
        The command's ID.
    version: :class:`int`
        The command's version.
    name: :class:`str`
        The command's name.
    name_localized: Optional[:class:`str`]
        The localized name of the command, if available.
    name_localizations: Dict[:class:`~discord.Locale`, :class:`str`]
        The full name localization mapping, if available.
    description: :class:`str`
        The command's description, if any.
    description_localized: Optional[:class:`str`]
        The localized description of the command, if available.
    description_localizations: Dict[:class:`~discord.Locale`, :class:`str`]
        The full description localization mapping, if available.
    dm_permission: :class:`bool`
        Whether the command is enabled in DMs.

        .. deprecated:: 2.2
            Use :attr:`contexts` instead.
    nsfw: :class:`bool`
        Whether the command is marked NSFW and only available in NSFW channels.
    contexts: Optional[:class:`~discord.ApplicationCommandContext`]
        The contexts where the command can be used.
    integration_types: Optional[:class:`~discord.ApplicationIntegrationType`]
        The installation types where the command is available.
    permissions: Optional[:class:`~discord.GuildApplicationCommandPermissions`]
        The command's permission overwrites from an application command index
        response. User overwrite entries are only included
        for the current user.
    global_popularity_rank: Optional[:class:`int`]
        The command's global popularity rank, if provided.
    handler: :class:`~discord.ApplicationCommandHandlerType`
        The command handler type.
    application: Optional[Union[:class:`~discord.CommandApplication`, :class:`~discord.IntegrationApplication`, :class:`~discord.PartialApplication`]]
        The application this command belongs to

        .. versionchanged:: 2.2

            Added :class:`~discord.CommandApplication` and :class:`~discord.PartialApplication` as possible types for this attribute.
    application_id: :class:`int`
        The ID of the application this command belongs to.
    guild_id: Optional[:class:`int`]
        The ID of the guild this command is registered in. A value of ``None``
        denotes that it is a global command.
    """

    __slots__ = ('handler',)

    def __init__(self, *, data: ApplicationCommandPayload, **kwargs) -> None:
        super().__init__(data=data, **kwargs)
        self.handler: Optional[ApplicationCommandHandlerType] = try_enum(
            ApplicationCommandHandlerType, data.get('handler', 2)
        )

    async def __call__(self, *, channel: Optional[Messageable] = None) -> None:
        """|coro|

        Use the primary entry point command.

        Parameters
        ----------
        channel: Optional[:class:`abc.Messageable`]
            The channel to use the command on. Overrides :attr:`target_channel`.
            Required if :attr:`target_channel` is not set.
        """
        command = self.to_dict()
        data: PrimaryEntryPointCommandInteractionData = {
            'application_command': command,
            'attachments': [],
            'id': str(self.id),
            'name': self.name,
            'options': [],
            'type': self.type.value,
            'version': str(self.version),
        }
        if self.guild_id:
            data['guild_id'] = str(self.guild_id)
        await super().__call__(data, None, channel)

    @property
    def type(self) -> Literal[ApplicationCommandType.primary_entry_point]:
        """:class:`ApplicationCommandType`: The type of application command. This is always :attr:`ApplicationCommandType.primary_entry_point`."""
        return ApplicationCommandType.primary_entry_point

    def to_dict(self) -> ApplicationCommandPayload:
        data: Any = super().to_dict()
        if self.handler is not None:
            data['handler'] = self.handler.value
        return data


class SlashCommand(BaseCommand, SlashMixin):
    """Represents a slash command.

    .. container:: operations

        .. describe:: x == y

            Checks if two commands are equal.

        .. describe:: x != y

            Checks if two commands are not equal.

        .. describe:: hash(x)

            Return the command's hash.

        .. describe:: str(x)

            Returns the command's name.

    .. versionadded:: 2.0

    .. versionchanged:: 2.1

        Removed ``default_permission`` attribute.

    Attributes
    ----------
    id: :class:`int`
        The command's ID.
    version: :class:`int`
        The command's version.
    name: :class:`str`
        The command's name.
    name_localized: Optional[:class:`str`]
        The localized name of the command, if available.

        .. versionadded:: 2.2
    name_localizations: Dict[:class:`~discord.Locale`, :class:`str`]
        The full name localization mapping, if available.

        .. versionadded:: 2.2
    description: :class:`str`
        The command's description, if any.
    description_localized: Optional[:class:`str`]
        The localized description of the command, if available.

        .. versionadded:: 2.2
    description_localizations: Dict[:class:`~discord.Locale`, :class:`str`]
        The full description localization mapping, if available.

        .. versionadded:: 2.2
    dm_permission: :class:`bool`
        Whether the command is enabled in DMs.

        .. deprecated:: 2.2
            Use :attr:`contexts` instead.
    nsfw: :class:`bool`
        Whether the command is marked NSFW and only available in NSFW channels.
    contexts: Optional[:class:`~discord.ApplicationCommandContext`]
        The contexts where the command can be used.

        .. versionadded:: 2.2
    integration_types: Optional[:class:`~discord.ApplicationIntegrationType`]
        The installation types where the command is available.

        .. versionadded:: 2.2
    permissions: Optional[:class:`~discord.GuildApplicationCommandPermissions`]
        The command's permission overwrites from an application command index
        response. User overwrite entries are only included
        for the current user.

        .. versionadded:: 2.2
    global_popularity_rank: Optional[:class:`int`]
        The command's global popularity rank, if provided.

        .. versionadded:: 2.2
    application: Optional[Union[:class:`~discord.CommandApplication`, :class:`~discord.IntegrationApplication`, :class:`~discord.PartialApplication`]]
        The application this command belongs to

        .. versionchanged:: 2.2

            Added :class:`~discord.CommandApplication` and :class:`~discord.PartialApplication` as possible types for this attribute.
    application_id: :class:`int`
        The ID of the application this command belongs to.
    guild_id: Optional[:class:`int`]
        The ID of the guild this command is registered in. A value of ``None``
        denotes that it is a global command.
    options: List[:class:`Option`]
        The command's options.
    children: List[:class:`SubCommand`]
        The command's subcommands. If a command has subcommands, it is a group and cannot be used.
    """

    __slots__ = ('_parent', 'options', 'children')

    def __init__(self, *, data: ApplicationCommandPayload, **kwargs) -> None:
        super().__init__(data=data, **kwargs)
        self._parent = self
        self._unwrap_options(data.get('options', []))

    async def __call__(self, channel: Optional[Messageable] = None, /, **kwargs) -> None:
        r"""|coro|

        Use the slash command.

        .. versionchanged:: 2.2

            This no longer returns the created interaction.
            Options now accept :class:`OptionChoice` directly.

        Parameters
        ----------
        channel: Optional[:class:`abc.Messageable`]
            The channel to use the command on. Overrides :attr:`target_channel`.
            Required if :attr:`target_channel` is not set.
        \*\*kwargs: Any
            The options to use. These will be casted to the correct type.
            If an option has choices, they are automatically converted from name to value for you.

        Raises
        ------
        TypeError
            Attempted to use a group.
        """
        if self.is_group():
            raise TypeError('Cannot use a group')

        await super().__call__(*self._parse_kwargs(kwargs), channel)

    def __repr__(self) -> str:
        BASE = f'<SlashCommand id={self.id} name={self.name!r}'
        if self.options:
            BASE += f' options={len(self.options)}'
        if self.children:
            BASE += f' children={len(self.children)}'
        return BASE + '>'

    @property
    def type(self) -> Literal[ApplicationCommandType.chat_input]:
        """:class:`ApplicationCommandType`: The type of application command. This is always :attr:`ApplicationCommandType.chat_input`."""
        return ApplicationCommandType.chat_input

    def is_group(self) -> bool:
        """Query whether this command is a group.

        Returns
        -------
        :class:`bool`
            Whether this command is a group.
        """
        return bool(self.children)

    def to_dict(self) -> ApplicationCommandPayload:
        data: Any = super().to_dict()
        options: List[ApplicationCommandOption] = [child.to_dict() for child in self.children]
        options.extend(option.to_dict() for option in self.options)
        if options:
            data['options'] = options
        return data


class SubCommand(SlashMixin):
    """Represents a slash command child.

    This could be a subcommand, or a subgroup.

    .. container:: operations

        .. describe:: str(x)

            Returns the command's name.

    .. versionadded:: 2.0

    .. versionchanged:: 2.1

        Removed ``default_permission`` property.

    Attributes
    ----------
    name: :class:`str`
        The subcommand's name.
    description: :class:`str`
        The subcommand's description, if any.
    parent: Union[:class:`~discord.SlashCommand`, :class:`~discord.SubCommand`]
        The parent command.
    options: List[:class:`Option`]
        The subcommand's options.
    children: List[:class:`SubCommand`]
        The subcommand's subcommands. If a subcommand has subcommands, it is a group and cannot be used.
    """

    __slots__ = (
        'name',
        'description',
        'name_localized',
        'name_localizations',
        'description_localized',
        'description_localizations',
        '_parent',
        '_state',
        '_type',
        'parent',
        'options',
        'children',
    )

    def __init__(self, *, parent: Union[SlashCommand, SubCommand], data: SubCommandPayload):
        self.name, self.name_localized, self.name_localizations = _parse_localizations(data, 'name')
        self.description, self.description_localized, self.description_localizations = _parse_localizations(
            data, 'description'
        )
        self._state = parent._state
        self.parent = parent
        self._parent: SlashCommand = getattr(parent, 'parent', parent)  # type: ignore
        self._type: Literal[
            ApplicationCommandOptionType.sub_command,
            ApplicationCommandOptionType.sub_command_group,
        ] = try_enum(ApplicationCommandOptionType, data['type'])  # type: ignore
        self._unwrap_options(data.get('options', []))

    def __str__(self) -> str:
        return self.name

    def _walk_parents(self):
        parent = self.parent
        while True:
            if isinstance(parent, SlashCommand):
                break
            else:
                yield parent
                parent = parent.parent

    @property
    def display_name(self) -> str:
        """:class:`str`: The localized name if available, otherwise :attr:`name`.

        .. versionadded:: 2.2
        """
        return self.name_localized or self._state.parsed_locale._resolve_from(self.name_localizations) or self.name

    @property
    def display_description(self) -> str:
        """:class:`str`: The localized description if available, otherwise :attr:`description`.

        .. versionadded:: 2.2
        """
        return (
            self.description_localized
            or self._state.parsed_locale._resolve_from(self.description_localizations)
            or self.description
        )

    async def __call__(self, channel: Optional[Messageable] = None, /, **kwargs) -> None:
        r"""|coro|

        Use the sub command.

        .. versionchanged:: 2.2

            This no longer returns the created interaction.

        Parameters
        ----------
        channel: Optional[:class:`abc.Messageable`]
            The channel to use the command on. Overrides :attr:`target_channel`.
            Required if :attr:`target_channel` is not set.
        \*\*kwargs: Any
            The options to use. These will be casted to the correct type.
            If an option has choices, they are automatically converted from name to value for you.

        Raises
        ------
        TypeError
            Attempted to use a group.
        """
        if self.is_group():
            raise TypeError('Cannot use a group')

        options, files, attachments = self._parse_kwargs(kwargs)
        await super().__call__(options, files, attachments, channel)

    def __repr__(self) -> str:
        BASE = f'<SubCommand name={self.name!r}'
        if self.options:
            BASE += f' options={len(self.options)}'
        if self.children:
            BASE += f' children={len(self.children)}'
        return BASE + '>'

    @property
    def type(self) -> Literal[ApplicationCommandType.chat_input]:
        """:class:`ApplicationCommandType`: The type of application command. Always :attr:`ApplicationCommandType.chat_input`."""
        # Avoid confusion I guess
        return ApplicationCommandType.chat_input

    @property
    def qualified_name(self) -> str:
        """:class:`str`: Returns the fully qualified command name.
        The qualified name includes the parent name as well. For example,
        in a command like ``/foo bar`` the qualified name is ``foo bar``.
        """
        names = [self.name, self.parent.name]
        if isinstance(self.parent, SubCommand):
            names.append(self._parent.name)
        return ' '.join(reversed(names))

    @property
    def mention(self) -> str:
        """:class:`str`: Returns a string that allows you to mention the subcommand."""
        return f'</{self.qualified_name}:{self._parent.id}>'

    @property
    def _default_member_permissions(self) -> Optional[int]:
        return self._parent._default_member_permissions

    @property
    def default_member_permissions(self) -> Optional[Permissions]:
        """Optional[:class:`~discord.Permissions`]: The default permissions required to use the parent command."""
        return self._parent.default_member_permissions

    @property
    def application_id(self) -> int:
        """:class:`int`: The ID of the application this command belongs to."""
        return self._parent.application_id

    @property
    def version(self) -> int:
        """:class:`int`: The version of the command."""
        return self._parent.version

    @property
    def dm_permission(self) -> bool:
        """:class:`bool`: Whether the command is enabled in DMs.

        .. deprecated:: 2.2
            Use :attr:`contexts` instead.
        """
        return self._parent.dm_permission

    @property
    def nsfw(self) -> bool:
        """:class:`bool`: Whether the command is marked NSFW and only available in NSFW channels."""
        return self._parent.nsfw

    @property
    def contexts(self) -> Optional[ApplicationCommandContext]:
        """Optional[:class:`~discord.ApplicationCommandContext`]: The contexts where the parent command can be used."""
        return self._parent.contexts

    @property
    def integration_types(self) -> Optional[ApplicationIntegrationType]:
        """Optional[:class:`~discord.ApplicationIntegrationType`]: The installation types where the parent command is available."""
        return self._parent.integration_types

    @property
    def permissions(self) -> Optional[GuildApplicationCommandPermissions]:
        """Optional[:class:`~discord.GuildApplicationCommandPermissions`]: The parent command's permission overwrites, if provided."""
        return self._parent.permissions

    @property
    def guild_id(self) -> Optional[int]:
        """Optional[:class:`int`]: The ID of the guild this command is registered in. A value of ``None``
        denotes that it is a global command."""
        return self._parent.guild_id

    @property
    def guild(self) -> Optional[Guild]:
        """Optional[:class:`~discord.Guild`]: Returns the guild this command is registered to
        if it exists.
        """
        return self._parent.guild

    def _require_guild(self) -> Guild:
        return self._parent._require_guild()

    def permission_for(self, channel: Union[GuildChannel, Thread], /) -> bool:
        return self._parent.permission_for(channel)

    def is_group(self) -> bool:
        """:class:`bool`: Whether this command is a group."""
        return self._type is ApplicationCommandOptionType.sub_command_group

    def to_dict(self) -> SubCommandPayload:
        data: Dict[str, Any] = {
            'type': self._type.value,
            'name': self.name,
            'description': self.description,
        }
        if self.name_localized is not None:
            data['name_localized'] = self.name_localized
        if self.name_localizations:
            data['name_localizations'] = {locale.value: value for locale, value in self.name_localizations.items()}
        if self.description_localized is not None:
            data['description_localized'] = self.description_localized
        if self.description_localizations:
            data['description_localizations'] = {
                locale.value: value for locale, value in self.description_localizations.items()
            }
        options: List[ApplicationCommandOption] = [child.to_dict() for child in self.children]
        options.extend(option.to_dict() for option in self.options)
        if options:
            data['options'] = options
        return data  # type: ignore

    @property
    def application(self) -> Optional[CommandApplicationTarget]:
        """Optional[Union[:class:`~discord.CommandApplication`, :class:`~discord.IntegrationApplication`, :class:`~discord.PartialApplication`]]: The application this command belongs to."""
        return self._parent.application

    @property
    def target_channel(self) -> Optional[Messageable]:
        """Optional[:class:`.abc.Messageable`]: The channel this command will be used on.

        You can set this in order to use this command on a different channel without re-fetching it.
        """
        return self._parent.target_channel

    @target_channel.setter
    def target_channel(self, value: Optional[Messageable]) -> None:
        self._parent.target_channel = value


class Option:
    """Represents a command option.

    .. container:: operations

        .. describe:: str(x)

            Returns the option's name.

    .. versionadded:: 2.0

    Attributes
    ----------
    name: :class:`str`
        The option's name.
    name_localized: Optional[:class:`str`]
        The localized name of the option, if available.

        .. versionadded:: 2.2
    name_localizations: Dict[:class:`~discord.Locale`, :class:`str`]
        The full name localization mapping, if available.

        .. versionadded:: 2.2
    description: :class:`str`
        The option's description, if any.
    description_localized: Optional[:class:`str`]
        The localized description of the option, if available.

        .. versionadded:: 2.2
    description_localizations: Dict[:class:`~discord.Locale`, :class:`str`]
        The full description localization mapping, if available.

        .. versionadded:: 2.2
    type: :class:`ApplicationCommandOptionType`
        The type of option.
    required: :class:`bool`
        Whether the option is required.
    min_value: Optional[Union[:class:`int`, :class:`float`]]
        Minimum value of the option. Only applicable to :attr:`ApplicationCommandOptionType.integer` and :attr:`ApplicationCommandOptionType.number`.
    max_value: Optional[Union[:class:`int`, :class:`float`]]
        Maximum value of the option. Only applicable to :attr:`ApplicationCommandOptionType.integer` and :attr:`ApplicationCommandOptionType.number`.
    min_length: Optional[:class:`int`]
        Minimum length of the option. Only applicable to :attr:`ApplicationCommandOptionType.string`.

        .. versionadded:: 2.2
    max_length: Optional[:class:`int`]
        Maximum length of the option. Only applicable to :attr:`ApplicationCommandOptionType.string`.

        .. versionadded:: 2.2
    choices: List[:class:`OptionChoice`]
        A list of possible choices to choose from. If these are present, you must choose one from them.

        Only applicable to :attr:`ApplicationCommandOptionType.string`, :attr:`ApplicationCommandOptionType.integer`, and :attr:`ApplicationCommandOptionType.number`.
    channel_types: List[:class:`ChannelType`]
        A list of channel types that you can choose from. If these are present, you must choose a channel that is one of these types.

        Only applicable to :attr:`ApplicationCommandOptionType.channel`.
    autocomplete: :class:`bool`
        Whether the option autocompletes.

        Only applicable to :attr:`ApplicationCommandOptionType.string`, :attr:`ApplicationCommandOptionType.integer`, and :attr:`ApplicationCommandOptionType.number`.
        Always ``False`` if :attr:`choices` are present.
    """

    __slots__ = (
        '_state',
        'name',
        'description',
        'name_localized',
        'name_localizations',
        'description_localized',
        'description_localizations',
        'type',
        'required',
        'min_value',
        'max_value',
        'min_length',
        'max_length',
        'choices',
        'channel_types',
        'autocomplete',
    )

    def __init__(self, data: OptionPayload, state: ConnectionState):
        self._state = state
        self.name, self.name_localized, self.name_localizations = _parse_localizations(data, 'name')
        self.description, self.description_localized, self.description_localizations = _parse_localizations(
            data, 'description'
        )
        self.type: ApplicationCommandOptionType = try_enum(ApplicationCommandOptionType, data['type'])
        self.required: bool = data.get('required', False)
        self.min_value: Optional[Union[int, float]] = data.get('min_value')
        self.max_value: Optional[Union[int, float]] = data.get('max_value')
        self.min_length: Optional[int] = data.get('min_length')
        self.max_length: Optional[int] = data.get('max_length')
        self.choices = [OptionChoice(choice, self.type) for choice in data.get('choices', [])]
        self.channel_types: List[ChannelType] = [try_enum(ChannelType, c) for c in data.get('channel_types', [])]
        self.autocomplete: bool = data.get('autocomplete', False)

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f'<Option name={self.name!r} type={self.type!r} required={self.required}>'

    @property
    def display_name(self) -> str:
        """:class:`str`: The localized name if available, otherwise :attr:`name`.

        .. versionadded:: 2.2
        """
        return self.name_localized or self._state.parsed_locale._resolve_from(self.name_localizations) or self.name

    @property
    def display_description(self) -> str:
        """:class:`str`: The localized description if available, otherwise :attr:`description`.

        .. versionadded:: 2.2
        """
        return (
            self.description_localized
            or self._state.parsed_locale._resolve_from(self.description_localizations)
            or self.description
        )

    def _convert(self, value):
        for choice in self.choices:
            new_value = choice._convert(value)
            if new_value != value:
                return new_value
        return value

    def to_dict(self) -> ApplicationCommandOption:
        data = {
            'type': self.type.value,
            'name': self.name,
            'description': self.description,
        }
        if self.name_localized is not None:
            data['name_localized'] = self.name_localized
        if self.name_localizations:
            data['name_localizations'] = {locale.value: value for locale, value in self.name_localizations.items()}
        if self.description_localized is not None:
            data['description_localized'] = self.description_localized
        if self.description_localizations:
            data['description_localizations'] = {
                locale.value: value for locale, value in self.description_localizations.items()
            }
        if self.required:
            data['required'] = self.required
        if self.min_value is not None:
            data['min_value'] = self.min_value
        if self.max_value is not None:
            data['max_value'] = self.max_value
        if self.min_length is not None:
            data['min_length'] = self.min_length
        if self.max_length is not None:
            data['max_length'] = self.max_length
        if self.choices:
            data['choices'] = [choice.to_dict() for choice in self.choices]
        if self.channel_types:
            data['channel_types'] = [channel_type.value for channel_type in self.channel_types]
        if self.autocomplete:
            data['autocomplete'] = self.autocomplete
        return data  # type: ignore


class OptionChoice:
    """Represents a choice for an option.

    .. container:: operations

        .. describe:: str(x)

            Returns the choice's name.

    .. versionadded:: 2.0

    Attributes
    ----------
    name: :class:`str`
        The choice's displayed name.
    name_localized: Optional[:class:`str`]
        The localized choice name, if available.

        .. versionadded:: 2.2
    name_localizations: Dict[:class:`~discord.Locale`, :class:`str`]
        The full name localization mapping, if available.

        .. versionadded:: 2.2
    value: Union[:class:`str`, :class:`int`, :class:`float`]
        The choice's value. The type of this depends on the option's type.
    """

    __slots__ = ('name', 'name_localized', 'name_localizations', 'value')

    def __init__(self, data: OptionChoicePayload, type: ApplicationCommandOptionType):
        self.name, self.name_localized, self.name_localizations = _parse_localizations(data, 'name')
        self.value: Union[str, int, float]
        if type is ApplicationCommandOptionType.string:
            self.value = data['value']
        elif type is ApplicationCommandOptionType.integer:
            self.value = int(data['value'])
        elif type is ApplicationCommandOptionType.number:
            self.value = float(data['value'])

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f'<OptionChoice name={self.name!r} value={self.value!r}>'

    def _convert(self, value):
        if value is self or value == self.name:
            return self.value
        return value

    def to_dict(self) -> OptionChoicePayload:
        data: Dict[str, Any] = {
            'name': self.name,
            'value': self.value,
        }
        if self.name_localized is not None:
            data['name_localized'] = self.name_localized
        if self.name_localizations:
            data['name_localizations'] = {locale.value: value for locale, value in self.name_localizations.items()}
        return data  # type: ignore


class ApplicationCommandAutocompleteChoice:
    """Represents an application command autocomplete choice.

    .. versionadded:: 2.2

    Attributes
    ----------
    name: :class:`str`
        The choice name.
    name_localized: Optional[:class:`str`]
        The localized choice name shown by the client, if available.
    value: Union[:class:`str`, :class:`int`, :class:`float`]
        The parsed choice value.
    """

    __slots__ = ('name', 'name_localized', 'value')

    def __init__(self, data: ApplicationCommandAutocompleteChoicePayload, option: Option):
        self.name: str = data['name']
        self.name_localized: Optional[str] = data.get('name_localized')
        self.value: Union[str, int, float]
        if option.type is ApplicationCommandOptionType.integer:
            self.value = int(data['value'])
        elif option.type is ApplicationCommandOptionType.number:
            self.value = float(data['value'])
        else:
            self.value = str(data['value'])

    @property
    def display_name(self) -> str:
        """:class:`str`: The localized name if available, otherwise :attr:`name`."""
        return self.name_localized or self.name

    def __repr__(self) -> str:
        return f'<ApplicationCommandAutocompleteChoice name={self.name!r} value={self.value!r}>'


class ApplicationCommandAutocomplete:
    """Represents an application command autocomplete response.

    .. versionadded:: 2.2

    Attributes
    ----------
    nonce: Union[:class:`int`, :class:`str`]
        The nonce used to correlate the response to the request.
    channel: :class:`abc.Messageable`
        The channel the autocomplete request originated from.
    command: :class:`~discord.SlashCommand`
        The root command that requested autocomplete choices.
    option: :class:`Option`
        The focused option that requested autocomplete choices.
    value: Union[:class:`str`, :class:`int`, :class:`float`]
        The parsed focused option value used for the request.
    choices: List[:class:`ApplicationCommandAutocompleteChoice`]
        The choices returned by Discord.
    """

    __slots__ = ('nonce', 'channel', 'command', 'option', 'value', 'choices', '_state')

    def __init__(
        self,
        *,
        state: ConnectionState,
        data: gw.ApplicationCommandAutocompleteEvent,
        context: Tuple[Messageable, SlashCommand, Option, Union[str, int, float]],
    ) -> None:
        self._state = state
        self.nonce: Union[int, str] = data['nonce']
        self.channel, self.command, self.option, self.value = context
        self.choices: List[ApplicationCommandAutocompleteChoice] = [
            ApplicationCommandAutocompleteChoice(choice, self.option) for choice in data.get('choices', [])
        ]

    def __repr__(self) -> str:
        return (
            f'<ApplicationCommandAutocomplete nonce={self.nonce!r} command={self.command!r} '
            f'option={self.option!r} choices={len(self.choices)}>'
        )


def _command_factory(command_type: int) -> Tuple[ApplicationCommandType, Type[BaseCommand]]:
    value = try_enum(ApplicationCommandType, command_type)
    if value is ApplicationCommandType.chat_input:
        return value, SlashCommand
    elif value is ApplicationCommandType.user:
        return value, UserCommand
    elif value is ApplicationCommandType.message:
        return value, MessageCommand
    elif value is ApplicationCommandType.primary_entry_point:
        return value, PrimaryEntryPointCommand
    else:
        return value, BaseCommand

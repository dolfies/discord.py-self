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

from typing import TYPE_CHECKING, Collection, List, Literal, Mapping, Optional, Sequence, Union

from . import utils
from .asset import Asset, AssetMixin
from .enums import (
    ApplicationAssetType,
    ApplicationType,
    ApplicationVerificationState,
    Distributor,
    Locale,
    RPCApplicationState,
    StoreApplicationState,
    try_enum,
)
from .flags import ApplicationFlags
from .mixins import Hashable
from .permissions import Permissions
from .store import SKU, StoreAsset, StoreListing
from .user import User
from .utils import _bytes_to_base64_data, _parse_localizations

if TYPE_CHECKING:
    from datetime import date

    from .abc import Snowflake
    from .enums import SKUAccessLevel, SKUFeature, SKUGenre, SKUType
    from .file import File
    from .guild import Guild
    from .state import ConnectionState
    from .store import ContentRating
    from .types.appinfo import (
        AppInfo as AppInfoPayload,
        Asset as AssetPayload,
        Company as CompanyPayload,
        PartialAppInfo as PartialAppInfoPayload,
    )
    from .types.user import User as UserPayload

__all__ = (
    'Company',
    'EULA',
    'Achievement',
    'ApplicationBot',
    'ApplicationExecutable',
    'ApplicationInstallParams',
    'Application',
    'PartialApplication',
    'InteractionApplication',
)

MISSING = utils.MISSING


class Company(Hashable):
    """Represents a Discord company. This is usually the developer or publisher of an application.

    .. container:: operations

        .. describe:: x == y

            Checks if two companies are equal.

        .. describe:: x != y

            Checks if two companies are not equal.

        .. describe:: hash(x)

            Return the company's hash.

        .. describe:: str(x)

            Returns the company's name.

    .. versionadded:: 2.0

    Attributes
    -----------
    id: :class:`int`
        The company's ID.
    name: :class:`str`
        The company's name.
    """

    __slots__ = (
        'id',
        'name',
    )

    def __init__(self, data: CompanyPayload):
        self.id: int = int(data['id'])
        self.name: str = data['name']

    def __str__(self) -> str:
        return self.name


class EULA(Hashable):
    """Represents the EULA for an application.

    This is usually found on applications that are a game.

    .. container:: operations

        .. describe:: x == y

            Checks if two EULAs are equal.

        .. describe:: x != y

            Checks if two EULAs are not equal.

        .. describe:: hash(x)

            Returns the EULA's hash.

        .. describe:: str(x)

            Returns the EULA's name.

    .. versionadded:: 2.0

    Attributes
    -----------
    id: :class:`int`
        The EULA's ID.
    name: :class:`str`
        The EULA's name.
    content: :class:`str`
        The EULA's content.
    """

    __slots__ = ('id', 'name', 'content')

    def __init__(self, data: dict) -> None:
        self.id: int = int(data['id'])
        self.name: str = data['name']
        self.content: str = data['content']

    def __repr__(self) -> str:
        return f'<StoreEULA id={self.id} name={self.name!r}>'

    def __str__(self) -> str:
        return self.name


class Achievement(Hashable):
    """Represents a Discord application achievement.

    .. container:: operations

        .. describe:: x == y

            Checks if two achievements are equal.

        .. describe:: x != y

            Checks if two achievements are not equal.

        .. describe:: hash(x)

            Return the achievement's hash.

        .. describe:: str(x)

            Returns the achievement's name.

    .. versionadded:: 2.0

    Attributes
    -----------
    id: :class:`int`
        The achievement's ID.
    name: :class:`str`
        The achievement's name.
    name_localizations: Dict[:class:`locale`, :class:`str`]
        The achievement's name localized to other languages, if available.
    description: :class:`str`
        The achievement's description.
    description_localizations: Dict[:class:`locale`, :class:`str`]
        The achievement's description localized to other languages, if available.
    application_id: :class:`int`
        The application ID that the achievement belongs to.
    application: :class:`PartialApplication`
        The application that the achievement belongs to.
    secure: :class:`bool`
        Whether the achievement is secure.
    secret: :class:`bool`
        Whether the achievement is secret.
    """

    __slots__ = (
        'id',
        'name',
        'name_localizations',
        'description',
        'description_localizations',
        'application_id',
        'application',
        'secure',
        'secret',
        '_icon',
        '_state',
    )

    if TYPE_CHECKING:
        name: str
        name_localizations: dict[Locale, str]
        description: str
        description_localizations: dict[Locale, str]

    def __init__(self, *, data: dict, state: ConnectionState, application: PartialApplication):
        self._state = state
        self.application = application
        self._update(data)

    def _update(self, data: dict):
        self.id: int = int(data['id'])
        self.application_id: int = int(data['application_id'])
        self.secure: bool = data['secure']
        self.secret: bool = data['secret']
        self._icon = data.get('icon', data.get('icon_hash'))

        self.name, self.name_localizations = _parse_localizations(data, 'name')
        self.description, self.description_localizations = _parse_localizations(data, 'description')

    def __repr__(self) -> str:
        return f'<Achievement id={self.id} name={self.name!r}>'

    def __str__(self) -> str:
        return self.name

    @property
    def icon(self) -> Optional[Asset]:
        """:class:`Asset`: Returns the achievement's icon, if available."""
        if self._icon is None:
            return None
        return Asset._from_achievement_icon(self._state, self.application_id, self.id, self._icon)

    async def edit(
        self,
        *,
        name: str = MISSING,
        name_localizations: Mapping[Locale, str] = MISSING,
        description: str = MISSING,
        description_localizations: Mapping[Locale, str] = MISSING,
        icon: bytes = MISSING,
        secure: bool = MISSING,
        secret: bool = MISSING,
    ) -> None:
        """|coro|

        Edits the achievement.

        Parameters
        -----------
        name: :class:`str`
            The achievement's name.
        name_localizations: Dict[:class:`locale`, :class:`str`]
            The achievement's name localized to other languages.
        description: :class:`str`
            The achievement's description.
        description_localizations: Dict[:class:`locale`, :class:`str`]
            The achievement's description localized to other languages.
        icon: :class:`bytes`
            A :term:`py:bytes-like object` representing the new icon.
        secure: :class:`bool`
            Whether the achievement is secure.
        secret: :class:`bool`
            Whether the achievement is secret.

        Raises
        -------
        Forbidden
            You do not have permissions to edit the achievement.
        HTTPException
            Editing the achievement failed.
        """
        payload = {}
        if secure is not MISSING:
            payload['secure'] = secure
        if secret is not MISSING:
            payload['secret'] = secret
        if icon is not MISSING:
            payload['icon'] = utils._bytes_to_base64_data(icon)

        if name is not MISSING or name_localizations is not MISSING:
            localizations = (name_localizations or {}) if name_localizations is not MISSING else self.name_localizations
            payload['name'] = {'default': name or self.name, 'localizations': {str(k): v for k, v in localizations.items()}}
        if description is not MISSING or description_localizations is not MISSING:
            localizations = (
                (name_localizations or {}) if description_localizations is not MISSING else self.description_localizations
            )
            payload['description'] = {
                'default': description or self.description,
                'localizations': {str(k): v for k, v in localizations.items()},
            }

        data = await self._state.http.edit_achievement(self.application_id, self.id, payload)
        self._update(data)

    async def delete(self):
        """|coro|

        Deletes the achievement.

        Raises
        -------
        Forbidden
            You do not have permissions to delete the achievement.
        HTTPException
            Deleting the achievement failed.
        """
        await self._state.http.delete_achievement(self.application_id, self.id)


class ThirdPartySKU:
    """Represents an application's primary SKU on third-party platforms.

    .. versionadded:: 2.0

    Attributes
    -----------
    distributor: :class:`Distributor`
        The distributor of the SKU.
    id: Optional[:class:`str`]
        The product ID.
    sku_id: Optional[:class:`str`]
        The SKU ID.
    """

    __slots__ = ('distributor', 'id', 'sku_id')

    def __init__(self, *, data: dict):
        self.distributor: Distributor = try_enum(Distributor, data['distributor'])
        self.id: Optional[str] = data.get('id')
        self.sku_id: Optional[str] = data.get('sku_id')

    def __repr__(self) -> str:
        return f'<ThirdPartySKU distributor={self.distributor!r} id={self.id!r} sku_id={self.sku_id!r}>'


class ApplicationBot(User):
    """Represents a bot attached to an application.

    .. container:: operations

        .. describe:: x == y

            Checks if two bots are equal.

        .. describe:: x != y

            Checks if two bots are not equal.

        .. describe:: hash(x)

            Return the bot's hash.

        .. describe:: str(x)

            Returns the bot's name with discriminator.

    .. versionadded:: 2.0

    Attributes
    -----------
    application: :class:`Application`
        The application that the bot is attached to.
    public: :class:`bool`
        Whether the bot can be invited by anyone or if it is locked
        to the application owner.
    require_code_grant: :class:`bool`
        Whether the bot requires the completion of the full OAuth2 code
        grant flow to join.
    """

    __slots__ = ('application', 'public', 'require_code_grant')

    def __init__(self, *, data: UserPayload, state: ConnectionState, application: Application):
        super().__init__(state=state, data=data)
        self.application = application

    def _update(self, data: UserPayload) -> None:
        super()._update(data)
        self.public: bool = data.get('public', True)
        self.require_code_grant: bool = data.get('require_code_grant', False)

    @property
    def bio(self) -> Optional[str]:
        """Optional[:class:`str`]: Returns the bot's 'about me' section."""
        return self.application.description or None

    @property
    def mfa_enabled(self) -> bool:
        """:class:`bool`: Whether the bot has MFA turned on and working. This follows the bot owner's value."""
        if self.application.owner.public_flags.team_user:
            return True
        return self._state.user.mfa_enabled  # type: ignore # user is always present at this point

    @property
    def verified(self) -> bool:
        """:class:`bool`: Whether the bot's email has been verified. This follows the bot owner's value."""
        # Not possible to have a bot without a verified email
        return True

    async def edit(
        self,
        *,
        username: str = MISSING,
        avatar: Optional[bytes] = MISSING,
        bio: Optional[str] = MISSING,
        public: bool = MISSING,
        require_code_grant: bool = MISSING,
    ) -> None:
        """|coro|

        Edits the bot.

        Parameters
        -----------
        username: :class:`str`
            The new username you wish to change your bot to.
        avatar: Optional[:class:`bytes`]
            A :term:`py:bytes-like object` representing the image to upload.
            Could be ``None`` to denote no avatar.
        bio: Optional[:class:`str`]
            Your bot's 'about me' section. This is just the application description.
            Could be ``None`` to represent no 'about me'.
        public: :class:`bool`
            Whether the bot is public or not.
        require_code_grant: :class:`bool`
            Whether the bot requires a code grant or not.

        Raises
        ------
        Forbidden
            You are not allowed to edit this bot.
        HTTPException
            Editing the bot failed.
        """
        payload = {}
        if username is not MISSING:
            payload['username'] = username
        if avatar is not MISSING:
            if avatar is not None:
                payload['avatar'] = _bytes_to_base64_data(avatar)
            else:
                payload['avatar'] = None

        if payload:
            data = await self._state.http.edit_bot(self.application.id, payload)
            self._update(data)
            payload = {}

        if public is not MISSING:
            payload['bot_public'] = public
        if require_code_grant is not MISSING:
            payload['bot_require_code_grant'] = require_code_grant
        if bio is not MISSING:
            payload['description'] = bio

        if payload:
            data = await self._state.http.edit_application(self.application.id, payload)
            self.application._update(data)

    async def token(self) -> None:
        """|coro|

        Gets the bot's token.

        This revokes all previous tokens.

        Raises
        ------
        Forbidden
            You are not allowed to reset the token.
        HTTPException
            Resetting the token failed.

        Returns
        -------
        :class:`str`
            The new token.
        """
        data = await self._state.http.reset_bot_token(self.application.id)
        return data['token']


class ApplicationExecutable:
    """Represents an application executable.

    .. container:: operations

        .. describe:: str(x)

            Returns the executable's name.

    .. versionadded:: 2.0

    Attributes
    -----------
    name: :class:`str`
        The name of the executable.
    os: :class:`str`
        The operating system the executable is for.
    launcher: :class:`bool`
        Whether the executable is a launcher or not.
    application: :class:`PartialApplication`
        The application that the executable is for.
    """

    __slots__ = (
        'name',
        'os',
        'launcher',
        'application',
    )

    def __init__(self, *, data: dict, application: PartialApplication):
        self.name: str = data['name']
        self.os: Literal['win32', 'linux', 'darwin'] = data['os']
        self.launcher: bool = data['is_launcher']
        self.application = application

    def __repr__(self) -> str:
        return f'<ApplicationExecutable name={self.name!r} os={self.os!r} launcher={self.launcher!r}>'

    def __str__(self) -> str:
        return self.name


class ApplicationInstallParams:
    """Represents an application's authorization parameters.

    .. container:: operations

        .. describe:: str(x)

            Returns the authorization URL.

    .. versionadded:: 2.0

    Attributes
    ----------
    application_id: :class:`int`
        The ID of the application to be authorized.
    scopes: List[:class:`str`]
        The list of `OAuth2 scopes <https://discord.com/developers/docs/topics/oauth2#shared-resources-oauth2-scopes>`_
        to add the application with.
    permissions: :class:`Permissions`
        The permissions to grant to the added bot.
    """

    __slots__ = ('application_id', 'scopes', 'permissions')

    def __init__(
        self, application_id: int, *, scopes: Optional[List[str]] = None, permissions: Optional[Permissions] = None
    ):
        self.application_id: int = application_id
        self.scopes: List[str] = scopes or ['bot', 'applications.commands']
        self.permissions: Permissions = permissions or Permissions(0)

    @classmethod
    def from_application(cls, application: Snowflake, data: dict) -> ApplicationInstallParams:
        return cls(
            application.id,
            scopes=data.get('scopes', []),
            permissions=Permissions(data.get('permissions', 0)),
        )

    def __repr__(self) -> str:
        return f'<ApplicationInstallParams application_id={self.application_id} scopes={self.scopes!r} permissions={self.permissions!r}>'

    def __str__(self) -> str:
        return self.url

    @property
    def url(self) -> str:
        """:class:`str`: The URL to add the application with the parameters."""
        return utils.oauth_url(self.application_id, permissions=self.permissions, scopes=self.scopes)

    def to_dict(self) -> dict:
        return {
            'scopes': self.scopes,
            'permissions': self.permissions.value,
        }


class ApplicationAsset(AssetMixin, Hashable):
    """Represents an application asset.

    .. container:: operations

        .. describe:: x == y

            Checks if two assets are equal.

        .. describe:: x != y

            Checks if two assets are not equal.

        .. describe:: hash(x)

            Return the asset's hash.

        .. describe:: str(x)

            Returns the asset's name.

    .. versionadded:: 2.0

    Attributes
    -----------
    application: Union[:class:`PartialApplication`, :class:`InteractionApplication`]
        The application that the asset is for.
    id: :class:`int`
        The asset's ID.
    name: :class:`str`
        The asset's name.
    """

    __slots__ = ('_state', 'id', 'name', 'type', 'application')

    def __init__(
        self, *, data: AssetPayload, state: ConnectionState, application: Union[PartialApplication, InteractionApplication]
    ) -> None:
        self._state: ConnectionState = state
        self.application = application
        self.id: int = int(data['id'])
        self.name: str = data['name']
        self.type: ApplicationAssetType = try_enum(ApplicationAssetType, data.get('type', 1))

    def __repr__(self) -> str:
        return f'<ApplicationAsset id={self.id} name={self.name!r}>'

    def __str__(self) -> str:
        return self.name

    @property
    def animated(self) -> bool:
        """:class:`bool`: Indicates if the asset is animated. Here for compatibility purposes."""
        return False

    @property
    def url(self) -> str:
        """:class:`str`: Returns the URL of the asset."""
        return f'{Asset.BASE}/app-assets/{self.application.id}/{self.id}.png'

    async def delete(self) -> None:
        """|coro|

        Deletes the asset.

        Raises
        ------
        Forbidden
            You are not allowed to delete this asset.
        HTTPException
            Deleting the asset failed.
        """
        await self._state.http.delete_asset(self.application.id, self.id)


class PartialApplication(Hashable):
    """Represents a partial Application.

    .. container:: operations

        .. describe:: x == y

            Checks if two applications are equal.

        .. describe:: x != y

            Checks if two applications are not equal.

        .. describe:: hash(x)

            Return the application's hash.

        .. describe:: str(x)

            Returns the application's name.

    .. versionadded:: 2.0

    Attributes
    -------------
    id: :class:`int`
        The application ID.
    name: :class:`str`
        The application name.
    description: :class:`str`
        The application description.
    rpc_origins: List[:class:`str`]
        A list of RPC origin URLs, if RPC is enabled.
    verify_key: :class:`str`
        The hex encoded key for verification in interactions and the
        GameSDK's `GetTicket <https://discord.com/developers/docs/game-sdk/applications#getticket>`_.
    terms_of_service_url: Optional[:class:`str`]
        The application's terms of service URL, if set.
    privacy_policy_url: Optional[:class:`str`]
        The application's privacy policy URL, if set.
    public: :class:`bool`
        Whether the integration can be invited by anyone or if it is locked
        to the application owner.
    require_code_grant: :class:`bool`
        Whether the integration requires the completion of the full OAuth2 code
        grant flow to join
    max_participants: Optional[:class:`int`]
        The max number of people that can participate in the activity.
        Only available for embedded activities.
    premium_tier_level: Optional[:class:`int`]
        The required premium tier level to launch the activity.
        Only available for embedded activities.
    type: Optional[:class:`ApplicationType`]
        The type of application.
    tags: List[:class:`str`]
        A list of tags that describe the application.
    overlay: :class:`bool`
        Whether the application has a Discord overlay or not.
    guild_id: Optional[:class:`int`]
        The ID of the guild the application is attached to, if any.
    primary_sku_id: Optional[:class:`int`]
        The application's primary SKU ID, if any.
        This is usually the ID of the game SKU if the application is a game.
    slug: Optional[:class:`str`]
        The slug for the application's primary SKU, if any.
    eula_id: Optional[:class:`int`]
        The ID of the EULA for the application, if any.
    aliases: List[:class:`str`]
        A list of aliases that can be used to identify the application.
    developers: List[:class:`Company`]
        A list of developers that developed the application.
    publishers: List[:class:`Company`]
        A list of publishers that published the application.
    executables: List[:class:`ApplicationExecutable`]
        A list of executables that are the application's.
    third_party_skus: List[:class:`ThirdPartySKU`]
        A list of third party platforms the SKU is available at.
    custom_install_url: Optional[:class:`str`]
        The custom URL to use for authorizing the application, if specified.
    install_params: Optional[:class:`ApplicationInstallParams`]
        The parameters to use for authorizing the application, if specified.
    """

    __slots__ = (
        '_state',
        'id',
        'name',
        'description',
        'rpc_origins',
        'verify_key',
        'terms_of_service_url',
        'privacy_policy_url',
        '_icon',
        '_flags',
        '_cover_image',
        '_splash',
        'public',
        'require_code_grant',
        'type',
        'hook',
        'premium_tier_level',
        'tags',
        'max_participants',
        'overlay',
        'overlay_compatibility_hook',
        'aliases',
        'developers',
        'publishers',
        'executables',
        'third_party_skus',
        'custom_install_url',
        'install_params',
        'guild_id',
        'primary_sku_id',
        'slug',
        'eula_id',
    )

    def __init__(self, *, state: ConnectionState, data: PartialAppInfoPayload):
        self._state: ConnectionState = state
        self._update(data)

    def __str__(self) -> str:
        return self.name

    def _update(self, data: PartialAppInfoPayload) -> None:
        self.id: int = int(data['id'])
        self.name: str = data['name']
        self.description: str = data['description']
        self.rpc_origins: Optional[List[str]] = data.get('rpc_origins') or []
        self.verify_key: str = data['verify_key']

        self.aliases: List[str] = data.get('aliases', [])
        self.developers: List[Company] = [Company(data=d) for d in data.get('developers', [])]
        self.publishers: List[Company] = [Company(data=d) for d in data.get('publishers', [])]
        self.executables: List[ApplicationExecutable] = [
            ApplicationExecutable(data=e, application=self) for e in data.get('executables', [])
        ]
        self.third_party_skus: List[ThirdPartySKU] = [ThirdPartySKU(data=t) for t in data.get('third_party_skus', [])]

        self._icon: Optional[str] = data.get('icon')
        self._cover_image: Optional[str] = data.get('cover_image')
        self._splash: Optional[str] = data.get('splash')

        self.terms_of_service_url: Optional[str] = data.get('terms_of_service_url')
        self.privacy_policy_url: Optional[str] = data.get('privacy_policy_url')
        self._flags: int = data.get('flags', 0)
        self.type: Optional[ApplicationType] = try_enum(ApplicationType, data['type']) if data.get('type') else None
        self.hook: bool = data.get('hook', False)
        self.max_participants: Optional[int] = data.get('max_participants')
        self.premium_tier_level: Optional[int] = data.get('embedded_activity_config', {}).get('activity_premium_tier_level')
        self.tags: List[str] = data.get('tags', [])
        self.overlay: bool = data.get('overlay', False)
        self.overlay_compatibility_hook: bool = data.get('overlay_compatibility_hook', False)
        self.guild_id: Optional[int] = utils._get_as_snowflake(data, 'guild_id')
        self.primary_sku_id: Optional[int] = utils._get_as_snowflake(data, 'primary_sku_id')
        self.slug: Optional[str] = data.get('slug')
        self.eula_id: Optional[int] = utils._get_as_snowflake(data, 'eula_id')

        params = data.get('install_params')
        self.custom_install_url: Optional[str] = data.get('custom_install_url')
        self.install_params: Optional[ApplicationInstallParams] = (
            ApplicationInstallParams.from_application(self, params) if params else None
        )

        self.public: bool = data.get(
            'integration_public', data.get('bot_public', True)
        )  # The two seem to be used interchangeably?
        self.require_code_grant: bool = data.get(
            'integration_require_code_grant', data.get('bot_require_code_grant', False)
        )  # Same here

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} id={self.id} name={self.name!r} description={self.description!r}>'

    @property
    def icon(self) -> Optional[Asset]:
        """Optional[:class:`Asset`]: Retrieves the application's icon asset, if any."""
        if self._icon is None:
            return None
        return Asset._from_icon(self._state, self.id, self._icon, path='app')

    @property
    def cover_image(self) -> Optional[Asset]:
        """Optional[:class:`Asset`]: Retrieves the cover image on a store embed, if any.

        This is only available if the application is a game sold on Discord.
        """
        if self._cover_image is None:
            return None
        return Asset._from_cover_image(self._state, self.id, self._cover_image)

    @property
    def splash(self) -> Optional[Asset]:
        """Optional[:class:`Asset`]: Retrieves the application's splash asset, if any."""
        if self._splash is None:
            return None
        return Asset._from_application_asset(self._state, self.id, self._splash)

    @property
    def flags(self) -> ApplicationFlags:
        """:class:`ApplicationFlags`: The flags of this application."""
        return ApplicationFlags._from_value(self._flags)

    @property
    def install_url(self) -> Optional[str]:
        """:class:`str`: The URL to install the application."""
        return self.custom_install_url or self.install_params.url if self.install_params else None

    @property
    def guild(self) -> Optional[Guild]:
        """Optional[:class:`Guild`]: The guild linked to the application, if any and available."""
        return self._state._get_guild(self.guild_id)

    @property
    def primary_sku_url(self) -> Optional[str]:
        """:class:`str`: The URL to the primary SKU of the application, if any."""
        if self.primary_sku_id:
            return f'https://discord.com/store/skus/{self.primary_sku_id}/{self.slug or "unknown"}'

    async def assets(self) -> List[ApplicationAsset]:
        """|coro|

        Retrieves the assets of this application.

        Raises
        ------
        HTTPException
            Retrieving the assets failed.

        Returns
        -------
        List[:class:`ApplicationAsset`]
            The application's assets.
        """
        state = self._state
        data = await state.http.get_app_assets(self.id)
        return [ApplicationAsset(state=state, data=d, application=self) for d in data]

    async def published_store_listings(self, *, localize: bool = True) -> List[StoreListing]:
        """|coro|

        Retrieves all published store listings for this application.

        Parameters
        ----------
        localize: :class:`bool`
            Whether to localize the store listings to the current user's locale.
            If ``False`` then all localizations are returned.

        Raises
        -------
        HTTPException
            Retrieving the listings failed.

        Returns
        -------
        List[:class:`StoreListing`]
            The store listings.
        """
        state = self._state
        data = await state.http.get_app_store_listings(self.id, country_code=state.country_code or 'US', localize=localize)
        return [StoreListing(state=state, data=d, application=self) for d in data]

    async def primary_store_listing(self, *, localize: bool = True) -> StoreListing:
        """|coro|

        Retrieves the primary store listing of this application.

        This is the public store listing of the primary SKU.

        Parameters
        -----------
        localize: :class:`bool`
            Whether to localize the store listing to the current user's locale.
            If ``False`` then all localizations are returned.

        Raises
        ------
        NotFound
            The application does not have a primary SKU.
        HTTPException
            Retrieving the store listing failed.

        Returns
        -------
        :class:`StoreListing`
            The application's primary store listing, if any.
        """
        state = self._state
        data = await state.http.get_app_store_listing(self.id, country_code=state.country_code or 'US', localize=localize)
        return StoreListing(state=state, data=data, application=self)

    async def achievements(self, completed: bool = True) -> List[Achievement]:
        """|coro|

        Retrieves the achievements for this application.

        Parameters
        -----------
        completed: :class:`bool`
            Whether to include achievements the user has completed or can access.
            This means secret achievements that are not yet unlocked will not be included.

            If ``False``, then you require access to the application.

        Raises
        -------
        Forbidden
            You do not have permissions to fetch achievements.
        HTTPException
            Fetching the achievements failed.

        Returns
        --------
        List[:class:`Achievement`]
            The achievements retrieved.
        """
        state = self._state
        data = (await state.http.get_my_achievements(self.id)) if completed else (await state.http.get_achievements(self.id))
        return [Achievement(data=achievement, state=state, application=self) for achievement in data]

    async def eula(self) -> Optional[EULA]:
        """|coro|

        Retrieves the EULA for this application.

        Raises
        -------
        HTTPException
            Retrieving the EULA failed.

        Returns
        --------
        Optional[:class:`EULA`]
            The EULA retrieved, if any.
        """
        if self.eula_id is None:
            return None

        state = self._state
        data = await state.http.get_eula(self.eula_id)
        return EULA(data=data)


class Application(PartialApplication):
    """Represents application info for an application you own.

    .. container:: operations

        .. describe:: x == y

            Checks if two applications are equal.

        .. describe:: x != y

            Checks if two applications are not equal.

        .. describe:: hash(x)

            Return the application's hash.

        .. describe:: str(x)

            Returns the application's name.

    .. versionadded:: 2.0

    Attributes
    -------------
    owner: :class:`User`
        The application owner. This may be a team user account.
    bot: Optional[:class:`ApplicationBot`]
        The bot attached to the application, if any.
    interactions_endpoint_url: Optional[:class:`str`]
        The URL interactions will be sent to, if set.
    redirect_uris: List[:class:`str`]
        A list of redirect URIs authorized for this application.
    verification_state: :class:`ApplicationVerificationState`
        The verification state of the application.
    store_application_state: :class:`StoreApplicationState`
        The approval state of the commerce application.
    rpc_application_state: :class:`RPCApplicationState`
        The approval state of the RPC usage application.
    """

    __slots__ = (
        'owner',
        'redirect_uris',
        'bot',
        'verification_state',
        'store_application_state',
        'rpc_application_state',
        'interactions_endpoint_url',
    )

    def _update(self, data: AppInfoPayload) -> None:
        super()._update(data)

        self.redirect_uris: List[str] = data.get('redirect_uris', [])
        self.interactions_endpoint_url: Optional[str] = data.get('interactions_endpoint_url')

        self.verification_state = try_enum(ApplicationVerificationState, data['verification_state'])
        self.store_application_state = try_enum(StoreApplicationState, data.get('store_application_state', 1))
        self.rpc_application_state = try_enum(RPCApplicationState, data.get('rpc_application_state', 0))

        state = self._state

        # Hacky, but I want these to be persisted
        existing = getattr(self, 'bot', None)
        if bot := data.get('bot'):
            bot['public'] = data.get('bot_public', self.public)
            bot['require_code_grant'] = data.get('bot_require_code_grant', self.require_code_grant)
        if existing is not None:
            existing._update(bot)
        else:
            self.bot: Optional[ApplicationBot] = ApplicationBot(data=bot, state=state, application=self) if bot else None

        existing = getattr(self, 'owner', None)
        if not existing:
            owner = data.get('owner')
            if owner is not None:
                self.owner: User = state.store_user(owner)
            else:
                self.owner: User = state.user  # type: ignore # state.user will always be present here

    def __repr__(self) -> str:
        return (
            f'<{self.__class__.__name__} id={self.id} name={self.name!r} '
            f'description={self.description!r} public={self.public} '
            f'owner={self.owner!r}>'
        )

    async def edit(
        self,
        *,
        name: str = MISSING,
        description: Optional[str] = MISSING,
        icon: Optional[bytes] = MISSING,
        cover_image: Optional[bytes] = MISSING,
        tags: Sequence[str] = MISSING,
        terms_of_service_url: Optional[str] = MISSING,
        privacy_policy_url: Optional[str] = MISSING,
        interactions_endpoint_url: Optional[str] = MISSING,
        redirect_uris: Sequence[str] = MISSING,
        rpc_origins: Sequence[str] = MISSING,
        public: bool = MISSING,
        require_code_grant: bool = MISSING,
        flags: ApplicationFlags = MISSING,
        custom_install_url: Optional[str] = MISSING,
        install_params: Optional[ApplicationInstallParams] = MISSING,
        developers: Sequence[Snowflake] = MISSING,
        publishers: Sequence[Snowflake] = MISSING,
        guild: Snowflake = MISSING,
        team: Snowflake = MISSING,
    ) -> None:
        """|coro|

        Edits the application.

        Parameters
        -----------
        name: :class:`str`
            The name of the application.
        description: :class:`str`
            The description of the application.
        icon: Optional[:class:`bytes`]
            The icon of the application.
        cover_image: Optional[:class:`bytes`]
            The cover image of the application.
        tags: List[:class:`str`]
            A list of tags that describe the application.
        terms_of_service_url: Optional[:class:`str`]
            The URL to the terms of service of the application.
        privacy_policy_url: Optional[:class:`str`]
            The URL to the privacy policy of the application.
        interactions_endpoint_url: Optional[:class:`str`]
            The URL interactions will be sent to, if set.
        redirect_uris: List[:class:`str`]
            A list of redirect URIs authorized for this application.
        rpc_origins: List[:class:`str`]
            A list of RPC origins authorized for this application.
        public: :class:`bool`
            Whether the application is public or not.
        require_code_grant: :class:`bool`
            Whether the application requires a code grant or not.
        flags: :class:`ApplicationFlags`
            The flags of the application.
        developers: List[:class:`Company`]
            A list of companies that are the developers of the application.
        publishers: List[:class:`Company`]
            A list of companies that are the publishers of the application.
        guild: :class:`Guild`
            The guild to transfer the application to.
        team: :class:`Team`
            The team to transfer the application to.

        Raises
        -------
        Forbidden
            You do not have permissions to edit this application.
        HTTPException
            Editing the application failed.
        """
        payload = {}
        if name is not MISSING:
            payload['name'] = name or ''
        if description is not MISSING:
            payload['description'] = description or ''
        if icon is not MISSING:
            if icon is not None:
                payload['icon'] = utils._bytes_to_base64_data(icon)
            else:
                payload['icon'] = ''
        if cover_image is not MISSING:
            if cover_image is not None:
                payload['cover_image'] = utils._bytes_to_base64_data(cover_image)
            else:
                payload['cover_image'] = ''
        if tags is not MISSING:
            payload['tags'] = tags or []
        if terms_of_service_url is not MISSING:
            payload['terms_of_service_url'] = terms_of_service_url or ''
        if privacy_policy_url is not MISSING:
            payload['privacy_policy_url'] = privacy_policy_url or ''
        if interactions_endpoint_url is not MISSING:
            payload['interactions_endpoint_url'] = interactions_endpoint_url or ''
        if redirect_uris is not MISSING:
            payload['redirect_uris'] = redirect_uris
        if rpc_origins is not MISSING:
            payload['rpc_origins'] = rpc_origins
        if public is not MISSING:
            if self.bot:
                payload['bot_public'] = public
            else:
                payload['integration_public'] = public
        if require_code_grant is not MISSING:
            if self.bot:
                payload['bot_require_code_grant'] = require_code_grant
            else:
                payload['integration_require_code_grant'] = require_code_grant
        if flags is not MISSING:
            payload['flags'] = flags.value
        if custom_install_url is not MISSING:
            payload['custom_install_url'] = custom_install_url or ''
        if install_params is not MISSING:
            payload['install_params'] = install_params.to_dict() if install_params else None
        if developers is not MISSING:
            payload['developer_ids'] = [developer.id for developer in developers or []]
        if publishers is not MISSING:
            payload['publisher_ids'] = [publisher.id for publisher in publishers or []]
        if guild:
            payload['guild_id'] = guild.id

        if team:
            await self._state.http.transfer_application(self.id, team.id)

        data = await self._state.http.edit_application(self.id, payload)

        self._update(data)

    async def fetch_bot(self) -> ApplicationBot:
        """|coro|

        Retrieves the bot attached to this application.

        Raises
        ------
        Forbidden
            You do not have permissions to fetch the bot,
            or the application does not have a bot.
        HTTPException
            Fetching the bot failed.
        """
        data = await self._state.http.edit_bot(self.id, {})
        data['public'] = self.public  # type: ignore
        data['require_code_grant'] = self.require_code_grant  # type: ignore

        self.bot = ApplicationBot(data=data, state=self._state, application=self)
        return self.bot

    async def create_bot(self) -> None:
        """|coro|

        Creates a bot attached to this application.

        Raises
        ------
        Forbidden
            You do not have permissions to create bots.
        HTTPException
            Creating the bot failed.

        Returns
        -------
        :class:`ApplicationBot`
            The bot that was created.
        """
        state = self._state
        await state.http.botify_app(self.id)

        # The endpoint no longer returns the bot so we fetch ourselves
        # This is fine, the dev portal does the same
        data = await state.http.get_my_application(self.id)
        self._update(data)
        return self.bot  # type: ignore

    async def create_asset(
        self, name: str, image: bytes, *, type: ApplicationAssetType = ApplicationAssetType.one
    ) -> ApplicationAsset:
        """|coro|

        Uploads an asset to this application.

        Parameters
        -----------
        name: :class:`str`
            The name of the asset.
        image: :class:`bytes`
            The image of the asset. Cannot be animated.

        Raises
        -------
        Forbidden
            You do not have permissions to upload assets.
        HTTPException
            Uploading the asset failed.

        Returns
        --------
        :class:`ApplicationAsset`
            The created asset.
        """
        state = self._state
        data = await state.http.create_asset(self.id, name, int(type), image)
        return ApplicationAsset(state=state, data=data, application=self)

    async def store_assets(self) -> List[StoreAsset]:
        """|coro|

        Retrieves the store assets for this application.

        Raises
        -------
        Forbidden
            You do not have permissions to store assets.
        HTTPException
            Storing the assets failed.

        Returns
        --------
        List[:class:`StoreAsset`]
            The store assets retrieved.
        """
        state = self._state
        data = await self._state.http.get_store_assets(self.id)
        return [StoreAsset(data=asset, state=state, parent=self) for asset in data]

    async def create_store_asset(self, file: File, /) -> StoreAsset:
        """|coro|

        Uploads a store asset to this application.

        Parameters
        -----------
        file: :class:`File`
            The file to upload. Must be a PNG, JPG, GIF, or MP4.

        Raises
        -------
        Forbidden
            You do not have permissions to upload assets.
        HTTPException
            Uploading the asset failed.

        Returns
        --------
        :class:`StoreAsset`
            The created asset.
        """
        state = self._state
        data = await state.http.create_store_asset(self.id, file)
        return StoreAsset(state=state, data=data, parent=self)

    async def skus(self, *, with_bundled_skus: bool = True, localize: bool = True) -> List[SKU]:
        """|coro|

        Retrieves the SKUs for this application.

        Parameters
        -----------
        with_bundled_skus: :class:`bool`
            Whether to include bundled SKUs in the response.
        localize: :class:`bool`
            Whether to localize the SKU name and description to the current user's locale.
            If ``False`` then all localizations are returned.

        Raises
        -------
        Forbidden
            You do not have permissions to fetch SKUs.
        HTTPException
            Fetching the SKUs failed.

        Returns
        --------
        List[:class:`SKU`]
            The SKUs retrieved.
        """
        state = self._state
        data = await self._state.http.get_app_skus(
            self.id, country_code=state.country_code or 'US', with_bundled_skus=with_bundled_skus, localize=localize
        )
        return [SKU(data=sku, state=state, application=self) for sku in data]

    async def primary_sku(self, *, localize: bool = True) -> Optional[SKU]:
        """|coro|

        Retrieves the primary SKU for this application if it exists.
        This is usually the game SKU if the application is a game.

        Parameters
        -----------
        localize: :class:`bool`
            Whether to localize the SKU name and description to the current user's locale.
            If ``False`` then all localizations are returned.

        Raises
        -------
        Forbidden
            You do not have permissions to fetch SKUs.
        HTTPException
            Fetching the SKUs failed.

        Returns
        --------
        Optional[:class:`SKU`]
            The primary SKU retrieved.
        """
        if not self.primary_sku_id:
            return None

        state = self._state
        data = await self._state.http.get_sku(
            self.primary_sku_id, country_code=state.country_code or 'US', localize=localize
        )
        return SKU(data=data, state=state, application=self)

    async def create_sku(
        self,
        *,
        name: str,
        name_localizations: Optional[Mapping[Locale, str]] = None,
        legal_notice: Optional[str] = None,
        legal_notice_localizations: Optional[Mapping[Locale, str]] = None,
        type: SKUType,
        price_tier: Optional[int] = None,
        price_overrides: Optional[Mapping[str, int]] = None,
        sale_price_tier: Optional[int] = None,
        sale_price_overrides: Optional[Mapping[str, int]] = None,
        dependent_sku: Optional[Snowflake] = None,
        access_level: Optional[SKUAccessLevel] = None,
        features: Optional[Collection[SKUFeature]] = None,
        locales: Optional[Collection[Locale]] = None,
        genres: Optional[Collection[SKUGenre]] = None,
        content_ratings: Optional[Collection[ContentRating]] = None,
        release_date: Optional[date] = None,
        bundled_skus: Optional[Sequence[Snowflake]] = None,
        manifest_labels: Optional[Sequence[Snowflake]] = None,
    ):
        """|coro|

        Creates a SKU for this application.

        Parameters
        -----------
        name: :class:`str`
            The SKU's name.
        name_localizations: Optional[Mapping[:class:`Locale`, :class:`str`]]
            The SKU's name localized to other languages.
        legal_notice: Optional[:class:`str`]
            The SKU's legal notice.
        legal_notice_localizations: Optional[Mapping[:class:`Locale`, :class:`str`]]
            The SKU's legal notice localized to other languages.
        type: :class:`SKUType`
            The SKU's type.
        price_tier: Optional[:class:`int`]
            The price tier of the SKU.
            This is the base price in USD that other currencies will be calculated from.
        price_overrides: Optional[Mapping[:class:`str`, :class:`int`]]
            A mapping of currency to price. These prices override the base price tier.
        sale_price_tier: Optional[:class:`int`]
            The sale price tier of the SKU.
            This is the base sale price in USD that other currencies will be calculated from.
        sale_price_overrides: Optional[Mapping[:class:`str`, :class:`int`]]
            A mapping of currency to sale price. These prices override the base sale price tier.
        dependent_sku: Optional[:class:`int`]
            The ID of the SKU that this SKU is dependent on.
        access_level: Optional[:class:`SKUAccessLevel`]
            The access level of the SKU.
        features: Optional[List[:class:`SKUFeature`]]
            A list of features of the SKU.
        locales: Optional[List[:class:`Locale`]]
            A list of locales supported by the SKU.
        genres: Optional[List[:class:`SKUGenre`]]
            A list of genres of the SKU.
        release_date: Optional[:class:`date`]
            The release date of the SKU.
        bundled_skus: Optional[List[:class:`SKU`]]
            A list SKUs that are bundled with this SKU.
        manifest_labels: Optional[List[:class:`Manifest`]]
            A list of manifest labels for the SKU.

        Raises
        -------
        Forbidden
            You do not have permissions to create SKUs.
        HTTPException
            Creating the SKU failed.

        Returns
        --------
        :class:`SKU`
            The SKU created.
        """
        payload = {
            'type': int(type),
            'name': {'default': name, 'localizations': {str(k): v for k, v in (name_localizations or {}).items()}},
            'application_id': self.id,
        }
        if legal_notice or legal_notice_localizations:
            payload['legal_notice'] = {
                'default': legal_notice,
                'localizations': {str(k): v for k, v in (legal_notice_localizations or {}).items()},
            }
        if price_tier is not None:
            payload['price_tier'] = price_tier
        if price_overrides:
            payload['price'] = {str(k): v for k, v in price_overrides.items()}
        if sale_price_tier is not None:
            payload['sale_price_tier'] = sale_price_tier
        if sale_price_overrides:
            payload['sale_price'] = {str(k): v for k, v in sale_price_overrides.items()}
        if dependent_sku is not None:
            payload['dependent_sku_id'] = dependent_sku.id
        if access_level is not None:
            payload['access_level'] = int(access_level)
        if locales:
            payload['locales'] = [str(l) for l in locales]
        if features:
            payload['features'] = [int(f) for f in features]
        if genres:
            payload['genres'] = [int(g) for g in genres]
        if content_ratings:
            payload['content_ratings'] = {
                content_rating.agency: content_rating.to_dict() for content_rating in content_ratings
            }
        if release_date is not None:
            payload['release_date'] = release_date.isoformat()
        if bundled_skus:
            payload['bundled_skus'] = [s.id for s in bundled_skus]
        if manifest_labels:
            payload['manifest_labels'] = [m.id for m in manifest_labels]

        state = self._state
        data = await state.http.create_sku(payload)
        return SKU(data=data, state=state, application=self)

    async def fetch_achievement(self, achievement_id: int) -> Achievement:
        """|coro|

        Retrieves an achievement for this application.

        Parameters
        -----------
        achievement_id: :class:`int`
            The ID of the achievement to fetch.

        Raises
        ------
        Forbidden
            You do not have permissions to fetch the achievement.
        HTTPException
            Fetching the achievement failed.

        Returns
        -------
        :class:`Achievement`
            The achievement retrieved.
        """
        data = await self._state.http.get_achievement(self.id, achievement_id)
        return Achievement(data=data, state=self._state, application=self)

    async def create_achievement(
        self,
        *,
        name: str,
        name_localizations: Optional[Mapping[Locale, str]] = None,
        description: str,
        description_localizations: Optional[Mapping[Locale, str]] = None,
        icon: bytes,
        secure: bool = False,
        secret: bool = False,
    ) -> Achievement:
        """|coro|

        Creates an achievement for this application.

        Parameters
        -----------
        name: :class:`str`
            The name of the achievement.
        name_localizations: Mapping[:class:`Locale`, :class:`str`]
            The localized names of the achievement.
        description: :class:`str`
            The description of the achievement.
        description_localizations: Mapping[:class:`Locale`, :class:`str`]
            The localized descriptions of the achievement.
        icon: :class:`bytes`
            The icon of the achievement.
        secure: :class:`bool`
            Whether the achievement is secure.
        secret: :class:`bool`
            Whether the achievement is secret.

        Raises
        -------
        Forbidden
            You do not have permissions to create achievements.
        HTTPException
            Creating the achievement failed.

        Returns
        --------
        :class:`Achievement`
            The created achievement.
        """
        state = self._state
        data = await state.http.create_achievement(
            self.id,
            name=name,
            name_localizations={str(k): v for k, v in name_localizations.items()} if name_localizations else None,
            description=description,
            description_localizations={str(k): v for k, v in description_localizations.items()}
            if description_localizations
            else None,
            icon=icon,
            secure=secure,
            secret=secret,
        )
        return Achievement(state=state, data=data, application=self)

    async def secret(self) -> str:
        """|coro|

        Gets the application's secret.

        This revokes all previous secrets.

        Raises
        ------
        Forbidden
            You do not have permissions to reset the secret.
        HTTPException
            Getting the secret failed.

        Returns
        -------
        :class:`str`
            The new secret.
        """
        data = await self._state.http.reset_secret(self.id)
        return data['secret']


class InteractionApplication(Hashable):
    """Represents a very partial application received in interaction contexts.

    .. container:: operations

        .. describe:: x == y

            Checks if two applications are equal.

        .. describe:: x != y

            Checks if two applications are not equal.

        .. describe:: hash(x)

            Return the application's hash.

        .. describe:: str(x)

            Returns the application's name.

    .. versionadded:: 2.0

    Attributes
    -------------
    id: :class:`int`
        The application ID.
    name: :class:`str`
        The application name.
    bot: Optional[:class:`User`]
        The bot attached to the application, if any.
    description: Optional[:class:`str`]
        The application description.
    type: Optional[:class:`ApplicationType`]
        The type of application.
    primary_sku_id: Optional[:class:`int`]
        The application's primary SKU ID, if any.
        This is usually the ID of the game SKU if the application is a game.
    """

    __slots__ = (
        '_state',
        'id',
        'name',
        'description',
        '_icon',
        '_cover_image',
        'primary_sku_id',
        'type',
        'bot',
    )

    def __init__(self, *, state: ConnectionState, data: dict):
        self._state: ConnectionState = state
        self._update(data)

    def __str__(self) -> str:
        return self.name

    def _update(self, data: dict) -> None:
        self.id: int = int(data['id'])
        self.name: str = data['name']
        self.description: str = data.get('description') or ''
        self.type: Optional[ApplicationType] = try_enum(ApplicationType, data['type']) if 'type' in data else None

        self._icon: Optional[str] = data.get('icon')
        self._cover_image: Optional[str] = data.get('cover_image')
        self.bot: Optional[User] = self._state.create_user(data['bot']) if data.get('bot') else None
        self.primary_sku_id: Optional[int] = utils._get_as_snowflake(data, 'primary_sku_id')

    def __repr__(self) -> str:
        return f'<InteractionApplication id={self.id} name={self.name!r}>'

    @property
    def icon(self) -> Optional[Asset]:
        """Optional[:class:`Asset`]: Retrieves the application's icon asset, if any."""
        if self._icon is None:
            return None
        return Asset._from_icon(self._state, self.id, self._icon, path='app')

    @property
    def cover_image(self) -> Optional[Asset]:
        """Optional[:class:`Asset`]: Retrieves the cover image on a store embed, if any.

        This is only available if the application is a game.
        """
        if self._cover_image is None:
            return None
        return Asset._from_cover_image(self._state, self.id, self._cover_image)

    @property
    def primary_sku_url(self) -> Optional[str]:
        """:class:`str`: The URL to the primary SKU of the application, if any."""
        if self.primary_sku_id:
            return f'https://discord.com/store/skus/{self.primary_sku_id}/unknown'

    async def assets(self) -> List[ApplicationAsset]:
        """|coro|

        Retrieves the assets of this application.

        Raises
        ------
        HTTPException
            Retrieving the assets failed.

        Returns
        -------
        List[:class:`ApplicationAsset`]
            The application's assets.
        """
        state = self._state
        data = await state.http.get_app_assets(self.id)
        return [ApplicationAsset(state=state, data=d, application=self) for d in data]

    async def published_store_listings(self, *, localize: bool = True) -> List[StoreListing]:
        """|coro|

        Retrieves all published store listings for this application.

        Parameters
        -----------
        localize: :class:`bool`
            Whether to localize the store listings to the current user's locale.
            If ``False`` then all localizations are returned.

        Raises
        -------
        HTTPException
            Retrieving the listings failed.

        Returns
        -------
        List[:class:`StoreListing`]
            The store listings.
        """
        state = self._state
        data = await state.http.get_app_store_listings(self.id, country_code=state.country_code or 'US', localize=localize)
        return [StoreListing(state=state, data=d) for d in data]

    async def primary_store_listing(self, *, localize: bool = True) -> StoreListing:
        """|coro|

        Retrieves the primary store listing of this application.

        This is the public store listing of the primary SKU.

        Parameters
        -----------
        localize: :class:`bool`
            Whether to localize the store listings to the current user's locale.
            If ``False`` then all localizations are returned.

        Raises
        ------
        NotFound
            The application does not have a primary SKU.
        HTTPException
            Retrieving the store listing failed.

        Returns
        -------
        :class:`StoreListing`
            The application's primary store listing, if any.
        """
        state = self._state
        data = await state.http.get_app_store_listing(self.id, country_code=state.country_code or 'US', localize=localize)
        return StoreListing(state=state, data=data)

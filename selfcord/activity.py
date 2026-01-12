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
import re
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Sequence, Tuple, Union, overload

from .asset import Asset, AssetMixin
from .colour import Colour
from .enums import (
    ActivityActionType,
    ActivityPlatform,
    ActivityType,
    ClientType,
    HangStatusType,
    OperatingSystem,
    Status,
    StatusDisplayType,
    try_enum,
)
from .flags import ActivityFlags
from .metadata import Metadata, MetadataObject
from .partial_emoji import PartialEmoji
from .utils import MISSING, _get_as_snowflake, deprecated, parse_time, parse_timestamp, utcnow

__all__ = (
    'BaseActivity',
    'ActivityTimestamps',
    'ActivityAssets',
    'ActivityImage',
    'ActivityParty',
    'ActivityButton',
    'ActivitySecrets',
    'Activity',
    'Streaming',
    'Game',
    'Spotify',
    'CustomActivity',
    'HangActivity',
    'Session',
)


if TYPE_CHECKING:
    from typing_extensions import Self

    from .application import ApplicationAsset
    from .message import Message
    from .state import ConnectionState
    from .types.activity import (
        Activity as ActivityPayload,
        ActivityAssets as ActivityAssetsPayload,
        ActivityEmoji as ActivityEmojiPayload,
        ActivityParty as ActivityPartyPayload,
        ActivitySecrets as ActivitySecretsPayload,
        ActivityTimestamps as ActivityTimestampsPayload,
        HangStatusVariantType,
        SettingsActivity,
    )
    from .types.gateway import Session as SessionPayload


class BaseActivity:
    """The base activity that all activity types inherit from.
    These types can be used in :meth:`Client.change_presence`.

    .. versionadded:: 1.3
    """

    __slots__ = (
        '_state',
        'id',
        'type',
        'name',
        '_created_at',
    )

    def __init__(self, *, name: Optional[str] = None, **kwargs: Any) -> None:
        self._state: Optional[ConnectionState] = None
        self.id: str = kwargs.pop('id', '')
        type = kwargs.pop('type', 0)
        self.type: ActivityType = type if isinstance(type, ActivityType) else try_enum(ActivityType, type)
        self.name: Optional[str] = name
        self._created_at: Optional[float] = kwargs.pop('created_at', None)

    def __hash__(self) -> int:
        return hash((self.id, self.type, self.name))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, BaseActivity):
            return self.to_dict() == other.to_dict() and self.id == other.id
        return NotImplemented

    @property
    def created_at(self) -> datetime.datetime:
        """:class:`datetime.datetime`: When the user started doing this activity in UTC.

        .. versionadded:: 1.3

        .. versionchanged:: 2.1

            This is no longer optional and will always return a :class:`datetime.datetime` object.
        """
        if self._created_at is not None:
            return parse_timestamp(self._created_at)
        return utcnow()

    def copy(self) -> Self:
        """Returns a shallow copy of the activity."""
        return self.__class__.from_dict(self.to_dict(), state=self._state)  # type: ignore

    @classmethod
    def from_dict(cls, data: ActivityPayload) -> Self:
        raise NotImplementedError

    def to_dict(self) -> ActivityPayload:
        raise NotImplementedError


class ActivityTimestamps:
    """Represents the timestamps of an activity.

    .. container:: operations

        .. describe:: x == y

            Checks if the timestamps are equal to other timestamps.

        .. describe:: x != y

            Checks if the timestamps are not equal to other timestamps.

        .. describe:: bool(x)

            Checks if the timestamp has a value.

    .. versionadded:: 2.1

    Parameters
    -----------
    start: Optional[:class:`datetime.datetime`]
        When the user started doing this activity.
    end: Optional[:class:`datetime.datetime`]
        When the user will stop doing this activity.
    """

    __slots__ = ('_start', '_end')

    def __init__(
        self,
        *,
        start: Optional[datetime.datetime] = None,
        end: Optional[datetime.datetime] = None,
    ) -> None:
        self._start: Optional[int] = int(start.timestamp() * 1000) if start else None
        self._end: Optional[int] = int(end.timestamp() * 1000) if end else None

    def __repr__(self) -> str:
        return f'<ActivityTimestamps start={self.start!r} end={self.end!r}>'

    def __bool__(self) -> bool:
        return self._start is not None or self._end is not None

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ActivityTimestamps):
            return other._start == self._start and other._end == self._end
        return NotImplemented

    @classmethod
    def from_dict(cls, data: ActivityTimestampsPayload) -> Self:
        self = cls.__new__(cls)
        self._start = data.get('start')
        self._end = data.get('end')
        return self

    def to_dict(self) -> ActivityTimestampsPayload:
        ret: ActivityTimestampsPayload = {}
        if self._start is not None:
            ret['start'] = self._start
        if self._end is not None:
            ret['end'] = self._end
        return ret

    @property
    def start(self) -> Optional[datetime.datetime]:
        """Optional[:class:`datetime.datetime`]: When the user started doing this activity in UTC, if applicable."""
        return parse_timestamp(self._start)

    @property
    def end(self) -> Optional[datetime.datetime]:
        """Optional[:class:`datetime.datetime`]: When the user will stop doing this activity in UTC, if applicable."""
        return parse_timestamp(self._end)

    @property
    def duration(self) -> Optional[datetime.timedelta]:
        """Optional[:class:`datetime.timedelta`]: The duration of the activity."""
        if self._start is not None:
            return datetime.timedelta(milliseconds=(self._end or utcnow().timestamp() * 1000) - self._start)


class ActivityAssets:
    """Represents the assets of an activity.

    .. container:: operations

        .. describe:: x == y

            Checks if the assets are equal to other assets.

        .. describe:: x != y

            Checks if the assets are not equal to other assets.

        .. describe:: bool(x)

            Checks if the assets have a value.

    .. versionadded:: 2.1

    .. note::

        Discord CDN, media proxy, application, Twitch, YouTube, and Spotify assets
        are able to be used directly in activity assets by providing their URLs or URIs.

        In order to provide an arbitrary image link, you must use :meth:`~selfcord.Client.proxy_external_application_assets`
        or :meth:`~selfcord.Application.proxy_external_assets` to retrieved a proxied URL from Discord.
        Otherwise, the image will not render in clients.

    Attributes
    -----------
    large_text: Optional[:class:`str`]
        The hover text for the large image asset.
    large_url: Optional[:class:`str`]
        A URL that is linked to when clicking on the large image asset.
    small_text: Optional[:class:`str`]
        The hover text for the small image asset.
    small_url: Optional[:class:`str`]
        A URL that is linked to when clicking on the small image asset.

    Parameters
    -----------
    large_image: Optional[Union[:class:`str`, :class:`ApplicationAsset`]]
        The large image asset.
    large_text: Optional[:class:`str`]
        The hover text for the large image asset.
    large_url: Optional[:class:`str`]
        A URL that is linked to when clicking on the large image asset.
    small_image: Optional[Union[:class:`str`, :class:`ApplicationAsset`]]
        The ID for the small image asset.
    small_text: Optional[:class:`str`]
        The hover text for the small image asset.
    small_url: Optional[:class:`str`]
        A URL that is linked to when clicking on the small image asset.
    invite_cover_image: Optional[Union[:class:`str`, :class:`ApplicationAsset`]]
        The invite cover image asset.
    """

    MP_REGEX = re.compile(r'https?://(?:cdn|media|images-ext-\d+)\.discordapp\.(?:com|net)/(.+)')
    TWITCH_REGEX = re.compile(r'https?://static-cdn\.jtvnw\.net/previews-ttv/live_user_(.+?)(?:-(\d+)x(\d+))?\.jpg')
    YOUTUBE_REGEX = re.compile(r'https?://i\.ytimg\.com/vi/(.+?)/(.+?)\.jpg')
    SPOTIFY_REGEX = re.compile(r'https?://i\.scdn\.co/image/(.+)')

    __slots__ = (
        '_state',
        '_application_id',
        '_large_image',
        'large_text',
        'large_url',
        '_small_image',
        'small_text',
        'small_url',
        '_invite_cover_image',
    )

    def __init__(
        self,
        *,
        large_image: Optional[Union[str, ApplicationAsset]] = None,
        large_text: Optional[str] = None,
        large_url: Optional[str] = None,
        small_image: Optional[Union[str, ApplicationAsset]] = None,
        small_text: Optional[str] = None,
        small_url: Optional[str] = None,
        invite_cover_image: Optional[Union[str, ApplicationAsset]] = None,
    ) -> None:
        self._state: Optional[ConnectionState] = None
        self._application_id: Optional[int] = None
        self._large_image = self._parse_asset(large_image)
        self.large_text = large_text
        self.large_url = large_url
        self._small_image = self._parse_asset(small_image)
        self.small_text = small_text
        self.small_url = small_url
        self._invite_cover_image = self._parse_asset(invite_cover_image)

    def __repr__(self) -> str:
        return f'<ActivityAssets large_image={self._large_image!r} small_image={self._small_image!r} invite_cover_image={self._invite_cover_image!r}>'

    def __bool__(self) -> bool:
        return (
            self._large_image is not None
            or self.large_text is not None
            or self.large_url is not None
            or self._small_image is not None
            or self.small_text is not None
            or self.small_url is not None
            or self._invite_cover_image is not None
        )

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ActivityAssets):
            return (
                other._large_image == self._large_image
                and other.large_text == self.large_text
                and other.large_url == self.large_url
                and other._small_image == self._small_image
                and other.small_text == self.small_text
                and other.small_url == self.small_url
                and other._invite_cover_image == self._invite_cover_image
            )
        return NotImplemented

    @classmethod
    def from_dict(
        cls, data: ActivityAssetsPayload, application_id: Optional[int] = None, state: Optional[ConnectionState] = None
    ) -> Self:
        self = cls.__new__(cls)
        self._state = state
        self._application_id = application_id
        self._large_image = data.get('large_image')
        self.large_text = data.get('large_text')
        self.large_url = data.get('large_url')
        self._small_image = data.get('small_image')
        self.small_text = data.get('small_text')
        self.small_url = data.get('small_url')
        self._invite_cover_image = data.get('invite_cover_image')
        return self

    def to_dict(self) -> ActivityAssetsPayload:
        ret: ActivityAssetsPayload = {}
        if self._large_image is not None:
            ret['large_image'] = self._large_image
        if self.large_text is not None:
            ret['large_text'] = self.large_text
        if self.large_url is not None:
            ret['large_url'] = self.large_url
        if self._small_image is not None:
            ret['small_image'] = self._small_image
        if self.small_text is not None:
            ret['small_text'] = self.small_text
        if self.small_url is not None:
            ret['small_url'] = self.small_url
        if self._invite_cover_image is not None:
            ret['invite_cover_image'] = self._invite_cover_image
        return ret

    def _parse_asset(self, asset: Optional[Union[str, ApplicationAsset]]) -> Optional[str]:
        if not asset:
            return None

        if not isinstance(asset, str):
            self._application_id = asset.application.id
            return str(asset.id)

        asset = str(asset)
        match = self.MP_REGEX.match(asset)
        if match:
            return f'mp:{match[1]}'
        match = self.TWITCH_REGEX.match(asset)
        if match:
            return f'twitch:{match[1]}'
        match = self.YOUTUBE_REGEX.match(asset)
        if match:
            return f'youtube:{match[1]}'
        match = self.SPOTIFY_REGEX.match(asset)
        if match:
            return f'spotify:{match[1]}'
        return asset

    @property
    def large_image(self) -> Optional[ActivityImage]:
        """Optional[:class:`ActivityImage`]: The large image asset of the activity."""
        if self._large_image is None:
            return None
        return ActivityImage(asset=self._large_image, assets=self)

    @property
    def small_image(self) -> Optional[ActivityImage]:
        """Optional[:class:`ActivityImage`]: The small image asset of the activity."""
        if self._small_image is None:
            return None
        return ActivityImage(asset=self._small_image, assets=self)

    @property
    def invite_cover_image(self) -> Optional[ActivityImage]:
        """Optional[:class:`ActivityImage`]: The invite cover image asset of the activity."""
        if self._invite_cover_image is None:
            return None
        return ActivityImage(asset=self._invite_cover_image, assets=self)


class ActivityImage(AssetMixin):
    """Represents an activity image asset.

    .. container:: operations

        .. describe:: x == y

            Checks if the asset is equal to another asset.

        .. describe:: x != y

            Checks if the asset is not equal to another asset.

        .. describe:: hash(x)

            Returns the hash of the asset.

        .. describe:: str(x)

            Returns the URL of the asset.

    .. versionadded:: 2.1

    Attributes
    -----------
    asset: :class:`str`
        The asset of the image.
    """

    __slots__ = ('asset', '_assets')

    def __init__(self, *, asset: str, assets: ActivityAssets) -> None:
        self.asset = asset
        self._assets = assets

    def __repr__(self) -> str:
        return f'<ActivityImage asset={self.asset!r}>'

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ActivityImage):
            return other.asset == self.asset
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.asset)

    def __str__(self) -> str:
        return self.url

    @property
    def _state(self) -> Optional[ConnectionState]:
        return self._assets._state

    @property
    def prefix(self) -> Literal['application', 'mp', 'twitch', 'youtube', 'spotify']:
        """:class:`str`: The asset prefix."""
        asset = self.asset
        if asset.isdigit():
            return 'application'
        prefix, _, _ = self.asset.partition(':')
        return prefix  # type: ignore

    @property
    def animated(self) -> bool:
        """:class:`bool`: Indicates if the asset is animated. Here for compatibility purposes."""
        return False

    @property
    def url(self) -> str:
        """:class:`str`: Returns the URL of the asset."""
        prefix = self.prefix
        if prefix == 'mp':
            return f'https://media.discordapp.net/{self.asset[3:]}'
        elif prefix == 'twitch':
            username = self.asset[8:]
            return f'https://static-cdn.jtvnw.net/previews-ttv/live_user_{username}.jpg'
        elif prefix == 'youtube':
            video_id = self.asset[8:]
            return f'https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg'
        elif prefix == 'spotify':
            spotify_id = self.asset[8:]
            return f'https://i.scdn.co/image/{spotify_id}'
        elif self.asset.isdigit() and self._assets._application_id is not None:
            return Asset.BASE + f'/app-assets/{self._assets._application_id}/{self.asset}.png'
        return self.asset


class ActivityParty:
    """Represents the party of an activity.

    .. container:: operations

        .. describe:: x == y

            Checks if the party is equal to another party.

        .. describe:: x != y

            Checks if the party is not equal to another party.

        .. describe:: bool(x)

            Checks if the party has a value.

    .. versionadded:: 2.1

    Attributes
    -----------
    id: Optional[:class:`str`]
        The party ID.

    Parameters
    -----------
    id: Optional[:class:`str`]
        The party ID.
    current_size: Optional[:class:`int`]
        The current size of the party. Required if ``max_size`` is provided.
    max_size: Optional[:class:`int`]
        The maximum size of the party. Required if ``current_size`` is provided.
    """

    __slots__ = ('id', '_size')

    def __init__(
        self,
        *,
        id: Optional[str] = None,
        current_size: Optional[int] = None,
        max_size: Optional[int] = None,
    ) -> None:
        self.id: Optional[str] = id

        if current_size is not None and max_size is not None:
            self._size: Optional[Tuple[int, int]] = (current_size, max_size)
        elif current_size is not None or max_size is not None:
            raise TypeError('current_size and max_size must be provided together')
        else:
            self._size = None

    def __repr__(self) -> str:
        return f'<ActivityParty id={self.id!r} size={self._size!r}>'

    def __bool__(self) -> bool:
        return self.id is not None or self._size is not None

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ActivityParty):
            return other.id == self.id and other._size == self._size
        return NotImplemented

    @classmethod
    def from_dict(cls, data: ActivityPartyPayload) -> Self:
        self = cls.__new__(cls)
        self.id = data.get('id')
        self._size = tuple(data['size']) if data.get('size') else None  # type: ignore
        return self

    def to_dict(self) -> ActivityPartyPayload:
        ret: ActivityPartyPayload = {}
        if self.id is not None:
            ret['id'] = self.id
        if self._size is not None:
            ret['size'] = list(self._size)
        return ret

    @property
    def current_size(self) -> Optional[int]:
        """Optional[:class:`int`]: The current size of the party."""
        if self._size is not None:
            return self._size[0]

    @property
    def max_size(self) -> Optional[int]:
        """Optional[:class:`int`]: The maximum size of the party."""
        if self._size is not None:
            return self._size[1]

    @property
    def owner_id(self) -> Optional[int]:
        """Optional[:class:`int`]: The party owner's user ID. Only applicable to Spotify activities."""
        if self.id and self.id.startswith('spotify:'):
            try:
                return int(self.id[8:])
            except ValueError:
                return


class ActivityButton:
    """A helper class that abstracts button creation in an activity.

    .. container:: operations

        .. describe:: x == y

            Checks if the button is equal to another button.

        .. describe:: x != y

            Checks if the button is not equal to another button.

    .. versionadded:: 2.1

    Attributes
    -----------
    label: :class:`str`
        The label of the button.
    url: Optional[:class:`str`]
        The URL of the button.

    Parameters
    -----------
    label: :class:`str`
        The label of the button.
    url: Optional[:class:`str`]
        The URL of the button.
    """

    __slots__ = ('label', 'url')

    def __init__(self, label: str, url: Optional[str] = None) -> None:
        self.label: str = label
        self.url: Optional[str] = url

    def __repr__(self) -> str:
        return f'<ActivityButton label={self.label!r} url={self.url!r}>'

    def __str__(self) -> str:
        return self.label

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ActivityButton):
            return other.label == self.label and other.url == self.url
        return NotImplemented


class ActivitySecrets:
    """Represents the secrets of an activity.

    .. container:: operations

        .. describe:: x == y

            Checks if the secrets are equal to other secrets.

        .. describe:: x != y

            Checks if the secrets are not equal to other secrets.

        .. describe:: bool(x)

            Checks if the secrets have a value.

    .. versionadded:: 2.1

    Attributes
    -----------
    join: Optional[:class:`str`]
        The secret for joining a party.
    spectate: Optional[:class:`str`]
        The secret for spectating a party.

    Parameters
    -----------
    join: Optional[:class:`str`]
        The secret for joining a party.
    spectate: Optional[:class:`str`]
        The secret for spectating a party.
    """

    __slots__ = ('join', 'spectate')

    def __init__(
        self,
        *,
        join: Optional[str] = None,
        spectate: Optional[str] = None,
    ) -> None:
        self.join: Optional[str] = join
        self.spectate: Optional[str] = spectate

    def __repr__(self) -> str:
        return f'<ActivitySecrets join={self.join!r} spectate={self.spectate!r}>'

    def __bool__(self) -> bool:
        return self.join is not None or self.spectate is not None

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ActivitySecrets):
            return other.join == self.join and other.spectate == self.spectate
        return NotImplemented

    @classmethod
    def from_dict(cls, data: ActivitySecretsPayload) -> Self:
        self = cls.__new__(cls)
        self.join = data.get('join')
        self.spectate = data.get('spectate')
        return self

    def to_dict(self) -> ActivitySecretsPayload:
        ret: ActivitySecretsPayload = {}
        if self.join is not None:
            ret['join'] = self.join
        if self.spectate is not None:
            ret['spectate'] = self.spectate
        return ret


class Activity(BaseActivity):
    """Represents an activity in Discord.

    This could be an activity such as streaming, playing, listening
    or watching.

    For memory optimisation purposes, some activities are offered in slimmed
    down versions:

    - :class:`CustomActivity`

    Similarly, some activities are offered in more feature-rich versions:

    - :class:`Spotify`

    .. container:: operations

        .. describe:: x == y

            Checks if the activity is equal to another activity.

        .. describe:: x != y

            Checks if the activity is not equal to another activity.

        .. describe:: hash(x)

            Returns the hash of the activity.

        .. describe:: str(x)

            Returns the string representation of the activity.

    Attributes
    ------------
    id: :class:`str`
        The ID of the activity. If this was manually created then the ID will be empty.

        .. versionadded:: 2.1
    type: :class:`ActivityType`
        The type of activity currently being done.
    session_id: Optional[:class:`str`]
        The ID of the session this activity belongs to.
    application_id: Optional[:class:`int`]
        The application ID of the game.
    name: :class:`str`
        The name of the activity.
    url: Optional[:class:`str`]
        A stream URL that the activity could be doing.
    state: Optional[:class:`str`]
        The user's current state. For example, "In Game".
    state_url: Optional[:class:`str`]
        A URL that is linked to when clicking on the state text of the activity.

        .. versionadded:: 2.1
    details: Optional[:class:`str`]
        The detail of the user's current activity.
    details_url: Optional[:class:`str`]
        A URL that is linked to when clicking on the details text of the activity.

        .. versionadded:: 2.1
    sync_id: Optional[:class:`str`]
        The ID used to synchronize the activity.
    status_display_type: Optional[:class:`StatusDisplayType`]
        Determines which field from the user's status text is displayed
        in the members list.

        .. versionadded:: 2.1
    platform: Optional[:class:`ActivityPlatform`]
        The user's current platform.

        .. versionadded:: 2.1
    supported_platforms: List[:class:`ActivityPlatform`]
        A list of platforms that the activity supports.
    emoji: Optional[:class:`PartialEmoji`]
        The emoji that belongs to this activity.
    timestamps: :class:`ActivityTimestamps`
        The timestamps that denote when the activity started and ended.

        .. versionchanged:: 2.1

            Type is now :class:`ActivityTimestamps` instead of :class:`dict`.
    assets: :class:`ActivityAssets`
        The assets for the rich presence.

        .. versionchanged:: 2.1

            Type is now :class:`ActivityAssets` instead of :class:`dict`.
    party: :class:`ActivityParty`
        The party information for the rich presence.

        .. versionchanged:: 2.1

            Type is now :class:`ActivityParty` instead of :class:`dict`.
    buttons: List[:class:`str`]
        A list of strings representing the labels of custom buttons shown in a rich presence.

        .. versionadded:: 2.0
    secrets: Optional[:class:`ActivitySecrets`]
        The secrets for the rich presence.
        This will only be available on manually created activities.
        For received activities, see :meth:`fetch_secret`.

        .. versionadded:: 2.1
    metadata: Optional[:class:`Metadata`]
        Extra metadata for the activity.
        This will only be available on manually created activities.
        For received activities, see :meth:`fetch_metadata`.

        .. versionadded:: 2.1

    Parameters
    -----------
    type: :class:`ActivityType`
        The type of activity currently being done.
    flags: Optional[:class:`ActivityFlags`]
        The activity flags.
    application_id: Optional[:class:`int`]
        The application ID of the game.
    name: :class:`str`
        The name of the activity.
    url: Optional[:class:`str`]
        A stream URL that the activity could be doing.
    state: Optional[:class:`str`]
        The user's current state. For example, "In Game".
    state_url: Optional[:class:`str`]
        A URL that is linked to when clicking on the state text of the activity.
    details: Optional[:class:`str`]
        The detail of the user's current activity.
    details_url: Optional[:class:`str`]
        A URL that is linked to when clicking on the details text of the activity.
    sync_id: Optional[:class:`str`]
        The ID used to synchronize the activity.
    status_display_type: Optional[:class:`StatusDisplayType`]
        Determines which field from the user's status text is displayed
        in the members list.
    platform: Optional[:class:`ActivityPlatform`]
        The user's current platform.
    supported_platforms: Optional[List[:class:`ActivityPlatform`]]
        A list of platforms that the activity supports.
    emoji: Optional[Union[:class:`PartialEmoji`, :class:`str`]]
        The emoji that belongs to this activity.
    timestamps: Optional[:class:`ActivityTimestamps`]
        The timestamps that denote when the activity started and ended.
    assets: Optional[:class:`ActivityAssets`]
        The assets for the rich presence.
    party: Optional[:class:`ActivityParty`]
        The party information for the rich presence.
    buttons: Optional[List[Union[:class:`ActivityButton`, :class:`str`]]]
        A list of strings representing the labels of custom buttons shown in a rich presence.

        .. note::

            If you would like to specify URLs for buttons, you may use the :class:`ActivityButton`
            helper class, which will insert the ``button_urls`` field into the :attr:`metadata` attribute
            for you. Note that this cannot be used in combination with ``button_urls`` in the ``metadata`` parameter.
    secrets: Optional[:class:`ActivitySecrets`]
        The secrets for the rich presence.
    metadata: Optional[Mapping[:class:`str`, Any]]
        Extra metadata for the activity.
    """

    __slots__ = (
        '_state',
        '_user_id',
        'state',
        'details',
        'timestamps',
        'platform',
        'supported_platforms',
        'assets',
        'party',
        '_flags',
        'sync_id',
        'session_id',
        'type',
        'name',
        'url',
        'application_id',
        'emoji',
        'buttons',
        'secrets',
        'metadata',
        'state_url',
        'details_url',
        'status_display_type',
    )

    def __init__(
        self,
        *,
        type: ActivityType = ActivityType.playing,
        flags: Optional[ActivityFlags] = None,
        application_id: Optional[int] = None,
        name: str,
        url: Optional[str] = None,
        state: Optional[str] = None,
        state_url: Optional[str] = None,
        details: Optional[str] = None,
        details_url: Optional[str] = None,
        sync_id: Optional[str] = None,
        status_display_type: Optional[StatusDisplayType] = None,
        platform: Optional[ActivityPlatform] = None,
        supported_platforms: Optional[List[ActivityPlatform]] = None,
        emoji: Optional[Union[PartialEmoji, Dict[str, Any], str]] = None,
        timestamps: Optional[Union[ActivityTimestamps, ActivityTimestampsPayload]] = None,
        assets: Optional[Union[ActivityAssets, ActivityAssetsPayload]] = None,
        party: Optional[Union[ActivityParty, ActivityPartyPayload]] = None,
        buttons: Optional[List[Union[ActivityButton, str]]] = None,
        secrets: Optional[Union[ActivitySecrets, ActivitySecretsPayload]] = None,
        metadata: Optional[MetadataObject] = None,
    ) -> None:
        super().__init__(name=name, type=type)
        self.name: str = name
        self._state: Optional[ConnectionState] = None
        self._user_id: Optional[int] = None
        self._flags: int = flags.value if flags is not None else 0
        self.application_id: Optional[int] = application_id
        self.url = url
        self.state: Optional[str] = state
        self.state_url = state_url
        self.details: Optional[str] = details
        self.details_url = details_url
        self.sync_id: Optional[str] = sync_id
        self.session_id: Optional[str] = None
        self.status_display_type: Optional[StatusDisplayType] = status_display_type
        self.platform: Optional[ActivityPlatform] = (
            platform
            if isinstance(platform, ActivityPlatform)
            else try_enum(ActivityPlatform, platform)
            if platform is not None
            else None
        )
        self.supported_platforms: List[ActivityPlatform] = supported_platforms or []

        self.emoji: Optional[PartialEmoji]
        if isinstance(emoji, dict):
            self.emoji = PartialEmoji.from_dict(emoji)
        elif isinstance(emoji, str):
            self.emoji = PartialEmoji(name=emoji)
        elif isinstance(emoji, PartialEmoji) or emoji is None:
            self.emoji = emoji
        else:
            raise TypeError(f'Expected str, PartialEmoji, or None, received {type(emoji)!r} instead')

        self.timestamps: ActivityTimestamps = (
            timestamps
            if isinstance(timestamps, ActivityTimestamps)
            else ActivityTimestamps.from_dict(timestamps)
            if timestamps is not None
            else ActivityTimestamps()
        )
        self.assets: ActivityAssets = (
            assets
            if isinstance(assets, ActivityAssets)
            else ActivityAssets.from_dict(assets)
            if assets is not None
            else ActivityAssets()
        )
        self.assets._application_id = application_id
        self.party: ActivityParty = (
            party
            if isinstance(party, ActivityParty)
            else ActivityParty.from_dict(party)
            if party is not None
            else ActivityParty()
        )
        self.secrets: Optional[ActivitySecrets] = (
            secrets
            if isinstance(secrets, ActivitySecrets)
            else ActivitySecrets.from_dict(secrets)
            if secrets is not None
            else None
        )

        self.buttons: List[str] = [str(button) for button in buttons] if buttons else []
        self.metadata: Optional[Metadata] = Metadata(metadata) if metadata is not None else None
        if buttons and any(isinstance(button, ActivityButton) for button in buttons):
            if self.metadata is None:
                self.metadata = Metadata()
            if self.metadata.button_urls:
                raise ValueError('Cannot mix ActivityButton instances with button_urls in metadata')
            self.metadata.button_urls = [getattr(button, 'url', None) or '' for button in buttons]

    @classmethod
    def from_dict(cls, data: ActivityPayload, *, state: ConnectionState, user_id: Optional[int] = None) -> Self:
        self = cls.__new__(cls)
        self._state = state
        self._user_id = user_id
        self.id = data.get('id', '')
        self.type = try_enum(ActivityType, data.get('type', 0))
        self.name = data['name']
        self._created_at = data.get('created_at')
        self._flags = data.get('flags', 0)
        self.application_id = _get_as_snowflake(data, 'application_id')
        self.url = data.get('url')
        self.state = data.get('state')
        self.state_url = data.get('state_url')
        self.details = data.get('details')
        self.details_url = data.get('details_url')
        self.sync_id = data.get('sync_id')
        self.session_id = data.get('session_id')
        self.status_display_type = (
            try_enum(StatusDisplayType, data['status_display_type']) if data.get('status_display_type') is not None else None  # type: ignore
        )
        self.platform = try_enum(ActivityPlatform, data['platform']) if data.get('platform') else None  # type: ignore
        self.supported_platforms = (
            [try_enum(ActivityPlatform, p) for p in data['supported_platforms']] if data.get('supported_platforms') else []  # type: ignore
        )

        emoji_data = data.get('emoji')
        if emoji_data is not None:
            self.emoji = PartialEmoji.from_dict_stateful(emoji_data, state)
        else:
            self.emoji = None

        timestamps_data = data.get('timestamps')
        if timestamps_data:
            self.timestamps = ActivityTimestamps.from_dict(timestamps_data)
        else:
            self.timestamps = ActivityTimestamps()

        assets_data = data.get('assets')
        if assets_data:
            self.assets = ActivityAssets.from_dict(assets_data, application_id=self.application_id, state=state)
        else:
            self.assets = ActivityAssets()

        party_data = data.get('party')
        if party_data:
            self.party = ActivityParty.from_dict(party_data)
        else:
            self.party = ActivityParty()

        secrets_data = data.get('secrets')
        if secrets_data:
            self.secrets = ActivitySecrets.from_dict(secrets_data)
        else:
            self.secrets = None

        metadata_data = data.get('metadata')
        if metadata_data:
            self.metadata = Metadata(metadata_data)
        else:
            self.metadata = None

        self.buttons = data.get('buttons') or []
        return self

    def __repr__(self) -> str:
        attrs = (
            ('type', self.type),
            ('name', self.name),
            ('url', self.url),
            ('state', self.state),
            ('details', self.details),
            ('application_id', self.application_id),
            ('emoji', self.emoji),
        )
        inner = ' '.join('%s=%r' % t for t in attrs if t[1] is not None)
        return f'<Activity {inner}>'

    def __str__(self) -> str:
        # TODO: Maybe avoid the duplication here
        if self.type == ActivityType.custom:
            if self.emoji:
                if self.state:
                    return f'{self.emoji} {self.state}'
                return str(self.emoji)
            else:
                return self.state or ''
        elif self.type == ActivityType.hang:
            status_type = try_enum(HangStatusType, self.state.split(':', 1)[0]) if self.state else HangStatusType.custom
            if status_type == HangStatusType.custom and self.emoji:
                if self.details:
                    return f'{self.emoji} {self.details}'
                return str(self.emoji)
            else:
                return status_type.text or ''

        prefix = ''
        if self.type == ActivityType.playing:
            prefix = 'Playing '
        elif self.type == ActivityType.streaming:
            prefix = 'Streaming '
        elif self.type == ActivityType.listening:
            prefix = 'Listening to '
        elif self.type == ActivityType.watching:
            prefix = 'Watching '
        elif self.type == ActivityType.competing:
            prefix = 'Competing in '

        if self.status_display_type == StatusDisplayType.name:
            return f'{prefix}{self.name}'
        elif self.status_display_type == StatusDisplayType.details:
            return f'{prefix}{self.details or self.name}'
        elif self.status_display_type == StatusDisplayType.state:
            return f'{prefix}{self.state or self.name}'
        else:
            # Defaults differ per type
            if self.type == ActivityType.streaming:
                return f'{prefix}{self.details}'
            return f'{prefix}{self.name}'

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Activity):
            return self.to_dict() == other.to_dict()
        return NotImplemented

    def to_dict(self) -> ActivityPayload:
        ret: ActivityPayload = {
            'type': self.type.value,
            'name': self.name,
        }
        if self.id:
            ret['id'] = self.id
        if self._flags:
            ret['flags'] = self._flags
        if self.application_id:
            ret['application_id'] = self.application_id
        if self.url:
            ret['url'] = self.url
        if self.state:
            ret['state'] = self.state
        if self.state_url:
            ret['state_url'] = self.state_url
        if self.details:
            ret['details'] = self.details
        if self.details_url:
            ret['details_url'] = self.details_url
        if self.sync_id:
            ret['sync_id'] = self.sync_id
        if self.status_display_type:
            ret['status_display_type'] = self.status_display_type.value
        if self.platform:
            ret['platform'] = self.platform.value
        if self.supported_platforms:
            ret['supported_platforms'] = [platform.value for platform in self.supported_platforms]
        if self.emoji:
            ret['emoji'] = self.emoji.to_dict()
        if self.timestamps:
            ret['timestamps'] = self.timestamps.to_dict()
        if self.assets:
            ret['assets'] = self.assets.to_dict()
        if self.party:
            ret['party'] = self.party.to_dict()
        if self.buttons:
            ret['buttons'] = self.buttons
        if self.secrets:
            ret['secrets'] = self.secrets.to_dict()
        if self.metadata:
            ret['metadata'] = dict(self.metadata)
        return ret

    @property
    def flags(self) -> ActivityFlags:
        """:class:`ActivityFlags`: Returns this activity's flags.

        .. versionadded:: 2.1
        """
        return ActivityFlags._from_value(self._flags)

    @property
    @deprecated('Activity.timestamps.start')
    def start(self) -> Optional[datetime.datetime]:
        """Optional[:class:`datetime.datetime`]: When the user started doing this activity in UTC, if applicable.

        .. deprecated:: 2.1

            Use :attr:`~selfcord.ActivityTimestamps.start` instead.
        """
        return self.timestamps.start

    @property
    @deprecated('Activity.timestamps.end')
    def end(self) -> Optional[datetime.datetime]:
        """Optional[:class:`datetime.datetime`]: When the user will stop doing this activity in UTC, if applicable.

        .. deprecated:: 2.1

            Use :attr:`~selfcord.ActivityTimestamps.end` instead.
        """
        return self.timestamps.end

    @property
    @deprecated('Activity.assets.large_image.url')
    def large_image_url(self) -> Optional[str]:
        """Optional[:class:`str`]: Returns a URL pointing to the large image asset of this activity, if applicable.

        .. deprecated:: 2.1

            Use :attr:`~selfcord.ActivityAssets.large_image` instead.
        """
        return self.assets.large_image.url if self.assets.large_image else None

    @property
    @deprecated('Activity.assets.small_image.url')
    def small_image_url(self) -> Optional[str]:
        """Optional[:class:`str`]: Returns a URL pointing to the small image asset of this activity, if applicable.

        .. deprecated:: 2.1

            Use :attr:`~selfcord.ActivityAssets.small_image` instead.
        """
        return self.assets.small_image.url if self.assets.small_image else None

    @property
    @deprecated('Activity.assets.large_text')
    def large_image_text(self) -> Optional[str]:
        """Optional[:class:`str`]: Returns the large image asset hover text of this activity, if applicable.

        .. deprecated:: 2.1

            Use :attr:`~selfcord.ActivityAssets.large_text` instead.
        """

        return self.assets.large_text

    @property
    @deprecated('Activity.assets.small_text')
    def small_image_text(self) -> Optional[str]:
        """Optional[:class:`str`]: Returns the small image asset hover text of this activity, if applicable.

        .. deprecated:: 2.1

            Use :attr:`~selfcord.ActivityAssets.small_text` instead.
        """
        return self.assets.small_text

    async def fetch_metadata(self) -> Metadata:
        """|coro|

        Fetches the full metadata for this activity.

        Activities must have an :attr:`application_id` to fetch metadata,
        unless they are of type :attr:`ActivityType.listening` and the user only
        has a single activity of that type.

        Raises
        ------
        NotFound
            The rich presence was not found.
        HTTPException
            Fetching the metadata failed.
        ValueError
            The activity does not have a :attr:`session_id`.
            The non-listening activity does not have an :attr:`application_id`.
        TypeError
            The emoji does not have state available.

        Returns
        -------
        :class:`Metadata`
            The full metadata for this activity.
        """
        if self._state is None or self._user_id is None:
            raise TypeError('Activity does not have state available')
        if self.session_id is None:
            raise ValueError('Activity must have a session_id to fetch metadata')
        if self.type != ActivityType.listening and self.application_id is None:
            raise ValueError('Activity must have an application_id to fetch metadata')

        metadata_data = await self._state.http.get_activity_metadata(
            user_id=self._user_id,
            session_id=self.session_id,
            application_id=self.application_id or 0,
        )
        self.metadata = Metadata(metadata_data or {})
        return self.metadata

    async def fetch_secret(
        self, action_type: ActivityActionType = ActivityActionType.join, message: Optional[Message] = None
    ) -> str:
        """|coro|

        Fetches the secret for this activity.

        Activities must have an :attr:`application_id` to fetch secrets.

        Parameters
        -----------
        action_type: :class:`ActivityActionType`
            The type of secret to fetch. Only :attr:`ActivityActionType.join` and
            :attr:`ActivityActionType.spectate` are valid.
        message: Optional[:class:`selfcord.Message`]
            The message that contains the rich presence invite. Required if you do
            not meet public party requirements.

        Raises
        ------
        NotFound
            The rich presence was not found.
        HTTPException
            Fetching the secret failed.
        ValueError
            The activity does not have a :attr:`session_id`.
            The activity does not have an :attr:`application_id`.
            The ``action_type`` is invalid.
        TypeError
            The activity does not have state available.

        Returns
        -------
        :class:`str`
            The secret for the specified action type.
        """
        if action_type not in (ActivityActionType.join, ActivityActionType.spectate):
            raise ValueError('Invalid action_type specified')
        if self._state is None or self._user_id is None:
            raise TypeError('Activity does not have state available')
        if self.session_id is None:
            raise ValueError('Activity must have a session_id to fetch secrets')
        if self.application_id is None:
            raise ValueError('Activity must have an application_id to fetch secrets')

        secret_data = await self._state.http.get_activity_secret(
            user_id=self._user_id,
            session_id=self.session_id,
            application_id=self.application_id or 0,
            action_type=action_type.value,
            channel_id=message.channel.id if message else None,
            message_id=message.id if message else None,
        )
        return secret_data.get('secret') or ''


class _ActivityInstanceProxy(type):
    @deprecated('Activity.type')
    def __instancecheck__(cls, instance: object) -> bool:
        return isinstance(instance, BaseActivity) and instance.type == getattr(cls, '__type__', None)


class Game(Activity, metaclass=_ActivityInstanceProxy):
    """A slimmed down version of :class:`Activity` that represents a Discord game.

    This is typically displayed via **Playing** on the official Discord client.

    .. deprecated:: 2.1

        This is now the same as :class:`Activity` and will be removed in a future version.
        It is only kept for backwards compatibility.

        Use :class:`Activity` with :attr:`ActivityType.playing` instead.
    """

    __type__ = ActivityType.playing
    __slots__ = ()

    @deprecated('Activity')
    def __init__(self, *, name: str, **kwargs: Any) -> None:
        super().__init__(name=name, type=ActivityType.playing, **kwargs)


class Streaming(Activity, metaclass=_ActivityInstanceProxy):
    """A slimmed down version of :class:`Activity` that represents a Discord streaming status.

    This is typically displayed via **Streaming** on the official Discord client.

    .. deprecated:: 2.1

        This is now the same as :class:`Activity` and will be removed in a future version.
        It is only kept for backwards compatibility.

        Use :class:`Activity` with :attr:`ActivityType.streaming` instead.
    """

    __type__ = ActivityType.streaming
    __slots__ = ()

    @deprecated('Activity.__init__')
    def __init__(self, *, name: str, url: str, **kwargs: Any) -> None:
        super().__init__(name=name, type=ActivityType.streaming, url=url, **kwargs)

    @property
    @deprecated('Activity.state')
    def game(self) -> Optional[str]:
        """Optional[:class:`str`]: The game being streamed."""
        return self.state

    @property
    @deprecated('Activity.assets.large_image')
    def twitch_name(self) -> Optional[str]:
        """Optional[:class:`str`]: If provided, the twitch name of the user streaming.

        This corresponds to the ``large_image`` key of the :attr:`Streaming.assets`
        dictionary if it starts with ``twitch:``. Typically set by the Discord client.
        """
        if self.assets.large_image and self.assets.large_image.prefix == 'twitch':
            return self.assets.large_image.asset[7:]


class Spotify(Activity):
    """Represents a Spotify listening activity from Discord. This is a special case of
    :class:`Activity` that makes it easier to work with the Spotify integration.

    .. container:: operations

        .. describe:: x == y

            Checks if two activities are equal.

        .. describe:: x != y

            Checks if two activities are not equal.

        .. describe:: hash(x)

            Returns the activity's hash.

        .. describe:: str(x)

            Returns the string representation of the activity.

    .. versionchanged:: 2.1

        Made the class user-constructible to provide a friendly interface
        for creating Spotify activities.

    Parameters
    -----------
    title: :class:`str`
        The title of the song being played.
    track_id: Optional[:class:`str`]
        The track ID used by Spotify to identify this song, if not a local file.

        .. note::

            This is required to enable the "Listen Along" feature on Discord.
    track_type: Optional[:class:`str`]
        The type of the track being played (e.g. "track", "episode"), if not a local file.
    artists: List[:class:`str`]
        The artists of the song being played. Truncated to the first 5 elements.
    artist_ids: Optional[List[:class:`str`]]
        The artist IDs used by Spotify to identify the artists of this song, if not a local file.
        Truncated to the first 5 elements.
    album: Optional[:class:`str`]
        The album that the song being played belongs to, if not a single.
    album_id: Optional[:class:`str`]
        The album ID used by Spotify to identify the album of this song, if not a single or local file.
    album_cover_url: Optional[:class:`str`]
        The album cover image URL from Spotify's CDN, if not a local file or single.
    start_time: :class:`datetime.datetime`
        When the user started playing this song in UTC. Defaults to now.
    duration: :class:`datetime.timedelta`
        The duration of the song being played.
    party_owner_id: :class:`int`
        The user ID of the party owner. This is used to identify the listening party.
        Typically the user themselves unless they are listening along with someone else.
    context_uri: Optional[:class:`str`]
        The Spotify URI of the current player context (e.g. playlist), if applicable.
    """

    __slots__ = ()

    def __init__(
        self,
        *,
        title: str,
        track_id: Optional[str] = None,
        track_type: Optional[str] = None,
        artists: Sequence[str],
        artist_ids: Optional[Sequence[str]] = None,
        album: Optional[str] = None,
        album_id: Optional[str] = None,
        album_cover_url: Optional[str] = None,
        start_time: datetime.datetime = MISSING,
        duration: datetime.timedelta,
        party_owner_id: int,
        context_uri: Optional[str] = None,
    ):
        assets = ActivityAssets(
            large_image=album_cover_url,
            large_text=album,
        )

        start_time = start_time or utcnow()
        timestamps = ActivityTimestamps(
            start=start_time,
            end=start_time + duration,
        )

        party = ActivityParty(
            id=f'spotify:{party_owner_id}',
        )

        metadata = Metadata()
        if context_uri:
            metadata.context_uri = context_uri
        if album_id:
            metadata.album_id = album_id
        if artist_ids:
            metadata.artist_ids = list(artist_ids)[:5]
        if track_type:
            metadata.type = track_type

        flags = ActivityFlags()
        if track_id is not None:
            flags.play = flags.sync = True

        super().__init__(
            type=ActivityType.listening,
            name='Spotify',
            details=title,
            state='; '.join([artist.replace(';', '') for artist in artists[:5]]),
            sync_id=track_id,
            timestamps=timestamps,
            assets=assets,
            party=party,
            metadata=metadata,
            flags=flags,
        )

    @property
    def colour(self) -> Colour:
        """:class:`Colour`: Returns the Spotify integration colour, as a :class:`Colour`.

        There is an alias for this named :attr:`color`"""
        return Colour(0x1DB954)

    @property
    def color(self) -> Colour:
        """:class:`Colour`: Returns the Spotify integration colour, as a :class:`Colour`.

        There is an alias for this named :attr:`colour`"""
        return self.colour

    def __repr__(self) -> str:
        return f'<Spotify title={self.title!r} artist={self.artist!r} track_id={self.track_id!r}>'

    @property
    def title(self) -> str:
        """:class:`str`: The title of the song being played."""
        return self.details or ''

    @property
    def artists(self) -> List[str]:
        """List[:class:`str`]: The artists of the song being played."""
        return self.state.split('; ') if self.state else []

    @property
    def artist(self) -> str:
        """:class:`str`: The artist of the song being played.

        This does not attempt to split the artist information into
        multiple artists. Useful if there's only a single artist.
        """
        return self.state or ''

    @property
    def album(self) -> str:
        """:class:`str`: The album that the song being played belongs to."""
        return self.assets.large_text or self.title

    @property
    def album_cover_url(self) -> Optional[str]:
        """Optional[:class:`str`]: The album cover image URL from Spotify's CDN.

        .. versionchanged:: 2.1

            This property is now optional, as local files and singles may not have an album cover.
        """
        return self.assets.large_image.url if self.assets.large_image else ''

    @property
    def track_id(self) -> Optional[str]:
        """Optional[:class:`str`]: The track ID used by Spotify to identify this song.

        .. versionchanged:: 2.1

            This property is now optional, as local files do not have a track ID.
        """
        return self.sync_id

    @property
    def track_url(self) -> str:
        """:class:`str`: The track URL to listen on Spotify.

        .. versionadded:: 2.0
        """
        return f'https://open.spotify.com/track/{self.track_id}'

    @property
    def start(self) -> datetime.datetime:
        """:class:`datetime.datetime`: When the user started playing this song in UTC."""
        # The start key will be present here
        return self.timestamps.start or utcnow()

    @property
    def end(self) -> datetime.datetime:
        """:class:`datetime.datetime`: When the user will stop playing this song in UTC."""
        # The end key will be present here
        return self.timestamps.end or utcnow()

    @property
    def duration(self) -> datetime.timedelta:
        """:class:`datetime.timedelta`: The duration of the song being played."""
        return self.end - self.start

    @property
    @deprecated('Activity.party.id')
    def party_id(self) -> str:
        """:class:`str`: The party ID of the listening party.

        .. deprecated:: 2.1

            Use :attr:`~selfcord.ActivityParty.id` instead.
        """
        return self.party.id or ''


class CustomActivity(BaseActivity):
    """Represents a custom status activity from Discord.

    .. container:: operations

        .. describe:: x == y

            Checks if two activities are equal.

        .. describe:: x != y

            Checks if two activities are not equal.

        .. describe:: hash(x)

            Returns the activity's hash.

        .. describe:: str(x)

            Returns the custom status text.

    .. versionadded:: 1.3

    Attributes
    -----------
    id: :class:`str`
        The ID of the activity. If this was manually created then the ID will be empty.

        .. versionadded:: 2.1
    type: :class:`ActivityType`
        The type of activity currently being done. For this class, it is always :attr:`ActivityType.custom`.
    name: Optional[:class:`str`]
        The custom activity's text.
    emoji: Optional[:class:`PartialEmoji`]
        The emoji to pass to the activity, if any.
    expires_at: Optional[:class:`datetime.datetime`]
        When the custom activity will expire. This is only available from :attr:`UserSettings.custom_activity`.

        .. versionadded:: 2.0

    Parameters
    -----------
    name: Optional[:class:`str`]
        The custom activity's text.
    emoji: Optional[Union[:class:`PartialEmoji`, :class:`str`]]
        The emoji to pass to the activity, if any.
    expires_at: Optional[:class:`datetime.datetime`]
        When the custom activity will expire.
    """

    __slots__ = ('name', 'emoji', 'expires_at')

    def __init__(
        self,
        name: Optional[str] = None,
        *,
        emoji: Optional[Union[PartialEmoji, ActivityEmojiPayload, str]] = None,
        state: Optional[str] = None,
        expires_at: Optional[datetime.datetime] = None,
    ):
        # Activity.name is technically required, but because we make the state value
        # the name (which is nullable), we have a mismatch of types here
        # I don't like this abstraction, but I don't want to cause
        # an annoyingly subtle breaking change for the sake of it
        super().__init__(name=name, type=ActivityType.custom)
        if self.name == 'Custom Status':
            self.name = state
        self.expires_at = expires_at

        self.emoji: Optional[PartialEmoji]
        if isinstance(emoji, dict):
            self.emoji = PartialEmoji.from_dict(emoji)
        elif isinstance(emoji, str):
            self.emoji = PartialEmoji(name=emoji)
        elif isinstance(emoji, PartialEmoji) or emoji is None:
            self.emoji = emoji
        else:
            raise TypeError(f'Expected str, PartialEmoji, or None, received {type(emoji)!r} instead')

    @classmethod
    def from_dict(cls, data: ActivityPayload, *, state: ConnectionState, **kwargs: Any) -> Self:
        self = cls.__new__(cls)
        self.id = data.get('id', '')
        self.type = ActivityType.custom
        self.name = data.get('state')
        self._created_at = data.get('created_at')
        self.expires_at = None

        emoji_data = data.get('emoji')
        self.emoji = PartialEmoji.from_dict_stateful(emoji_data, state) if emoji_data else None
        return self

    @classmethod
    def _from_legacy_settings(cls, *, data: Optional[dict], state: ConnectionState) -> Optional[Self]:
        if not data:
            return

        emoji = None
        if data.get('emoji_id'):
            emoji = state.get_emoji(int(data['emoji_id']))
            if not emoji:
                emoji = PartialEmoji(id=int(data['emoji_id']), name=data['emoji_name'])
                emoji._state = state
            else:
                emoji = emoji._to_partial()
        elif data.get('emoji_name'):
            emoji = PartialEmoji(name=data['emoji_name'])
            emoji._state = state

        return cls(name=data.get('text'), emoji=emoji, expires_at=parse_time(data.get('expires_at')))

    @classmethod
    def _from_settings(cls, *, data: Any, state: ConnectionState) -> Self:
        """
        message CustomStatus {
            string text = 1;
            fixed64 emoji_id = 2;
            string emoji_name = 3;
            fixed64 expires_at_ms = 4;
        }
        """
        emoji = None
        if data.emoji_id:
            emoji = state.get_emoji(data.emoji_id)
            if not emoji:
                emoji = PartialEmoji(id=data.emoji_id, name=data.emoji_name)
                emoji._state = state
            else:
                emoji = emoji._to_partial()
        elif data.emoji_name:
            emoji = PartialEmoji(name=data.emoji_name)
            emoji._state = state

        return cls(name=data.text, emoji=emoji, expires_at=parse_timestamp(data.expires_at_ms))

    def __repr__(self) -> str:
        return f'<CustomActivity name={self.name!r} emoji={self.emoji!r}>'

    def __str__(self) -> str:
        if self.emoji:
            if self.name:
                return f'{self.emoji} {self.name}'
            return str(self.emoji)
        else:
            return self.name or ''

    def to_dict(self) -> ActivityPayload:
        payload: ActivityPayload = {
            'type': ActivityType.custom.value,
            # Abstracted away
            'name': 'Custom Status',
            'state': self.name or None,
        }
        if self.emoji:
            payload['emoji'] = self.emoji.to_dict()
        return payload

    def to_legacy_settings_dict(self) -> SettingsActivity:
        payload: SettingsActivity = {}
        if self.name:
            payload['text'] = self.name
        if self.emoji:
            payload['emoji_name'] = self.emoji.name
            if self.emoji.id:
                payload['emoji_id'] = self.emoji.id
        if self.expires_at is not None:
            payload['expires_at'] = self.expires_at.isoformat()
        return payload

    def to_settings_dict(self) -> Dict[str, Optional[Union[str, int]]]:
        payload: Dict[str, Optional[Union[str, int]]] = {}

        if self.name:
            payload['text'] = self.name
        if self.emoji:
            emoji = self.emoji
            payload['emoji_name'] = emoji.name
            if emoji.id:
                payload['emoji_id'] = emoji.id
        if self.expires_at is not None:
            payload['expires_at_ms'] = int(self.expires_at.timestamp() * 1000)
        return payload


class HangActivity(BaseActivity):
    """Represents a Discord Hang status activity.

    .. container:: operations

        .. describe:: x == y

            Checks if two activities are equal.

        .. describe:: x != y

            Checks if two activities are not equal.

        .. describe:: hash(x)

            Returns the activity's hash.

        .. describe:: str(x)

            Returns the string representation of the activity.

    .. versionadded:: 2.1

    Attributes
    -----------
    id: :class:`str`
        The ID of the activity. If this was manually created then the ID will be empty.
    type: :class:`ActivityType`
        The type of activity currently being done. For this class, it is always :attr:`ActivityType.hang`.
    name: :class:`str`
        The name of the hang activity. Will always be "Hang Status".
    state: Optional[:class:`str`]
        The hang activity's raw state. It is recommended to use :attr:`status_type` instead.
    details: Optional[:class:`str`]
        The hang activity's custom text. Only used if :attr:`status_type` is :attr:`HangStatusType.custom`.
        It is recommended to use :attr:`text` instead.
    emoji: Optional[:class:`PartialEmoji`]
        The hang activity's custom emoji. Only used if :attr:`status_type` is :attr:`HangStatusType.custom`.

    Parameters
    -----------
    status_type: :class:`HangStatusType`
        The type of hang status.
    variant: :class:`str`
        The variant of the hang status icon.
    text: Optional[:class:`str`]
        The custom text for the hang status. Must be provided if :attr:`status_type` is :attr:`HangStatusType.custom`.
    emoji: Optional[Union[:class:`PartialEmoji`, :class:`str`]]
        The custom emoji for the hang status. Should be provided if :attr:`status_type` is :attr:`HangStatusType.custom`.
    """

    __slots__ = ('state', 'details', 'emoji')

    def __init__(
        self,
        *,
        status_type: HangStatusType,
        variant: HangStatusVariantType = 'twemoji',
        text: Optional[str] = None,
        emoji: Optional[Union[PartialEmoji, ActivityEmojiPayload, str]] = None,
    ):
        super().__init__(name='Hang Status', type=ActivityType.hang)
        self.state: Optional[str] = f'{status_type.value}:{variant}'
        self.details: Optional[str] = text
        self.emoji: Optional[PartialEmoji]
        if isinstance(emoji, dict):
            self.emoji = PartialEmoji.from_dict(emoji)
        elif isinstance(emoji, str):
            self.emoji = PartialEmoji(name=emoji)
        elif isinstance(emoji, PartialEmoji) or emoji is None:
            self.emoji = emoji
        else:
            raise TypeError(f'Expected str, PartialEmoji, or None, received {type(emoji)!r} instead')

        if status_type == HangStatusType.custom and not text:
            raise TypeError('text must be provided when status_type is HangStatusType.custom')

    @classmethod
    def from_dict(cls, data: ActivityPayload, *, state: ConnectionState, **kwargs: Any) -> Self:
        self = cls.__new__(cls)
        self.id = data.get('id', '')
        self.type = ActivityType.hang
        self.name = 'Hang Status'
        self._created_at = data.get('created_at')
        self.state = data.get('state')
        self.details = data.get('details')

        emoji_data = data.get('emoji')
        self.emoji = PartialEmoji.from_dict_stateful(emoji_data, state) if emoji_data else None
        return self

    def __repr__(self) -> str:
        return f'<HangActivity text={self.text!r} emoji={self.emoji!r}>'

    def __str__(self) -> str:
        if self.status_type == HangStatusType.custom and self.emoji:
            if self.text:
                return f'{self.emoji} {self.text}'
            return str(self.emoji)
        return self.text

    def to_dict(self) -> ActivityPayload:
        payload: ActivityPayload = {
            'type': ActivityType.hang.value,
            'name': 'Hang Status',
            'state': self.state,
        }
        if self.details:
            payload['details'] = self.details
        if self.emoji:
            payload['emoji'] = self.emoji.to_dict()
        return payload

    @property
    def status_type(self) -> HangStatusType:
        """:class:`HangStatusType`: The type of hang status. For types other than :attr:`HangStatusType.custom`,
        official clients will render a custom icon and ignore :attr:`text` and :attr:`emoji`."""
        if self.state:
            status_value = self.state.split(':', 1)[0]
            return try_enum(HangStatusType, status_value)

        # All official clients always send a state, but due to the rich presence API
        # being what it is, the key is technically optional; this is a safe fallback
        return HangStatusType.custom

    @property
    def variant(self) -> HangStatusVariantType:
        """:class:`str`: The variant of the hang status icon."""
        if self.state:
            parts = self.state.split(':', 1)
            if len(parts) == 2:
                return parts[1]  # type: ignore
        return 'twemoji'

    @property
    def text(self) -> str:
        """:class:`str`: The rendered text of the hang status."""
        return self.status_type.text or self.details or ''


class Session:
    """Represents a connected Discord Gateway session.

    .. container:: operations

        .. describe:: x == y

            Checks if two sessions are equal.

        .. describe:: x != y

            Checks if two sessions are not equal.

        .. describe:: hash(x)

            Returns the session's hash.

    .. versionadded:: 2.0

    Attributes
    -----------
    session_id: :class:`str`
        The session ID.
    active: :class:`bool`
        Whether the session is active.
    os: :class:`OperatingSystem`
        The operating system the session is running on.
    client: :class:`ClientType`
        The client the session is running on.
    version: :class:`int`
        The version of the client the session is running on (used for differentiating between e.g. PS4/PS5).
    status: :class:`Status`
        The status of the session.
    activities: Tuple[:class:`BaseActivity`, ...]
        The activities the session is currently doing.
    hidden_activities: Tuple[:class:`BaseActivity`, ...]
        The activities the session is currently doing that are hidden.

        .. versionadded:: 2.1
    """

    __slots__ = (
        'session_id',
        'active',
        'os',
        'client',
        'version',
        'status',
        'activities',
        'hidden_activities',
        '_state',
    )

    def __init__(self, *, data: SessionPayload, state: ConnectionState):
        self._state = state
        client_info = data['client_info']

        self.session_id: str = data['session_id']
        self.os: OperatingSystem = OperatingSystem.from_string(client_info['os'])
        self.client: ClientType = try_enum(ClientType, client_info['client'])
        self.version: int = client_info.get('version', 0)
        self._update(data)

    def _update(self, data: SessionPayload):
        state = self._state

        # Only these should ever change
        self.active: bool = data.get('active', False)
        self.status: Status = try_enum(Status, data['status'])
        self.activities: Tuple[ActivityTypes, ...] = tuple(
            create_activity(activity, state, state.self_id) for activity in data.get('activities', [])
        )
        self.hidden_activities: Tuple[ActivityTypes, ...] = tuple(
            create_activity(activity, state, state.self_id) for activity in data.get('hidden_activities', [])
        )

    def __repr__(self) -> str:
        return f'<Session session_id={self.session_id!r} active={self.active!r} status={self.status!r} activities={self.activities!r} hidden_activities={self.hidden_activities!r}>'

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Session) and self.session_id == other.session_id

    def __ne__(self, other: object) -> bool:
        if isinstance(other, Session):
            return self.session_id != other.session_id
        return True

    def __hash__(self) -> int:
        return hash(self.session_id)

    @classmethod
    def _fake_all(cls, *, state: ConnectionState, data: SessionPayload) -> Self:
        self = cls.__new__(cls)
        self._state = state
        self.session_id = 'all'
        self.os = OperatingSystem.unknown
        self.client = ClientType.unknown
        self.version = 0
        self._update(data)
        return self

    def is_overall(self) -> bool:
        """:class:`bool`: Whether the session represents the overall presence across all platforms.

        .. note::

            If this is ``True``, then :attr:`session_id`, :attr:`os`, and :attr:`client` will not be real values.
        """
        return self.session_id == 'all'

    def is_headless(self) -> bool:
        """:class:`bool`: Whether the session is headless."""
        return self.session_id.startswith('h:')

    def is_current(self) -> bool:
        """:class:`bool`: Whether the session is the current session."""
        return self.session_id == self._state.session_id


ActivityTypes = Union[Activity, CustomActivity, HangActivity, Spotify]


@overload
def create_activity(data: ActivityPayload, state: ConnectionState, user_id: int) -> ActivityTypes: ...


@overload
def create_activity(data: None, state: ConnectionState, user_id: int) -> None: ...


@overload
def create_activity(data: Optional[ActivityPayload], state: ConnectionState, user_id: int) -> Optional[ActivityTypes]: ...


def create_activity(data: Optional[ActivityPayload], state: ConnectionState, user_id: int) -> Optional[ActivityTypes]:
    if not data:
        return None

    game_type = try_enum(ActivityType, data.get('type', 0))
    if game_type is ActivityType.custom:
        return CustomActivity.from_dict(data=data, state=state)
    elif game_type is ActivityType.hang:
        return HangActivity.from_dict(data=data, state=state)
    elif (
        game_type is ActivityType.listening
        and data['name'] == 'Spotify'
        and data.get('party', {}).get('id', '').startswith('spotify:')
    ):
        return Spotify.from_dict(data=data, state=state, user_id=user_id)
    else:
        return Activity.from_dict(data=data, state=state, user_id=user_id)

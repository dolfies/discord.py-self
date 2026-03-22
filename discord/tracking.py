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

import asyncio
from base64 import b64encode
import datetime
import json
import logging
import random
import re
from typing import Any, Callable, Dict, Final, List, Literal, Optional, Tuple, TypedDict, TYPE_CHECKING, Union
import uuid

import curl_cffi
from curl_cffi import requests

from . import __version__
from .errors import HTTPException, InvalidData
from .utils import MISSING, cached_property, _to_json, utcnow

if TYPE_CHECKING:
    from typing_extensions import Self

    from aiohttp import BasicAuth, ClientSession

    from .enums import ChannelType
    from .types.snowflake import Snowflake

__all__ = ('HeadersContext',)

_BUILD_NUMBER_REGEX = re.compile(r'"BUILD_NUMBER":\s*"(\d+)"')

_log = logging.getLogger(__name__)


class ContextPropertiesMeta(type):
    if TYPE_CHECKING:

        def __getattribute__(self, name: str) -> Callable[[], ContextProperties]: ...

    def __new__(cls, name: str, bases: Tuple[type, ...], attrs: Dict[str, Any]):
        cls = super().__new__(cls, name, bases, attrs)
        locations = attrs.get('LOCATIONS', {})
        sources = attrs.get('SOURCES', {})

        def build_location(location: str) -> classmethod:
            def f(cls) -> ContextProperties:
                data = {'location': location}
                return cls(data)

            return classmethod(f)

        def build_source(source: str) -> classmethod:
            def f(cls) -> ContextProperties:
                data = {'source': source}
                return cls(data)

            return classmethod(f)

        for location in locations:
            if location:
                setattr(cls, f'from_{location.lower().replace(" ", "_").replace("/", "")}', build_location(location))

        for source in sources:
            if source:
                setattr(cls, f'from_{source.lower().replace(" ", "_")}', build_source(source))

        return cls


class ContextProperties(metaclass=ContextPropertiesMeta):
    """Represents the Discord X-Context-Properties header.

    This header is essential for certain actions (e.g. joining guilds, friend requesting).
    """

    __slots__ = ('_data',)

    LOCATIONS = {
        None: 'e30=',
        'Friends': 'eyJsb2NhdGlvbiI6IkZyaWVuZHMifQ==',
        'ContextMenu': 'eyJsb2NhdGlvbiI6IkNvbnRleHRNZW51In0=',
        'Context Menu': 'eyJsb2NhdGlvbiI6IkNvbnRleHQgTWVudSJ9',
        'User Profile': 'eyJsb2NhdGlvbiI6IlVzZXIgUHJvZmlsZSJ9',
        'Add Friend': 'eyJsb2NhdGlvbiI6IkFkZCBGcmllbmQifQ==',
        'Guild Header': 'eyJsb2NhdGlvbiI6Ikd1aWxkIEhlYWRlciJ9',
        'Group DM': 'eyJsb2NhdGlvbiI6Ikdyb3VwIERNIn0=',
        'DM Channel': 'eyJsb2NhdGlvbiI6IkRNIENoYW5uZWwifQ==',
        '/app': 'eyJsb2NhdGlvbiI6ICIvYXBwIn0=',
        'Login': 'eyJsb2NhdGlvbiI6IkxvZ2luIn0=',
        'Register': 'eyJsb2NhdGlvbiI6IlJlZ2lzdGVyIn0=',
        'Verify Email': 'eyJsb2NhdGlvbiI6IlZlcmlmeSBFbWFpbCJ9',
        'New Group DM': 'eyJsb2NhdGlvbiI6Ik5ldyBHcm91cCBETSJ9',
        'Add Friends to DM': 'eyJsb2NhdGlvbiI6IkFkZCBGcmllbmRzIHRvIERNIn0=',
        'Group DM Invite Create': 'eyJsb2NhdGlvbiI6Ikdyb3VwIERNIEludml0ZSBDcmVhdGUifQ==',
        'Stage Channel': 'eyJsb2NhdGlvbiI6IlN0YWdlIENoYW5uZWwifQ==',
        'chat_input': 'eyJsb2NhdGlvbiI6ImNoYXRfaW5wdXQifQ==',
        'greet': 'eyJsb2NhdGlvbiI6ImdyZWV0In0=',
    }

    SOURCES = {
        None: 'e30=',
        'Chat Input Blocker - Lurker Mode': 'eyJzb3VyY2UiOiJDaGF0IElucHV0IEJsb2NrZXIgLSBMdXJrZXIgTW9kZSJ9',
        'Notice - Lurker Mode': 'eyJzb3VyY2UiOiJOb3RpY2UgLSBMdXJrZXIgTW9kZSJ9',
    }

    def __init__(self, data: dict) -> None:
        self._data: Dict[str, Snowflake] = data

    def _encode_data(self) -> str:
        try:
            target = self.target
            return self.LOCATIONS.get(target, self.SOURCES[target])
        except KeyError:
            return b64encode(json.dumps(self._data, separators=(',', ':')).encode()).decode('utf-8')

    @classmethod
    def empty(cls) -> Self:
        return cls({})

    @classmethod
    def from_accept_invite_page(
        cls,
        *,
        guild_id: Optional[Snowflake] = None,
        channel_id: Optional[Snowflake] = None,
        channel_type: Optional[ChannelType] = None,
    ) -> Self:
        data: Dict[str, Snowflake] = {
            'location': 'Accept Invite Page',
        }
        if guild_id:
            data['location_guild_id'] = str(guild_id)
        if channel_id:
            data['location_channel_id'] = str(channel_id)
        if channel_type:
            data['location_channel_type'] = int(channel_type)
        return cls(data)

    @classmethod
    def from_join_guild(
        cls,
        *,
        guild_id: Snowflake = MISSING,
        channel_id: Snowflake = MISSING,
        channel_type: ChannelType = MISSING,
    ) -> Self:
        data: Dict[str, Snowflake] = {
            'location': 'Join Guild',
        }
        if guild_id is not MISSING:
            data['location_guild_id'] = str(guild_id)
        if channel_id is not MISSING:
            data['location_channel_id'] = str(channel_id)
        if channel_type is not MISSING:
            data['location_channel_type'] = int(channel_type)
        return cls(data)

    @classmethod
    def from_invite_button_embed(
        cls,
        *,
        guild_id: Optional[Snowflake],
        channel_id: Snowflake,
        message_id: Snowflake,
        channel_type: Optional[ChannelType],
    ) -> Self:
        data = {
            'location': 'Invite Button Embed',
            'location_guild_id': str(guild_id) if guild_id else None,
            'location_channel_id': str(channel_id),
            'location_channel_type': int(channel_type) if channel_type else None,
            'location_message_id': str(message_id),
        }
        return cls(data)

    @classmethod
    def from_lurking(cls, source: str = MISSING) -> Self:
        data = {'source': source or random.choice(('Chat Input Blocker - Lurker Mode', 'Notice - Lurker Mode'))}
        return cls(data)

    @property
    def target(self) -> Optional[str]:
        return self._data.get('location', self._data.get('source'))  # type: ignore

    @property
    def value(self) -> str:
        return self._encode_data()

    def __str__(self) -> str:
        return self.target or 'None'

    def __repr__(self) -> str:
        return f'<ContextProperties target={self.target!r}>'

    def __eq__(self, other) -> bool:
        return isinstance(other, ContextProperties) and self.value == other.value

    def __ne__(self, other) -> bool:
        if isinstance(other, ContextProperties):
            return self.value != other.value
        return True


def _resolve_proxy_auth(proxy_auth: Optional[Union[BasicAuth, Tuple[str, str]]]) -> Optional[BasicAuth]:
    # HACK: Client technically allows tuples as proxy auth
    if proxy_auth is None:
        return None
    if isinstance(proxy_auth, BasicAuth):
        return proxy_auth
    return BasicAuth(proxy_auth[0], proxy_auth[1])


class APIProperties(TypedDict):
    properties: Dict[str, Any]
    extra_gateway_properties: Optional[Dict[str, Any]]
    encoded: str
    metadata: Optional[Dict[str, Any]]


class HeadersContext:
    """A user-constructible class to provide standard headers and client contexts for HTTP requests.

    Contains various utility methods and classmethods for helping you generate a valid instance.
    May also be subclassed to provide more granular control over the context.

    .. versionadded:: 2.2

    .. warning::

        Configuring your own header context from scratch is not recommended,
        as it may lead to account termination by anti abuse systems.

    Parameters
    -----------
    super_properties: Dict[:class:`str`, Any]
        The client properties to use for the context.
    extra_gateway_properties: Optional[Dict[:class:`str`, Any`]]
        Additional properties to send in the Gateway Identify payload.
        These will be merged with the super properties, with these taking precedence in case of conflicts.
    platform: :class:`str`
        The platform to impersonate.
    browser_type: :class:`str`
        The browser type to impersonate.
    browser_major_version: :class:`int`
        The major version of the browser to impersonate. Only used for Chromium-based browsers.
    """

    BASE_DOMAIN: Final[str] = 'discord.com'
    FALLBACK_BUILD_NUMBER: Final[int] = 9999
    FALLBACK_BROWSER_VERSION: Final[int] = 136

    # TODO: Migrate this off aiohttp for the eventual deprecation

    def __init__(
        self,
        *,
        super_properties: Dict[str, Any],
        encoded_super_properties: str = MISSING,
        extra_gateway_properties: Optional[Dict[str, Any]] = None,
        initialization_timestamp: datetime.datetime = MISSING,
        platform: Literal['Windows', 'macOS', 'Linux', 'Android', 'iOS'] = 'Windows',
        browser_type: Literal['chrome', 'electron', 'edge', 'firefox', 'safari'] = 'chrome',
        browser_major_version: int = MISSING,
    ) -> None:
        if browser_type == 'electron' and platform in ('Android', 'iOS'):
            raise ValueError('Electron cannot be used on mobile platforms')
        if browser_type in ('chrome', 'electron', 'edge') and browser_major_version is MISSING:
            raise ValueError('Browser major version must be specified for Chromium-based browsers')

        self.super_properties: Dict[str, Any] = super_properties
        self.encoded_super_properties: str = encoded_super_properties or b64encode(
            _to_json(super_properties).encode()
        ).decode('utf-8')
        self.extra_gateway_properties: Dict[str, Any] = extra_gateway_properties or {}
        self.initialization_timestamp: datetime.datetime = initialization_timestamp or utcnow()
        self.platform: Literal['Windows', 'macOS', 'Linux', 'Android', 'iOS'] = platform
        self.browser_type: Literal['chrome', 'electron', 'edge', 'firefox', 'safari'] = browser_type
        self.browser_major_version: int = browser_major_version

    def __repr__(self) -> str:
        return f'<HeadersContext impersonate={self.impersonate!r} user_agent={self.user_agent!r}>'

    @classmethod
    async def default(
        cls: type[Self], session: ClientSession, proxy: Optional[str] = None, proxy_auth: Optional[BasicAuth] = None
    ) -> Self:
        """|coro|

        Creates a new instance for the Chrome web client on Windows.

        This is what the library uses by defualt if you do not provide a context.
        As such, it has built-in fallbacks in case the info API is down or returns invalid data,
        or if the client build number or browser version cannot be retrieved for any reason.

        Returns
        --------
        :class:`HeadersContext`
            The generated header context.
        """
        try:
            data = await asyncio.wait_for(
                cls.fetch_api_properties(session, 'web', proxy=proxy, proxy_auth=proxy_auth), timeout=3
            )
        except Exception:
            _log.info('Info API temporarily down. Falling back to manual retrieval...')
        else:
            return cls(
                platform='Windows',
                browser_type='chrome',
                browser_major_version=int(data['properties']['browser_version'].split('.')[0]),
                super_properties=data['properties'],
                encoded_super_properties=data.get('encoded'),
                extra_gateway_properties=data.get('extra_gateway_properties'),
            )

        try:
            bn = await cls.scrape_client_build_number(session, proxy=proxy, proxy_auth=proxy_auth)
        except Exception:
            _log.critical('Could not retrieve client build number. Falling back to hardcoded value...')
            bn = cls.FALLBACK_BUILD_NUMBER

        try:
            fbv = await cls.fetch_chrome_version(session, proxy=proxy, proxy_auth=proxy_auth)
            bv = int(fbv.split('.')[0])
        except Exception:
            _log.warning('Could not retrieve browser version. Falling back to local value...')
            try:
                impersonate = requests.impersonate.DEFAULT_CHROME
                bv = int(re.sub(r'\D', '', impersonate))
            except Exception:
                bv = cls.FALLBACK_BROWSER_VERSION

        properties = {
            'os': 'Windows',
            'browser': 'Chrome',
            'device': '',
            'system_locale': 'en-US',
            'browser_user_agent': cls.format_chromium_user_agent(bv),
            'browser_version': f'{bv}.0.0.0',
            'os_version': '10',
            'referrer': '',
            'referring_domain': '',
            'referrer_current': '',
            'referring_domain_current': '',
            'release_channel': 'stable',
            'client_build_number': bn,
            'client_event_source': None,
            'has_client_mods': False,
            'client_launch_id': str(uuid.uuid4()),
            'client_app_state': 'unfocused',
            'client_heartbeat_session_id': str(uuid.uuid4()),
            'launch_signature': cls.generate_launch_signature(),
        }

        return cls(
            platform='Windows',
            browser_type='chrome',
            browser_major_version=bv,
            super_properties=properties,
            extra_gateway_properties={
                'is_fast_connect': False,
                'gateway_connect_reasons': 'AppSkeleton',
            },
        )

    @classmethod
    async def desktop(
        cls: type[Self], session: ClientSession, proxy: Optional[str] = None, proxy_auth: Optional[BasicAuth] = None
    ) -> Self:
        """|coro|

        Creates a new instance for the desktop client on Windows.

        .. warning::

            Unlike :meth:`default`, this method does not have built-in fallbacks,
            and will raise if the info API is down or returns invalid data.

        Raises
        ------
        HTTPException
            The info API is down.
        InvalidData
            The info API returned invalid data.

        Returns
        --------
        :class:`HeadersContext`
            The generated header context.
        """
        # Fallbacks are infeasible here because of the sheer amount of data needed for desktop client super properties :(
        data = await cls.fetch_api_properties(session, 'windows', proxy=proxy, proxy_auth=proxy_auth)
        try:
            # metadata will always be provided on desktop client properties
            bv = int(data['metadata']['native_chrome_version'].split('.')[0])  # type: ignore
        except Exception:
            raise InvalidData('Invalid native Chrome version in API response')

        return cls(
            platform='Windows',
            browser_type='electron',
            browser_major_version=bv,
            super_properties=data['properties'],
            encoded_super_properties=data.get('encoded'),
            extra_gateway_properties=data.get('extra_gateway_properties'),
        )

    @cached_property
    def user_agent(self) -> str:
        """:class:`str`: The user agent to be used for HTTP requests."""
        return self.super_properties['browser_user_agent']

    @cached_property
    def client_hints(self) -> Dict[str, str]:
        """Dict[:class:`str`, :class:`str`]: The client hints to be used for HTTP requests. Browser implementation-specific headers should go here."""
        brands = {'chrome': 'Google Chrome', 'electron': None, 'edge': 'Microsoft Edge'}

        if self.browser_type in ('chrome', 'electron', 'edge'):
            return {
                'Priority': 'u=0, i',
                'Sec-CH-UA': ', '.join(
                    [
                        f'"{brand}";v="{version}"'
                        for brand, version in self.generate_chromium_brand_version_list(brand=brands[self.browser_type])
                    ]
                ),
                'Sec-CH-UA-Mobile': '?1' if self.platform in ('Android', 'iOS') else '?0',
                'Sec-CH-UA-Platform': f'"{self.platform}"',
            }
        elif self.browser_type == 'firefox':
            return {
                # Firefox does not appear to send Priority on XHR requests
                'Alt-Used': self.BASE_DOMAIN,
                'TE': 'trailers',
            }
        elif self.browser_type == 'safari':
            return {
                'Priority': 'u=3, i',
            }
        return {}

    @property
    def impersonate(self) -> str:
        """:class:`str`: The curl-cffi TLS fingerprint to adopt for HTTP requests."""
        try:
            if self.platform == 'iOS':
                return requests.impersonate.DEFAULT_SAFARI_IOS
            elif self.browser_type == 'firefox':
                return requests.impersonate.DEFAULT_FIREFOX
            elif self.browser_type == 'safari':
                return requests.impersonate.DEFAULT_SAFARI
            else:
                if self.platform == 'Android':
                    return requests.impersonate.DEFAULT_CHROME_ANDROID
                return requests.impersonate.DEFAULT_CHROME
        except Exception:
            # Guard breaking change
            return 'chrome'

    @property
    def gateway_properties(self) -> Dict[str, Any]:
        """Dict[:class:`str`, :class:`Any`]: The properties to be used for the Discord Gateway."""
        return {
            **self.super_properties,
            **self.extra_gateway_properties,
        }

    @staticmethod
    async def fetch_api_properties(
        session: ClientSession,
        type: Literal['web', 'developers', 'marketing', 'windows', 'mac', 'linux'],
        release_channel: Literal['stable', 'ptb', 'canary', 'development'] = 'stable',
        browser: Optional[Literal['chrome', 'firefox', 'safari', 'edge']] = None,
        platform: Optional[Literal['windows', 'mac', 'linux']] = None,
        *,
        proxy: Optional[str] = None,
        proxy_auth: Optional[BasicAuth] = None,
    ) -> APIProperties:
        """|coro|

        Fetches client properties from the info API.

        Parameters
        -----------
        session: :class:`aiohttp.ClientSession`
            The session to make the request with.
        type: :class:`str`
            The type of properties to fetch. Can be one of ``web``, ``windows``, ``mac``, or ``linux``.
            The last three represent desktop clients on their respective platforms.
        release_channel: :class:`str`
            The release channel to fetch properties for. Can be one of ``stable``, ``ptb``, ``canary``, or ``development``.
            ``development`` is only applicable for the desktop client types.
        browser: Optional[:class:`str`]
            The browser to fetch properties for. Can be one of ``chrome``, ``firefox``, ``safari``, or ``edge``.
            Does not apply to the desktop client types.
        platform: Optional[:class:`str`]
            The platform to fetch properties for. Can be one of ``windows``, ``mac``, or ``linux``.
            Does not apply to the desktop client types.
        proxy: Optional[:class:`str`]
            The proxy to use for the request.
        proxy_auth: Optional[:class:`aiohttp.BasicAuth`]
            The proxy authentication to use for the request.

        Raises
        ------
        HTTPException
            The info API is down.
            The info API returned a 202 status code, indicating that the properties could not be retrieved at this time.
            This is a temporary state and should be retried.

        Returns
        --------
        :class:`dict`
            The API response, containing ``properties``, ``extra_gateway_properties``, and ``encoded`` keys.
        """
        params = {'release_channel': release_channel}
        if browser is not None:
            params['browser'] = browser
        if platform is not None:
            params['platform'] = platform

        # Support the regular platform literals
        if type.lower() == 'macos':
            type = 'mac'

        async with session.post(
            f'https://cordapi.dolfi.es/api/v2/properties/{type.lower()}',
            proxy=proxy,
            proxy_auth=_resolve_proxy_auth(proxy_auth),
            headers={'User-Agent': f'discord.py-self/{__version__} curl_cffi/{curl_cffi.__version__}'},  # type: ignore
        ) as resp:
            if not resp.ok:
                raise HTTPException(resp, 'Failed to fetch properties from info API')
            if resp.status == 202:
                # While we do return a retry_after, it's not actively based on anything
                # Better to just raise
                raise HTTPException(resp, 'Info API is temporarily unavailable')

            return await resp.json()

    @staticmethod
    async def scrape_client_build_number(
        session: ClientSession, *, proxy: Optional[str] = None, proxy_auth: Optional[BasicAuth] = None
    ) -> int:
        """|coro|

        Scrapes the client build number from the Discord app.

        Parameters
        -----------
        session: :class:`aiohttp.ClientSession`
            The session to make the request with.
        proxy: Optional[:class:`str`]
            The proxy to use for the request.
        proxy_auth: Optional[:class:`aiohttp.BasicAuth`]
            The proxy authentication to use for the request.

        Raises
        ------
        InvalidData
            Client build number could not be found in the app.

        Returns
        --------
        :class:`int`
            The client build number.
        """
        async with session.get('https://discord.com/login', proxy=proxy, proxy_auth=_resolve_proxy_auth(proxy_auth)) as resp:
            app = await resp.text()
            match = _BUILD_NUMBER_REGEX.search(app)
            if match is None:
                raise InvalidData('Could not find client global env')
            return int(match.group(1))

    @staticmethod
    async def fetch_chrome_version(
        session: ClientSession,
        platform: Literal['Windows', 'macOS', 'Linux', 'Android', 'iOS'] = 'Windows',
        *,
        proxy: Optional[str] = None,
        proxy_auth: Optional[BasicAuth] = None,
    ) -> str:
        """|coro|

        Fetches the latest Chrome browser version.

        Parameters
        -----------
        session: :class:`aiohttp.ClientSession`
            The session to make the request with.
        platform: :class:`str`
            The platform to fetch the Chrome version for. Can be one of ``Windows``, ``macOS``, ``Linux``, ``Android``, or ``iOS``.
        proxy: Optional[:class:`str`]
            The proxy to use for the request.
        proxy_auth: Optional[:class:`aiohttp.BasicAuth`]
            The proxy authentication to use for the request.

        Raises
        ------
        HTTPException
            Failed to fetch Chrome version from API.

        Returns
        --------
        :class:`str`
            The latest Chrome browser version.
        """
        api_platform = platform.lower()
        if api_platform == 'windows':
            api_platform = 'win'
        elif api_platform == 'macos':
            api_platform = 'mac'

        async with session.get(
            f'https://versionhistory.googleapis.com/v1/chrome/platforms/{api_platform}/channels/stable/versions',
            proxy=proxy,
            proxy_auth=_resolve_proxy_auth(proxy_auth),
        ) as response:
            if not response.ok:
                raise HTTPException(response, 'Failed to fetch Chrome version from API')

            data = await response.json()
            return data['versions'][0]['version']

    @staticmethod
    async def fetch_firefox_version(
        session: ClientSession, *, proxy: Optional[str] = None, proxy_auth: Optional[BasicAuth] = None
    ) -> str:
        """|coro|

        Fetches the latest Firefox browser version.

        Parameters
        -----------
        session: :class:`aiohttp.ClientSession`
            The session to make the request with.
        proxy: Optional[:class:`str`]
            The proxy to use for the request.
        proxy_auth: Optional[:class:`aiohttp.BasicAuth`]
            The proxy authentication to use for the request.

        Raises
        ------
        HTTPException
            Failed to fetch Firefox version from API.

        Returns
        --------
        :class:`str`
            The latest Firefox browser version.
        """
        async with session.get(
            'https://product-details.mozilla.org/1.0/firefox_versions.json',
            proxy=proxy,
            proxy_auth=_resolve_proxy_auth(proxy_auth),
        ) as response:
            if not response.ok:
                raise HTTPException(response, 'Failed to fetch Firefox version from API')

            data = await response.json()
            return data['LATEST_FIREFOX_VERSION']

    @staticmethod
    async def fetch_edge_version(
        session: ClientSession,
        platform: Literal['Windows', 'macOS', 'Linux', 'Android', 'iOS'] = 'Windows',
        *,
        proxy: Optional[str] = None,
        proxy_auth: Optional[BasicAuth] = None,
    ) -> str:
        """|coro|

        Fetches the latest Edge browser version.
        Note that the major version will always match across platforms.

        Parameters
        -----------
        session: :class:`aiohttp.ClientSession`
            The session to make the request with.
        platform: :class:`str`
            The platform to fetch the Edge version for.
            Can be one of ``Windows``, ``macOS``, ``Linux``, ``Android``, or ``iOS``.
        proxy: Optional[:class:`str`]
            The proxy to use for the request.
        proxy_auth: Optional[:class:`aiohttp.BasicAuth`]
            The proxy authentication to use for the request.

        Raises
        ------
        HTTPException
            Failed to fetch Edge version from API.
        InvalidData
            Could not find Edge version in the response.

        Returns
        --------
        :class:`str`
            The latest Edge browser version.
        """
        async with session.get(
            'https://edgeupdates.microsoft.com/api/products',
            proxy=proxy,
            proxy_auth=_resolve_proxy_auth(proxy_auth),
        ) as response:
            if not response.ok:
                raise HTTPException(response, 'Failed to fetch Edge version from API')

            for product in await response.json():
                if product['Product'] == 'Stable':
                    for release in product['Releases'][::-1]:
                        if release['Platform'].lower() == platform.lower():
                            return release['ProductVersion']

            raise InvalidData('Could not find Edge version')

    @staticmethod
    async def fetch_safari_version(
        session: ClientSession, proxy: Optional[str] = None, proxy_auth: Optional[BasicAuth] = None
    ) -> str:
        """|coro|

        Fetches the latest Safari browser version.

        Parameters
        -----------
        session: :class:`aiohttp.ClientSession`
            The session to make the request with.
        proxy: Optional[:class:`str`]
            The proxy to use for the request.
        proxy_auth: Optional[:class:`aiohttp.BasicAuth`]
            The proxy authentication to use for the request.

        Raises
        ------
        HTTPException
            Failed to fetch Safari version from API.
        InvalidData
            Could not find Safari version in the response.

        Returns
        --------
        :class:`str`
            The latest Safari browser version.
        """
        async with session.get(
            'https://developer.apple.com/tutorials/data/documentation/safari-release-notes.json',
            proxy=proxy,
            proxy_auth=_resolve_proxy_auth(proxy_auth),
        ) as response:
            if not response.ok:
                raise HTTPException(response, 'Failed to fetch Safari version from API')
            data = await response.json()

            # We can't just use the first one as it's usually the beta
            for section in data['topicSections']:
                for identifier in section['identifiers']:
                    ref = data['references'][identifier]
                    if 'Beta' not in ref['abstract'][0]['title']:
                        return ref['title'].split(' ')[1]

            raise InvalidData('Could not find Safari version')

    # TODO: The below two do not support iOS as they do not currently freeze the OS version
    # For now, users can implement that themselves

    @staticmethod
    def format_chromium_user_agent(
        version: int,
        platform: Literal['Windows', 'macOS', 'Linux', 'Android'] = 'Windows',
        brand: Optional[str] = None,
    ) -> str:
        """
        Formats a Chromium user agent string given a major version and optional brand.

        Parameters
        -----------
        version: :class:`int`
            The major version of the browser.
        platform: :class:`str`
            The platform to format the user agent for. Can be one of ``Windows``, ``macOS``, ``Linux``, or ``Android``.
        brand: Optional[:class:`str`]
            The browser brand, if any. For example, "Edg" for Microsoft Edge.

        Returns
        --------
        :class:`str`
            The formatted user agent string.
        """
        # Because of [user agent reduction](https://www.chromium.org/updates/ua-reduction/), we just need the major version now :)
        platforms = {
            'Windows': 'Windows NT 10.0; Win64; x64',
            'macOS': 'Macintosh; Intel Mac OS X 10_15_7',
            'Linux': 'X11; Linux x86_64',
            'Android': 'Linux; Android 10; K',
        }

        # Android devices append "Mobile" before the Safari suffix
        safari_suffix = 'Mobile Safari/537.36' if platform == 'Android' else 'Safari/537.36'
        ret = f'Mozilla/5.0 ({platforms[platform]}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 {safari_suffix}'
        if brand:
            # e.g. Edg/120.0.0.0 for Microsoft Edge
            ret += f' {brand}/{version}.0.0.0'

        return ret

    @staticmethod
    def format_firefox_user_agent(
        version: int, platform: Literal['Windows', 'macOS', 'Linux', 'Android'] = 'Windows'
    ) -> str:
        """
        Formats a Firefox user agent string given a major version.

        Parameters
        -----------
        version: int
            The major version of the browser.
        platform: str
            The platform to format the user agent for. Can be one of ``Windows``, ``macOS``, ``Linux``, or ``Android``.

        Returns
        --------
        :class:`str`
            The formatted user agent string.
        """
        platforms = {
            'Windows': 'Windows NT 10.0; Win64; x64',
            'macOS': 'Macintosh; Intel Mac OS X 10.15',
            'Linux': 'X11; Linux x86_64',
            # Firefox actually reverted the Android freezing changes, but I'm hoping they reinstate them
            'Android': 'Android 10; Mobile',
        }

        # Desktop platforms use the frozen Gecko/20100101 trail
        gecko = f'{version}.0' if platform == 'Android' else '20100101'
        return f'Mozilla/5.0 ({platforms[platform]}; rv:{version}.0) Gecko/{gecko} Firefox/{version}.0'

    @staticmethod
    def format_safari_user_agent(version: str, platform: Literal['macOS', 'iOS'] = 'macOS') -> str:
        """
        Formats a Safari user agent string given a version.

        Parameters
        -----------
        version: str
            The version of Safari.
        platform: str
            The platform to format the user agent for. Can be ``macOS`` or ``iOS``.

        Returns
        --------
        :class:`str`
            The formatted user agent string.
        """
        # Apple has similarly frozen all user agents as of the latest OS versions
        if platform == 'iOS':
            return f'Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{version} Mobile/15E148 Safari/604.1'
        return f'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{version} Safari/605.1.15'

    @staticmethod
    def generate_launch_signature() -> str:
        """
        Generates a client launch signature.

        Returns
        --------
        :class:`str`
            A client launch signature.
        """
        bits = 0b00000000100000000001000000010000000010000001000000001000000000000010000010000001000000000100000000000001000000000000100000000000

        # Force all bits to 0
        random_uuid = uuid.uuid4().int & (~bits & ((1 << 128) - 1))
        result = uuid.UUID(int=random_uuid)
        return str(result)

    # These are all adapted from Chromium source code (https://github.com/chromium/chromium/blob/master/components/embedder_support/user_agent_utils.cc)

    def generate_chromium_brand_version_list(self, brand: Optional[str] = 'Google Chrome') -> List[Tuple[str, str]]:
        """
        Generates a list of brand and version pairs for the user-agent.

        This is used for the Sec-CH-UA client hint header. The list is shuffled in a deterministic way based on the browser major version.

        Parameters
        -----------
        brand: Optional[:class:`str`]
            The browser brand to include in the list, if any. For example, "Google Chrome" or "Microsoft Edge".
        """
        version = self.browser_major_version
        greasey_bv = self._get_greased_user_agent_brand_version(version)
        chromium_bv = ('Chromium', version)
        brand_version_list = [greasey_bv, chromium_bv]
        if brand:
            brand_version_list.append((brand, version))

        order = self._get_random_order(version, len(brand_version_list))
        shuffled_brand_version_list: List[Any] = [None] * len(brand_version_list)
        for i, idx in enumerate(order):
            shuffled_brand_version_list[idx] = brand_version_list[i]
        return shuffled_brand_version_list

    @staticmethod
    def _get_random_order(seed: int, size: int) -> List[int]:
        random.seed(seed)
        if size == 2:
            return [seed % size, (seed + 1) % size]
        elif size == 3:
            orders = [[0, 1, 2], [0, 2, 1], [1, 0, 2], [1, 2, 0], [2, 0, 1], [2, 1, 0]]
            return orders[seed % len(orders)]
        else:
            orders = [
                [0, 1, 2, 3],
                [0, 1, 3, 2],
                [0, 2, 1, 3],
                [0, 2, 3, 1],
                [0, 3, 1, 2],
                [0, 3, 2, 1],
                [1, 0, 2, 3],
                [1, 0, 3, 2],
                [1, 2, 0, 3],
                [1, 2, 3, 0],
                [1, 3, 0, 2],
                [1, 3, 2, 0],
                [2, 0, 1, 3],
                [2, 0, 3, 1],
                [2, 1, 0, 3],
                [2, 1, 3, 0],
                [2, 3, 0, 1],
                [2, 3, 1, 0],
                [3, 0, 1, 2],
                [3, 0, 2, 1],
                [3, 1, 0, 2],
                [3, 1, 2, 0],
                [3, 2, 0, 1],
                [3, 2, 1, 0],
            ]
            return orders[seed % len(orders)]

    @staticmethod
    def _get_greased_user_agent_brand_version(seed: int) -> Tuple[str, str]:
        greasey_chars = [' ', '(', ':', '-', '.', '/', ')', ';', '=', '?', '_']
        greased_versions = ['8', '99', '24']
        greasey_brand = (
            f'Not{greasey_chars[seed % len(greasey_chars)]}A{greasey_chars[(seed + 1) % len(greasey_chars)]}Brand'
        )
        greasey_version = greased_versions[seed % len(greased_versions)]

        version_parts = greasey_version.split('.')
        if len(version_parts) > 1:
            greasey_major_version = version_parts[0]
        else:
            greasey_major_version = greasey_version
        return (greasey_brand, greasey_major_version)

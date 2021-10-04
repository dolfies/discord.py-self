# -*- coding: utf-8 -*-

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

import array
import asyncio
import collections.abc
import unicodedata
from base64 import b64encode
from bisect import bisect_left
import datetime
import functools
from inspect import isawaitable as _isawaitable, signature as _signature
from operator import attrgetter
import os
from threading import Timer
import json
import re
import warnings
import logging
import platform
import subprocess
import tempfile

from .enums import BrowserEnum
from .errors import InvalidArgument

DISCORD_EPOCH = 1420070400000
MAX_ASYNCIO_SECONDS = 3456000

log = logging.getLogger(__name__)

class cached_property:
    def __init__(self, function):
        self.function = function
        self.__doc__ = getattr(function, '__doc__')

    def __get__(self, instance, owner):
        if instance is None:
            return self

        value = self.function(instance)
        setattr(instance, self.function.__name__, value)

        return value

class CachedSlotProperty:
    def __init__(self, name, function):
        self.name = name
        self.function = function
        self.__doc__ = getattr(function, '__doc__')

    def __get__(self, instance, owner):
        if instance is None:
            return self

        try:
            return getattr(instance, self.name)
        except AttributeError:
            value = self.function(instance)
            setattr(instance, self.name, value)
            return value

def cached_slot_property(name):
    def decorator(func):
        return CachedSlotProperty(name, func)
    return decorator

class SequenceProxy(collections.abc.Sequence):
    """Read-only proxy of a Sequence."""
    def __init__(self, proxied):
        self.__proxied = proxied

    def __getitem__(self, idx):
        return self.__proxied[idx]

    def __len__(self):
        return len(self.__proxied)

    def __contains__(self, item):
        return item in self.__proxied

    def __iter__(self):
        return iter(self.__proxied)

    def __reversed__(self):
        return reversed(self.__proxied)

    def index(self, value, *args, **kwargs):
        return self.__proxied.index(value, *args, **kwargs)

    def count(self, value):
        return self.__proxied.count(value)

def parse_time(timestamp):
    if timestamp:
        return datetime.datetime(*map(int, re.split(r'[^\d]', timestamp.replace('+00:00', ''))))
    return None

def copy_doc(original):
    def decorator(overriden):
        overriden.__doc__ = original.__doc__
        overriden.__signature__ = _signature(original)
        return overriden
    return decorator

def deprecated(instead=None):
    def actual_decorator(func):
        @functools.wraps(func)
        def decorated(*args, **kwargs):
            warnings.simplefilter('always', DeprecationWarning) # turn off filter
            if instead:
                fmt = "{0.__name__} is deprecated, use {1} instead."
            else:
                fmt = '{0.__name__} is deprecated.'

            warnings.warn(fmt.format(func, instead), stacklevel=3, category=DeprecationWarning)
            warnings.simplefilter('default', DeprecationWarning) # reset filter
            return func(*args, **kwargs)
        return decorated
    return actual_decorator

def snowflake_time(id):
    """
    Parameters
    -----------
    id: :class:`int`
        The snowflake ID.

    Returns
    --------
    :class:`datetime.datetime`
        The creation date in UTC of a Discord snowflake ID."""
    return datetime.datetime.utcfromtimestamp(((id >> 22) + DISCORD_EPOCH) / 1000)

def time_snowflake(datetime_obj, high=False):
    """Returns a numeric snowflake pretending to be created at the given date.

    When using as the lower end of a range, use ``time_snowflake(high=False) - 1`` to be inclusive, ``high=True`` to be exclusive
    When using as the higher end of a range, use ``time_snowflake(high=True)`` + 1 to be inclusive, ``high=False`` to be exclusive

    Parameters
    -----------
    datetime_obj: :class:`datetime.datetime`
        A timezone-naive datetime object representing UTC time.
    high: :class:`bool`
        Whether or not to set the lower 22 bit to high or low.
    """
    unix_seconds = (datetime_obj - type(datetime_obj)(1970, 1, 1)).total_seconds()
    discord_millis = int(unix_seconds * 1000 - DISCORD_EPOCH)

    return (discord_millis << 22) + (2**22-1 if high else 0)

def find(predicate, seq):
    """A helper to return the first element found in the sequence
    that meets the predicate. For example: ::

        member = discord.utils.find(lambda m: m.name == 'Mighty', channel.guild.members)

    would find the first :class:`~discord.Member` whose name is 'Mighty' and return it.
    If an entry is not found, then ``None`` is returned.

    This is different from :func:`py:filter` due to the fact it stops the moment it finds
    a valid entry.

    Parameters
    -----------
    predicate
        A function that returns a boolean-like result.
    seq: iterable
        The iterable to search through.
    """

    for element in seq:
        if predicate(element):
            return element
    return None

def get(iterable, **attrs):
    r"""A helper that returns the first element in the iterable that meets
    all the traits passed in ``attrs``. This is an alternative for
    :func:`~discord.utils.find`.

    When multiple attributes are specified, they are checked using
    logical AND, not logical OR. Meaning they have to meet every
    attribute passed in and not one of them.

    To have a nested attribute search (i.e. search by ``x.y``) then
    pass in ``x__y`` as the keyword argument.

    If nothing is found that matches the attributes passed, then
    ``None`` is returned.

    Examples
    ---------

    Basic usage:

    .. code-block:: python3

        member = discord.utils.get(message.guild.members, name='Foo')

    Multiple attribute matching:

    .. code-block:: python3

        channel = discord.utils.get(guild.voice_channels, name='Foo', bitrate=64000)

    Nested attribute matching:

    .. code-block:: python3

        channel = discord.utils.get(client.get_all_channels(), guild__name='Cool', name='general')

    Parameters
    -----------
    iterable
        An iterable to search through.
    \*\*attrs
        Keyword arguments that denote attributes to search with.
    """

    # global -> local
    _all = all
    attrget = attrgetter

    # Special case the single element call
    if len(attrs) == 1:
        k, v = attrs.popitem()
        pred = attrget(k.replace('__', '.'))
        for elem in iterable:
            if pred(elem) == v:
                return elem
        return None

    converted = [
        (attrget(attr.replace('__', '.')), value)
        for attr, value in attrs.items()
    ]

    for elem in iterable:
        if _all(pred(elem) == value for pred, value in converted):
            return elem
    return None

def _unique(iterable):
    seen = set()
    adder = seen.add
    return [x for x in iterable if not (x in seen or adder(x))]

def _get_as_snowflake(data, key):
    try:
        value = data[key]
    except KeyError:
        return None
    else:
        return value and int(value)

def _get_mime_type_for_image(data):
    if data.startswith(b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A'):
        return 'image/png'
    elif data[0:3] == b'\xff\xd8\xff' or data[6:10] in (b'JFIF', b'Exif'):
        return 'image/jpeg'
    elif data.startswith((b'\x47\x49\x46\x38\x37\x61', b'\x47\x49\x46\x38\x39\x61')):
        return 'image/gif'
    elif data.startswith(b'RIFF') and data[8:12] == b'WEBP':
        return 'image/webp'
    else:
        raise InvalidArgument('Unsupported image type given')

def _bytes_to_base64_data(data):
    fmt = 'data:{mime};base64,{data}'
    mime = _get_mime_type_for_image(data)
    b64 = b64encode(data).decode('ascii')
    return fmt.format(mime=mime, data=b64)

def to_json(obj):
    return json.dumps(obj, separators=(',', ':'), ensure_ascii=True)

def _parse_ratelimit_header(request, *, use_clock=False):
    reset_after = request.headers.get('X-Ratelimit-Reset-After')
    if use_clock or not reset_after:
        utc = datetime.timezone.utc
        now = datetime.datetime.now(utc)
        reset = datetime.datetime.fromtimestamp(float(request.headers['X-Ratelimit-Reset']), utc)
        return (reset - now).total_seconds()
    else:
        return float(reset_after)

async def maybe_coroutine(f, *args, **kwargs):
    value = f(*args, **kwargs)
    if _isawaitable(value):
        return await value
    else:
        return value

async def async_all(gen, *, check=_isawaitable):
    for elem in gen:
        if check(elem):
            elem = await elem
        if not elem:
            return False
    return True

async def sane_wait_for(futures, *, timeout):
    ensured = [
        asyncio.ensure_future(fut) for fut in futures
    ]
    done, pending = await asyncio.wait(ensured, timeout=timeout, return_when=asyncio.ALL_COMPLETED)

    if len(pending) != 0:
        raise asyncio.TimeoutError()

    return done

async def sleep_until(when, result=None):
    """|coro|

    Sleep until a specified time.

    If the time supplied is in the past this function will yield instantly.

    .. versionadded:: 1.3

    Parameters
    -----------
    when: :class:`datetime.datetime`
        The timestamp in which to sleep until. If the datetime is naive then
        it is assumed to be in UTC.
    result: Any
        If provided is returned to the caller when the coroutine completes.
    """
    if when.tzinfo is None:
        when = when.replace(tzinfo=datetime.timezone.utc)
    now = datetime.datetime.now(datetime.timezone.utc)
    delta = (when - now).total_seconds()
    while delta > MAX_ASYNCIO_SECONDS:
        await asyncio.sleep(MAX_ASYNCIO_SECONDS)
        delta -= MAX_ASYNCIO_SECONDS
    return await asyncio.sleep(max(delta, 0), result)

def valid_icon_size(size):
    """Icons must be power of 2 within [16, 4096]."""
    return not size & (size - 1) and size in range(16, 4097)

class SnowflakeList(array.array):
    """Internal data storage class to efficiently store a list of snowflakes.

    This should have the following characteristics:

    - Low memory usage
    - O(n) iteration (obviously)
    - O(n log n) initial creation if data is unsorted
    - O(log n) search and indexing
    - O(n) insertion
    """

    __slots__ = ()

    def __new__(cls, data, *, is_sorted=False):
        return array.array.__new__(cls, 'Q', data if is_sorted else sorted(data))

    def add(self, element):
        i = bisect_left(self, element)
        self.insert(i, element)

    def get(self, element):
        i = bisect_left(self, element)
        return self[i] if i != len(self) and self[i] == element else None

    def has(self, element):
        i = bisect_left(self, element)
        return i != len(self) and self[i] == element

_IS_ASCII = re.compile(r'^[\x00-\x7f]+$')

def _string_width(string, *, _IS_ASCII=_IS_ASCII):
    """Returns string's width."""
    match = _IS_ASCII.match(string)
    if match:
        return match.endpos

    UNICODE_WIDE_CHAR_TYPE = 'WFA'
    func = unicodedata.east_asian_width
    return sum(2 if func(char) in UNICODE_WIDE_CHAR_TYPE else 1 for char in string)

def resolve_invite(invite):
    """
    Resolves an invite from a :class:`~discord.Invite`, URL or code.

    Parameters
    -----------
    invite: Union[:class:`~discord.Invite`, :class:`str`]
        The invite.

    Returns
    --------
    :class:`str`
        The invite code.
    """
    from .invite import Invite  # circular import
    if isinstance(invite, Invite):
        return invite.code
    else:
        rx = r'(?:https?\:\/\/)?discord(?:\.gg|(?:app)?\.com\/invite)\/(.+)'
        m = re.match(rx, invite)
        if m:
            return m.group(1)
    return invite

def resolve_template(code):
    """
    Resolves a template code from a :class:`~discord.Template`, URL or code.

    .. versionadded:: 1.4

    Parameters
    -----------
    code: Union[:class:`~discord.Template`, :class:`str`]
        The code.

    Returns
    --------
    :class:`str`
        The template code.
    """
    from .template import Template # circular import
    if isinstance(code, Template):
        return code.code
    else:
        rx = r'(?:https?\:\/\/)?discord(?:\.new|(?:app)?\.com\/template)\/(.+)'
        m = re.match(rx, code)
        if m:
            return m.group(1)
    return code

_MARKDOWN_ESCAPE_SUBREGEX = '|'.join(r'\{0}(?=([\s\S]*((?<!\{0})\{0})))'.format(c)
                                     for c in ('*', '`', '_', '~', '|'))

_MARKDOWN_ESCAPE_COMMON = r'^>(?:>>)?\s|\[.+\]\(.+\)'

_MARKDOWN_ESCAPE_REGEX = re.compile(r'(?P<markdown>%s|%s)' % (_MARKDOWN_ESCAPE_SUBREGEX, _MARKDOWN_ESCAPE_COMMON), re.MULTILINE)

_URL_REGEX = r'(?P<url><[^: >]+:\/[^ >]+>|(?:https?|steam):\/\/[^\s<]+[^<.,:;\"\'\]\s])'

_MARKDOWN_STOCK_REGEX = r'(?P<markdown>[_\\~|\*`]|%s)' % _MARKDOWN_ESCAPE_COMMON

def remove_markdown(text, *, ignore_links=True):
    """A helper function that removes markdown characters.

    .. versionadded:: 1.7
    
    .. note::
            This function is not markdown aware and may remove meaning from the original text. For example,
            if the input contains ``10 * 5`` then it will be converted into ``10  5``.
    
    Parameters
    -----------
    text: :class:`str`
        The text to remove markdown from.
    ignore_links: :class:`bool`
        Whether to leave links alone when removing markdown. For example,
        if a URL in the text contains characters such as ``_`` then it will
        be left alone. Defaults to ``True``.

    Returns
    --------
    :class:`str`
        The text with the markdown special characters removed.
    """

    def replacement(match):
        groupdict = match.groupdict()
        return groupdict.get('url', '')

    regex = _MARKDOWN_STOCK_REGEX
    if ignore_links:
        regex = '(?:%s|%s)' % (_URL_REGEX, regex)
    return re.sub(regex, replacement, text, 0, re.MULTILINE)

def escape_markdown(text, *, as_needed=False, ignore_links=True):
    r"""A helper function that escapes Discord's markdown.

    Parameters
    -----------
    text: :class:`str`
        The text to escape markdown from.
    as_needed: :class:`bool`
        Whether to escape the markdown characters as needed. This
        means that it does not escape extraneous characters if it's
        not necessary, e.g. ``**hello**`` is escaped into ``\*\*hello**``
        instead of ``\*\*hello\*\*``. Note however that this can open
        you up to some clever syntax abuse. Defaults to ``False``.
    ignore_links: :class:`bool`
        Whether to leave links alone when escaping markdown. For example,
        if a URL in the text contains characters such as ``_`` then it will
        be left alone. This option is not supported with ``as_needed``.
        Defaults to ``True``.

    Returns
    --------
    :class:`str`
        The text with the markdown special characters escaped with a slash.
    """

    if not as_needed:
        def replacement(match):
            groupdict = match.groupdict()
            is_url = groupdict.get('url')
            if is_url:
                return is_url
            return '\\' + groupdict['markdown']

        regex = _MARKDOWN_STOCK_REGEX
        if ignore_links:
            regex = '(?:%s|%s)' % (_URL_REGEX, regex)
        return re.sub(regex, replacement, text, 0, re.MULTILINE)
    else:
        text = re.sub(r'\\', r'\\\\', text)
        return _MARKDOWN_ESCAPE_REGEX.sub(r'\\\1', text)

def escape_mentions(text):
    """A helper function that escapes everyone, here, role, and user mentions.

    .. note::

        This does not include channel mentions.

    .. note::

        For more granular control over what mentions should be escaped
        within messages, refer to the :class:`~discord.AllowedMentions`
        class.

    Parameters
    -----------
    text: :class:`str`
        The text to escape mentions from.

    Returns
    --------
    :class:`str`
        The text with the mentions removed.
    """
    return re.sub(r'@(everyone|here|[!&]?[0-9]{17,20})', '@\u200b\\1', text)

class ExpiringQueue(asyncio.Queue):  # Inspired from https://github.com/NoahCardoza/CaptchaHarvester
    def __init__(self, timeout, maxsize=0):
        super().__init__(maxsize)
        self.timeout = timeout
        self.timers = asyncio.Queue()

    async def put(self, item):
        thread = Timer(self.timeout, self.expire)
        thread.start()
        await self.timers.put(thread)
        await super().put(item)

    async def get(self, block=True):
        if block:
            thread = await self.timers.get()
        else:
            thread = self.timers.get_nowait()
        thread.cancel()
        if block:
            return await super().get()
        else:
            return self.get_nowait()

    def expire(self):
        try:
            self._queue.popleft()
        except:
            pass

    def to_list(self):
        return list(self._queue)

class Browser:  # Inspired from https://github.com/NoahCardoza/CaptchaHarvester
    def __init__(self, browser=None):
        if isinstance(browser, (BrowserEnum, type(None))):
            try:
                browser = self.get_browser(browser)
            except:
                raise RuntimeError('Could not find browser. Please pass browser path manually.')

        if browser is None:
            raise RuntimeError('Could not find browser. Please pass browser path manually.')

        self.browser = browser
        self.proc = None

    def get_mac_browser(pkg, binary):
        import plistlib as plist
        pfile = f'{os.environ["HOME"]}/Library/Preferences/{pkg}.plist'
        if os.path.exists(pfile):
            with open(pfile, 'rb') as f:
                binary_path = plist.load(f).get('LastRunAppBundlePath')
            if binary_path is not None:
                return os.path.join(binary_path, 'Contents', 'MacOS', binary)

    def get_windows_browser(browser):
        import winreg as reg
        reg_path = f'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{browser}.exe'
        exe_path = None
        for install_type in reg.HKEY_CURRENT_USER, reg.HKEY_LOCAL_MACHINE:
            try:
                reg_key = reg.OpenKey(install_type, reg_path, 0, reg.KEY_READ)
                exe_path = reg.QueryValue(reg_key, None)
                reg_key.Close()
                if not os.path.isfile(exe_path):
                    continue
            except WindowsError:
                pass
            else:
                break
        return exe_path

    def get_linux_browser(browser):
        from shutil import which as exist
        possibilities = [browser + channel for channel in ('', '-beta', '-dev', '-developer', '-canary')]
        for browser in possibilities:
            if exist(browser):
                return browser

    registry = {
        'Windows': {
            'chrome': functools.partial(get_windows_browser, 'chrome'),
            'chromium': functools.partial(get_windows_browser, 'chromium'),
            'microsoft-edge': lambda: os.environ.get('ProgramFiles(x86)',
                                                     'C:\\Program Files (x86)') + '\\Microsoft\\Edge\\Application\\msedge.exe',
            'opera': functools.partial(get_windows_browser, 'opera'),
        },
        'Darwin': {
            'chrome': functools.partial(get_mac_browser, 'com.google.Chrome', 'Google Chrome'),
            'chromium': functools.partial(get_mac_browser, 'org.chromium.Chromium', 'Chromium'),
            'microsoft-edge': functools.partial(get_mac_browser, 'com.microsoft.Edge', 'Microsoft Edge'),
            'opera': functools.partial(get_mac_browser, 'com.operasoftware.Opera', 'Opera'),
        },
        'Linux': {
            'chrome': functools.partial(get_linux_browser, 'chrome'),
            'chromium': functools.partial(get_linux_browser, 'chromium'),
            'microsoft-edge': functools.partial(get_linux_browser, 'microsoft-edge'),
            'opera': functools.partial(get_linux_browser, 'opera'),
        }
    }

    def get_browser(self, browser=None):
        if browser is not None:
            return self.registry.get(platform.system())[browser.value]()

        for browser in self.registry.get(platform.system()).values():
            browser = browser()
            if browser is not None:
                return browser

    @property
    def running(self):
        try:
            return self.proc.poll() is None
        except:
            return False

    def launch(self, domain=None, server=(None, None), width=400, height=500, browser_args=[], extensions=None):
        browser_command = [self.browser, *browser_args]

        if extensions:
            browser_command.append(f'--load-extension={extensions}')

        browser_command.extend((
            '--disable-default-apps',
            '--no-default-browser-check',
            '--no-check-default-browser',
            '--no-first-run',
            '--ignore-certificate-errors',
            '--disable-background-networking',
            '--disable-component-update',
            '--disable-domain-reliability',
            f'--user-data-dir={os.path.join(tempfile.TemporaryDirectory().name, "Profiles")}',
            f'--host-rules=MAP {domain} {server[0]}:{server[1]}',
            f'--window-size={width},{height}',
            f'--app=https://{domain}'
        ))

        self.proc = subprocess.Popen(browser_command, stdout=-1, stderr=-1)

    def stop(self):
        try:
            self.proc.terminate()
        except:
            pass

async def _get_build_number(session): # Thank you Discord-S.C.U.M
    """Fetches client build number"""
    try:
        login_page_request = await session.request('GET', 'https://discord.com/login', headers={'Accept-Encoding': 'gzip, deflate'}, timeout=10)
        login_page = await login_page_request.text()
        build_url = 'https://discord.com/assets/' + re.compile(r'assets/+([a-z0-9]+)\.js').findall(login_page)[-2] + '.js'
        build_request = await session.request('GET', build_url, headers={'Accept-Encoding': 'gzip, deflate'}, timeout=10)
        build_file = await build_request.text()
        build_index = build_file.find('buildNumber') + 14
        return int(build_file[build_index:build_index + 5])
    except:
        log.warning('Could not fetch client build number.')
        return 88863

async def _get_user_agent(session):
    """Fetches the latest Windows 10/Chrome user-agent."""
    try:
        request = await session.request('GET', 'https://jnrbsn.github.io/user-agents/user-agents.json', timeout=10)
        response = json.loads(await request.text())
        return response[0]
    except:
        log.warning('Could not fetch user-agent.')
        return 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36'

async def _get_browser_version(session):
    """Fetches the latest Windows 10/Chrome version."""
    try:
        request = await session.request('GET', 'https://omahaproxy.appspot.com/all.json', timeout=10)
        response = json.loads(await request.text())
        if response[0]['versions'][4]['channel'] == 'stable':
            return response[0]['versions'][4]['version']
        raise RuntimeError
    except:
        log.warning('Could not fetch browser version.')
        return '91.0.4472.77'

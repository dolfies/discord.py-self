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

import asyncio
from base64 import b64encode
import json
import logging
from random import getrandbits

import aiohttp

from discord.context_properties import ContextProperties
from discord.errors import HTTPException, Forbidden, NotFound, LoginFailure, DiscordServerError
from discord.gateway import DiscordClientWebSocketResponse
from discord.http import json_or_text
from discord import utils

log = logging.getLogger(__name__)

class AuthClient:
    """Represents an HTTP client sending HTTP requests to the Discord authentication API."""

    BASE = 'https://discord.com/api/v9' # Using older versions of the auth APIs is a big nono

    def __init__(self, connector=None, *, proxy=None, proxy_auth=None, loop=None, unsync_clock=True, captcha_handler=None):
        self.connector = connector
        self.loop = asyncio.get_event_loop() if loop is None else loop
        self.session = None
        self.proxy = proxy
        self.proxy_auth = proxy_auth
        self.captcha_handler = captcha_handler
        self.use_clock = not unsync_clock
        self._started = False

        self.token = None
        self.fingerprint = None

    async def startup(self):
        self._started = True
        self.session = aiohttp.ClientSession(connector=self.connector, ws_response_class=DiscordClientWebSocketResponse)
        self.user_agent = await utils._get_user_agent(self.session)
        self.client_build_number = await utils._get_build_number(self.session)
        self.browser_version = await utils._get_browser_version(self.session)
        self.super_properties = {
            'os': 'Windows',
            'browser': 'Chrome',
            'device': '',
            'browser_user_agent': self.user_agent,
            'browser_version': self.browser_version,
            'os_version': '10',
            'referrer': '',
            'referring_domain': '',
            'referrer_current': '',
            'referring_domain_current': '',
            'release_channel': 'stable',
            'system_locale': 'en-US',
            'client_build_number': self.client_build_number,
            'client_event_source': None
        }
        self.encoded_super_properties = b64encode(json.dumps(self.super_properties).encode()).decode('utf-8')

    async def ws_connect(self, url, *, compress=0, host=None):
        websocket_key = b64encode(bytes(getrandbits(8) for _ in range(16))).decode() # Thank you Discord-S.C.U.M
        if not host:
            host = url[6:].split('?')[0].rstrip('/') # Removes the 'wss://' and the query params
        kwargs = {
            'proxy_auth': self.proxy_auth,
            'proxy': self.proxy,
            'max_msg_size': 0,
            'timeout': 30.0,
            'autoclose': False,
            'headers': {
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US',
                'Cache-Control': 'no-cache',
                'Connection': 'Upgrade',
                'Host': host,
                'Origin': 'https://discord.com',
                'Pragma': 'no-cache',
                'Sec-WebSocket-Extensions': 'permessage-deflate; client_max_window_bits',
                'Sec-WebSocket-Key': websocket_key,
                'Sec-WebSocket-Version': '13',
                'Upgrade': 'websocket',
                'User-Agent': self.user_agent,
            },
            'compress': compress
        }

        return await self.session.ws_connect(url, **kwargs)

    async def request(self, verb, url, **kwargs):
        if not self._started:
            await self.startup()

        if not self.session:
            self.session = aiohttp.ClientSession(connector=self.connector, ws_response_class=DiscordClientWebSocketResponse)

        method = verb
        url = (self.BASE + url)

        # header creation
        headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Origin': 'https://discord.com',
            'Pragma': 'no-cache',
            'Referer': 'https://discord.com',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': self.user_agent,
            'X-Super-Properties': self.encoded_super_properties
        }

        if kwargs.pop('auth', False):
            headers['Authorization'] = self.token or 'undefined'

        if kwargs.pop('fingerprint', False):
            if self.fingerprint is None:
                # This shouldn't ever happen...
                raise AttributeError('Fingerprint cannot be found')
            headers['X-Fingerprint'] = self.fingerprint

        # some checking if it's a JSON request
        if 'json' in kwargs:
            headers['Content-Type'] = 'application/json'
            kwargs['data'] = utils.to_json(kwargs.pop('json'))

        if 'context_properties' in kwargs:
            context_properties = kwargs.pop('context_properties')
            if isinstance(context_properties, ContextProperties):
                headers['X-Context-Properties'] = context_properties.value

        if 'referer' in kwargs:
            headers['Referer'] = kwargs.pop('referer')

        if kwargs.pop('super_properties_to_track', False):
            headers['X-Track'] = headers.pop('X-Super-Properties')

        kwargs['headers'] = headers

        # Proxy support
        if self.proxy is not None:
            kwargs['proxy'] = self.proxy
        if self.proxy_auth is not None:
            kwargs['proxy_auth'] = self.proxy_auth

        for tries in range(5):
            try:
                async with self.session.request(method, url, **kwargs) as r:
                    log.debug('%s %s with %s has returned %s', method, url, kwargs.get('data'), r.status)

                    # even errors have text involved in them so this is safe to call
                    data = await json_or_text(r)

                    # check if we have rate limit header information
                    remaining = r.headers.get('X-Ratelimit-Remaining')
                    if remaining == '0' and r.status != 429:
                        delta = utils._parse_ratelimit_header(r, use_clock=self.use_clock)
                        log.debug('Auth ratelimit has been hit (retry: %s).', delta)
                        await asyncio.sleep(delta)

                    # the request was successful so just return the text/json
                    if 300 > r.status >= 200:
                        log.debug('%s %s has received %s', method, url, data)
                        return data

                    # we are being rate limited
                    if r.status == 429:
                        if not r.headers.get('Via'):
                            # Banned by Cloudflare more than likely.
                            raise HTTPException(r, data)

                        retry_after = data['retry_after'] / 1000.0
                        log.warning('We are being rate limited. Retrying in %.2f seconds. Handled under the bucket "$ACCOUNTS"', retry_after)
                        await asyncio.sleep(retry_after)
                        continue

                    # we've received a 500 or 502, unconditional retry
                    if r.status in {500, 502}:
                        await asyncio.sleep(1 + tries * 2)
                        continue

                    # the usual error cases
                    if r.status == 403:
                        raise Forbidden(r, data)
                    elif r.status == 404:
                        raise NotFound(r, data)
                    elif r.status == 503:
                        raise DiscordServerError(r, data)
                    else:
                        raise HTTPException(r, data)

            # This is handling exceptions from the request
            except OSError as e:
                # Connection reset by peer
                if tries < 4 and e.errno in (54, 10054):
                    continue
                raise

        # We've run out of retries, raise
        if r.status >= 500:
            raise DiscordServerError(r, data)

        raise HTTPException(r, data)

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

    # API wraps

    async def get_fingerprint(self, *, mode, referer=None):
        self.token = None
        if mode == 0: # Home page
            data = await self.request('GET', '/experiments', super_properties_to_track=True)
        elif mode == 1: # Accept invite page
            context_properties = ContextProperties._from_accept_invite_page_blank()
            data = await self.request('GET', '/experiments', auth=True, context_properties=context_properties, referer=referer)
        elif mode == 2: # Register page
            do_stuff()
        elif mode == 3: # Login page
            referer = 'https://discord.com/login'
            context_properties = ContextProperties._from_login()
            data = await self.request('GET', '/experiments', auth=True, context_properties=context_properties, referer=referer)
        elif mode == -1: # Currently unused, still works
            data = await self.request('POST', '/auth/fingerprint')

        self.fingerprint = fingerprint = data['fingerprint']
        return fingerprint

    async def static_login(self, token):
        old_token, self.token = self.token, token
        try:
            data = await self.request('GET', '/users/@me', auth=True, referer='https://discord.com/channels/@me')
        except HTTPException as exc:
            self.token = old_token
            if exc.response.status == 401:
                raise LoginFailure('Improper token has been passed.') from exc
            raise
        else:
            return data

    def get_invite(self, invite_id):
        params = {
            'with_counts': 'true',
            'with_expiration': 'true'
        }
        return self.request('GET', f'/invites/{invite_id}', auth=True, fingerprint=True,
                            referer=f'https://discord.com/invite/{invite_id}', params=params)

    async def register_from_invite(self, invite_id, username, *, captcha_handler=None):
        # Prepare environment
        referer = f'https://discord.com/invite/{invite_id}'
        fingerprint = await self.get_fingerprint(mode=1, referer=referer)

        # Get the invite (useless to us atm)
        await self.get_invite(invite_id)

        # Construct the payload (captcha_key may be required later)
        payload = {
            'captcha_key': None,
            'consent': True,
            'fingerprint': fingerprint,
            'gift_code_sku_id': None,
            'invite': invite_id,
            'username': username
        }

        for _ in range(5):
            try:
                data = await self.request('POST', '/auth/register', auth=True, fingerprint=True, referer=referer, json=payload)
                if token := data.get('token'):
                    log.info("Created %s", token)
                    return token

            except HTTPException as exc:
                if exc.response.status == 400:
                    if captcha_error := exc.json.get('captcha_key'):
                        if captcha_handler is None:  # No captcha handler ¯\_(ツ)_/¯
                            raise LoginFailure('Captcha required.') from exc

                        captcha_sitekey = exc.json.get('captcha_sitekey')
                        captcha_service = exc.json.get('captcha_service')
                        if any(item in captcha_error for item in ('incorrect-captcha', 'response-already-used', 'captcha-required')):
                            payload['captcha_key'] = await captcha_handler(captcha_service=captcha_service, captcha_sitekey=captcha_sitekey)

                    elif exc.code == 50035:
                        raise LoginFailure('Too many users have this username, please try another.') from exc
                    else:
                        raise

    async def register(self):
        ...

    async def login(self, email, password, *, undelete=False):
        # Prepare environment
        referer = 'https://discord.com/login'
        captcha_handler = self.captcha_handler
        await self.get_fingerprint(mode=0)

        # Get experiments (useless to us atm)
        context_properties = ContextProperties._from_login()
        await self.request('GET', '/experiments', auth=True, fingerprint=True,
                           referer=referer, context_properties=context_properties)

        # Construct the payload (captcha_key may be required later)
        payload = {
            'captcha_key': None,
            'gift_code_sku_id': None,
            'login': email,
            'login_source': None,
            'password': password,
            'undelete': undelete
        }

        # Try 1 (without captcha)
        try:
            data = await self.request('POST', '/auth/login', auth=True, fingerprint=True,
                                      referer=referer, json=payload)
        except HTTPException as exc:
            if exc.response.status == 400:
                if exc.code == 50035:
                    raise LoginFailure('Improper email/password has been passed.') from exc
                elif something:
                    if captcha_handler is None:  # No captcha handler ¯\_(ツ)_/¯
                        raise LoginFailure('Captcha required.') from exc
                    payload['captcha_key'] = await captcha_handler(something, session=self.session)
                else:
                    raise
            else:
                raise
        else:
            self.token = token = data['token']
            return token

        # Try 2 (with captcha)
        try:
            data = await self.request('POST', '/auth/login', auth=True, fingerprint=True,
                                      referer=referer, json=payload)
        except HTTPException as exc:
            if exc.response.status == 400:
                if exc.code == 50035:
                    raise LoginFailure('Improper email/password has been passed.') from exc
            raise exc
        else:
            self.token = token = data['token']
            return token

    def logout(self):
        payload = { # Not sure what these are
            'provider': None,
            'voip_provider': None
        }
        return self.request('POST', '/auth/logout', auth=True,
                            referer='https://discord.com/channels/@me', json=payload)

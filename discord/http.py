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

import asyncio
import json
import logging
import weakref
from base64 import b64encode
from datetime import datetime
from random import choice, getrandbits
from urllib.parse import quote as _uriquote

import aiohttp

from . import utils
from .context_properties import ContextProperties
from .enums import RelationshipAction
from .errors import HTTPException, Forbidden, NotFound, AuthFailure, DiscordServerError
from . import utils

log = logging.getLogger(__name__)

# For some reason, the Discord voice websocket expects this header to be
# completely lowercase while aiohttp respects spec and does it as case-insensitive
aiohttp.hdrs.WEBSOCKET = 'websocket'

async def json_or_text(response):
    text = await response.text(encoding='utf-8')
    try:
        if response.headers['content-type'] == 'application/json':
            return json.loads(text)
    except KeyError:
        # Thanks Cloudflare
        pass

    return text

class Route:
    BASE = 'https://discord.com/api/v7'

    def __init__(self, method, path, *, base=None, **parameters):
        self.path = path
        self.method = method
        base = base or self.BASE
        url = (base + self.path)
        if parameters:
            self.url = url.format(**{k: _uriquote(v) if isinstance(v, str) else v for k, v in parameters.items()})
        else:
            self.url = url

        # major parameters:
        self.channel_id = parameters.get('channel_id')
        self.guild_id = parameters.get('guild_id')

    @property
    def bucket(self):
        # the bucket is just method + path w/ major parameters
        return '{0.channel_id}:{0.guild_id}:{0.path}'.format(self)

class MaybeUnlock:
    def __init__(self, lock):
        self.lock = lock
        self._unlock = True

    def __enter__(self):
        return self

    def defer(self):
        self._unlock = False

    def __exit__(self, type, value, traceback):
        if self._unlock:
            self.lock.release()

class _FakeResponse:
    def __init__(self, reason, status):
        self.reason = reason
        self.status = status

class HTTPClient:
    """Represents an HTTP client sending HTTP requests to the Discord API."""

    def __init__(self, connector=None, *, proxy=None, proxy_auth=None, loop=None, unsync_clock=True):
        self.loop = asyncio.get_event_loop() if loop is None else loop
        self.connector = connector
        self.__session = None
        self._locks = weakref.WeakValueDictionary()
        self._global_over = asyncio.Event()
        self._global_over.set()
        self.token = None
        self.proxy = proxy
        self.proxy_auth = proxy_auth
        self.use_clock = not unsync_clock

        self.user_agent = None
        self.super_properties = {}
        self.encoded_super_properties = None
        self._started = False

    def __del__(self):
        session = self.__session
        if session:
            try:
                session.connector._close()
            except AttributeError:
                pass

    def recreate(self):
        if self.__session.closed:
            self.__session = aiohttp.ClientSession(connector=self.connector)

    async def startup(self):
        if self._started:
            return
        self.__session = aiohttp.ClientSession(connector=self.connector)
        self.user_agent = ua = await utils._get_user_agent(self.__session)
        self.client_build_number = bn = await utils._get_build_number(self.__session)
        self.browser_version = bv = await utils._get_browser_version(self.__session)
        log.info('Found user agent %s (%s), build number %s.', ua, bv, bn)
        self.super_properties = super_properties = {
            'os': 'Windows',
            'browser': 'Chrome',
            'device': '',
            'browser_user_agent': ua,
            'browser_version': bv,
            'os_version': '10',
            'referrer': '',
            'referring_domain': '',
            'referrer_current': '',
            'referring_domain_current': '',
            'release_channel': 'stable',
            'system_locale': 'en-US',
            'client_build_number': bn,
            'client_event_source': None
        }
        self.encoded_super_properties = b64encode(json.dumps(self.super_properties).encode()).decode('utf-8')
        self._started = True

    async def ws_connect(self, url, *, compress=0, host=None):
        websocket_key = b64encode(bytes(getrandbits(8) for _ in range(16))).decode()  # Thank you Discord-S.C.U.M
        if not host:
            host = url[6:].split('?')[0].rstrip('/')  # Removes the 'wss://' and the query params
        kwargs = {
            'proxy_auth': self.proxy_auth,
            'proxy': self.proxy,
            'max_msg_size': 0,
            'timeout': 30.0,
            'autoclose': False,
            'headers': {
                'Accept-Encoding': 'gzip, deflate',
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
                'User-Agent': self.user_agent
            },
            'compress': compress
        }

        return await self.__session.ws_connect(url, **kwargs)

    async def request(self, route, *, files=None, form=None, **kwargs):
        bucket = route.bucket
        method = route.method
        url = route.url

        lock = self._locks.get(bucket)
        if lock is None:
            lock = asyncio.Lock()
            if bucket is not None:
                self._locks[bucket] = lock

        # Header creation
        headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Origin': 'https://discord.com',
            'Pragma': 'no-cache',
            'Referer': 'https://discord.com/channels/@me',
            'Sec-CH-UA': '"Google Chrome";v="{0}", "Chromium";v="{0}", ";Not A Brand";v="99"'.format(self.browser_version.split('.')[0]),
            'Sec-CH-UA-Mobile': '?0',
            'Sec-CH-UA-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': self.user_agent,
            'X-Debug-Options': 'bugReporterEnabled',
            'X-Super-Properties': self.encoded_super_properties
        }

        if self.token is not None:
            headers['Authorization'] = self.token

        reason = kwargs.pop('reason', None)
        if reason:
            headers['X-Audit-Log-Reason'] = _uriquote(reason)

        # Header modification
        if 'json' in kwargs:
            headers['Content-Type'] = 'application/json'
            kwargs['data'] = utils.to_json(kwargs.pop('json'))

        if 'context_properties' in kwargs:
            context_properties = kwargs.pop('context_properties')
            if isinstance(context_properties, ContextProperties):
                headers['X-Context-Properties'] = context_properties.value

        if kwargs.pop('super_properties_to_track', False):
            headers['X-Track'] = headers.pop('X-Super-Properties')

        kwargs['headers'] = headers

        # Proxy support
        if self.proxy is not None:
            kwargs['proxy'] = self.proxy
        if self.proxy_auth is not None:
            kwargs['proxy_auth'] = self.proxy_auth

        if not self._global_over.is_set():
            # wait until the global lock is complete
            await self._global_over.wait()

        await lock.acquire()
        with MaybeUnlock(lock) as maybe_lock:
            for tries in range(5):
                if files:
                    for f in files:
                        f.reset(seek=tries)

                if form:
                    form_data = aiohttp.FormData()
                    for params in form:
                        form_data.add_field(**params)
                    kwargs['data'] = form_data

                try:
                    async with self.__session.request(method, url, **kwargs) as r:
                        log.debug('%s %s with %s has returned %s', method, url, kwargs.get('data'), r.status)

                        data = await json_or_text(r)

                        # Check if we have rate limit information
                        remaining = r.headers.get('X-Ratelimit-Remaining')
                        if remaining == '0' and r.status != 429:
                            # We've depleted our current bucket
                            delta = utils._parse_ratelimit_header(r, use_clock=self.use_clock)
                            log.debug('A rate limit bucket has been exhausted (bucket: %s, retry: %s).', bucket, delta)
                            maybe_lock.defer()
                            self.loop.call_later(delta, lock.release)

                        # Request was successful so just return the text/json
                        if 300 > r.status >= 200:
                            log.debug('%s %s has received %s', method, url, data)
                            return data

                        # Rate limited
                        if r.status == 429:
                            if not r.headers.get('Via'):
                                # Banned by Cloudflare more than likely
                                raise HTTPException(r, data)

                            fmt = 'We are being rate limited. Retrying in %.2f seconds. Handled under the bucket "%s".'

                            # Sleep a bit
                            retry_after = data['retry_after'] / 1000.0
                            log.warning(fmt, retry_after, bucket)

                            # Check if it's a global rate limit
                            is_global = data.get('global', False)
                            if is_global:
                                log.warning('Global rate limit has been hit. Retrying in %.2f seconds.', retry_after)
                                self._global_over.clear()

                            await asyncio.sleep(retry_after)
                            log.debug('Done sleeping for the rate limit. Retrying...')

                            # Release the global lock now that the rate limit passed
                            if is_global:
                                self._global_over.set()
                                log.debug('Global rate limit is now over.')

                            continue

                        # Unconditional retry
                        if r.status in {500, 502}:
                            await asyncio.sleep(1 + tries * 2)
                            continue

                        # Usual error cases
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

            # We've run out of retries, raise.
            if r.status >= 500:
                raise DiscordServerError(r, data)

            raise HTTPException(r, data)

    async def get_from_cdn(self, url):
        async with self.__session.get(url) as resp:
            if resp.status == 200:
                return await resp.read()
            elif resp.status == 404:
                raise NotFound(resp, 'asset not found')
            elif resp.status == 403:
                raise Forbidden(resp, 'cannot retrieve asset')
            else:
                raise HTTPException(resp, 'failed to get asset')

    # State management

    async def close(self):
        if self.__session:
            await self.__session.close()

    def _token(self, token):
        self.token = token
        self._ack_token = None

    # Login management

    async def static_login(self, token):
        old_token = self.token
        self._token(token)

        await self.startup()

        params = {
            'with_analytics_token': 'true'
        }
        try:
            data = await self.get_me()
        except HTTPException as exc:
            self._token(old_token)
            if exc.response.status == 401:
                raise AuthFailure('Improper token has been passed') from exc
            raise

        return data

    # Group functionality

    def get_me(self):
        params = {
            'with_analytics_token': 'true'
        }
        return self.request(Route('GET', '/users/@me'), params=params)

    def start_group(self, recipients):
        payload = {
            'recipients': recipients
        }
        context_properties = ContextProperties._from_new_group_dm()  # New Group DM button

        return self.request(Route('POST', '/users/@me/channels'), json=payload, context_properties=context_properties)

    def leave_group(self, channel_id):
        return self.request(Route('DELETE', '/channels/{channel_id}', channel_id=channel_id))

    def add_group_recipient(self, channel_id, user_id):
        r = Route('PUT', '/channels/{channel_id}/recipients/{user_id}', channel_id=channel_id, user_id=user_id)
        return self.request(r)

    def remove_group_recipient(self, channel_id, user_id):
        r = Route('DELETE', '/channels/{channel_id}/recipients/{user_id}', channel_id=channel_id, user_id=user_id)
        return self.request(r)

    def edit_group(self, channel_id, **options):
        valid_keys = ('name', 'icon')
        payload = {
            k: v for k, v in options.items() if k in valid_keys
        }

        return self.request(Route('PATCH', '/channels/{channel_id}', channel_id=channel_id), json=payload)

    # Message management

    def start_private_message(self, recipient):
        payload = {
            'recipients': [recipient]
        }
        context_properties = ContextProperties._empty() # {}

        return self.request(Route('POST', '/users/@me/channels'), json=payload, context_properties=context_properties)

    def send_message(self, channel_id, content, *, tts=False, embed=None, nonce=0, allowed_mentions=None, message_reference=None):
        r = Route('POST', '/channels/{channel_id}/messages', channel_id=channel_id)
        payload = {'tts': tts}

        if content:
            payload['content'] = content

        if embed:
            payload['embed'] = embed

        if nonce:
            payload['nonce'] = nonce
        elif nonce is not None:
            payload['nonce'] = utils.time_snowflake(datetime.utcnow())

        if allowed_mentions:
            payload['allowed_mentions'] = allowed_mentions

        if message_reference:
            payload['message_reference'] = message_reference

        return self.request(r, json=payload)
    
    def send_interaction(self, application_id, message, data, interaction_type:int):
        r = Route('POST', '/interactions')
        payload = {
            'application_id': str(application_id),
            'channel_id': str(message.channel.id),
            'data': data,
            'guild_id': str(message.guild.id),
            'message_id': str(message.id),
            'message_flags': message.flags.value,
            'nonce': utils.time_snowflake(datetime.utcnow()),
            'type': interaction_type
        }
        return self.request(r, json=payload)

    def send_typing(self, channel_id):
        return self.request(Route('POST', '/channels/{channel_id}/typing', channel_id=channel_id))

    def send_files(self, channel_id, *, files, content=None, tts=False, embed=None, nonce=0, allowed_mentions=None, message_reference=None):
        r = Route('POST', '/channels/{channel_id}/messages', channel_id=channel_id)
        form = []
        payload = {'tts': tts}

        if content:
            payload['content'] = content

        if embed:
            payload['embed'] = embed

        if nonce:
            payload['nonce'] = nonce
        elif nonce is not None:
            payload['nonce'] = utils.time_snowflake(datetime.utcnow())

        if allowed_mentions:
            payload['allowed_mentions'] = allowed_mentions

        if message_reference:
            payload['message_reference'] = message_reference

        form.append({'name': 'payload_json', 'value': utils.to_json(payload)})
        if len(files) == 1:
            file = files[0]
            form.append({
                'name': 'file',
                'value': file.fp,
                'filename': file.filename,
                'content_type': 'application/octet-stream'
            })
        else:
            for index, file in enumerate(files):
                form.append({
                    'name': 'file%s' % index,
                    'value': file.fp,
                    'filename': file.filename,
                    'content_type': 'application/octet-stream'
                })

        return self.request(r, form=form, files=files)

    async def ack_message(self, channel_id, message_id):
        r = Route('POST', '/channels/{channel_id}/messages/{message_id}/ack', channel_id=channel_id, message_id=message_id)
        data = await self.request(r, json={'token': self._ack_token})
        self._ack_token = data['token']

    def ack_messages(self, read_states):
        payload = {
            'read_states': read_states
        }

        return self.request(Route('POST', '/read-states/ack-bulk'), json=payload)

    def unack_message(self, channel_id, message_id, *, mention_count=0):
        r = Route('POST', '/channels/{channel_id}/messages/{message_id}/ack', channel_id=channel_id, message_id=message_id)
        payload = {
            'manual': True,
            'mention_count': mention_count
        }

        return self.request(r, json=payload)

    def ack_guild(self, guild_id):
        return self.request(Route('POST', '/guilds/{guild_id}/ack', guild_id=guild_id))

    def delete_message(self, channel_id, message_id):
        r = Route('DELETE', '/channels/{channel_id}/messages/{message_id}', channel_id=channel_id, message_id=message_id)
        return self.request(r)

    def edit_message(self, channel_id, message_id, **fields):
        r = Route('PATCH', '/channels/{channel_id}/messages/{message_id}', channel_id=channel_id, message_id=message_id)
        return self.request(r, json=fields)

    def add_reaction(self, channel_id, message_id, emoji):
        r = Route('PUT', '/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/@me',
                  channel_id=channel_id, message_id=message_id, emoji=emoji)
        return self.request(r)

    def remove_reaction(self, channel_id, message_id, emoji, member_id):
        r = Route('DELETE', '/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/{member_id}',
                  channel_id=channel_id, message_id=message_id, member_id=member_id, emoji=emoji)
        return self.request(r)

    def remove_own_reaction(self, channel_id, message_id, emoji):
        r = Route('DELETE', '/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/@me',
                  channel_id=channel_id, message_id=message_id, emoji=emoji)
        return self.request(r)

    def get_reaction_users(self, channel_id, message_id, emoji, limit, after=None):
        r = Route('GET', '/channels/{channel_id}/messages/{message_id}/reactions/{emoji}',
                  channel_id=channel_id, message_id=message_id, emoji=emoji)
        params = {
            'limit': limit
        }
        if after:
            params['after'] = after

        return self.request(r, params=params)

    def clear_reactions(self, channel_id, message_id):
        r = Route('DELETE', '/channels/{channel_id}/messages/{message_id}/reactions',
                  channel_id=channel_id, message_id=message_id)

        return self.request(r)

    def clear_single_reaction(self, channel_id, message_id, emoji):
        r = Route('DELETE', '/channels/{channel_id}/messages/{message_id}/reactions/{emoji}',
                   channel_id=channel_id, message_id=message_id, emoji=emoji)
        return self.request(r)

    async def get_message(self, channel_id, message_id):
        data = await self.logs_from(channel_id, 1, around=message_id)
        try:
            msg = data[0]
        except IndexError:
            raise NotFound(_FakeResponse('Not Found', 404), 'message not found')

        if int(msg.get('id')) == message_id:
            return msg
        raise NotFound(_FakeResponse('Not Found', 404), 'message not found')

    def get_private_channels(self):
        return self.request(Route('GET', '/users/@me/channels'))

    def get_channel(self, channel_id):
        return self.request(Route('GET', '/channels/{channel_id}', channel_id=channel_id))

    def logs_from(self, channel_id, limit, before=None, after=None, around=None):
        params = {
            'limit': limit
        }
        if before is not None:
            params['before'] = before
        if after is not None:
            params['after'] = after
        if around is not None:
            params['around'] = around

        return self.request(Route('GET', '/channels/{channel_id}/messages', channel_id=channel_id), params=params)

    def publish_message(self, channel_id, message_id):
        return self.request(Route('POST', '/channels/{channel_id}/messages/{message_id}/crosspost',
                                  channel_id=channel_id, message_id=message_id))

    def pin_message(self, channel_id, message_id):
        return self.request(Route('PUT', '/channels/{channel_id}/pins/{message_id}',
                                  channel_id=channel_id, message_id=message_id))

    def unpin_message(self, channel_id, message_id):
        return self.request(Route('DELETE', '/channels/{channel_id}/pins/{message_id}',
                                  channel_id=channel_id, message_id=message_id))

    def pins_from(self, channel_id):
        return self.request(Route('GET', '/channels/{channel_id}/pins', channel_id=channel_id))

    # Member management

    def kick(self, guild_id, user_id, reason=None):
        return self.request(Route('DELETE', '/guilds/{guild_id}/members/{user_id}', guild_id=guild_id, user_id=user_id), reason=reason)

    def ban(self, guild_id, user_id, delete_message_days=1, reason=None):
        r = Route('PUT', '/guilds/{guild_id}/bans/{user_id}', guild_id=guild_id, user_id=user_id)
        payload = {
            'delete_message_days': str(delete_message_days),
        }

        return self.request(r, json=payload, reason=reason)

    def unban(self, guild_id, user_id):
        r = Route('DELETE', '/guilds/{guild_id}/bans/{user_id}', guild_id=guild_id, user_id=user_id)
        return self.request(r)

    def guild_voice_state(self, user_id, guild_id, *, mute=None, deafen=None):
        r = Route('PATCH', '/guilds/{guild_id}/members/{user_id}', guild_id=guild_id, user_id=user_id)
        payload = {}
        if mute is not None:
            payload['mute'] = mute

        if deafen is not None:
            payload['deaf'] = deafen

        return self.request(r, json=payload)

    def edit_profile(self, **fields):
        return self.request(Route('PATCH', '/users/@me'), json=fields)

    def change_my_nickname(self, guild_id, nickname):
        r = choice((
            Route('PATCH', '/guilds/{guild_id}/members/@me/nick', guild_id=guild_id),
            Route('PATCH', '/guilds/{guild_id}/members/@me', guild_id=guild_id)
        ))
        payload = {
            'nick': nickname
        }

        return self.request(r, json=payload)

    def change_nickname(self, guild_id, user_id, nickname):
        r = Route('PATCH', '/guilds/{guild_id}/members/{user_id}', guild_id=guild_id, user_id=user_id)
        payload = {
            'nick': nickname
        }

        return self.request(r, json=payload)

    def edit_my_voice_state(self, guild_id, payload):
        r = Route('PATCH', '/guilds/{guild_id}/voice-states/@me', guild_id=guild_id)
        return self.request(r, json=payload)

    def edit_voice_state(self, guild_id, user_id, payload):
        r = Route('PATCH', '/guilds/{guild_id}/voice-states/{user_id}', guild_id=guild_id, user_id=user_id)
        return self.request(r, json=payload)

    def edit_member(self, guild_id, user_id, **fields):
        r = Route('PATCH', '/guilds/{guild_id}/members/{user_id}', guild_id=guild_id, user_id=user_id)
        return self.request(r, json=fields)

    # Channel management

    def edit_channel(self, channel_id, **options):
        r = Route('PATCH', '/channels/{channel_id}', channel_id=channel_id)
        valid_keys = ('name', 'parent_id', 'topic', 'bitrate', 'nsfw',
                      'user_limit', 'position', 'permission_overwrites', 'rate_limit_per_user',
                      'type', 'rtc_region')
        payload = {
            k: v for k, v in options.items() if k in valid_keys
        }

        return self.request(r, json=payload)

    def bulk_channel_update(self, guild_id, data):
        r = Route('PATCH', '/guilds/{guild_id}/channels', guild_id=guild_id)
        return self.request(r, json=data)

    def create_channel(self, guild_id, channel_type, **options):
        payload = {
            'type': channel_type
        }

        valid_keys = ('name', 'parent_id', 'topic', 'bitrate', 'nsfw',
                      'user_limit', 'position', 'permission_overwrites', 'rate_limit_per_user',
                      'rtc_region')
        payload.update({
            k: v for k, v in options.items() if k in valid_keys and v is not None
        })

        return self.request(Route('POST', '/guilds/{guild_id}/channels', guild_id=guild_id), json=payload)

    def delete_channel(self, channel_id):
        return self.request(Route('DELETE', '/channels/{channel_id}', channel_id=channel_id))

    # Webhook management

    def create_webhook(self, channel_id, *, name, avatar=None):
        payload = {
            'name': name
        }
        if avatar is not None:
            payload['avatar'] = avatar

        r = Route('POST', '/channels/{channel_id}/webhooks', channel_id=channel_id)
        return self.request(r, json=payload)

    def channel_webhooks(self, channel_id):
        return self.request(Route('GET', '/channels/{channel_id}/webhooks', channel_id=channel_id))

    def guild_webhooks(self, guild_id):
        return self.request(Route('GET', '/guilds/{guild_id}/webhooks', guild_id=guild_id))

    def get_webhook(self, webhook_id):
        return self.request(Route('GET', '/webhooks/{webhook_id}', webhook_id=webhook_id))

    def follow_webhook(self, channel_id, webhook_channel_id):
        payload = {
            'webhook_channel_id': str(webhook_channel_id)
        }
        return self.request(Route('POST', '/channels/{channel_id}/followers', channel_id=channel_id), json=payload)

    # Guild management

    def get_guilds(self, *, with_counts=True):
        params = {
            'with_counts': str(with_counts).lower()
        }

        return self.request(Route('GET', '/users/@me/guilds'), params=params, super_properties_to_track=True)

    def join_guild(self, invite_id, *, guild_id, channel_id, channel_type, message_id=None):
        if message_id:
            context_properties = ContextProperties._from_invite_embed(guild_id=guild_id, channel_id=channel_id, channel_type=channel_type, message_id=message_id)  # Invite Button Embed
        else:
            context_properties = choice((  # Join Guild, Accept Invite Page
                ContextProperties._from_accept_invite_page(guild_id=guild_id, channel_id=channel_id, channel_type=channel_type),
                ContextProperties._from_join_guild_popup(guild_id=guild_id, channel_id=channel_id, channel_type=channel_type)
            ))
        return self.request(Route('POST', '/invites/{invite_id}', invite_id=invite_id), context_properties=context_properties, json={})

    def leave_guild(self, guild_id):
        return self.request(Route('DELETE', '/users/@me/guilds/{guild_id}', guild_id=guild_id))

    def get_guild(self, guild_id):
        return self.request(Route('GET', '/guilds/{guild_id}', guild_id=guild_id))

    def delete_guild(self, guild_id):
        return self.request(Route('DELETE', '/guilds/{guild_id}', guild_id=guild_id))

    def create_guild(self, name, icon, *, template='2TffvPucqHkN'):
        payload = {
            'name': name,
            'icon': icon,
            'system_channel_id': None,
            'channels': [],
            'guild_template_code': template  # API go brrr
        }

        return self.request(Route('POST', '/guilds'), json=payload)

    def edit_guild(self, guild_id, **fields):
        valid_keys = ('name', 'region', 'icon', 'afk_timeout', 'owner_id',
                      'afk_channel_id', 'splash', 'verification_level',
                      'system_channel_id', 'default_message_notifications',
                      'description', 'explicit_content_filter', 'banner',
                      'system_channel_flags', 'rules_channel_id',
                      'public_updates_channel_id', 'preferred_locale', 'features')
        payload = {
            k: v for k, v in fields.items() if k in valid_keys
        }

        return self.request(Route('PATCH', '/guilds/{guild_id}', guild_id=guild_id), json=payload)

    def edit_guild_settings(self, guild_id, **fields):
        return self.request(Route('PATCH', '/users/@me/guilds/{guild_id}/settings', guild_id=guild_id), json=fields)

    def get_template(self, code):
        return self.request(Route('GET', '/guilds/templates/{code}', code=code))

    def guild_templates(self, guild_id):
        return self.request(Route('GET', '/guilds/{guild_id}/templates', guild_id=guild_id))

    def create_template(self, guild_id, payload):
        return self.request(Route('POST', '/guilds/{guild_id}/templates', guild_id=guild_id), json=payload)

    def sync_template(self, guild_id, code):
        return self.request(Route('PUT', '/guilds/{guild_id}/templates/{code}', guild_id=guild_id, code=code))

    def edit_template(self, guild_id, code, payload):
        valid_keys = (
            'name',
            'description',
        )
        payload = {
            k: v for k, v in payload.items() if k in valid_keys
        }

        return self.request(Route('PATCH', '/guilds/{guild_id}/templates/{code}', guild_id=guild_id, code=code), json=payload)

    def delete_template(self, guild_id, code):
        return self.request(Route('DELETE', '/guilds/{guild_id}/templates/{code}', guild_id=guild_id, code=code))

    def create_from_template(self, code, name, icon):
        payload = {
            'name': name,
            'icon': icon,
        }

        return self.request(Route('POST', '/guilds/templates/{code}', code=code), json=payload)

    def get_bans(self, guild_id):
        return self.request(Route('GET', '/guilds/{guild_id}/bans', guild_id=guild_id))

    def get_ban(self, guild_id, user_id):
        return self.request(Route('GET', '/guilds/{guild_id}/bans/{user_id}', guild_id=guild_id, user_id=user_id))

    def get_vanity_code(self, guild_id):
        return self.request(Route('GET', '/guilds/{guild_id}/vanity-url', guild_id=guild_id))

    def change_vanity_code(self, guild_id, code):
        payload = {'code': code}
        return self.request(Route('PATCH', '/guilds/{guild_id}/vanity-url', guild_id=guild_id), json=payload)

    def get_all_guild_channels(self, guild_id):
        return self.request(Route('GET', '/guilds/{guild_id}/channels', guild_id=guild_id))

    def get_member_verification(self, guild_id, *, with_guild=False, invite=None):
        params = {
            'with_guild': str(with_guild).lower(),
            'invite_code': invite
        }
        return self.request(Route('GET', '/guilds/{guild_id}/member-verification', guild_id=guild_id), params=params)

    def accept_member_verification(self, guild_id, **payload):
        return self.request(Route('PUT', '/guilds/{guild_id}/requests/@me', guild_id=guild_id), json=payload)

    def get_member(self, guild_id, member_id):
        return self.request(Route('GET', '/guilds/{guild_id}/members/{member_id}', guild_id=guild_id, member_id=member_id))

    def prune_members(self, guild_id, days, compute_prune_count, roles):
        payload = {
            'days': days,
            'compute_prune_count': str(compute_prune_count).lower()
        }
        if roles:
            payload['include_roles'] = ', '.join(roles)

        return self.request(Route('POST', '/guilds/{guild_id}/prune', guild_id=guild_id), json=payload)

    def estimate_pruned_members(self, guild_id, days, roles):
        params = {
            'days': days
        }
        if roles:
            params['include_roles'] = roles

        return self.request(Route('GET', '/guilds/{guild_id}/prune', guild_id=guild_id), params=params)

    def get_all_custom_emojis(self, guild_id):
        return self.request(Route('GET', '/guilds/{guild_id}/emojis', guild_id=guild_id))

    def get_custom_emoji(self, guild_id, emoji_id):
        return self.request(Route('GET', '/guilds/{guild_id}/emojis/{emoji_id}', guild_id=guild_id, emoji_id=emoji_id))

    def create_custom_emoji(self, guild_id, name, image):
        payload = {
            'name': name,
            'image': image,
        }

        r = Route('POST', '/guilds/{guild_id}/emojis', guild_id=guild_id)
        return self.request(r, json=payload)

    def delete_custom_emoji(self, guild_id, emoji_id):
        r = Route('DELETE', '/guilds/{guild_id}/emojis/{emoji_id}', guild_id=guild_id, emoji_id=emoji_id)
        return self.request(r)

    def edit_custom_emoji(self, guild_id, emoji_id, *, name):
        payload = {
            'name': name
        }
        r = Route('PATCH', '/guilds/{guild_id}/emojis/{emoji_id}', guild_id=guild_id, emoji_id=emoji_id)
        return self.request(r, json=payload)

    def get_all_integrations(self, guild_id, *, include_applications=True):
        r = Route('GET', '/guilds/{guild_id}/integrations', guild_id=guild_id)

        params = {
            'include_applications': str(include_applications).lower()
        }

        return self.request(r, params=params)

    def create_integration(self, guild_id, type, id):
        payload = {
            'type': type,
            'id': id
        }

        r = Route('POST', '/guilds/{guild_id}/integrations', guild_id=guild_id)
        return self.request(r, json=payload)

    def edit_integration(self, guild_id, integration_id, **payload):
        r = Route('PATCH', '/guilds/{guild_id}/integrations/{integration_id}', guild_id=guild_id,
                  integration_id=integration_id)

        return self.request(r, json=payload)

    def sync_integration(self, guild_id, integration_id):
        r = Route('POST', '/guilds/{guild_id}/integrations/{integration_id}/sync', guild_id=guild_id,
                  integration_id=integration_id)

        return self.request(r)

    def delete_integration(self, guild_id, integration_id):
        r = Route('DELETE', '/guilds/{guild_id}/integrations/{integration_id}', guild_id=guild_id,
                  integration_id=integration_id)

        return self.request(r)

    def get_audit_logs(self, guild_id, limit=100, before=None, after=None, user_id=None, action_type=None):
        params = {'limit': limit}
        if before:
            params['before'] = before
        if after:
            params['after'] = after
        if user_id:
            params['user_id'] = user_id
        if action_type:
            params['action_type'] = action_type

        r = Route('GET', '/guilds/{guild_id}/audit-logs', guild_id=guild_id)
        return self.request(r, params=params)

    def get_widget(self, guild_id):
        return self.request(Route('GET', '/guilds/{guild_id}/widget.json', guild_id=guild_id))

    # Invite management

    def create_invite(self, channel_id, **options):
        r = Route('POST', '/channels/{channel_id}/invites', channel_id=channel_id)
        payload = {
            'max_age': options.get('max_age', 0),
            'max_uses': options.get('max_uses', 0),
            'temporary': options.get('temporary', False),
            'unique': options.get('unique', True)
        }

        if options.get('validate') is not None:
            payload['validate'] = options['validate']

        if options.get('target_type') is not None:
            payload['target_type'] = options['target_type']

        if options.get('target_application_id'):
            payload['target_application_id'] = options['target_application_id']

        return self.request(r, json=payload)

    def get_invite(self, invite_id, *, with_counts=True, with_expiration=True):
        params = {
            'inputValue': invite_id,
            'with_counts': str(with_counts).lower(),
            'with_expiration': str(with_expiration).lower()
        }
        return self.request(Route('GET', '/invites/{invite_id}', invite_id=invite_id), params=params)

    def invites_from(self, guild_id):
        return self.request(Route('GET', '/guilds/{guild_id}/invites', guild_id=guild_id))

    def invites_from_channel(self, channel_id):
        return self.request(Route('GET', '/channels/{channel_id}/invites', channel_id=channel_id))

    def delete_invite(self, invite_id):
        return self.request(Route('DELETE', '/invites/{invite_id}', invite_id=invite_id))

    # Role management

    def get_roles(self, guild_id):
        return self.request(Route('GET', '/guilds/{guild_id}/roles', guild_id=guild_id))

    def edit_role(self, guild_id, role_id, **fields):
        r = Route('PATCH', '/guilds/{guild_id}/roles/{role_id}', guild_id=guild_id, role_id=role_id)
        valid_keys = ('name', 'permissions', 'color', 'hoist', 'mentionable')
        payload = {
            k: v for k, v in fields.items() if k in valid_keys
        }

        return self.request(r, json=payload)

    def delete_role(self, guild_id, role_id):
        r = Route('DELETE', '/guilds/{guild_id}/roles/{role_id}', guild_id=guild_id, role_id=role_id)
        return self.request(r)

    def replace_roles(self, user_id, guild_id, role_ids):
        return self.edit_member(guild_id=guild_id, user_id=user_id, roles=role_ids)

    def create_role(self, guild_id, **fields):
        r = Route('POST', '/guilds/{guild_id}/roles', guild_id=guild_id)
        return self.request(r, json=fields)

    def move_role_position(self, guild_id, positions):
        r = Route('PATCH', '/guilds/{guild_id}/roles', guild_id=guild_id)
        return self.request(r, json=positions)

    def add_role(self, guild_id, user_id, role_id):
        r = Route('PUT', '/guilds/{guild_id}/members/{user_id}/roles/{role_id}',
                  guild_id=guild_id, user_id=user_id, role_id=role_id)
        return self.request(r)

    def remove_role(self, guild_id, user_id, role_id):
        r = Route('DELETE', '/guilds/{guild_id}/members/{user_id}/roles/{role_id}',
                  guild_id=guild_id, user_id=user_id, role_id=role_id)
        return self.request(r)

    def edit_channel_permissions(self, channel_id, target, allow, deny, type):
        payload = {
            'id': target,
            'allow': allow,
            'deny': deny,
            'type': type
        }

        r = Route('PUT', '/channels/{channel_id}/permissions/{target}', channel_id=channel_id, target=target)
        return self.request(r, json=payload)

    def delete_channel_permissions(self, channel_id, target):
        r = Route('DELETE', '/channels/{channel_id}/permissions/{target}', channel_id=channel_id, target=target)
        return self.request(r)

    # Voice management

    def move_member(self, user_id, guild_id, channel_id):
        return self.edit_member(guild_id=guild_id, user_id=user_id, channel_id=channel_id)

    def ring(self, channel_id, *recipients):
        payload = {
            'recipients': recipients or None
        }
        return self.request(Route('POST', '/channels/{channel_id}/call/ring', channel_id=channel_id), json=payload)

    def stop_ringing(self, channel_id, *recipients):
        payload = {
            'recipients': recipients
        }
        return self.request(Route('POST', '/channels/{channel_id}/call/stop-ringing', channel_id=channel_id), json=payload)

    def change_call_voice_region(self, channel_id, voice_region):
        payload = {
            'region': voice_region
        }
        return self.request(Route('PATCH', '/channels/{channel_id}/call', channel_id=channel_id), json=payload)

    # Relationship related

    def get_relationships(self):
        return self.request(Route('GET', '/users/@me/relationships'))

    def remove_relationship(self, user_id, *, action):
        r = Route('DELETE', '/users/@me/relationships/{user_id}', user_id=user_id)

        if action is RelationshipAction.deny_request: # User Profile, Friends, DM Channel
            context_properties = choice((
                ContextProperties._from_friends_page(), ContextProperties._from_user_profile(),
                ContextProperties._from_dm_channel()
            ))
        elif action is RelationshipAction.unfriend: # Friends, ContextMenu, User Profile, DM Channel
            context_properties = choice((
                ContextProperties._from_context_menu(), ContextProperties._from_user_profile(),
                ContextProperties._from_friends_page(), ContextProperties._from_dm_channel()
            ))
        elif action == RelationshipAction.unblock: # Friends, ContextMenu, User Profile, DM Channel, NONE
            context_properties = choice((
                ContextProperties._from_context_menu(), ContextProperties._from_user_profile(),
                ContextProperties._from_friends_page(), ContextProperties._from_dm_channel(), None
            ))
        elif action == RelationshipAction.remove_pending_request: # Friends
            context_properties = ContextProperties._from_friends_page()

        return self.request(r, context_properties=context_properties)

    def add_relationship(self, user_id, type=None, *, action):
        r = Route('PUT', '/users/@me/relationships/{user_id}', user_id=user_id)

        if action is RelationshipAction.accept_request: # User Profile, Friends, DM Channel
            context_properties = choice((
                ContextProperties._from_friends_page(),
                ContextProperties._from_user_profile(),
                ContextProperties._from_dm_channel()
            ))
        elif action is RelationshipAction.block: # Friends, ContextMenu, User Profile, DM Channel.
            context_properties = choice((
                ContextProperties._from_context_menu(),
                ContextProperties._from_user_profile(),
                ContextProperties._from_friends_page(),
                ContextProperties._from_dm_channel()
            ))
        elif action is RelationshipAction.send_friend_request: # ContextMenu, User Profile, DM Channel
            context_properties = choice((
                ContextProperties._from_context_menu(),
                ContextProperties._from_user_profile(),
                ContextProperties._from_dm_channel()
            ))

        payload = {}
        if type:
            payload['type'] = type

        return self.request(r, json=payload, context_properties=context_properties)

    def send_friend_request(self, username, discriminator):
        r = Route('POST', '/users/@me/relationships')
        context_properties = choice(( # Friends, Group DM
            ContextProperties._from_add_friend_page,
            ContextProperties._from_group_dm
        ))
        payload = {
            'username': username,
            'discriminator': int(discriminator)
        }
        return self.request(r, json=payload, context_properties=context_properties)

    def change_friend_nickname(self, user_id, nickname):
        payload = {
            'nickname': nickname
        }
        return self.request(Route('PATCH', '/users/@me/relationships/{user_id}', user_id=user_id), json=payload)

    # Misc

    async def get_gateway(self, *, encoding='json', v=6, zlib=True):
        # The gateway URL hasn't changed for over 5 years. And,
        # the official clients aren't using it anymore. Sooooo...

        #try:
            #data = await self.request(Route('GET', '/gateway'))
        #except HTTPException as exc:
            #raise GatewayNotFound() from exc

        self.zlib = zlib
        if zlib:
            value = 'wss://gateway.discord.gg?encoding={0}&v={1}&compress=zlib-stream'
        else:
            value = 'wss://gateway.discord.gg?encoding={0}&v={1}'
        return value.format(encoding, v)

    def get_user(self, user_id):
        return self.request(Route('GET', '/users/{user_id}', user_id=user_id))

    def get_user_profile(self, user_id, *, with_mutual_guilds=True):
        params = {
            'with_mutual_guilds': str(with_mutual_guilds).lower()
        }
        return self.request(Route('GET', '/users/{user_id}/profile', user_id=user_id), params=params)

    def get_mutual_friends(self, user_id):
        return self.request(Route('GET', '/users/{user_id}/relationships', user_id=user_id))

    def get_notes(self):
        return self.request(Route('GET', '/users/@me/notes'))

    def get_note(self, user_id):
        return self.request(Route('GET', '/users/@me/notes/{user_id}', user_id=user_id))

    def set_note(self, user_id, *, note=None):
        payload = {
            'note': note or ''
        }
        return self.request(Route('PUT', '/users/@me/notes/{user_id}', user_id=user_id), json=payload)

    def change_hypesquad_house(self, house_id):
        payload = {
            'house_id': house_id
        }
        return self.request(Route('POST', '/hypesquad/online'), json=payload)

    def leave_hypesquad_house(self):
        return self.request(Route('DELETE', '/hypesquad/online'))

    def get_settings(self):
        return self.request(Route('GET', '/users/@me/settings'))

    def edit_settings(self, **payload):
        return self.request(Route('PATCH', '/users/@me/settings'), json=payload)

    def get_applications(self, *, with_team_applications=True):
        params = {
            'with_team_applications': str(with_team_applications).lower()
        }
        return self.request(Route('GET', '/applications'), params=params, super_properties_to_track=True)

    def get_application(self, app_id):
        return self.request(Route('GET', '/applications/{app_id}', app_id=app_id), super_properties_to_track=True)

    def get_app_entitlements(self, app_id):
        return self.request(Route('GET', '/users/@me/applications/{app_id}/entitlements', app_id=app_id), super_properties_to_track=True)

    def get_app_skus(self, app_id, *, localize=False, with_bundled_skus=True):
        params = {
            'localize': str(localize).lower(),
            'with_bundled_skus': str(with_bundled_skus).lower()
        }
        return self.request(Route('GET', '/applications/{app_id}/skus', app_id=app_id), params=params, super_properties_to_track=True)

    def get_app_whitelist(self, app_id):
        return self.request(Route('GET', '/oauth2/applications/{app_id}/allowlist', app_id=app_id), super_properties_to_track=True)

    def get_teams(self):
        return self.request(Route('GET', '/teams'), super_properties_to_track=True)

    def get_team(self, team_id):
        return self.request(Route('GET', '/teams/{team_id}', team_id=team_id), super_properties_to_track=True)

    def mobile_report(self, guild_id, channel_id, message_id, reason):
        payload = {
            'guild_id': guild_id,
            'channel_id': channel_id,
            'message_id': message_id,
            'reason': reason
        }
        return self.request(Route('POST', '/report'), json=payload)

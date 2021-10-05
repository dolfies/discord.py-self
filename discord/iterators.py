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
import datetime
import functools
import collections

from .audit_logs import AuditLogEntry
from .errors import NoMoreItems
from .object import Object
from .utils import maybe_coroutine, time_snowflake

OLDEST_OBJECT = Object(id=0)

class _AsyncIterator:
    __slots__ = ()

    def get(self, **attrs):
        def predicate(elem):
            for attr, val in attrs.items():
                nested = attr.split('__')
                obj = elem
                for attribute in nested:
                    obj = getattr(obj, attribute)

                if obj != val:
                    return False
            return True

        return self.find(predicate)

    async def find(self, predicate):
        while True:
            try:
                elem = await self.next()
            except NoMoreItems:
                return None

            ret = await maybe_coroutine(predicate, elem)
            if ret:
                return elem

    def chunk(self, max_size):
        if max_size <= 0:
            raise ValueError('async iterator chunk sizes must be greater than 0.')
        return _ChunkedAsyncIterator(self, max_size)

    def map(self, func):
        return _MappedAsyncIterator(self, func)

    def filter(self, predicate):
        return _FilteredAsyncIterator(self, predicate)

    async def flatten(self):
        return [element async for element in self]

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return await self.next()
        except NoMoreItems:
            raise StopAsyncIteration()


def _identity(x):
    return x

class _ChunkedAsyncIterator(_AsyncIterator):
    def __init__(self, iterator, max_size):
        self.iterator = iterator
        self.max_size = max_size

    async def next(self):
        ret = []
        n = 0
        while n < self.max_size:
            try:
                item = await self.iterator.next()
            except NoMoreItems:
                if ret:
                    return ret
                raise
            else:
                ret.append(item)
                n += 1
        return ret

class _MappedAsyncIterator(_AsyncIterator):
    def __init__(self, iterator, func):
        self.iterator = iterator
        self.func = func

    async def next(self):
        # this raises NoMoreItems and will propagate appropriately
        item = await self.iterator.next()
        return await maybe_coroutine(self.func, item)

class _FilteredAsyncIterator(_AsyncIterator):
    def __init__(self, iterator, predicate):
        self.iterator = iterator

        if predicate is None:
            predicate = _identity

        self.predicate = predicate

    async def next(self):
        getter = self.iterator.next
        pred = self.predicate
        while True:
            # propagate NoMoreItems similar to _MappedAsyncIterator
            item = await getter()
            ret = await maybe_coroutine(pred, item)
            if ret:
                return item

class ReactionIterator(_AsyncIterator):
    def __init__(self, message, emoji, limit=100, after=None):
        self.message = message
        self.limit = limit
        self.after = after
        state = message._state
        self.getter = state.http.get_reaction_users
        self.state = state
        self.emoji = emoji
        self.guild = message.guild
        self.channel_id = message.channel.id
        self.users = asyncio.Queue()

    async def next(self):
        if self.users.empty():
            await self.fill_users()

        try:
            return self.users.get_nowait()
        except asyncio.QueueEmpty:
            raise NoMoreItems()

    async def fill_users(self):
        # this is a hack because >circular imports<
        from .user import User

        if self.limit > 0:
            retrieve = self.limit if self.limit <= 100 else 100

            after = self.after.id if self.after else None
            data = await self.getter(self.channel_id, self.message.id, self.emoji, retrieve, after=after)

            if data:
                self.limit -= retrieve
                self.after = Object(id=int(data[-1]['id']))

            if self.guild is None or isinstance(self.guild, Object):
                for element in reversed(data):
                    await self.users.put(User(state=self.state, data=element))
            else:
                for element in reversed(data):
                    member_id = int(element['id'])
                    member = self.guild.get_member(member_id)
                    if member is not None:
                        await self.users.put(member)
                    else:
                        await self.users.put(User(state=self.state, data=element))

class HistoryIterator(_AsyncIterator):
    """Iterator for receiving a channel's message history.

    The messages endpoint has two behaviours we care about here:
    If ``before`` is specified, the messages endpoint returns the `limit`
    newest messages before ``before``, sorted with newest first. For filling over
    100 messages, update the ``before`` parameter to the oldest message received.
    Messages will be returned in order by time.
    If ``after`` is specified, it returns the ``limit`` oldest messages after
    ``after``, sorted with newest first. For filling over 100 messages, update the
    ``after`` parameter to the newest message received. If messages are not
    reversed, they will be out of order (99-0, 199-100, so on)

    A note that if both ``before`` and ``after`` are specified, ``before`` is ignored by the
    messages endpoint.

    Parameters
    -----------
    messageable: :class:`abc.Messageable`
        Messageable class to retrieve message history from.
    limit: :class:`int`
        Maximum number of messages to retrieve
    before: Optional[Union[:class:`abc.Snowflake`, :class:`datetime.datetime`]]
        Message before which all messages must be.
    after: Optional[Union[:class:`abc.Snowflake`, :class:`datetime.datetime`]]
        Message after which all messages must be.
    around: Optional[Union[:class:`abc.Snowflake`, :class:`datetime.datetime`]]
        Message around which all messages must be. Limit max 101. Note that if
        limit is an even number, this will return at most limit+1 messages.
    oldest_first: Optional[:class:`bool`]
        If set to ``True``, return messages in oldest->newest order. Defaults to
        ``True`` if `after` is specified, otherwise ``False``.
    """

    def __init__(self, messageable, limit,
                 before=None, after=None, around=None, oldest_first=None):

        if isinstance(before, datetime.datetime):
            before = Object(id=time_snowflake(before, high=False))
        if isinstance(after, datetime.datetime):
            after = Object(id=time_snowflake(after, high=True))
        if isinstance(around, datetime.datetime):
            around = Object(id=time_snowflake(around))

        if oldest_first is None:
            self.reverse = after is not None
        else:
            self.reverse = oldest_first

        self.messageable = messageable
        self.limit = limit
        self.before = before
        self.after = after or OLDEST_OBJECT
        self.around = around

        self._filter = None  # message dict -> bool

        self.state = self.messageable._state
        self.logs_from = self.state.http.logs_from
        self.messages = asyncio.Queue()

        if self.around:
            if self.limit is None:
                raise ValueError('history does not support around with limit=None')
            if self.limit > 101:
                raise ValueError("history max limit 101 when specifying around parameter")
            elif self.limit == 101:
                self.limit = 100  # Thanks discord

            self._retrieve_messages = self._retrieve_messages_around_strategy
            if self.before and self.after:
                self._filter = lambda m: self.after.id < int(m['id']) < self.before.id
            elif self.before:
                self._filter = lambda m: int(m['id']) < self.before.id
            elif self.after:
                self._filter = lambda m: self.after.id < int(m['id'])
        else:
            if self.reverse:
                self._retrieve_messages = self._retrieve_messages_after_strategy
                if (self.before):
                    self._filter = lambda m: int(m['id']) < self.before.id
            else:
                self._retrieve_messages = self._retrieve_messages_before_strategy
                if (self.after and self.after != OLDEST_OBJECT):
                    self._filter = lambda m: int(m['id']) > self.after.id

    async def next(self):
        if self.messages.empty():
            await self.fill_messages()

        try:
            return self.messages.get_nowait()
        except asyncio.QueueEmpty:
            raise NoMoreItems()

    def _get_retrieve(self):
        l = self.limit
        if l is None or l > 100:
            r = 100
        else:
            r = l
        self.retrieve = r
        return r > 0

    async def flatten(self):
        # this is similar to fill_messages except it uses a list instead
        # of a queue to place the messages in.
        result = []
        channel = await self.messageable._get_channel()
        self.channel = channel
        while self._get_retrieve():
            data = await self._retrieve_messages(self.retrieve)
            if len(data) < 100:
                self.limit = 0 # terminate the infinite loop

            if self.reverse:
                data = reversed(data)
            if self._filter:
                data = filter(self._filter, data)

            for element in data:
                result.append(self.state.create_message(channel=channel, data=element))
        return result

    async def fill_messages(self):
        if not hasattr(self, 'channel'):
            # do the required set up
            channel = await self.messageable._get_channel()
            self.channel = channel

        if self._get_retrieve():
            data = await self._retrieve_messages(self.retrieve)
            if len(data) < 100:
                self.limit = 0 # terminate the infinite loop

            if self.reverse:
                data = reversed(data)
            if self._filter:
                data = filter(self._filter, data)

            channel = self.channel
            for element in data:
                await self.messages.put(self.state.create_message(channel=channel, data=element))

    async def _retrieve_messages(self, retrieve):
        """Retrieve messages and update next parameters."""
        pass

    async def _retrieve_messages_before_strategy(self, retrieve):
        """Retrieve messages using before parameter."""
        before = self.before.id if self.before else None
        data = await self.logs_from(self.channel.id, retrieve, before=before)
        if len(data):
            if self.limit is not None:
                self.limit -= retrieve
            self.before = Object(id=int(data[-1]['id']))
        return data

    async def _retrieve_messages_after_strategy(self, retrieve):
        """Retrieve messages using after parameter."""
        after = self.after.id if self.after else None
        data = await self.logs_from(self.channel.id, retrieve, after=after)
        if len(data):
            if self.limit is not None:
                self.limit -= retrieve
            self.after = Object(id=int(data[0]['id']))
        return data

    async def _retrieve_messages_around_strategy(self, retrieve):
        """Retrieve messages using around parameter."""
        if self.around:
            around = self.around.id if self.around else None
            data = await self.logs_from(self.channel.id, retrieve, around=around)
            self.around = None
            return data
        return []

class AuditLogIterator(_AsyncIterator):
    def __init__(self, guild, limit=None, before=None, after=None, oldest_first=None, user_id=None, action_type=None):
        if isinstance(before, datetime.datetime):
            before = Object(id=time_snowflake(before, high=False))
        if isinstance(after, datetime.datetime):
            after = Object(id=time_snowflake(after, high=True))


        if oldest_first is None:
            self.reverse = after is not None
        else:
            self.reverse = oldest_first

        self.guild = guild
        self.loop = guild._state.loop
        self.request = guild._state.http.get_audit_logs
        self.limit = limit
        self.before = before
        self.user_id = user_id
        self.action_type = action_type
        self.after = OLDEST_OBJECT
        self._users = {}
        self._state = guild._state


        self._filter = None  # entry dict -> bool

        self.entries = asyncio.Queue()


        if self.reverse:
            self._strategy = self._after_strategy
            if self.before:
                self._filter = lambda m: int(m['id']) < self.before.id
        else:
            self._strategy = self._before_strategy
            if self.after and self.after != OLDEST_OBJECT:
                self._filter = lambda m: int(m['id']) > self.after.id

    async def _before_strategy(self, retrieve):
        before = self.before.id if self.before else None
        data = await self.request(self.guild.id, limit=retrieve, user_id=self.user_id,
                                  action_type=self.action_type, before=before)

        entries = data.get('audit_log_entries', [])
        if len(data) and entries:
            if self.limit is not None:
                self.limit -= retrieve
            self.before = Object(id=int(entries[-1]['id']))
        return data.get('users', []), entries

    async def _after_strategy(self, retrieve):
        after = self.after.id if self.after else None
        data = await self.request(self.guild.id, limit=retrieve, user_id=self.user_id,
                                  action_type=self.action_type, after=after)
        entries = data.get('audit_log_entries', [])
        if len(data) and entries:
            if self.limit is not None:
                self.limit -= retrieve
            self.after = Object(id=int(entries[0]['id']))
        return data.get('users', []), entries

    async def next(self):
        if self.entries.empty():
            await self._fill()

        try:
            return self.entries.get_nowait()
        except asyncio.QueueEmpty:
            raise NoMoreItems()

    def _get_retrieve(self):
        l = self.limit
        if l is None or l > 100:
            r = 100
        else:
            r = l
        self.retrieve = r
        return r > 0

    async def _fill(self):
        from .user import User

        if self._get_retrieve():
            users, data = await self._strategy(self.retrieve)
            if len(data) < 100:
                self.limit = 0 # terminate the infinite loop

            if self.reverse:
                data = reversed(data)
            if self._filter:
                data = filter(self._filter, data)

            for user in users:
                u = User(data=user, state=self._state)
                self._users[u.id] = u

            for element in data:
                # TODO: remove this if statement later
                if element['action_type'] is None:
                    continue

                await self.entries.put(AuditLogEntry(data=element, users=self._users, guild=self.guild))


class MessageSearchIterator(_AsyncIterator):
    """Iterator for receiving the message results on your search.

    Parameters
    -----------
    guild: :class:`Guild`
        The guild to search messages in
    messageable: :class:`Messageable`
        The channel to search messages in
    """
    def __init__(self, *, guild=None, messageable=None, **options):
        before = options.pop('before', None)
        after = options.pop('after', None)
        if isinstance(before, Object):
            options['max_id'] = before
        elif isinstance(before, datetime.datetime):
            options['max_id'] = Object(id=time_snowflake(before, high=False))
        if isinstance(after, Object):
            options['min_id'] = Object
        elif isinstance(after, datetime.datetime):
            options['min_id'] = Object(id=time_snowflake(after, high=True))

        if guild is not None and messageable is None:
            self.state = guild._state
            self.get_messages = functools.partial(self.state.http.search_messages, guild_id=guild.id)
        elif guild is None and messageable is not None:
            self.state = messageable._state
            self.get_messages = functools.partial(self.state.http.search_messages, _channel_id=messageable.id)

        # I don't want to bother checking if it even needs to be a list
        # HTTPClient.search_messages handles it properly either way
        _options = collections.defaultdict(list)
        for k, v in options.items():
            for sv in [v] if not isinstance(v, list) else v:
                if k in {'channel', 'author'}:
                    k += '_id'
                sv = getattr(sv, 'id', sv)
                _options[k].append(sv)

        self.options = dict(_options)
        self.messages = asyncio.Queue()

    async def next(self):
        # even when there are items in the queue, .empty() returns True
        # causing there to be an infinite loop of requests to api 🙄
        if self.messages.empty():
            await self.fill_messages()

        try:
            return self.messages.get_nowait()
        except asyncio.QueueEmpty:
            raise NoMoreItems()

    def create_message(self, data):
        from .message import Message
        channel = self.state.get_channel(int(data['channel_id']))
        return Message(state=self.state, channel=channel, data=data)

    async def fill_messages(self):
        data = await self._retrieve_messages()

        for element in data:
            await self.messages.put(self.create_message(element))

    async def _retrieve_messages(self):
        # I don't know why the resulting messages are in a nested list
        # api response looks like a bit like this {..., 'messages': [ [{message 1 ...}], [{message 2...}] ]}
        data = sum((await self.get_messages(**self.options))['messages'], [])
        return data


class GuildIterator(_AsyncIterator):
    """Iterator for receiving the client's guilds.

    Parameters
    -----------
    bot: :class:`discord.Client`
        The client to retrieve the guilds from.
    """
    def __init__(self, bot):
        self.bot = bot

        self._filter = None

        self.state = self.bot._connection
        self.get_guilds = self.bot.http.get_guilds
        self.guilds = asyncio.Queue()

    async def next(self):
        if self.guilds.empty():
            await self.fill_guilds()

        try:
            return self.guilds.get_nowait()
        except asyncio.QueueEmpty:
            raise NoMoreItems()

    def create_guild(self, data):
        from .guild import Guild
        return Guild(state=self.state, data=data)

    async def flatten(self):
        result = []
        data = await self._retrieve_guilds()

        if self._filter:
            data = filter(self._filter, data)

        for element in data:
            result.append(self.create_guild(element))

        return result

    async def fill_guilds(self):
        data = await self._retrieve_guilds()

        if self._filter:
            data = filter(self._filter, data)

        for element in data:
            await self.guilds.put(self.create_guild(element))

    async def _retrieve_guilds(self):
        data = await self.get_guilds()
        return data

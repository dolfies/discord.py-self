# -*- coding: utf-8 -*-

"""
The MIT License (MIT)

Copyright (c) 2015-present Dolfies

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

from base64 import b64encode
import json

class ContextProperties: # Thank you Discord-S.C.U.M
    """Represents the Discord X-Context-Properties header.

    This header is essential for certain actions (e.g. joining guilds, friend requesting).
    """

    __slots__ = ('_data', '_value')

    def __init__(self, data):
        self._data = data
        self._value = self._encode_data(data)

    def _encode_data(self, data):
        library = {
            'Friends': 'eyJsb2NhdGlvbiI6IkZyaWVuZHMifQ==',
            'ContextMenu': 'eyJsb2NhdGlvbiI6IkNvbnRleHRNZW51In0=',
            'User Profile': 'eyJsb2NhdGlvbiI6IlVzZXIgUHJvZmlsZSJ9',
            'Add Friend': 'eyJsb2NhdGlvbiI6IkFkZCBGcmllbmQifQ==',
            'Guild Header': 'eyJsb2NhdGlvbiI6Ikd1aWxkIEhlYWRlciJ9',
            'Group DM': 'eyJsb2NhdGlvbiI6Ikdyb3VwIERNIn0=',
            'DM Channel': 'eyJsb2NhdGlvbiI6IkRNIENoYW5uZWwifQ==',
            '/app': 'eyJsb2NhdGlvbiI6ICIvYXBwIn0=',
            'Login': 'eyJsb2NhdGlvbiI6IkxvZ2luIn0=',
            'Register': 'eyJsb2NhdGlvbiI6IlJlZ2lzdGVyIn0=',
        }

        try:
            return library[data['location']]
        except KeyError:
            return b64encode(json.dumps(data).encode()).decode('utf-8')

    @classmethod
    def _empty(cls):
        data = {}
        return cls(data)

    @classmethod
    def _from_friends_page(cls):
        data = {
            'location': 'Friends'
        }
        return cls(data)

    @classmethod
    def _from_context_menu(cls):
        data = {
            'location': 'ContextMenu'
        }
        return cls(data)

    @classmethod
    def _from_user_profile(cls):
        data = {
            'location': 'User Profile'
        }
        return cls(data)

    @classmethod
    def _from_add_friend_page(cls):
        data = {
            'location': 'Add Friend'
        }
        return cls(data)

    @classmethod
    def _from_guild_header_menu(cls):
        data = {
            'location': 'Guild Header'
        }
        return cls(data)

    @classmethod
    def _from_group_dm(cls):
        data = {
            'location': 'Group DM'
        }
        return cls(data)

    @classmethod
    def _from_dm_channel(cls):
        data = {
            'location': 'DM Channel'
        }
        return cls(data)

    @classmethod
    def _from_accept_invite_page_blank(cls):
        data = {
            'location': 'Accept Invite Page'
        }
        return cls(data)

    @classmethod
    def _from_app(cls):
        data = {
            'location': '/app'
        }
        return cls(data)

    @classmethod
    def _from_login(cls):
        data = {
            'location': 'Login'
        }
        return cls(data)

    @classmethod
    def _from_register(cls):
        data = {
            'location': 'Register'
        }
        return cls(data)

    @classmethod
    def _from_accept_invite_page(cls, *, guild_id, channel_id, channel_type):
        data = {
            'location': 'Accept Invite Page',
            'location_guild_id': guild_id,
            'location_channel_id': channel_id,
            'location_channel_type': channel_type
        }
        return cls(data)

    @classmethod
    def _from_join_guild_popup(cls, *, guild_id, channel_id, channel_type):
        data = {
            'location': 'Join Guild',
            'location_guild_id': guild_id,
            'location_channel_id': channel_id,
            'location_channel_type': channel_type
        }
        return cls(data)

    @classmethod
    def _from_invite_embed(cls, *, guild_id, channel_id, channel_type, message_id):
        data = {
            'location': 'Invite Button Embed',
            'location_guild_id': guild_id,
            'location_channel_id': channel_id,
            'location_channel_type': channel_type,
            'location_message_id': message_id
        }
        return cls(data)

    @property
    def value(self):
        return self._value

    @property
    def location(self):
        return self._data.get('location', None)

    @property
    def guild_id(self):
        return self._data.get('location_guild_id', None)

    @property
    def channel_id(self):
        return self._data.get('location_channel_id', None)

    @property
    def channel_type(self):
        return self._data.get('location_channel_type', None)

    @property
    def message_id(self):
        return self._data.get('location_message_id', None)

    def __bool__(self):
        return self.value is not None

    def __str__(self):
        return self._data.get('location', 'None')

    def __repr__(self):
        return '<ContextProperties location={0.location}>'.format(self)

    def __eq__(self, other):
        return isinstance(other, ContextProperties) and self._data == other._data

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._data)

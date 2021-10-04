# -*- coding: utf-8 -*-

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

from .colour import Colour


class GuildFolder:
    __slots__ = ('_state', 'id', 'name', '_color', 'guilds')

    def __init__(self, *, data, state):
        self._state = state
        self.id = data['id']
        self.name = data['name']
        self._color = data['color']
        self.guilds = list(filter(None, map(self._get_guild, data['guild_ids'])))

    def _get_guild(self, id):
        return self._state._get_guild(int(id))

    @property
    def color(self):
        color = self._color
        return Colour(color) if color else None

    colour = color

    def __str__(self):
        return self.name or 'None'

    def __repr__(self):
        return '<GuildFolder id={0.id} name={0.name} color={0.color} guilds={0.guilds!r}>'.format(self)

    def __len__(self):
        return len(self.name)

    def __eq__(self, other):
        return isinstance(other, GuildFolder) and self.id == other.id

    def __ne__(self, other):
        return not self.__eq__(other)

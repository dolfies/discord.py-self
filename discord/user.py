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

import discord.abc

from .asset import Asset
from .colour import Colour
from .enums import (DefaultAvatar, HypeSquadHouse, PremiumType,
                    RelationshipAction, RelationshipType, UserFlags, try_enum)
from .errors import ClientException, NotFound
from .flags import PublicUserFlags
from .object import Object
from .settings import Settings
from .utils import (_bytes_to_base64_data, cached_slot_property, parse_time,
                    snowflake_time)


from datetime import datetime

from datetime import datetime

class Note:
    """Represents a Discord note."""
    __slots__ = ('_state', '_note', '_user_id', '_user')

    def __init__(self, state, user_id, *, user=None, note=0):
        self._state = state
        self._user_id = user_id
        self._note = note
        if user:
            self._user = user

    @property
    def note(self):
        """Returns the note.

        Raises
        -------
        ClientException
            Attempted to access note without fetching it.
        """
        if self._note == 0:
            raise ClientException('Note is not fetched.')
        return self._note

    @cached_slot_property('_user')
    def user(self):
        """Returns the :class:`User` the note belongs to.

        If the user isn't in the cache, it returns a
        :class:`Object` instead.
        """
        state = self._state
        user_id = self._user_id

        user = state.get_user(user_id)
        if user is None:
            user = Object(user_id)
        return user

    async def fetch(self):
        """|coro|

        Retrieves the note.

        Raises
        -------
        HTTPException
            Fetching the note failed.

        Returns
        --------
        :class:`str`
            The note.
        """
        try:
            data = await self._state.http.get_note(self.user.id)
            self._note = data['note']
            return data['note']
        except NotFound: # 404 = no note
            self._note = None
            return None

    async def edit(self, note):
        """|coro|

        Changes the note.

        Raises
        -------
        HTTPException
            Changing the note failed.
        """
        await self._state.http.set_note(self._user_id, note=note)
        self._note = note

    async def delete(self):
        """|coro|

        A shortcut to :meth:`.edit` that deletes the note.

        Raises
        -------
        HTTPException
            Deleting the note failed.
        """
        await self.edit(None)
        self._note = None

    def __str__(self):
        note = self._note
        if note == 0:
            raise ClientException('Note is not fetched.')
        elif note is None:
            return ''
        else:
            return note

    def __repr__(self):
        base = f'<Note user={self.user!r}'
        note = self._note
        if note != 0:
            base += f' note={note or ""}>'
        else:
            base += '>'
        return base

    def __len__(self):
        try:
            return len(self._note)
        except TypeError:
            return 0

    def __eq__(self, other):
        try:
            return isinstance(other, Note) and self.note == other.note
        except TypeError:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __bool__(self):
        try:
            return bool(self._note)
        except TypeError:
            return False

class Profile:
    """Represents a Discord profile.

    Attributes
    ----------
    flags: :class:`int`
        The user's flags. Will be its own class (like public_flags) in the future.
    bio: Optional[:class:`str`]
        The user's "about me" field. Could be ``None``.
    banner: Optional[:class:`str`]
        The banner hash the user has. Could be ``None``.
    user: :class:`User`
        The user the profile represents.
    premium_since: Optional[:class:`datetime.datetime`]
        A datetime object denoting how long a user has been premium (had Nitro).
        Could be ``None``.
    connected_accounts: Optional[List[:class:`dict`]]
        The connected accounts that show up on the profile.
        These are currently just the raw json, but this will change in the future.
    note: :class:`Note`
        Represents the note on the profile.
    """
    def __init__(self, state, data):
        self._state = state

        user = data['user']
        self.flags = user.pop('flags', 0) # TODO: Figure out the differences and parse them
        bio = user.pop('bio')
        self.bio = bio if bio else None
        self.banner = user.pop('banner')
        self._accent_color = user.pop('accent_color')
        self.user = user = User(data=user, state=state)

        self.premium_since = parse_time(data['premium_since'])
        self.connected_accounts = data['connected_accounts']

        self.note = Note(state, user.id, user=user)

        if 'mutual_guilds' in data:
            self.mutual_guilds = self._parse_mutual_guilds(data['mutual_guilds'])
        if 'mutual_friends' in data:
            self.mutual_friends = self._parse_mutual_friends(data['mutual_friends'])

    def __str__(self):
        return '{0.name}#{0.discriminator}'.format(self.user)

    def __repr__(self):
        return '<Profile user={0.user!r} bio={0.bio}>'.format(self)

    def _parse_mutual_guilds(self, mutual_guilds):
        state = self._state

        def get_guild(guild):
            return state._get_guild(int(guild['id']))

        return list(filter(None, map(get_guild, mutual_guilds)))

    def _parse_mutual_friends(self, mutual_friends):
        state = self._state
        return [state.store_user(friend) for friend in mutual_friends]

    @property
    def banner_url(self):
        """:class:`Asset`: Returns an :class:`Asset` for the banner the user has.

        This is equivalent to calling :meth:`banner_url_as` with
        the default parameters (i.e. webp/gif detection and a size of 1024).

        .. versionadded:: 1.9
        """
        return self.banner_url_as(format=None, size=1024)

    def is_banner_animated(self):
        """:class:`bool`: Indicates if the user has an animated banner.

        .. versionadded:: 1.9
        """
        return bool(self.banner and self.banner.startswith('a_'))

    def banner_url_as(self, *, format=None, static_format='webp', size=1024):
        """Returns an :class:`Asset` for the banner the user has.

        The format must be one of 'webp', 'jpeg', 'jpg', 'png' or 'gif', and
        'gif' is only valid for animated banner. The size must be a power of
        2 between 16 and 4096.

        Parameters
        -----------
        format: Optional[:class:`str`]
            The format to attempt to convert the avatar to.
            If the format is ``None``, then it is automatically
            detected into either 'gif' or static_format depending on the
            banner being animated or not.
        static_format: Optional[:class:`str`]
            Format to attempt to convert only non-animated banners to.
            Defaults to 'webp'
        size: :class:`int`
            The size of the image to display.

        Raises
        ------
        InvalidArgument
            Bad image format passed to ``format`` or ``static_format``, or
            invalid ``size``.

        Returns
        --------
        :class:`Asset`
            The resulting CDN asset.

        .. versionadded:: 1.9
        """
        return Asset._from_user_banner(self.user._state, self, format=format, static_format=static_format, size=size)

    @property
    def accent_colour(self):
        """:class:`Colour`: Returns the user's accent colour.

        There is an alias for this named :attr:`accent_color`.

        .. versionadded:: 1.9
        """
        if self._accent_color is None:
            return None
        return Colour(self._accent_color)

    accent_color = accent_colour

    @property
    def nitro(self):
        return self.premium_since is not None

    premium = nitro

    def _has_flag(self, o):
        v = o.value
        return (self.flags & v) == v

    @property
    def staff(self):
        return self._has_flag(UserFlags.staff)

    @property
    def partner(self):
        return self._has_flag(UserFlags.partner)

    @property
    def bug_hunter(self):
        return self._has_flag(UserFlags.bug_hunter)

    @property
    def early_supporter(self):
        return self._has_flag(UserFlags.early_supporter)

    @property
    def hypesquad(self):
        return self._has_flag(UserFlags.hypesquad)

    @property
    def hypesquad_house(self):
        flags = (UserFlags.hypesquad_bravery, UserFlags.hypesquad_brilliance, UserFlags.hypesquad_balance)
        # I have no idea why this was originally a list but I'm just going to return the first item just in case.
        return [house for house, flag in zip(HypeSquadHouse, flags) if self._has_flag(flag)][0]

    @property
    def team_user(self):
        return self._has_flag(UserFlags.team_user)

    @property
    def system(self):
        return self._has_flag(UserFlags.system)

_BaseUser = discord.abc.User

class BaseUser(_BaseUser):
    __slots__ = ('name', 'id', 'discriminator', 'avatar', 'bot', 'system', '_public_flags', '_state')

    def __init__(self, *, state, data):
        self._state = state
        self._update(data)

    def __str__(self):
        return '{0.name}#{0.discriminator}'.format(self)

    def __eq__(self, other):
        return isinstance(other, _BaseUser) and other.id == self.id

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return self.id >> 22

    def _update(self, data):
        self.name = data['username']
        self.id = int(data['id'])
        self.discriminator = data['discriminator']
        self.avatar = data['avatar']
        self._public_flags = data.get('public_flags', 0)
        self.bot = data.get('bot', False)
        self.system = data.get('system', False)

    @classmethod
    def _copy(cls, user):
        self = cls.__new__(cls) # bypass __init__

        self.name = user.name
        self.id = user.id
        self.discriminator = user.discriminator
        self.avatar = user.avatar
        self.bot = user.bot
        self._state = user._state
        self._public_flags = user._public_flags

        return self

    def _to_minimal_user_json(self):
        return {
            'username': self.name,
            'id': self.id,
            'avatar': self.avatar,
            'discriminator': self.discriminator,
            'bot': self.bot,
            'system': self.system,
            'public_flags': self._public_flags
        }

    @property
    def public_flags(self):
        """:class:`PublicUserFlags`: The publicly available flags the user has."""
        return PublicUserFlags._from_value(self._public_flags)

    @property
    def avatar_url(self):
        """:class:`Asset`: Returns an :class:`Asset` for the avatar the user has.

        If the user does not have a traditional avatar, an asset for
        the default avatar is returned instead.

        This is equivalent to calling :meth:`avatar_url_as` with
        the default parameters (i.e. webp/gif detection and a size of 1024).
        """
        return self.avatar_url_as(format=None, size=1024)

    def is_avatar_animated(self):
        """:class:`bool`: Indicates if the user has an animated avatar."""
        return bool(self.avatar and self.avatar.startswith('a_'))

    def avatar_url_as(self, *, format=None, static_format='webp', size=1024):
        """Returns an :class:`Asset` for the avatar the user has.

        If the user does not have a traditional avatar, an asset for
        the default avatar is returned instead.

        The format must be one of 'webp', 'jpeg', 'jpg', 'png' or 'gif', and
        'gif' is only valid for animated avatars. The size must be a power of 2
        between 16 and 4096.

        Parameters
        -----------
        format: Optional[:class:`str`]
            The format to attempt to convert the avatar to.
            If the format is ``None``, then it is automatically
            detected into either 'gif' or static_format depending on the
            avatar being animated or not.
        static_format: Optional[:class:`str`]
            Format to attempt to convert only non-animated avatars to.
            Defaults to 'webp'
        size: :class:`int`
            The size of the image to display.

        Raises
        ------
        InvalidArgument
            Bad image format passed to ``format`` or ``static_format``, or
            invalid ``size``.

        Returns
        --------
        :class:`Asset`
            The resulting CDN asset.
        """
        return Asset._from_avatar(self._state, self, format=format, static_format=static_format, size=size)

    @property
    def default_avatar(self):
        """:class:`DefaultAvatar`: Returns the default avatar for a given user. This is calculated by the user's discriminator."""
        return try_enum(DefaultAvatar, int(self.discriminator) % len(DefaultAvatar))

    @property
    def default_avatar_url(self):
        """:class:`Asset`: Returns a URL for a user's default avatar."""
        return Asset(self._state, '/embed/avatars/{}.png'.format(self.default_avatar.value))

    @property
    def colour(self):
        """:class:`Colour`: A property that returns a colour denoting the rendered colour
        for the user. This always returns :meth:`Colour.default`.

        There is an alias for this named :attr:`color`.
        """
        return Colour.default()

    @property
    def color(self):
        """:class:`Colour`: A property that returns a color denoting the rendered color
        for the user. This always returns :meth:`Colour.default`.

        There is an alias for this named :attr:`colour`.
        """
        return self.colour

    @property
    def mention(self):
        """:class:`str`: Returns a string that allows you to mention the given user."""
        return '<@{0.id}>'.format(self)

    def permissions_in(self, channel):
        """An alias for :meth:`abc.GuildChannel.permissions_for`.

        Basically equivalent to:

        .. code-block:: python3

            channel.permissions_for(self)

        Parameters
        -----------
        channel: :class:`abc.GuildChannel`
            The channel to check your permissions for.
        """
        return channel.permissions_for(self)

    @property
    def created_at(self):
        """:class:`datetime.datetime`: Returns the user's creation time in UTC.

        This is when the user's Discord account was created."""
        return snowflake_time(self.id)

    @property
    def display_name(self):
        """:class:`str`: Returns the user's display name.

        For regular users this is just their username, but
        if they have a guild specific nickname then that
        is returned instead.
        """
        return self.name

    def mentioned_in(self, message):
        """Checks if the user is mentioned in the specified message.

        Parameters
        -----------
        message: :class:`Message`
            The message to check if you're mentioned in.

        Returns
        -------
        :class:`bool`
            Indicates if the user is mentioned in the message.
        """

        if message.mention_everyone:
            return True

        return any(user.id == self.id for user in message.mentions)

class ClientUser(BaseUser):
    """Represents your Discord user.

    .. container:: operations

        .. describe:: x == y

            Checks if two users are equal.

        .. describe:: x != y

            Checks if two users are not equal.

        .. describe:: hash(x)

            Return the user's hash.

        .. describe:: str(x)

            Returns the user's name with discriminator.

    Attributes
    -----------
    name: :class:`str`
        The user's username.
    id: :class:`int`
        The user's unique ID.
    discriminator: :class:`str`
        The user's discriminator.
    bio: Optional[:class:`str`]
        The user's "about me" field. Could be ``None``.
    avatar: Optional[:class:`str`]
        The avatar hash the user has. Could be ``None``.
    banner: Optional[:class:`str`]
        The banner hash the user has. Could be ``None``.
    bot: :class:`bool`
        Specifies if the user is a bot account.
    system: :class:`bool`
        Specifies if the user is a system user (i.e. represents Discord officially).

        .. versionadded:: 1.3

    verified: :class:`bool`
        Specifies if the user's email is verified.
    email: Optional[:class:`str`]
        The email of the user.
    phone: Optional[:class:`int`]
        The phone number of the user.

    locale: Optional[:class:`str`]
        The IETF language tag used to identify the language the user is using.
    mfa_enabled: :class:`bool`
        Specifies if the user has MFA turned on and working.
    premium: :class:`bool`
        Specifies if the user is a premium user (i.e. has Discord Nitro).
    premium_type: Optional[:class:`PremiumType`]
        Specifies the type of premium a user has (i.e. Nitro or Nitro Classic). Could be None if the user is not premium.
    settings: :class:`Settings`
        The user's client settings.
    note: :class:`Note`
        The user's note. Not pre-fetched.
    """
    __slots__ = BaseUser.__slots__ + \
                ('settings', 'bio', 'banner', '_accent_color', 'phone', 'email', 'locale', '_flags', 'verified', 'mfa_enabled',
                 'premium', 'premium_type', '_relationships', 'note', '__weakref__')

    def __init__(self, *, state, data):
        super().__init__(state=state, data=data)
        self._relationships = {}
        self.note = Note(state, self.id, user=self)

    def __repr__(self):
        return '<ClientUser id={0.id} name={0.name!r} discriminator={0.discriminator!r}' \
               ' bot={0.bot} verified={0.verified} mfa_enabled={0.mfa_enabled}>'.format(self)

    def _update(self, data):
        super()._update(data)
        self.verified = data.get('verified', False)
        self.email = data.get('email')
        self.phone = data.get('phone')
        self.locale = data.get('locale')
        self._flags = data.get('flags', 0)
        self.mfa_enabled = data.get('mfa_enabled', False)
        self.premium = data.get('premium', False)
        self.premium_type = try_enum(PremiumType, data.get('premium_type', None))
        self.bio = data.get('bio')
        self.banner = data.get('banner')
        self._accent_color = data.get('accent_color')

    def get_relationship(self, user_id):
        """Retrieves the :class:`Relationship` if applicable.

        Parameters
        -----------
        user_id: :class:`int`
            The user ID to check if we have a relationship with them.

        Returns
        --------
        Optional[:class:`Relationship`]
            The relationship if available or ``None``.
        """
        return self._relationships.get(user_id)

    @property
    def relationships(self):
        """List[:class:`User`]: Returns all the relationships that the user has."""
        return list(self._relationships.values())

    @property
    def friends(self):
        r"""List[:class:`User`]: Returns all the users that the user is friends with."""
        return [r.user for r in self._relationships.values() if r.type is RelationshipType.friend]

    @property
    def blocked(self):
        r"""List[:class:`User`]: Returns all the users that the user has blocked."""
        return [r.user for r in self._relationships.values() if r.type is RelationshipType.blocked]

    async def edit(self, **fields):
        """|coro|

        Edits the current profile of the client.

        .. note::

            To upload an avatar, a :term:`py:bytes-like object` must be passed in that
            represents the image being uploaded. If this is done through a file
            then the file must be opened via ``open('some_filename', 'rb')`` and
            the :term:`py:bytes-like object` is given through the use of ``fp.read()``.

            The only image formats supported for uploading is JPEG and PNG.

        Parameters
        -----------
        password: :class:`str`
            The current password for the client's account.
            Required for everything except avatar, banner, accent_colour, date_of_birth, and bio.
        new_password: :class:`str`
            The new password you wish to change to.
        email: :class:`str`
            The new email you wish to change to.
        house: Optional[:class:`HypeSquadHouse`]
            The hypesquad house you wish to change to.
            Could be ``None`` to leave the current house.
        username: :class:`str`
            The new username you wish to change to.
        discriminator: :class:`int`
            The new discriminator you wish to change to.
            Can only be used if you have Nitro.
        avatar: :class:`bytes`
            A :term:`py:bytes-like object` representing the image to upload.
            Could be ``None`` to denote no avatar.
        banner: :class:`bytes`
            A :term:`py:bytes-like object` representing the image to upload.
            Could be ``None`` to denote no banner.
        accent_colour/_color: :class:`Colour`
            A :class:`Colour` object of the colour you want to set your profile to.
        bio: :class:`str`
            Your 'about me' section.
            Could be ``None`` to represent no 'about me'.
        date_of_birth: :class:`datetime.datetime`
            Your date of birth.

        Raises
        ------
        HTTPException
            Editing your profile failed.
        InvalidArgument
            Wrong image format passed for ``avatar``.
        ClientException
            Password was not passed when it was required.
            `house` field was not a HypeSquadHouse.
            `date_of_birth` field was not a :class:`datetime.datetime` object.
        """

        args = {}

        if any(option in fields for option in ('new_password', 'email', 'username', 'discriminator')):
            password = fields.get('password')
            if password is None:
                raise ClientException('Password is required')
            args['password'] = password

        if 'avatar' in fields:
            avatar_bytes = fields['avatar']
            if avatar_bytes is not None:
                args['avatar'] = _bytes_to_base64_data(avatar_bytes)
            else:
                args['avatar'] = None

        if 'banner' in fields:
            banner_bytes = fields['banner']
            if banner_bytes is not None:
                args['banner'] = _bytes_to_base64_data(banner_bytes)
            else:
                args['banner'] = None

        if 'accent_color' or 'accent_colour' in fields:
            accent_color = fields.get('accent_color', None)
            accent_color = fields.get('accent_colour', accent_color)
            if accent_color is None:
                args['accent_color'] = accent_color
            elif not isinstance(accent_color, Colour):
                raise ClientException('`accent_colour` parameter was not a Colour')
            else:
                args['accent_color'] = accent_color.value

        if 'email' in fields:
            args['email'] = fields['email']

        if 'username' in fields:
            args['username'] = fields['username']

        if 'discriminator' in fields:
            args['discriminator'] = fields['discriminator']

        if 'new_password' in fields:
            args['new_password'] = fields['new_password']

        if 'bio' in fields:
            bio = fields['bio']
            if bio is not None:
                args['bio'] = bio
            else:
                args['bio'] = ''

        if 'date_of_birth' in fields:
            dob = fields['date_of_birth']
            if not isinstance(dob, datetime):
                raise ClientException('`date_of_birth` parameter was not a datetime object')
            args['date_of_birth'] = dob.strftime('%F')

        http = self._state.http

        if 'house' in fields:
            house = fields['house']
            if house is None:
                await http.leave_hypesquad_house()
            elif not isinstance(house, HypeSquadHouse):
                raise ClientException('`house` parameter was not a HypeSquadHouse')
            else:
                value = house.value

            await http.change_hypesquad_house(value)

        data = await http.edit_profile(**args)
        try:
            http._token(data['token'])
        except KeyError:
            pass

        self._update(data)

    async def create_group(self, *recipients):
        r"""|coro|

        Creates a group direct message with the recipients
        provided. These recipients must be have a relationship
        of type :attr:`RelationshipType.friend`.

        Parameters
        -----------
        \*recipients: :class:`User`
            An argument :class:`list` of :class:`User` to have in
            your group.

        Raises
        -------
        HTTPException
            Failed to create the group direct message.
        ClientException
            Attempted to create a group with only one recipient.
            This does not include yourself.

        Returns
        -------
        :class:`GroupChannel`
            The new group channel.
        """

        from .channel import GroupChannel

        if len(recipients) < 2:
            raise ClientException('You must have two or more recipients to create a group.')

        users = [str(u.id) for u in recipients]
        data = await self._state.http.start_group(users)
        return GroupChannel(me=self, data=data, state=self._state)

    async def edit_settings(self, **kwargs):
        """|coro|

        Edits the client user's settings.

        Parameters
        ----------
        afk_timeout: :class:`int`
            How long (in seconds) the user needs to be AFK until Discord
            sends push notifications to your mobile device.
        allow_accessibility_detection: :class:`bool`
            Whether or not to allow Discord to track screen reader usage.
        animate_emojis: :class:`bool`
            Whether or not to animate emojis in the chat.
        animate_stickers: :class:`StickerAnimationOptions`
            Whether or not to animate stickers in the chat.
        contact_sync_enabled: :class:`bool`
            Whether or not to enable the contact sync on Discord mobile.
        convert_emoticons: :class:`bool`
            Whether or not to automatically convert emoticons into emojis.
            e.g. :-) -> 😃
        default_guilds_restricted: :class:`bool`
            Whether or not to automatically disable DMs between you and
            members of new guilds you join.
        detect_platform_accounts: :class:`bool`
            Whether or not to automatically detect accounts from services
            like Steam and Blizzard when you open the Discord client.
        developer_mode: :class:`bool`
            Whether or not to enable developer mode.
        disable_games_tab: :class:`bool`
            Whether or not to disable the showing of the Games tab.
        enable_tts_command: :class:`bool`
            Whether or not to allow tts messages to be played/sent.
        explicit_content_filter: :class:`UserContentFilter`
            The filter for explicit content in all messages.
        friend_source_flags: :class:`FriendFlags`
            Who can add you as a friend.
        gif_auto_play: :class:`bool`
            Whether or not to automatically play gifs that are in the chat.
        guild_positions: List[:class:`abc.Snowflake`]
            A list of guilds in order of the guild/guild icons that are on
            the left hand side of the UI.
        inline_attachment_media: :class:`bool`
            Whether or not to display attachments when they are uploaded in chat.
        inline_embed_media: :class:`bool`
            Whether or not to display videos and images from links posted in chat.
        locale: :class:`str`
            The :rfc:`3066` language identifier of the locale to use for the language
            of the Discord client.
        message_display_compact: :class:`bool`
            Whether or not to use the compact Discord display mode.
        native_phone_integration_enabled: :class:`bool`
            Whether or not to enable the new Discord mobile phone number friend
            requesting features.
        render_embeds: :class:`bool`
            Whether or not to render embeds that are sent in the chat.
        render_reactions: :class:`bool`
            Whether or not to render reactions that are added to messages.
        restricted_guilds: List[:class:`abc.Snowflake`]
            A list of guilds that you will not receive DMs from.
        show_current_game: :class:`bool`
            Whether or not to display the game that you are currently playing.
        stream_notifications_enabled: :class:`bool`
            Unknown.
        theme: :class:`Theme`
            The theme of the Discord UI.
        timezone_offset: :class:`int`
            The timezone offset to use.
        view_nsfw_guilds: :class:`bool`
            Whether or not to show NSFW guilds on iOS.

        Raises
        -------
        HTTPException
            Editing the settings failed.

        Returns
        -------
        :class:`.Settings`
            The client user's updated settings.
        """
        payload = {}

        content_filter = kwargs.pop('explicit_content_filter', None)
        if content_filter:
            payload.update({'explicit_content_filter': content_filter.value})

        animate_stickers = kwargs.pop('animate_stickers', None)
        if animate_stickers:
            payload.update({'animate_stickers': animate_stickers.value})

        friend_flags = kwargs.pop('friend_source_flags', None)
        if friend_flags:
            payload.update({'friend_source_flags': friend_flags.to_dict()})

        guild_positions = kwargs.pop('guild_positions', None)
        if guild_positions:
            guild_positions = [str(x.id) for x in guild_positions]
            payload.update({'guild_positions': guild_positions})

        restricted_guilds = kwargs.pop('restricted_guilds', None)
        if restricted_guilds:
            restricted_guilds = [str(x.id) for x in restricted_guilds]
            payload.update({'restricted_guilds': restricted_guilds})

        status = kwargs.pop('status', None)
        if status:
            payload.update({'status': status.value})

        theme = kwargs.pop('theme', None)
        if theme:
            payload.update({'theme': theme.value})

        payload.update(kwargs)

        data = await self._state.http.edit_settings(**payload)
        self.settings = settings = Settings(data=data, state=self._state)
        return settings

    @property
    def banner_url(self):
        """:class:`Asset`: Returns an :class:`Asset` for the banner the user has.

        This is equivalent to calling :meth:`banner_url_as` with
        the default parameters (i.e. webp/gif detection and a size of 1024).
        """
        return self.banner_url_as(format=None, size=1024)

    def is_banner_animated(self):
        """:class:`bool`: Indicates if the user has an animated banner."""
        return bool(self.banner and self.banner.startswith('a_'))

    def banner_url_as(self, *, format=None, static_format='webp', size=1024):
        """Returns an :class:`Asset` for the banner the user has.

        The format must be one of 'webp', 'jpeg', 'jpg', 'png' or 'gif', and
        'gif' is only valid for animated banner. The size must be a power of
        2 between 16 and 4096.

        Parameters
        -----------
        format: Optional[:class:`str`]
            The format to attempt to convert the avatar to.
            If the format is ``None``, then it is automatically
            detected into either 'gif' or static_format depending on the
            banner being animated or not.
        static_format: Optional[:class:`str`]
            Format to attempt to convert only non-animated banners to.
            Defaults to 'webp'
        size: :class:`int`
            The size of the image to display.

        Raises
        ------
        InvalidArgument
            Bad image format passed to ``format`` or ``static_format``, or
            invalid ``size``.

        Returns
        --------
        :class:`Asset`
            The resulting CDN asset.
        """
        return Asset._from_user_banner(self._state, self, format=format, static_format=static_format, size=size, user=True)

    @property
    def accent_colour(self):
        """:class:`Colour`: Returns the user's accent colour.

        There is an alias for this named :attr:`accent_color`.

        .. versionadded:: 1.9
        """
        if self._accent_color is None:
            return None
        return Colour(self._accent_color)

    accent_color = accent_colour

    async def disable(self, password):
        """|coro|

        Disables the client's account.

        .. versionadded:: 1.9

        Parameters
        -----------
        password :class:`str`
            The current password of the user.

        Raises
        -------
        HTTPException
            Disabling the account failed.
        """
        return await self._state.http.disable_account(password)

    async def delete(self, password):
        """|coro|

        Deletes the client's account.

        .. versionadded:: 1.9

        Parameters
        -----------
        password :class:`str`
            The current password of the user.

        Raises
        -------
        HTTPException
            Deleting the account failed.
        """
        return await self._state.http.delete_account(password)


class User(BaseUser, discord.abc.Messageable):
    """Represents a Discord user.

    .. container:: operations

        .. describe:: x == y

            Checks if two users are equal.

        .. describe:: x != y

            Checks if two users are not equal.

        .. describe:: hash(x)

            Return the user's hash.

        .. describe:: str(x)

            Returns the user's name with discriminator.

    Attributes
    -----------
    name: :class:`str`
        The user's username.
    id: :class:`int`
        The user's unique ID.
    discriminator: :class:`str`
        The user's discriminator.
    avatar: Optional[:class:`str`]
        The avatar hash the user has. Could be None.
    bot: :class:`bool`
        Specifies if the user is a bot account.
    system: :class:`bool`
        Specifies if the user is a system user (i.e. represents Discord officially).
    """

    __slots__ = BaseUser.__slots__ + ('__weakref__',)

    def __repr__(self):
        return '<User id={0.id} name={0.name!r} discriminator={0.discriminator!r} bot={0.bot}>'.format(self)

    async def _get_channel(self):
        ch = await self.create_dm()
        return ch

    @property
    def dm_channel(self):
        """Optional[:class:`DMChannel`]: Returns the channel associated with this user if it exists.

        If this returns ``None``, you can create a DM channel by calling the
        :meth:`create_dm` coroutine function.
        """
        return self._state._get_private_channel_by_user(self.id)

    async def create_dm(self):
        """|coro|

        Creates a :class:`DMChannel` with this user.

        This should be rarely called, as this is done transparently for most
        people.

        Returns
        -------
        :class:`.DMChannel`
            The channel that was created.
        """
        found = self.dm_channel
        if found is not None:
            return found

        state = self._state
        data = await state.http.start_private_message(self.id)
        return state.add_dm_channel(data)

    @property
    def relationship(self):
        """Optional[:class:`Relationship`]: Returns the :class:`Relationship` with this user if applicable, ``None`` otherwise."""
        return self._state.user.get_relationship(self.id)

    async def mutual_friends(self):
        """|coro|

        Gets all mutual friends of this user.

        Raises
        -------
        Forbidden
            Not allowed to get mutual friends of this user.
        HTTPException
            Getting mutual friends failed.

        Returns
        -------
        List[:class:`User`]
            The users that are mutual friends.
        """
        state = self._state
        mutuals = await state.http.get_mutual_friends(self.id)
        return [state.store_user(friend) for friend in mutuals]

    async def mutual_guilds(self):
        """|coro|

        Gets all mutual guilds with this user.

        Raises
        -------
        Forbidden
            Not allowed to get mutual guilds of this user.
        HTTPException
            Getting mutual guilds failed.

        Returns
        -------
        List[:class:`User`]
            The users that are mutual friends.
        """
        profile = await self.profile()
        return profile.mutual_guilds

    def is_friend(self):
        """:class:`bool`: Checks if the user is your friend."""
        r = self.relationship
        if r is None:
            return False
        return r.type is RelationshipType.friend

    def is_blocked(self):
        """:class:`bool`: Checks if the user is blocked."""
        r = self.relationship
        if r is None:
            return False
        return r.type is RelationshipType.blocked

    async def block(self):
        """|coro|

        Blocks the user.

        Raises
        -------
        Forbidden
            Not allowed to block this user.
        HTTPException
            Blocking the user failed.
        """
        await self._state.http.add_relationship(self.id, type=RelationshipType.blocked.value, action=RelationshipAction.block)

    async def unblock(self):
        """|coro|

        Unblocks the user.

        Raises
        -------
        Forbidden
            Not allowed to unblock this user.
        HTTPException
            Unblocking the user failed.
        """
        await self._state.http.remove_relationship(self.id, action=RelationshipAction.unblock)

    async def remove_friend(self):
        """|coro|

        Removes the user as a friend.

        Raises
        -------
        Forbidden
            Not allowed to remove this user as a friend.
        HTTPException
            Removing the user as a friend failed.
        """
        await self._state.http.remove_relationship(self.id, action=RelationshipAction.unfriend)

    async def send_friend_request(self):
        """|coro|

        Sends the user a friend request.

        Raises
        -------
        Forbidden
            Not allowed to send a friend request to the user.
        HTTPException
            Sending the friend request failed.
        """
        await self._state.http.send_friend_request(self.name, self.discriminator)

    async def profile(self):
        """|coro|

        Gets the user's profile.

        Raises
        -------
        Forbidden
            Not allowed to fetch profiles.
        HTTPException
            Fetching the profile failed.

        Returns
        --------
        :class:`Profile`
            The profile of the user.
        """

        state = self._state
        data = await state.http.get_user_profile(self.id)
        data['mutual_friends'] = await state.http.get_mutual_friends(self.id)

        profile = Profile(state, data)
        await profile.note.fetch()

        return profile

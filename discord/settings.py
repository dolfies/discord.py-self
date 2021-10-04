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

from .enums import (FriendFlags, StickerAnimationOptions, Theme,
                    UserContentFilter, try_enum)
from .guild_folder import GuildFolder


class Settings:
    """Represents the Discord client settings.

    Attributes
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
    guild_positions: List[:class:`.Guild`]
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
    restricted_guilds: List[:class:`.Guild`]
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
    """

    def __init__(self, *, data, state):
        self._data = data
        self._state = state
        self.afk_timeout = data.get('afk_timeout')
        self.allow_accessibility_detection = data.get('allow_accessibility_detection')
        self.animate_emojis = data.get('animate_emojis')
        self.animate_stickers = try_enum(StickerAnimationOptions, data.get('animate_stickers'))
        self.contact_sync_enabled = data.get('contact_sync_enabled')
        self.convert_emoticons = data.get('convert_emoticons')
        self.default_guilds_restricted = data.get('default_guilds_restricted')
        self.detect_platform_accounts = data.get('detect_platform_accounts')
        self.developer_mode = data.get('developer_mode')
        self.disable_games_tab = data.get('disable_games_tab')
        self.enable_tts_command = data.get('enable_tts_command')
        self.explicit_content_filter = try_enum(UserContentFilter, data.get('explicit_content_filter'))
        self.friend_source_flags = FriendFlags._from_dict(data.get('friend_source_flags'))
        self.gif_auto_play = data.get('gif_auto_play')
        self.guild_folders = [GuildFolder(data=folder, state=state) for folder in data.get('guild_folders', [])]
        self.guild_positions = list(filter(None, map(self._get_guild, data.get('guild_positions', []))))
        self.inline_attachment_media = data.get('inline_attachment_media')
        self.inline_embed_media = data.get('inline_embed_media')
        self.locale = data.get('locale')
        self.message_display_compact = data.get('message_display_compact')
        self.native_phone_integration_enabled = data.get('native_phone_integration_enabled')
        self.render_embeds = data.get('render_embeds')
        self.render_reactions = data.get('render_reactions')
        self.restricted_guilds = list(filter(None, map(self._get_guild, data.get('restricted_guilds', []))))
        self.show_current_game = data.get('show_current_game')
        self.stream_notifications_enabled = data.get('stream_notifications_enabled')
        self.theme = try_enum(Theme, data.get('theme'))
        self.timezone_offset = data.get('timezone_offset')
        self.view_nsfw_guilds = data.get('view_nsfw_guilds')
        data.pop('status', None)
        data.pop('custom_status', None)

    def __repr__(self):
        return '<Settings>'

    def _get_guild(self, id):
        return self._state._get_guild(int(id))

    @property
    def raw(self):
        return self._data

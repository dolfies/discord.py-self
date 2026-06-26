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

from typing import TYPE_CHECKING, Any, List, Optional, overload

from .asset import Asset
from .colour import Colour
from .emoji import PartialEmoji
from .enums import GuildBadgeType, GuildVisibility, try_enum
from .mixins import Hashable

if TYPE_CHECKING:
    from .state import ConnectionState
    from .types.discovery import (
        GameActivity as GameActivityPayload,
    )
    from .types.discovery import (
        GuildProfile as GuildProfilePayload,
    )
    from .types.discovery import (
        GuildProfileTrait as GuildProfileTraitPayload,
    )

__all__ = (
    'GameActivity',
    'GuildTrait',
    'GuildProfile',
)


class GameActivity:
    """Represents the activity of the guild in a game.

    .. versionadded:: 2.2

    Attributes
    -----------
    application_id: :class:`int`
        The ID of the application representing the game.
    activity_level: :class:`int`
        The activity level for this game.
    activity_score: :class:`int`
        The activity score for this game.
    """

    __slots__ = ('application_id', 'activity_level', 'activity_score')

    def __init__(self, *, application_id: int, data: GameActivityPayload):
        self.application_id: int = application_id
        self.activity_level: int = data['activity_level']
        self.activity_score: int = data['activity_score']

    def __repr__(self) -> str:
        return f'<GameActivity application_id={self.application_id} activity_level={self.activity_level} activity_score={self.activity_score}>'


class GuildTrait:
    """Represents a guild profile trait.

    This class can be constructed by you to pass into :meth:`GuildProfile.edit`.

    .. versionadded:: 2.2

    Attributes
    -----------
    label: :class:`str`
        The label for this trait.
    position: :class:`int`
        The position of this trait in the list of traits for the guild.
    emoji: Optional[:class:`PartialEmoji`]
        The emoji for this trait, if it has one.
    """

    __slots__ = ('label', 'position', 'emoji')

    def __init__(
        self,
        *,
        label: str,
        position: int,
        emoji: Optional[PartialEmoji] = None,
    ) -> None:
        self.label: str = label
        self.position: int = position
        self.emoji: Optional[PartialEmoji] = emoji

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} label={self.label!r} position={self.position} emoji={self.emoji!r}>'

    @classmethod
    def from_dict(cls, *, state: ConnectionState, data: GuildProfileTraitPayload) -> GuildTrait:
        emoji_id = data.get('emoji_id')
        emoji_name = data.get('emoji_name')
        emoji_animated = data.get('emoji_animated', False)

        emoji: Optional[PartialEmoji] = None
        if emoji_id is not None or emoji_name is not None:
            emoji = PartialEmoji.with_state(
                state=state,
                id=int(emoji_id) if emoji_id is not None else None,
                name=emoji_name or '',  # can't be None
                animated=emoji_animated,
            )

        return cls(label=data['label'], position=data['position'], emoji=emoji)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            'label': self.label,
            'position': self.position,
        }
        if self.emoji is not None:
            result['emoji_id'] = str(self.emoji.id) if self.emoji.id is not None else None
            result['emoji_name'] = self.emoji.name
            result['emoji_animated'] = self.emoji.animated
        return result


class GuildProfile(Hashable):
    """Represents a guild's profile.

    You can get this from :meth:`Guild.profile`.

    .. versionadded:: 2.2

    Attributes
    -----------
    id: :class:`int`
        The ID of the guild.
    name: :class:`str`
        The name of the guild.
    approximate_member_count: :class:`int`
        Approximate count of total members in the guild.
    approximate_presence_count: :class:`int`
        Approximate count of non-offline members in the guild.
    description: :class:`str`
        The description for the guild.
    brand_colour_primary: Optional[:class:`selfcord.Colour`]
        The guild's accent colour.

        This is aliased to ``brand_color_primary`` as well.
    game_application_ids: List[:class:`int`]
        The IDs of the applications representing the games the guild plays.
    game_activity: List[:class:`GameActivity`]
        The activity of the guild in each game.
    tag: Optional[:class:`str`]
        The guild's tag, if applicable.
    badge: Optional[:class:`GuildBadgeType`]
        The badge shown on the guild's tag, if applicable.
    badge_primary_colour: Optional[:class:`selfcord.Colour`]
        The primary colour of the guild's badge, if applicable.

        This is aliased to ``badge_primary_color`` as well.
    badge_secondary_colour: Optional[:class:`selfcord.Colour`]
        The secondary colour of the guild's badge, if applicable.

        This is aliased to ``badge_secondary_color`` as well.
    traits: List[:class:`GuildTrait`]
        The terms used to describe the guild's interest and personality.
    features: List[:class:`str`]
        Enabled guild features.

        .. note::
            This is not a complete list of all possible guild features,
            but rather a list of community features that are enabled
            for the guild.

    visibility: :class:`GuildVisibility`
        The visibility level of the guild.
    premium_subscription_count: :class:`int`
        The number of premium subscriptions (boosts) the guild currently has.
    premium_tier: :class:`int`
        The premium tier for this guild. Corresponds to "Server Boost Level" in the official UI.
        The number goes from 0 to 3 inclusive.
    """

    __slots__ = (
        '_state',
        '_icon_hash',
        '_custom_banner_hash',
        '_badge_hash',
        'id',
        'name',
        'approximate_member_count',
        'approximate_presence_count',
        'description',
        'brand_colour_primary',
        'game_application_ids',
        'game_activity',
        'tag',
        'badge',
        'badge_primary_colour',
        'badge_secondary_colour',
        'traits',
        'features',
        'visibility',
        'premium_subscription_count',
        'premium_tier',
    )

    def __init__(self, *, state: ConnectionState, data: GuildProfilePayload):
        self._state = state
        self._update(data)

    def __repr__(self) -> str:
        attrs = [
            ('id', self.id),
            ('name', self.name),
            ('description', self.description),
            ('member_count', self.member_count),
            ('game_application_ids', self.game_application_ids),
            ('tag', self.tag),
            ('traits', self.traits),
            ('features', self.features),
            ('visibility', self.visibility),
            ('premium_tier', self.premium_tier),
        ]
        return f'<GuildProfile {" ".join(f"{attr}={value!r}" for attr, value in attrs)}>'

    def _update(self, data: GuildProfilePayload):
        self._icon_hash: str | None = data['icon_hash']
        self._custom_banner_hash: str | None = data.get('custom_banner_hash')

        self.id = int(data['id'])
        self.name: str = data['name']
        self.approximate_member_count: int = data['member_count']
        self.approximate_presence_count: int = data['online_count']
        self.description: str = data['description']

        brand_colour_primary = data.get('brand_color_primary')
        self.brand_colour_primary: Optional[Colour] = Colour.from_str(brand_colour_primary) if brand_colour_primary else None

        self.game_application_ids: List[int] = list(map(int, data['game_application_ids']))
        self.game_activity: List[GameActivity] = [
            GameActivity(application_id=int(app_id), data=activity_data)
            for app_id, activity_data in data.get('game_activity', {}).items()
        ]

        primary_colour = data.get('badge_color_primary')
        secondary_colour = data.get('badge_color_secondary')
        self._badge_hash: Optional[str] = data.get('badge_hash')

        self.tag: Optional[str] = data.get('tag')
        badge = data.get('badge')
        self.badge: Optional[GuildBadgeType] = try_enum(GuildBadgeType, badge) if badge is not None else None
        self.badge_primary_colour: Optional[Colour] = Colour.from_str(primary_colour) if primary_colour else None
        self.badge_secondary_colour: Optional[Colour] = Colour.from_str(secondary_colour) if secondary_colour else None

        self.traits: List[GuildTrait] = [
            GuildTrait.from_dict(state=self._state, data=trait) for trait in data.get('traits', [])
        ]
        self.features: List[str] = data['features']
        self.visibility: GuildVisibility = try_enum(GuildVisibility, data['visibility'])

        self.premium_subscription_count: int = data['premium_subscription_count']
        self.premium_tier: int = data['premium_tier']

    @property
    def icon(self) -> Optional[Asset]:
        """Optional[:class:`Asset`]: Returns the guild's icon asset, if available."""
        if self._icon_hash is None:
            return None
        return Asset._from_guild_icon(state=self._state, guild_id=self.id, icon_hash=self._icon_hash)

    @property
    def discovery_splash(self) -> Optional[Asset]:
        """Optional[:class:`Asset`]: Returns the guild's discovery splash asset, if available."""
        if self._custom_banner_hash is None:
            return None
        return Asset._from_guild_image(self._state, self.id, self._custom_banner_hash, path='discovery-splashes')

    @property
    def badge_icon(self) -> Optional[Asset]:
        """Optional[:class:`Asset`]: Returns the tag badge's icon asset."""
        if self._badge_hash is None:
            return None
        return Asset._from_guild_image(state=self._state, guild_id=self.id, image=self._badge_hash, path='guild-tag-badges')

    @property
    def member_count(self) -> int:
        """:class:`int`: Returns the approximate member count for the guild."""
        return self.approximate_member_count

    @property
    def online_count(self) -> int:
        """:class:`int`: Returns the approximate online count for the guild."""
        return self.approximate_presence_count

    @property
    def badge_secondary_color(self) -> Optional[Colour]:
        """Optional[:class:`selfcord.Colour`]: Alias for :attr:`badge_secondary_colour`."""
        return self.badge_secondary_colour

    @property
    def badge_primary_color(self) -> Optional[Colour]:
        """Optional[:class:`selfcord.Colour`]: Alias for :attr:`badge_primary_colour`."""
        return self.badge_primary_colour

    @property
    def brand_color_primary(self) -> Optional[Colour]:
        """Optional[:class:`selfcord.Colour`]: Alias for :attr:`brand_colour_primary`."""
        return self.brand_colour_primary

    @overload
    async def edit(
        self,
        *,
        name: str = ...,
        icon: Optional[bytes] = ...,
        description: Optional[str] = ...,
        brand_colour_primary: Optional[Colour] = ...,
        game_application_ids: Optional[List[int]] = ...,
        tag: Optional[str] = ...,
        badge: Optional[GuildBadgeType] = ...,
        badge_colour_primary: Optional[Colour] = ...,
        badge_colour_secondary: Optional[Colour] = ...,
        traits: Optional[List[GuildTrait]] = ...,
        visibility: Optional[GuildVisibility] = ...,
        discovery_splash: Optional[bytes] = ...,
    ) -> GuildProfile: ...

    @overload
    async def edit(
        self,
        *,
        name: str = ...,
        icon: Optional[bytes] = ...,
        description: Optional[str] = ...,
        brand_color_primary: Optional[Colour] = ...,
        game_application_ids: Optional[List[int]] = ...,
        tag: Optional[str] = ...,
        badge: Optional[GuildBadgeType] = ...,
        badge_color_primary: Optional[Colour] = ...,
        badge_color_secondary: Optional[Colour] = ...,
        traits: Optional[List[GuildTrait]] = ...,
        visibility: Optional[GuildVisibility] = ...,
        discovery_splash: Optional[bytes] = ...,
    ) -> GuildProfile: ...

    async def edit(self, **kwargs: Any) -> GuildProfile:
        """|coro|

        Edits the guild's discovery profile.

        Parameters
        -----------
        name: :class:`str`
            The new name for the guild.
        icon: Optional[:class:`bytes`]
            A :term:`py:bytes-like object` representing the new icon.
            ``None`` can be passed to remove the icon.
        description: Optional[:class:`str`]
            The new description for the guild. Max 300 characters.
            ``None`` can be passed to remove the description.
        brand_colour_primary: Optional[:class:`selfcord.Colour`]
            The new primary brand colour for the guild.
            This is aliased to ``brand_color_primary`` as well.
        game_application_ids: Optional[List[:class:`int`]]
            The new list of game application IDs representing the games the guild plays.
            Can only be up to 20.
        tag: Optional[:class:`str`]
            The new tag for the guild. Can only be between 3-4 characters.
            ``None`` can be passed to remove the tag.
        badge: Optional[:class:`GuildBadgeType`]
            The new badge for the guild.
        badge_colour_primary: Optional[:class:`selfcord.Colour`]
            The new primary badge color for the guild.
            This is aliased to ``badge_color_primary`` as well.
        badge_colour_secondary: Optional[:class:`selfcord.Colour`]
            The new secondary badge color for the guild.
            This is aliased to ``badge_color_secondary`` as well.
        traits: Optional[List[:class:`GuildTrait`]]
            The new list of traits for the guild.
        visibility: Optional[:class:`GuildVisibility`]
            The new visibility level for the guild.
        discovery_splash: Optional[:class:`bytes`]
            A :term:`py:bytes-like object` representing the new discovery splash.
            ``None`` can be passed to remove the discovery splash.

        Returns
        --------
        :class:`GuildProfile`
            The updated guild profile.

        Raises
        -------
        Forbidden
            You do not have permissions to edit this guild's profile.
        HTTPException
            Editing the profile failed.
        """
        guild = self._state._get_or_create_unavailable_guild(self.id)
        return await guild.edit_profile(**kwargs)

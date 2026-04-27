"""
The MIT License (MIT)

Copyright (c) 2021-present Dolfies
            This is aliased to ``badge_color_primary`` as well.
Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
            This is aliased to ``badge_color_secondary`` as well.
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

from typing import TYPE_CHECKING, Any, Dict, List, Optional, overload

from .asset import Asset
from .colour import Colour
from .emoji import PartialEmoji
from .enums import GuildBadgeType, GuildVisibility, try_enum
from .file import File
from .mixins import Hashable
from .utils import MISSING, _bytes_to_base64_data

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
    id: Optional[:class:`int`]
        The ID of the emoji for this trait, if it has one.
    label: :class:`str`
        The label for this trait.
    position: :class:`int`
        The position of this trait in the list of traits for the guild.
    emoji: Optional[:class:`PartialEmoji`]
        The emoji for this trait, if it has one.
    """

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
    approximate_online_count: :class:`int`
        Approximate count of non-offline members in the guild.
    description: :class:`str`
        The description for the guild.
    brand_colour_primary: :class:`discord.Colour`
        The guild's accent colour.
    game_application_ids: List[:class:`int`]
        The IDs of the applications representing the games the guild plays.
    game_activity: Dict[:class:`int`, :class:`GameActivity`]
        The activity of the guild in each game.
    tag: Optional[:class:`str`]
        The guild's tag, if applicable.
    badge: Optional[:class:`GuildBadgeType`]
        The badge shown on the guild's tag, if applicable.
    badge_primary_colour: Optional[:class:`discord.Colour`]
        The primary colour of the guild's badge, if applicable.
    badge_secondary_colour: Optional[:class:`discord.Colour`]
        The secondary colour of the guild's badge, if applicable.
    traits: List[:class:`GuildTrait`]
        The terms used to describe the guild's interest and personality.
    features: List[:class:`str`]
        Enabled guild features.

        .. note::
            This is not a complete list of all possible guild features,
            but rather a list of community features that are enabled
            for the guild.

    visibility: :class:`int`
        The visibility level of the guild.
    premium_subscription_count: :class:`int`
        The number of premium subscriptions (boosts) the guild currently has.
    premium_tier: :class:`int`
        The premium tier for this guild. Corresponds to "Server Boost Level" in the official UI.
        The number goes from 0 to 3 inclusive.
    """

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
        self.approximate_online_count: int = data['online_count']
        self.description: str = data['description']

        brand_color_primary: str = data.get('brand_color_primary')
        self.brand_color_primary: Optional[Colour] = Colour.from_str(brand_color_primary) if brand_color_primary else None

        self.game_application_ids: List[int] = list(map(int, data['game_application_ids']))
        self.game_activites: List[GameActivity] = [
            GameActivity(application_id=int(app_id), data=activity_data)
            for app_id, activity_data in data.get('game_activity', {}).items()
        ]

        primary_colour: str = data.get('badge_color_primary')
        secondary_colour: str = data.get('badge_color_secondary')
        self._badge_hash: str = data.get('badge_hash')

        self.tag: Optional[str] = data.get('tag')
        self.badge: Optional[GuildBadgeType] = try_enum(GuildBadgeType, data.get('badge', 0))
        self.badge_primary_colour: Optional[Colour] = Colour.from_str(primary_colour) if primary_colour else None
        self.badge_secondary_colour: Optional[Colour] = Colour.from_str(secondary_colour) if secondary_colour else None

        self.traits: List[GuildTrait] = [
            GuildTrait.from_dict(state=self._state, data=trait) for trait in data.get('traits', [])
        ]
        self.features: List[str] = data['features']
        self.visibility = data['visibility']

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
        """Optional[:class:`Asset`]: Returns the badge's icon asset."""
        if self._badge_hash is None:
            return None
        return Asset._from_guild_image(state=self._state, guild_id=self.id, image=self._badge_hash, path='guild-tag-badges')

    @property
    def member_count(self) -> int:
        """:class:`int`: Returns the approximate member count for the guild.

        .. warning::

            Due to a Discord limitation, this may not always be up-to-date and accurate.
        """
        return self.approximate_member_count

    @property
    def online_count(self) -> int:
        """:class:`int`: Returns the approximate online count for the guild.

        .. warning::

            Due to a Discord limitation, this may not always be up-to-date and accurate.
        """
        return self.approximate_online_count

    @property
    def badge_secondary_color(self) -> Optional[Colour]:
        """Optional[:class:`discord.Colour`]: Alias for :attr:`badge_secondary_colour`."""
        return self.badge_secondary_colour

    @property
    def badge_primary_color(self) -> Optional[Colour]:
        """Optional[:class:`discord.Colour`]: Alias for :attr:`badge_primary_colour`."""
        return self.badge_primary_colour

    @overload
    async def edit(
        self,
        *,
        name: Optional[str] = ...,
        icon: Optional[File] = ...,
        description: Optional[str] = ...,
        brand_color_primary: Optional[Colour] = ...,
        game_application_ids: Optional[List[int]] = ...,
        tag: Optional[str] = ...,
        badge: Optional[GuildBadgeType] = ...,
        badge_colour_primary: Optional[Colour] = ...,
        badge_colour_secondary: Optional[Colour] = ...,
        traits: Optional[List[GuildTrait]] = ...,
        visibility: Optional[GuildVisibility] = ...,
        discovery_splash: Optional[File] = ...,
    ) -> GuildProfile: ...

    @overload
    async def edit(
        self,
        *,
        name: Optional[str] = ...,
        icon: Optional[File] = ...,
        description: Optional[str] = ...,
        brand_color_primary: Optional[Colour] = ...,
        game_application_ids: Optional[List[int]] = ...,
        tag: Optional[str] = ...,
        badge: Optional[GuildBadgeType] = ...,
        badge_color_primary: Optional[Colour] = ...,
        badge_color_secondary: Optional[Colour] = ...,
        traits: Optional[List[GuildTrait]] = ...,
        visibility: Optional[GuildVisibility] = ...,
        discovery_splash: Optional[File] = ...,
    ) -> GuildProfile: ...

    async def edit(
        self,
        *,
        name: Optional[str] = None,
        icon: Optional[File] = MISSING,
        description: Optional[str] = MISSING,
        brand_color_primary: Optional[Colour] = None,
        game_application_ids: Optional[List[int]] = None,
        tag: Optional[str] = MISSING,
        badge: Optional[GuildBadgeType] = None,
        badge_color_primary: Optional[Colour] = MISSING,
        badge_color_secondary: Optional[Colour] = MISSING,
        badge_colour_primary: Optional[Colour] = MISSING,
        badge_colour_secondary: Optional[Colour] = MISSING,
        traits: Optional[List[GuildTrait]] = None,
        visibility: Optional[GuildVisibility] = None,
        discovery_splash: Optional[File] = None,
    ) -> GuildProfile:
        """|coro|

        Edits the guild's discovery profile.

        Parameters
        -----------
        name: Optional[:class:`str`]
            The new name for the guild.
        icon: Optional[:class:`File`]
            The new icon for the guild.
            ``None`` can be passed to remove the icon.
        description: Optional[:class:`str`]
            The new description for the guild. Max 300 characters.
            ``None`` can be passed to remove the description.
        brand_color_primary: Optional[:class:`discord.Colour`]
            The new primary brand color for the guild.
        game_application_ids: Optional[List[:class:`int`]]
            The new list of game application IDs representing the games the guild plays.
            Can only be up to 20.
        tag: Optional[:class:`str`]
            The new tag for the guild. Can only be between 3-4 characters.
            ``None`` can be passed to remove the tag.
        badge: Optional[:class:`GuildBadgeType`]
            The new badge for the guild.
        badge_colour_primary: Optional[:class:`discord.Colour`]
            The new primary badge color for the guild.
            This is aliased to ``badge_color_primary`` as well.
        badge_colour_secondary: Optional[:class:`discord.Colour`]
            The new secondary badge color for the guild.
            This is aliased to ``badge_color_secondary`` as well.
        traits: Optional[List[:class:`GuildTrait`]]
            The new list of traits for the guild.
        visibility: Optional[:class:`GuildVisibility`]
            The new visibility level for the guild.
        discovery_splash: Optional[:class:`File`]
            The new discovery splash for the guild.

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
        payload: Dict[str, Any] = {}
        if name is not None:
            payload['name'] = name
        if icon is not MISSING:
            if icon is not None:
                payload['icon'] = _bytes_to_base64_data(icon.fp.read())
            else:
                payload['icon'] = None

        if description is not MISSING:
            payload['description'] = description
        if brand_color_primary is not None:
            payload['brand_color_primary'] = str(brand_color_primary)
        if game_application_ids is not None:
            payload['game_application_ids'] = game_application_ids
        if tag is not MISSING:
            payload['tag'] = tag
        if badge is not None:
            payload['badge'] = badge.value

        actual_badge_colour_primary = badge_color_primary if badge_color_primary is not MISSING else badge_colour_primary
        if actual_badge_colour_primary is not MISSING:
            payload['badge_color_primary'] = str(actual_badge_colour_primary) if actual_badge_colour_primary else None

        actual_badge_colour_secondary = (
            badge_color_secondary if badge_color_secondary is not MISSING else badge_colour_secondary
        )
        if actual_badge_colour_secondary is not MISSING:
            payload['badge_color_secondary'] = str(actual_badge_colour_secondary) if actual_badge_colour_secondary else None

        if traits is not None:
            payload['traits'] = [trait.to_dict() for trait in traits]
        if visibility is not None:
            payload['visibility'] = visibility.value
        if discovery_splash is not None:
            payload['custom_banner'] = _bytes_to_base64_data(discovery_splash.fp.read())

        data = await self._state.http.edit_guild_profile(self.id, **payload)
        self._update(data)
        return self

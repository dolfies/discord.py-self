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

from typing import TYPE_CHECKING, Any, List, Optional

from .asset import Asset
from .colour import Color
from .emoji import PartialEmoji
from .enums import GuildBadgeType, GuildPremiumTier, GuildVisibility, try_enum
from .errors import ClientException
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
    'GuildTag',
    'GameActivity',
    'Trait',
    'GuildProfile',
)


class GuildTag:
    """Represents a guild's tag (badge).

    This class can be constructed by you to pass into :meth:`GuildProfile.edit`.

    .. versionadded:: 2.2

    Parameters
    -----------
    tag: :class:`str`
        The tag string for the guild. 3-4 characters.
    badge: :class:`GuildBadgeType`
        The badge to show on the guild's tag.
    color_primary: Optional[:class:`Color`]
        The primary color of the badge.
    color_secondary: Optional[:class:`Color`]
        The secondary color of the badge.

    Attributes
    -----------
    tag: Optional[:class:`str`]
        The tag string for the guild, if it has one.
    badge: :class:`GuildBadgeType`
        The badge shown on the guild's tag.
    color_primary: Optional[:class:`Color`]
        The primary color of the badge.
    color_secondary: Optional[:class:`Color`]
        The secondary color of the badge.
    """

    __slots__ = ('_guild_id', '_icon_hash', '_state', 'color_primary', 'color_secondary', 'type', 'tag')

    def __init__(
        self,
        *,
        type: GuildBadgeType,
        tag: Optional[str] = None,
        color_primary: Optional[Color] = None,
        color_secondary: Optional[Color] = None,
    ) -> None:
        self._guild_id: Optional[int] = None
        self._state: Optional[ConnectionState] = None
        self._icon_hash: Optional[str] = None

        self.type: GuildBadgeType = type
        self.tag: Optional[str] = tag
        self.color_primary: Optional[Color] = color_primary
        self.color_secondary: Optional[Color] = color_secondary

    def __repr__(self) -> str:
        return f'<GuildTag type={self.type} tag={self.tag!r} color_primary={self.color_primary} color_secondary={self.color_secondary}>'

    @property
    def icon(self) -> Asset:
        """Optional[:class:`Asset`]: Returns the badge's icon asset."""
        if self._icon_hash is None or self._guild_id is None or self._state is None:
            raise ClientException('This object was constructed by you, thus it does not have an icon hash yet.')

        return Asset._from_guild_image(
            state=self._state, guild_id=self._guild_id, image=self._icon_hash, path='guild-tag-badges'
        )

    @classmethod
    def from_dict(cls, *, state: ConnectionState, guild_id: int, data: GuildProfilePayload) -> GuildTag:
        badge = cls(
            type=try_enum(GuildBadgeType, data['badge']),
            color_primary=Color.from_str(data['badge_color_primary']),
            color_secondary=Color.from_str(data['badge_color_secondary']),
            tag=data.get('tag'),
        )
        badge._guild_id = guild_id
        badge._state = state
        badge._icon_hash = data.get('badge_hash')
        return badge

    def to_dict(self) -> dict[str, Any]:
        return {
            'badge': self.type.value,
            'tag': self.tag,
            'badge_color_primary': str(self.color_primary) if self.color_primary else None,
            'badge_color_secondary': str(self.color_secondary) if self.color_secondary else None,
        }


class GameActivity:
    """Represents the activity of the guild in a game.

    .. versionadded:: 2.2

    Attributes
    -----------
    activity_level: :class:`int`
        The activity level for this game.
    activity_score: :class:`int`
        The activity score for this game.
    """

    def __init__(self, data: GameActivityPayload):
        self.activity_level: int = data['activity_level']
        self.activity_score: int = data['activity_score']

    def __repr__(self) -> str:
        return f'<GameActivity activity_level={self.activity_level} activity_score={self.activity_score}>'


class Trait:
    """Represents a guild profile trait.

    .. versionadded:: 2.2

    Attributes
    -----------
    id: Optional[:class:`int`]
        The ID of the emoji for this trait, if it has one.
    name: :class:`str`
        The name of the emoji for this trait, if it has one.
    animated: :class:`bool`
        Whether the emoji for this trait is animated, if it has one.
    label: :class:`str`
        The label for this trait.
    position: :class:`int`
        The position of this trait in the list of traits for the guild.
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
        return f'<Trait label={self.label!r} position={self.position} emoji={self.emoji!r}>'

    @classmethod
    def from_dict(cls, *, state: ConnectionState, data: GuildProfileTraitPayload) -> Trait:
        emoji_id = data.get('emoji_id')
        emoji_name = data.get('emoji_name')
        emoji_animated = data.get('emoji_animated', False)

        emoji: Optional[PartialEmoji] = None
        if emoji_id is not None and emoji_name is not None:
            emoji = PartialEmoji.with_state(state=state, id=int(emoji_id), name=emoji_name, animated=emoji_animated)

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

    You can get this from :attr:`Guild.profile`.

    .. versionadded:: 2.2

    Attributes
    -----------
    id: :class:`int`
        The ID of the guild.
    name: :class:`str`
        The name of the guild.
    member_count: :class:`int`
        Approximate count of total members in the guild.
    online_count: :class:`int`
        Approximate count of non-offline members in the guild.
    description: :class:`str`
        The description for the guild.
    brand_color_primary: :class:`Color`
        The guild's accent color.
    game_application_ids: List[:class:`int`]
        The IDs of the applications representing the games the guild plays.
    game_activity: Dict[:class:`int`, :class:`GameActivity`]
        The activity of the guild in each game.
    tag: Optional[:class:`str`]
        The tag of the guild.
    badge: :class:`GuildBadge`
        The guild's badge (tag).
    traits: List[:class:`Trait`]
        Terms used to describe the guild's interest and personality.
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
    premium_tier: :class:`GuildPremiumTier`
        The guild's premium tier (boost level).
    """

    def __init__(self, *, state: ConnectionState, data: GuildProfilePayload):
        self._state = state
        self._update(data)

    def __repr__(self) -> str:
        attrs = [
            ('id', self.id),
            ('name', self.name),
            ('member_count', self.member_count),
            ('online_count', self.online_count),
            ('description', self.description),
            ('brand_color_primary', self.brand_color_primary),
            ('game_application_ids', self.game_application_ids),
            ('game_activity', self.game_activity),
            ('tag', self.badge.tag),
            ('badge', self.badge.type),
            ('traits', self.traits),
            ('features', self.features),
            ('visibility', self.visibility),
            ('premium_subscription_count', self.premium_subscription_count),
            ('premium_tier', self.premium_tier),
        ]
        return f'<GuildProfile {" ".join(f"{attr}={value!r}" for attr, value in attrs)}>'

    def _update(self, data: GuildProfilePayload):
        self._icon_hash: str | None = data['icon_hash']
        self._badge_hash: str | None = data.get('badge_hash')
        self._custom_banner_hash: str | None = data.get('custom_banner_hash')

        self.id = int(data['id'])
        self.name: str = data['name']
        self.member_count: int = data['member_count']
        self.online_count: int = data['online_count']
        self.description: str = data['description']
        self.brand_color_primary: Optional[Color] = Color.from_str(bcp) if (bcp := data.get('brand_color_primary')) else None
        self.game_application_ids: list[int] = list(map(int, data['game_application_ids']))
        self.game_activity: dict[int | str, GameActivity] = {
            int(app_id): GameActivity(activity) for app_id, activity in data['game_activity'].items()
        }

        self.badge: GuildTag = GuildTag.from_dict(
            state=self._state,
            guild_id=self.id,
            data=data,
        )
        self.traits: List[Trait] = [Trait.from_dict(state=self._state, data=trait) for trait in data.get('traits', [])]
        self.features: List[str] = data['features']
        self.visibility = data['visibility']

        self.premium_subscription_count: int = data['premium_subscription_count']
        self.premium_tier: GuildPremiumTier = try_enum(GuildPremiumTier, data['premium_tier'])

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

    async def edit(
        self,
        *,
        name: Optional[str] = None,
        icon: Optional[File] = MISSING,
        description: Optional[str] = MISSING,
        brand_color_primary: Optional[Color] = None,
        game_application_ids: Optional[List[int]] = None,
        tag: Optional[GuildTag] = MISSING,
        traits: Optional[List[Trait]] = None,
        visibility: Optional[GuildVisibility] = None,
        discovery_splash: Optional[File] = None,
    ) -> GuildProfile:
        """|coro|

        Edits the guild's discovery profile.

        Parameters
        -----------
        name: Optional[:class:`str`]
            The new name for the guild.
        icon: Optional[:class:`str`]
            The new icon for the guild. This should be a data URI string representing the image to use as the icon.
            ``None`` can be passed to remove the icon.
        description: Optional[:class:`str`]
            The new description for the guild. Max 300 characters.
            ``None`` can be passed to remove the description.
        brand_color_primary: Optional[:class:`Color`]
            The new primary brand color for the guild.
        game_application_ids: Optional[List[:class:`int`]]
            The new list of game application IDs representing the games the guild plays.
            Can only be up to 20.
        tag: Optional[:class:`GuildTag`]
            The new tag for the guild.

            Can be ``None`` to remove the tag, but the guild must have
            the ``GUILD_TAG`` feature to have a tag in the first place.
        traits: Optional[List[:class:`Trait`]]
            The new list of traits for the guild.
        visibility: Optional[:class:`GuildVisibility`]
            The new visibility level for the guild.
        discovery_splash: Optional[:class:`File`]
            The new discovery splash for the guild.

        Returns
        --------
        GuildProfile
            The updated guild profile.

        Raises
        -------
        Forbidden
            You do not have permissions to edit this guild's profile.
        HTTPException
            Editing the profile failed.
        """
        payload: dict[str, Any] = {}
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
            if 'GUILD_TAG' not in self.features:
                raise ClientException('This guild does not have the GUILD_TAG feature, thus it cannot have a tag.')

            if tag is not None:
                payload.update(tag.to_dict())
            else:
                payload['tag'] = None
                payload['badge_color_primary'] = None
                payload['badge_color_secondary'] = None
        if traits is not None:
            payload['traits'] = [trait.to_dict() for trait in traits]
        if visibility is not None:
            payload['visibility'] = visibility.value
        if discovery_splash is not None:
            payload['custom_banner'] = _bytes_to_base64_data(discovery_splash.fp.read())

        data = await self._state.http.edit_guild_profile(self.id, **payload)
        self._update(data)
        return self

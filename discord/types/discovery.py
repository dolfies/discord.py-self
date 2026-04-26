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
from typing import List, Literal, TypedDict, Optional
from .snowflake import Snowflake
from .activity import GameActivity
from .guild import PremiumTier

# fmt: off
GuildProfileBadge = Literal[
    0, 1, 2, 3, 4, 5, 6, 7, 
    8, 9, 10, 11, 12, 13, 14, 
    15, 16, 17, 18, 19, 20, 21, 
    22, 23, 24, 25, 26, 27, 28, 
    29, 30
]
GuildVisibility = Literal[0, 1, 2]
# fmt: on


class GuildProfile(TypedDict):
    id: Snowflake
    name: str
    icon_hash: Optional[str]
    member_count: int
    online_count: int
    description: str
    brand_color_primary: str
    game_application_ids: list[Snowflake]
    game_activity: dict[Snowflake, GameActivity]
    tag: Optional[str]
    badge: GuildProfileBadge
    badge_color_primary: str
    badge_color_secondary: str
    badge_hash: str
    traits: list[GuildProfileTrait]
    features: List[str]  # only community features
    visibility: GuildVisibility
    custom_banner_hash: Optional[str]
    premium_subscription_count: int
    premium_tier: PremiumTier


class GuildProfileTrait(TypedDict):
    emoji_id: Optional[Snowflake]
    emoji_name: Optional[str]
    emoji_animated: bool
    label: str
    position: int

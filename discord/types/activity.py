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

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict, Union
from typing_extensions import NotRequired
from .user import PartialUser
from .snowflake import Snowflake


StatusType = Literal['idle', 'dnd', 'online', 'offline']
StatusDisplayType = Literal[0, 1, 2]


class UserID(TypedDict):
    id: Snowflake


class BasePresenceUpdate(TypedDict):
    status: StatusType
    activities: List[Activity]
    hidden_activities: NotRequired[List[Activity]]
    client_status: ClientStatus
    processed_at_timestamp: Union[Literal[0], str]


class UserPresenceUpdate(BasePresenceUpdate):
    user: PartialUser


class PartialPresenceUpdate(BasePresenceUpdate):
    user: Union[PartialUser, UserID]
    guild_id: NotRequired[Snowflake]


class ClientStatus(TypedDict, total=False):
    desktop: StatusType
    mobile: StatusType
    web: StatusType
    embedded: StatusType


class ActivityTimestamps(TypedDict, total=False):
    start: int
    end: int


class ActivityParty(TypedDict, total=False):
    id: str
    size: List[int]


class ActivityAssets(TypedDict, total=False):
    large_image: str
    large_text: str
    small_image: str
    small_text: str
    large_url: str
    small_url: str
    invite_cover_image: str


class ActivitySecrets(TypedDict, total=False):
    join: str
    spectate: str


class ActivitySecret(TypedDict):
    secret: str


class ActivityEmoji(TypedDict):
    name: Optional[str]
    id: Optional[Snowflake]
    animated: NotRequired[bool]


ActivityType = Literal[0, 1, 2, 3, 4, 5, 6]


class _BaseActivity(TypedDict):
    name: str
    type: ActivityType

    # Receive-only fields
    id: NotRequired[str]
    created_at: NotRequired[int]


class Activity(_BaseActivity, total=False):
    url: Optional[str]
    state: Optional[str]
    details: Optional[str]
    timestamps: ActivityTimestamps
    platform: Optional[str]
    supported_platforms: List[str]
    assets: ActivityAssets
    party: ActivityParty
    application_id: Snowflake
    flags: int
    emoji: ActivityEmoji
    secrets: ActivitySecrets
    metadata: NotRequired[Dict[str, Any]]
    session_id: Optional[str]
    instance: bool
    buttons: List[str]
    sync_id: str
    state_url: str
    details_url: str
    status_display_type: Optional[StatusDisplayType]


HangStatusVariantType = Literal['illocons', 'twemoji', 'twemojimild']


class SettingsActivity(TypedDict, total=False):
    text: str
    emoji_id: Snowflake
    emoji_name: str
    expires_at: str

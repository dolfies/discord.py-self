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

from enum import Enum
from typing import List, NamedTuple, Optional, Tuple, TypedDict


class ExperimentInfo(TypedDict):
    fingerprint: str
    assignments: List[UserExperimentAssignment]
    guild_experiments: List[GuildExperiment]

class GuildExperiment(TypedDict):
    hash: int
    hash_key: Optional[str]
    revision: int
    populations: List[Population]
    overrides: List[Override]
    overrides_formatted: List[List[Population]]
    holdout: Optional[Holdout]
    aa_mode: bool

class Population(TypedDict):
    rollouts: List[Rollout]
    filters: Filters

class Rollout(TypedDict):
    bucket: int
    ranges: Tuple[int, int]

class Filters(TypedDict):
    features: Optional[List[str]]
    id_range: Optional[Tuple[int, int]]
    member_count: Tuple[int, int]
    ids: Optional[Tuple[int, int]]
    hub_types: Optional[List[int]]
    range_by_hash: Optional[RangeByHashFilter]
    vanity_url: Optional[bool]

class FilterType(Enum):
    FEATURE = 1604612045
    ID_RANGE = 2404720969
    MEMBER_COUNT = 2918402255
    ID_LIST = 30137718
    HUB_TYPE = 4148745523
    VANITY_URL = 188952590
    RANGE_BY_HASH = 2294888943 

class RangeByHashFilter(NamedTuple):
    hash_key: int
    target: int

class Override(NamedTuple):
    bucket: int
    ids: List[int]

class Holdout(NamedTuple):
    bucket: int
    experiment_name: str

class UserExperimentAssignment(TypedDict):
    hash_key: int
    revision: int
    bucket: int
    override: int
    population: int
    hash_result: int
    aa_mode: int
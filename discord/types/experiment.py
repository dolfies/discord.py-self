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

from typing import List, Literal, Optional, Tuple, TypedDict, Union

from typing_extensions import NotRequired


class ExperimentResponse(TypedDict):
    fingerprint: NotRequired[str]
    assignments: List[UserExperimentAssignment]


class ExperimentResponseWithGuild(ExperimentResponse):
    guild_experiments: NotRequired[List[GuildExperiment]]


class RolloutData(TypedDict):
    s: int
    e: int


Rollout = Tuple[int, List[RolloutData]]

FilterType = Literal[
    1604612045,  # FEATURE
    2404720969,  # ID_RANGE
    2918402255,  # MEMBER_COUNT
    30137718,  # ID_LIST
    4148745523,  # HUB_TYPE
    188952590,  # VANITY_URL
    2294888943,  # RANGE_BY_HASH
]

_ExperimentBoolean = Literal[0, 1]

Filters = Union[
    Tuple[Literal[1604612045], Tuple[Tuple[int, List[str]]]],  # FEATURE
    Tuple[Literal[2404720969], Tuple[Tuple[int, Optional[int]], Tuple[int, int]]],  # ID_RANGE
    Tuple[Literal[2918402255], Tuple[Tuple[int, Optional[int]], Tuple[int, int]]],  # MEMBER_COUNT
    Tuple[Literal[30137718], Tuple[Tuple[int, List[int]]]],  # ID_LIST
    Tuple[Literal[4148745523], Tuple[Tuple[int, List[int]]]],  # HUB_TYPE
    Tuple[Literal[188952590], Tuple[Tuple[Literal[188952590], bool]]],  # VANITY_URL
    Tuple[Literal[2294888943], Tuple[Tuple[int, int], Tuple[int, int]]],  # RANGE_BY_HASH
]


Population = Tuple[
    List[Rollout],  # rollouts
    List[Filters],  # filters
]


Override = Tuple[
    int,  # bucket
    List[int],  # ids
]


Holdout = Tuple[
    int,  # bucket
    str,  # experiment_name
]


UserExperimentAssignment = Tuple[
    int,  # hash
    int,  # revision
    int,  # bucket
    int,  # override
    int,  # population
    int,  # hash_result
    _ExperimentBoolean,  # aa_mode
]


GuildExperiment = Tuple[
    int,  # hash
    Optional[str],  # hash_key
    int,  # revision
    List[Population],  # populations
    List[Override],  # overrides
    List[List[Population]],  # overrides_formatted
    Optional[str],  # holdout name
    Optional[int],  # holdout bucket
    _ExperimentBoolean,  # aa_mode
]

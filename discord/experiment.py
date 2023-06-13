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
from typing import List, Optional, Tuple


from .types.experiment import (
    GuildExperiment as RawExperiment,
    Override,
    Population,
    UserExperimentAssignment as RawAssignment,
)


class FilterTypes(Enum):
    FEATURE = 1604612045
    ID_RANGE = 2404720969
    MEMBER_COUNT = 2918402255
    ID_LIST = 30137718
    HUB_TYPE = 4148745523
    VANITY_URL = 188952590
    RANGE_BY_HASH = 2294888943


class GuildExperiment:
    def __init__(self, data: RawExperiment):
        (
            hash_key,
            name,
            revision,
            populations,
            overrides,
            overrides_formatted,
            holdout_name,
            holdout_bucket,
            aa_mode,
        ) = data

        self.hash_key: int = hash_key
        self.name: Optional[str] = name
        self.revision: int = revision
        self.populations: List[Population] = populations
        self.overrides: List[Override] = overrides
        self.overrides_formatted: List[List[Population]] = overrides_formatted
        self.holdout: Optional[Tuple[str, int]] = (holdout_name, holdout_bucket) if holdout_name is not None else None
        self.aa_mode: bool = True if aa_mode == 1 else False

    def __repr__(self) -> str:
        return f'<GuildExperiment hash_key={self.hash_key} name={self.name}>'

    # FIXME(splatterxl): find a way to type `guild` as guild.Guild without crashing the whole thing
    def guild_bucket(self, guild) -> int:
        """
        Returns the assigned experiment bucket for a :class:`Guild`.

        Parameters
        -----------
        guild: :class:`Guild`
            The guild to compute experiment eligibility for.

        Returns
        -------
        int
            The experiment bucket.

        Raises
        ------
        ImportError
            The `mmh3` library is not installed (required for hash computation).
        """

        if self.aa_mode:
            return -1

        try:
            import mmh3
        except ImportError:
            raise ImportError("`GuildExperiment` requires the `mmh3` library to compute cryptographic hashes.")

        hash = mmh3.hash("foo", signed=False) % 1e4

        bucket = -1

        def handle_population(population: Population):
            (rollouts, filters) = population

            for type, value in filters:
                if type == FilterTypes.FEATURE:
                    ((_, features)) = value
                    for feature in features:
                        if feature in guild.features:
                            continue
                        else:
                            return -1
                elif type == FilterTypes.ID_RANGE:
                    ((_, start), (_, end)) = value
                    if start is not None and start <= guild.id <= end:
                        continue
                    elif start is None and guild.id <= end:
                        continue
                    else:
                        return -1
                elif type == FilterTypes.MEMBER_COUNT:
                    ((_, start), (_, end)) = value
                    if start is not None and start <= guild.member_count <= end:
                        continue
                    elif start is None and guild.member_count <= end:
                        continue
                    else:
                        return -1
                elif type == FilterTypes.ID_LIST:
                    ((_, ids)) = value
                    if guild.id in ids:
                        continue
                    else:
                        return -1
                elif type == FilterTypes.HUB_TYPE:
                    # no clue how this one works
                    pass
                elif type == FilterTypes.RANGE_BY_HASH:
                    # this one either
                    pass
                elif type == FilterTypes.VANITY_URL:
                    ((_, has_vanity)) = value
                    vanity_url = guild.vanity_url
                    if has_vanity == True:
                        if vanity_url is not None:
                            continue
                        else:
                            return -1
                    else:
                        if vanity_url is None:
                            continue
                        else:
                            return -1
                else:
                    raise NotImplementedError(f"Unknown filter type: {type}")

            for bucket, rollouts in rollouts:
                for rollout in rollouts:
                    if rollout.s <= hash <= rollout.e:
                        return bucket
                    else:
                        continue

            return -1

        for population in self.populations:
            pop_bucket = handle_population(population)

            bucket = pop_bucket if pop_bucket != -1 else bucket

        for overrides in self.overrides_formatted:
            for override in overrides:
                pop_bucket = handle_population(override)

                bucket = pop_bucket if pop_bucket != -1 else bucket

        for override_bucket, ids in self.overrides:
            if guild.id in ids or guild.owner_id in ids:
                bucket = override_bucket

        return bucket


class UserExperimentAssignment:
    def __init__(self, data: RawAssignment):
        print(data)

        (hash_key, revision, bucket, override, population, hash_result, aa_mode) = data

        self.hash_key: int = hash_key
        self.revision: int = revision
        self._bucket: int = bucket
        self.override: int = override
        self.population: int = population
        self.hash_result: int = hash_result
        self.aa_mode: bool = True if aa_mode == 1 else False

    def __repr__(self) -> str:
        return f'<UserExperimentAssignment hash_key={self.hash_key} bucket={self.bucket}>'

    @property
    def bucket(self) -> int:
        return -1 if self.aa_mode else self._bucket

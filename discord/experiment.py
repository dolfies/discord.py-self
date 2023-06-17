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

from typing import TYPE_CHECKING, List, NamedTuple, Optional

if TYPE_CHECKING:
    from .types.experiment import (
        GuildExperiment as GuildExperimentPayload,
        Override,
        Population,
        UserExperiment as AssignmentPayload,
    )
    from .guild import Guild

from .utils import hash
from .enums import ExperimentFilterType

class ExperimentHoldout(NamedTuple):
    name: str
    bucket: int

class GuildExperiment:
    def __init__(self, data: GuildExperimentPayload):
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
        self.holdout: Optional[ExperimentHoldout] = (
            ExperimentHoldout(holdout_name, holdout_bucket)
            if (holdout_name is not None and holdout_bucket is not None)
            else None
        )
        self.aa_mode: bool = aa_mode == 1

    def __repr__(self) -> str:
        return f"<GuildExperiment hash_key={self.hash_key} name={self.name}>"

    def handle_population(self, *, population: Population, guild: Guild, hash_result: int) -> int:
        (rollouts, filters) = population

        for type_, value in filters:
            if type_ == ExperimentFilterType.FEATURE:
                features = value[0][1]
                for feature in features: # type: ignore
                    if feature in guild.features:
                        continue
                    else:
                        return -1
            elif type_ == ExperimentFilterType.ID_RANGE:
                ((_, start), (_, end)) = value # type: ignore
                if start is not None and start <= guild.id <= end: # type: ignore -- start, end will always be int
                    continue
                elif start is None and guild.id <= end:
                    continue
                else:
                    return -1
            elif type_ == ExperimentFilterType.MEMBER_COUNT:
                ((_, start), (_, end)) = value # type: ignore

                if guild.member_count is None: continue

                if start is not None and start <= guild.member_count <= end: # type: ignore -- same here
                    continue
                elif start is None and guild.member_count <= end:
                    continue
                else:
                    return -1
            elif type_ == ExperimentFilterType.ID_LIST:
                ids = value[0][1]
                if guild.id in ids: # type: ignore -- same here
                    continue
                else:
                    return -1
            # TODO: when hubs are implemented add HUB_TYPE
            elif type_ == ExperimentFilterType.HUB_TYPE or type_ == ExperimentFilterType.RANGE_BY_HASH:
                # checks for these filters are unknown
                pass
            elif type_ == ExperimentFilterType.VANITY_URL:
                has_vanity = bool(guild.vanity_url_code)
                if value[0][1] != bool(guild.vanity_url_code):
                    return -1
            else:
                raise NotImplementedError(f"Unknown filter type: {type_}")

        for bucket, rollouts in rollouts:
            for rollout in rollouts:
                if rollout['s'] <= hash_result <= rollout['e']:
                    return bucket
                else:
                    continue

        return -1

    def bucket_for(self, guild: Guild) -> int:
        """
        Returns the assigned experiment bucket for a :class:`Guild`.

        Parameters
        -----------
        guild: :class:`.Guild`
            The guild to compute experiment eligibility for.

        Returns
        -------
        :class:`int`
            The experiment bucket.
        """

        if self.aa_mode:
            return -1

        hash_result = hash(f"{self.name}:{guild.id}")

        bucket = -1

        for population in self.populations:
            pop_bucket = self.handle_population(population=population, guild=guild, hash_result=hash_result)

            bucket = pop_bucket if pop_bucket != -1 else bucket

        for overrides in self.overrides_formatted:
            for override in overrides:
                pop_bucket = self.handle_population(population=override, guild=guild, hash_result=hash_result)

                bucket = pop_bucket if pop_bucket != -1 else bucket

        for override_bucket, ids in self.overrides:
            if guild.id in ids or guild.owner_id in ids:
                bucket = override_bucket

        return bucket


class UserExperiment:
    def __init__(self, data: AssignmentPayload):
        (hash_key, revision, bucket, override, population, hash_result, aa_mode) = data

        self.hash_key: int = hash_key
        self.revision: int = revision
        self._bucket: int = bucket
        self.override: int = override
        self.population: int = population
        self.hash_result: int = hash_result
        self.aa_mode: bool = True if aa_mode == 1 else False

    def __repr__(self) -> str:
        return (
            f"<UserExperimentAssignment hash_key={self.hash_key} bucket={self.bucket}>"
        )

    @property
    def bucket(self) -> int:
        return -1 if self.aa_mode else self._bucket

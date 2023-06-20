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

from typing import TYPE_CHECKING, List, NamedTuple, Optional, TypedDict

from .utils import murmurhash32
from .enums import ExperimentFilterType

if TYPE_CHECKING:
    from .types.experiment import (
        GuildExperiment as GuildExperimentPayload,
        Override as OverridePayload,
        UserExperiment as AssignmentPayload,
        Population as PopulationPayload,
        Filters,
        Rollout,
    )
    from .guild import Guild

class ExperimentHoldout(NamedTuple):
    name: str
    bucket: int

class Population:
    filters: List[Filters]
    rollouts: List[Rollout]

    def __init__(self, data: PopulationPayload):
        (rollouts, filters) = data

        self.filters: List[Filters] = filters
        self.rollouts: List[Rollout] = rollouts

class Override:
    bucket: int
    ids: List[int]

    def __init__(self, data: OverridePayload):
        self.bucket = data['b']
        self.ids = data['k']

class GuildExperiment:
    def __init__(self, data: GuildExperimentPayload):
        (
            hash,
            hash_key,
            revision,
            populations,
            overrides,
            overrides_formatted,
            holdout_name,
            holdout_bucket,
            aa_mode,
        ) = data

        self.hash: int = hash
        self.name: Optional[str] = hash_key
        self.revision: int = revision
        self.populations: List[Population] = list(map(lambda x: Population(x), populations))
        self.overrides: List[Override] = list(map(lambda x: Override(x), overrides))
        self.overrides_formatted: List[List[Population]] = list(map(lambda x: list(map(lambda y: Population(y), x)), overrides_formatted))
        self.holdout: Optional[ExperimentHoldout] = (
            ExperimentHoldout(holdout_name, holdout_bucket)
            if (holdout_name is not None and holdout_bucket is not None)
            else None
        )
        self.aa_mode: bool = aa_mode == 1

    def __repr__(self) -> str:
        return f'<GuildExperiment hash_key={self.hash} name={self.name}>'

    def __hash__(self) -> int:
        return self.hash
    
    def __eq__(self, __value: object) -> bool:
        return isinstance(__value, GuildExperiment) and self.hash == __value.hash
    
    def __ne__(self, __value: object) -> bool:
        return not self == __value

    def handle_population(self, *, population: Population, guild: Guild, hash_result: int) -> int:
        for type_, value in population.filters:
            if type_ == ExperimentFilterType.feature:
                features = value[0][1]
                for feature in features: # type: ignore
                    if feature in guild.features:
                        continue
                    else:
                        return -1
            elif type_ == ExperimentFilterType.id_range:
                ((_, start), (_, end)) = value # type: ignore
                if start is not None and start <= guild.id <= end: # type: ignore -- start, end will always be int
                    continue
                elif start is None and guild.id <= end:
                    continue
                else:
                    return -1
            elif type_ == ExperimentFilterType.member_count:
                ((_, start), (_, end)) = value # type: ignore

                if guild.member_count is None: continue

                if start is not None and start <= guild.member_count <= end: # type: ignore -- same here
                    continue
                elif start is None and guild.member_count <= end:
                    continue
                else:
                    return -1
            elif type_ == ExperimentFilterType.id_list:
                ids = value[0][1]
                if guild.id in ids: # type: ignore -- same here
                    continue
                else:
                    return -1
            # TODO: when hubs are implemented add HUB_TYPE
            elif type_ == ExperimentFilterType.hub_type or type_ == ExperimentFilterType.range_by_hash:
                # checks for these filters are unknown
                pass
            elif type_ == ExperimentFilterType.vanity_url:
                has_vanity = bool(guild.vanity_url_code)
                if value[0][1] != bool(guild.vanity_url_code):
                    return -1
            else:
                raise NotImplementedError(f"Unknown filter type: {type_}")

        for bucket, rollouts in population.rollouts:
            for rollout in rollouts:
                if rollout['s'] <= hash_result <= rollout['e']:
                    return bucket
                else:
                    continue

        return -1

    def bucket_for(self, guild: Guild) -> int:
        """Returns the assigned experiment bucket for a :class:`Guild`.

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

        hash_result = murmurhash32(f'{self.name or self.hash}:{guild.id}') % 1e4

        bucket = -1

        for population in self.populations:
            pop_bucket = self.handle_population(population=population, guild=guild, hash_result=hash_result)

            bucket = pop_bucket if pop_bucket != -1 else bucket

        for overrides in self.overrides_formatted:
            for override in overrides:
                pop_bucket = self.handle_population(population=override, guild=guild, hash_result=hash_result)

                bucket = pop_bucket if pop_bucket != -1 else bucket

        for override in self.overrides:
            ids = override.ids
            if guild.id in ids or guild.owner_id in ids:
                bucket = override.bucket

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

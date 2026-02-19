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

from typing import TYPE_CHECKING, Dict, Final, Iterator, List, Optional, Sequence, Tuple, Union

from .enums import ApexExperimentUnitType, HubType, try_enum
from .flags import ApexExperimentFlags
from .metadata import Metadata
from .utils import SequenceProxy, SnowflakeList, cached_slot_property, murmurhash32, utcnow

if TYPE_CHECKING:
    from .abc import Snowflake
    from .client import Client
    from .guild import Guild
    from .state import ConnectionState
    from .types.experiment import (
        Filters as FiltersPayload,
        GuildExperiment as GuildExperimentPayload,
        Override as OverridePayload,
        Population as PopulationPayload,
        Rollout as RolloutPayload,
        UserExperiment as AssignmentPayload,
        ApexExperimentResponse as ApexExperimentResponsePayload,
        ApexExperimentAssignment as ApexExperimentAssignmentPayload,
    )

__all__ = (
    'ExperimentRollout',
    'ExperimentFilters',
    'ExperimentPopulation',
    'ExperimentOverride',
    'HoldoutExperiment',
    'GuildExperiment',
    'UserExperiment',
    'ApexExperimentAssignment',
    'ApexExperiment',
)


class ExperimentRollout:
    """Represents a rollout for an experiment population.

    .. container:: operations

        .. describe:: x in y

            Checks if a position is eligible for the rollout.

    .. versionadded:: 2.1

    Attributes
    -----------
    population: :class:`ExperimentPopulation`
        The population this rollout belongs to.
    bucket: :class:`int`
        The bucket the rollout grants.
    ranges: List[Tuple[:class:`int`, :class:`int`]]
        The position ranges of the rollout.
    """

    __slots__ = ('population', 'bucket', 'ranges')

    def __init__(self, population: ExperimentPopulation, data: RolloutPayload):
        bucket, ranges = data

        self.population = population
        self.bucket: int = bucket
        self.ranges: List[Tuple[int, int]] = [(range['s'], range['e']) for range in ranges]

    def __repr__(self) -> str:
        return f'<ExperimentRollout bucket={self.bucket} ranges={self.ranges!r}>'

    def __contains__(self, item: int, /) -> bool:
        for start, end in self.ranges:
            if start <= item <= end:
                return True
        return False


class ExperimentFilters:
    """Represents a number of filters for an experiment population.
    A guild must fulfill all filters to be eligible for the population.

    This is a purposefuly very low-level object.

    .. container:: operations

        .. describe:: x in y

            Checks if a guild fulfills the filter requirements.

    .. versionadded:: 2.1

    Attributes
    -----------
    population: :class:`ExperimentPopulation`
        The population this filter belongs to.
    options: :class:`Metadata`
        The parameters for the filter. If known, murmur3-hashed keys are unhashed to their original names.

        .. note::

            You should query parameters via the properties rather than using this directly.
    """

    __slots__ = ('population', 'options')

    # Most of these are taken from the client
    FILTER_KEYS: Final[Dict[int, str]] = {
        1604612045: 'guild_has_feature',
        2404720969: 'guild_id_range',
        3730341874: 'guild_age_range_days',
        2918402255: 'guild_member_count_range',
        3013771838: 'guild_ids',
        4148745523: 'guild_hub_types',
        188952590: 'guild_has_vanity_url',
        2294888943: 'guild_in_range_by_hash',
        3399957344: 'min_id',
        1238858341: 'max_id',
        2690752156: 'hash_key',
        1982804121: 'target',
        1183251248: 'guild_features',
    }

    def __init__(self, population: ExperimentPopulation, data: FiltersPayload):
        self.population = population
        self.options: Metadata = self.array_object(data)

    def __repr__(self) -> str:
        keys = (
            'features',
            'id_range',
            'age_range',
            'member_count_range',
            'ids',
            'hub_types',
            'range_by_hash',
            'has_vanity_url',
        )
        attrs = [f'{attr}={getattr(self, attr)!r}' for attr in keys if getattr(self, attr) is not None]
        if attrs:
            return f'<ExperimentFilters {" ".join(attrs)}>'
        return '<ExperimentFilters>'

    def __contains__(self, guild: Guild, /) -> bool:
        return self.is_eligible(guild)

    @classmethod
    def array_object(cls, array: list) -> Metadata:
        metadata = Metadata()
        for key, value in array:
            try:
                key = cls.FILTER_KEYS[int(key)]
            except (KeyError, ValueError):
                pass
            if isinstance(value, str) and value.isdigit():
                value = int(value)
            elif value and isinstance(value, list) and isinstance(value[0], list):
                value = cls.array_object(value)
            metadata[str(key)] = value
        return metadata

    @staticmethod
    def in_range(num: float, start: Optional[float], end: Optional[float], /) -> bool:
        if start is not None and num < start:
            return False
        if end is not None and num > end:
            return False
        return True

    @property
    def features(self) -> Optional[List[str]]:
        """Optional[List[:class:`str`]]: The guild features that are eligible for the population."""
        features_filter = self.options.guild_has_feature
        if features_filter is not None:
            return features_filter.guild_features

    @property
    def id_range(self) -> Optional[Tuple[Optional[int], Optional[int]]]:
        """Optional[Tuple[Optional[:class:`int`], Optional[:class:`int`]]]: The range of guild IDs that are eligible for the population."""
        id_range_filter = self.options.guild_id_range
        if id_range_filter is not None:
            return id_range_filter.min_id, id_range_filter.max_id

    @property
    def age_range(self) -> Optional[Tuple[Optional[int], Optional[int]]]:
        """Optional[Tuple[Optional[:class:`int`], Optional[:class:`int`]]]: The range of guild ages that are eligible for the population."""
        age_range_filter = self.options.guild_age_range_days
        if age_range_filter is not None:
            return age_range_filter.min_id, age_range_filter.max_id

    @property
    def member_count_range(self) -> Optional[Tuple[Optional[int], Optional[int]]]:
        """Optional[Tuple[Optional[:class:`int`], Optional[:class:`int`]]]: The range of guild member counts that are eligible for the population."""
        member_count_range_filter = self.options.guild_member_count_range
        if member_count_range_filter is not None:
            return member_count_range_filter.min_id, member_count_range_filter.max_id

    @property
    def ids(self) -> Optional[List[int]]:
        """Optional[List[:class:`int`]]: The guild IDs that are eligible for the population."""
        ids_filter = self.options.guild_ids
        if ids_filter is not None:
            return ids_filter.guild_ids

    @property
    def hub_types(self) -> Optional[List[HubType]]:
        """Optional[List[:class:`HubType`]]: The Student Hub types that are eligible for the population."""
        hub_types_filter = self.options.guild_hub_types
        if hub_types_filter is not None:
            return [try_enum(HubType, hub_type) for hub_type in hub_types_filter.guild_hub_types]

    @property
    def range_by_hash(self) -> Optional[Tuple[int, int]]:
        """Optional[Tuple[:class:`int`, :class:`int`]]: The special rollout position limits on the population."""
        range_by_hash_filter = self.options.guild_in_range_by_hash
        if range_by_hash_filter is not None:
            return range_by_hash_filter.hash_key, range_by_hash_filter.target

    @property
    def has_vanity_url(self) -> Optional[bool]:
        """Optional[:class:`bool`]: Whether a vanity is or is not required to be eligible for the population."""
        has_vanity_url_filter = self.options.guild_has_vanity_url
        if has_vanity_url_filter is not None:
            return has_vanity_url_filter.target

    def is_eligible(self, guild: Guild, /) -> bool:
        """Checks whether the guild fulfills the filter requirements.

        .. note::

            This function is not intended to be used directly. Instead, use :func:`GuildExperiment.bucket_for`.

        Parameters
        -----------
        guild: :class:`Guild`
            The guild to check.

        Returns
        --------
        :class:`bool`
            Whether the guild fulfills the filter requirements.
        """
        features = self.features
        if features is not None:
            # At least one feature must be present
            if not any(feature in guild.features for feature in features):
                return False

        id_range = self.id_range
        if id_range is not None:
            # Guild must be within the range of snowflakes
            if not self.in_range(guild.id, *id_range):
                return False

        age_range = self.age_range
        if age_range is not None:
            # Guild must be within the range of ages (in days)
            if not self.in_range((utcnow() - guild.created_at).days, *age_range):
                return False

        member_count_range = self.member_count_range
        if member_count_range is not None and guild.member_count is not None:
            # Guild must be within the range of member counts
            if not self.in_range(guild.member_count, *member_count_range):
                return False

        ids = self.ids
        if ids is not None:
            # Guild must be in the list of snowflakes, similar to ExperimentOverride
            if guild.id not in ids:
                return False

        hub_types = self.hub_types
        if hub_types is not None:
            # Guild must be a hub in the list of hub types
            if not guild.hub_type or guild.hub_type not in hub_types:
                return False

        range_by_hash = self.range_by_hash
        if range_by_hash is not None:
            # Guild must fulfill the additional population requirements
            hash_key, target = range_by_hash
            result = murmurhash32(f'{hash_key}:{guild.id}', signed=False)
            if result > 0:
                result += result
            else:
                result = (result % 0x100000000) >> 0
            if target and (result % 10000) >= target:
                return False

        has_vanity_url = self.has_vanity_url
        if has_vanity_url is not None:
            # Guild must or must not have a vanity URL
            if not bool(guild.vanity_url_code) == has_vanity_url:
                return False

        return True


class ExperimentPopulation:
    """Represents a population of an experiment.

    .. container:: operations

        .. describe:: x in y

            Checks if a guild is present in the population.

    .. versionadded:: 2.1

    Attributes
    -----------
    experiment: :class:`GuildExperiment`
        The experiment this population belongs to.
    filters: :class:`ExperimentFilters`
        The filters that apply to the population.
    rollouts: List[Tuple[:class:`int`, :class:`int`]]
        The position-based rollouts of the population.
    """

    __slots__ = ('experiment', 'filters', 'rollouts')

    def __init__(self, experiment: GuildExperiment, data: PopulationPayload):
        rollouts, filters = data

        self.experiment = experiment
        self.filters: ExperimentFilters = ExperimentFilters(self, filters)
        self.rollouts: List[ExperimentRollout] = [ExperimentRollout(self, x) for x in rollouts]

    def __repr__(self) -> str:
        return f'<ExperimentPopulation experiment={self.experiment!r} filters={self.filters!r} rollouts={self.rollouts!r}>'

    def __contains__(self, item: Guild, /) -> bool:
        return self.bucket_for(item) != -1

    def is_eligible(self, guild: Guild, /) -> bool:
        """Checks whether the guild is eligible for the population.

        .. note::

            This function is not intended to be used directly. Instead, use :func:`GuildExperiment.bucket_for`.

        Parameters
        -----------
        guild: :class:`Guild`
            The guild to check.

        Returns
        --------
        :class:`bool`
            Whether the guild is eligible for the population.
        """
        return self.filters.is_eligible(guild)

    def bucket_for(self, guild: Guild, _result: Optional[int] = None, /) -> int:
        """Returns the assigned experiment bucket within a population for a guild.
        Defaults to None (-1) if the guild is not in the population.

        .. note::

            This function is not intended to be used directly. Instead, use :func:`GuildExperiment.bucket_for`.

        Parameters
        -----------
        guild: :class:`Guild`
            The guild to compute experiment eligibility for.

        Raises
        ------
        :exc:`ValueError`
            The experiment name is unset.

        Returns
        -------
        :class:`int`
            The experiment bucket.
        """
        if not self.filters.is_eligible(guild):
            return -1

        if _result is None:
            _result = self.experiment.result_for(guild)

        for rollout in self.rollouts:
            for start, end in rollout.ranges:
                if start <= _result <= end:
                    return rollout.bucket

        return -1


class ExperimentOverride:
    """Represents an experiment override.

    .. container:: operations

        .. describe:: len(x)

            Returns the number of resources eligible for the override.

        .. describe:: x in y

            Checks if a resource is eligible for the override.

        .. describe:: iter(x)

            Returns an iterator of the resources eligible for the override.

    .. versionadded:: 2.1

    Attributes
    -----------
    experiment: :class:`GuildExperiment`
        The experiment this override belongs to.
    bucket: :class:`int`
        The bucket the override applies.
    """

    __slots__ = ('experiment', 'bucket', '_ids')

    def __init__(self, experiment: GuildExperiment, data: OverridePayload):
        self.experiment = experiment
        self.bucket: int = data['b']
        self._ids: SnowflakeList = SnowflakeList(map(int, data['k']))

    def __repr__(self) -> str:
        return f'<ExperimentOverride bucket={self.bucket} ids={self.ids!r}>'

    def __len__(self) -> int:
        return len(self._ids)

    def __contains__(self, item: Union[int, Snowflake], /) -> bool:
        if isinstance(item, int):
            return item in self._ids
        return item.id in self._ids

    def __iter__(self) -> Iterator[int]:
        return iter(self._ids)

    @property
    def ids(self) -> Sequence[int]:
        """Sequence[:class:`int`]: The eligible guild IDs for the override."""
        return SequenceProxy(self._ids)


class HoldoutExperiment:
    """Represents an experiment holdout.

    .. container:: operations

        .. describe:: x in y

            Checks if a guild fulfills the dependency.

    .. versionadded:: 2.1

    Attributes
    -----------
    dependent: :class:`GuildExperiment`
        The experiment that this holdout blocks.
    name: :class:`str`
        The name of the dependency.
    bucket: :class:`int`
        The required bucket of the dependency.
    """

    __slots__ = ('dependent', 'name', 'bucket', '_hash')

    def __init__(self, dependent: GuildExperiment, name: str, bucket: int):
        self.dependent = dependent
        self.name: str = name
        self.bucket: int = bucket

    def __repr__(self) -> str:
        return f'<HoldoutExperiment name={self.name!r} bucket={self.bucket}>'

    def __contains__(self, item: Guild) -> bool:
        return self.is_blocked(item)

    @cached_slot_property('_hash')
    def hash(self) -> int:
        """:class:`int`: The 32-bit unsigned Murmur3 hash of the dependency name."""
        return murmurhash32(self.name, signed=False)

    @property
    def experiment(self) -> Optional[GuildExperiment]:
        """Optional[:class:`GuildExperiment`]: The experiment dependency, if found."""
        experiment = self.dependent._state.guild_experiments.get(self.hash)
        if experiment and not experiment.name:
            # Backfill the name
            experiment._name = self.name
        return experiment

    def is_blocked(self, guild: Guild, /) -> bool:
        """Checks whether the guild is blocked by the holdout.

        .. note::

            This function is not intended to be used directly. Instead, use :func:`GuildExperiment.bucket_for`.

        Parameters
        -----------
        guild: :class:`Guild`
            The guild to check.

        Returns
        --------
        :class:`bool`
            Whether the guild is blocked by the holdout.
        """
        experiment = self.experiment
        if self.hash == self.dependent.hash or experiment is None:
            # We don't have the experiment so there is no holdout
            return False

        return experiment.bucket_for(guild) == self.bucket


class GuildExperiment:
    """Represents a guild experiment rollout.

    .. container:: operations

        .. describe:: x == y

            Checks if two experiments are equal.

        .. describe:: x != y

            Checks if two experiments are not equal.

        .. describe:: hash(x)

            Returns the experiment's hash.

    .. versionadded:: 2.1

    Attributes
    -----------
    hash: :class:`int`
        The 32-bit unsigned Murmur3 hash of the experiment's name.
    revision: :class:`int`
        The current revision of the experiment rollout.
    populations: List[:class:`ExperimentPopulation`]
        The rollout populations of the experiment.
    overrides: List[:class:`ExperimentOverride`]
        The explicit bucket overrides of the experiment.
    overrides_formatted: List[List[:class:`ExperimentPopulation`]]
        Additional rollout populations for the experiment.
    holdout: Optional[:class:`HoldoutExperiment`]
        An experiment that blocks the rollout of this experiment.
    aa_mode: :class:`bool`
        Whether the experiment is in A/A mode.
    trigger_debugging: :class:`bool`
        Whether experiment analytics trigger debugging is enabled.
    """

    __slots__ = (
        '_state',
        'hash',
        '_name',
        'revision',
        'populations',
        'overrides',
        'overrides_formatted',
        'holdout',
        'aa_mode',
        'trigger_debugging',
    )

    def __init__(self, *, state: ConnectionState, data: GuildExperimentPayload):
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
            trigger_debugging,
            *_,
        ) = data

        self._state = state
        self.hash: int = hash
        self._name: Optional[str] = hash_key
        self.revision: int = revision
        self.populations: List[ExperimentPopulation] = [ExperimentPopulation(self, x) for x in populations]
        self.overrides: List[ExperimentOverride] = [ExperimentOverride(self, x) for x in overrides]
        self.overrides_formatted: List[List[ExperimentPopulation]] = [
            [ExperimentPopulation(self, y) for y in x] for x in overrides_formatted
        ]
        self.holdout: Optional[HoldoutExperiment] = (
            HoldoutExperiment(self, holdout_name, holdout_bucket)
            if holdout_name is not None and holdout_bucket is not None
            else None
        )
        self.aa_mode: bool = aa_mode == 1
        self.trigger_debugging: bool = trigger_debugging == 1

    def __repr__(self) -> str:
        return f'<GuildExperiment hash={self.hash}{f" name={self._name!r}" if self._name else ""}>'

    def __hash__(self) -> int:
        return self.hash

    def __eq__(self, other: object, /) -> bool:
        if isinstance(other, GuildExperiment):
            return self.hash == other.hash
        elif isinstance(other, UserExperiment):
            return False
        return NotImplemented

    @property
    def name(self) -> Optional[str]:
        """Optional[:class:`str`]: The unique name of the experiment.

        This data is not always available via the API, and must be set manually for using related functions.
        """
        return self._name

    @name.setter
    def name(self, value: Optional[str], /) -> None:
        if not value:
            self._name = None
        elif murmurhash32(value, signed=False) != self.hash:
            raise ValueError('The name provided does not match the experiment hash')
        else:
            self._name = value

    def result_for(self, guild: Snowflake, /) -> int:
        """Returns the calulated position of the guild within the experiment (0-9999).

        Parameters
        -----------
        guild: :class:`abc.Snowflake`
            The guild to compute the position for.

        Raises
        ------
        :exc:`ValueError`
            The experiment name is unset.

        Returns
        -------
        :class:`int`
            The position of the guild within the experiment.
        """
        if not self.name:
            raise ValueError('The experiment name must be set to compute the result')

        return murmurhash32(f'{self.name}:{guild.id}', signed=False) % 10000

    def bucket_for(self, guild: Guild, /, *, aa_mode: bool = False) -> int:
        """Returns the assigned experiment bucket for a guild.
        Defaults to None (-1) if the guild is not in the experiment.

        Parameters
        -----------
        guild: :class:`Guild`
            The guild to compute experiment eligibility for.
        aa_mode: :class:`bool`
            Whether to return the bucket for A/A mode.
            Otherwise, always returns None (-1) for populations in A/A mode.
            Does nothing if the experiment is not in A/A mode.

        Raises
        ------
        :exc:`ValueError`
            The experiment name is unset.

        Returns
        -------
        :class:`int`
            The experiment bucket.
        """
        # Overrides take precedence
        for override in self.overrides:
            if guild.id in override.ids:
                return override.bucket

        hash_result = self.result_for(guild)
        for overrides in self.overrides_formatted:
            for override in overrides:
                if override.is_eligible(guild):
                    return override.bucket_for(guild, hash_result)

        # a/a mode is always -1 without an override
        if self.aa_mode and not aa_mode:
            return -1

        # Holdout must not be fulfilled
        if self.holdout and self.holdout.is_blocked(guild):
            return -1

        for population in self.populations:
            if population.is_eligible(guild):
                return population.bucket_for(guild, hash_result)

        return -1

    def guilds_for(self, bucket: int, /) -> List[Guild]:
        """Returns a list of guilds assigned to a specific bucket.

        Parameters
        -----------
        bucket: :class:`int`
            The bucket to get guilds for.

        Raises
        ------
        :exc:`ValueError`
            The experiment name is unset.

        Returns
        -------
        List[:class:`Guild`]
            The guilds assigned to the bucket.
        """
        return [x for x in self._state.guilds if self.bucket_for(x) == bucket]


class UserExperiment:
    """Represents a user's experiment assignment.

    .. container:: operations

        .. describe:: x == y

            Checks if two experiments are equal.

        .. describe:: x != y

            Checks if two experiments are not equal.

        .. describe:: hash(x)

            Returns the experiment's hash.

    .. note::

        In contrast to the wide range of data provided for guild experiments,
        user experiments do not reveal detailed rollout information, providing only the assigned bucket.

    .. versionadded:: 2.1

    Attributes
    ----------
    hash: :class:`int`
        The 32-bit unsigned Murmur3 hash of the experiment's name.
    revision: :class:`int`
        The current revision of the experiment rollout.
    assignment: :class:`int`
        The assigned bucket for the user.
    override: :class:`bool`
        Whether the user has an explicit bucket override.
    population: :class:`int`
        The internal population group for the user, or None (-1) if manually overridden.
    holdout: Optional[:class:`UserExperiment`]
        An experiment that blocks the rollout of this experiment.
        Only present if the user has an assignment in the holdout.
    aa_mode: :class:`bool`
        Whether the experiment is in A/A mode.
    trigger_debugging: :class:`bool`
        Whether experiment analytics trigger debugging is enabled.
    """

    __slots__ = (
        '_state',
        '_name',
        'hash',
        'revision',
        'assignment',
        'override',
        'population',
        '_result',
        'aa_mode',
        'trigger_debugging',
        'holdout',
    )

    def __init__(self, *, state: ConnectionState, data: AssignmentPayload):
        (
            hash,
            revision,
            bucket,
            override,
            population,
            hash_result,
            aa_mode,
            trigger_debugging,
            holdout_name,
            holdout_revision,
            holdout_bucket,
            *_,
        ) = data

        self._state = state
        self._name: Optional[str] = None
        self.hash: int = hash
        self.revision: int = revision
        self.assignment: int = bucket
        self.override: bool = override == 0  # this is fucking weird
        self.population: int = population
        self._result: int = hash_result
        self.aa_mode: bool = aa_mode == 1
        self.trigger_debugging: bool = trigger_debugging == 1

        self.holdout: Optional[UserExperiment] = None
        if holdout_name is not None:
            holdout_hash = murmurhash32(holdout_name, signed=False)
            self.holdout = state.experiments.get(holdout_hash) or UserExperiment.from_holdout(
                state, holdout_hash, holdout_name, holdout_revision, holdout_bucket
            )

    @classmethod
    def from_holdout(
        cls, state: ConnectionState, hash: int, name: str, revision: Optional[int], bucket: Optional[int]
    ) -> UserExperiment:
        self = cls.__new__(cls)
        self._state = state
        self._name = name
        self.hash = hash
        self.revision = revision or 0
        self.assignment = bucket or -1

        # Most of these fields are defaults
        self.override = False
        self.population = 0
        self._result = -1
        self.aa_mode = False
        self.trigger_debugging = False
        self.holdout = None
        return self

    def __repr__(self) -> str:
        return f'<UserExperiment hash={self.hash}{f" name={self._name!r}" if self._name else ""} bucket={self.bucket}>'

    def __hash__(self) -> int:
        return self.hash

    def __eq__(self, other: object, /) -> bool:
        if isinstance(other, UserExperiment):
            return self.hash == other.hash
        elif isinstance(other, GuildExperiment):
            return False
        return NotImplemented

    @property
    def name(self) -> Optional[str]:
        """Optional[:class:`str`]: The unique name of the experiment.

        This data is not always available via the API, and must be set manually for using related functions.
        """
        return self._name

    @name.setter
    def name(self, value: Optional[str], /) -> None:
        if not value:
            self._name = None
        elif murmurhash32(value, signed=False) != self.hash:
            raise ValueError('The name provided does not match the experiment hash')
        else:
            self._name = value

    @property
    def bucket(self) -> int:
        """:class:`int`: The assigned bucket for the user."""
        if self.aa_mode:
            return -1
        return self.assignment

    @property
    def result(self) -> int:
        """:class:`int`: The calulated position of the user within the experiment (0-9999).

        Raises
        ------
        :exc:`ValueError`
            The experiment name is unset without a precomputed result.
        """
        if self._result >= 0:
            return self._result
        elif not self.name:
            raise ValueError('The experiment name must be set to compute the result')
        else:
            result = murmurhash32(f'{self.name}:{self._state.self_id}', signed=False) % 10000
            self._result = result
            return result


class ApexExperimentAssignment:
    """Represents a unit's assignment in an Apex experiment.

    .. container:: operations

        .. describe:: x == y

            Checks if two experiment assignments are equal.

        .. describe:: x != y

            Checks if two experiment assignments are not equal.

        .. describe:: hash(x)

            Returns the experiment assignment's hash.

    .. versionadded:: 2.2

    Attributes
    -----------
    experiment: :class:`ApexExperiment`
        The experiment this assignment belongs to.
    unit_id: :class:`int`
        The ID of the unit (i.e. user, guild, etc.) this assignment applies to.
    evaluation_id: :class:`str`
        The evaluation ID of the assignment, used for analytics.
    variant_id: :class:`int`
        The assigned variant ID (bucket) for the unit.
    """

    __slots__ = ('experiment', 'unit_id', 'evaluation_id', 'variant_id', '_flags')

    def __init__(
        self,
        experiment: ApexExperiment,
        unit_id: int,
        evaluation_id: str,
        data: ApexExperimentAssignmentPayload,
    ):
        self.experiment: ApexExperiment = experiment
        self.unit_id: int = unit_id
        self.evaluation_id: str = evaluation_id
        self.variant_id: int = data[1]
        self._flags: int = data[2] or 0

    def __repr__(self) -> str:
        return (
            f'<ApexExperimentAssignment experiment={self.experiment!r} unit_id={self.unit_id} variant_id={self.variant_id}>'
        )

    def __hash__(self) -> int:
        return hash((self.experiment, self.unit_id))

    def __eq__(self, other: object, /) -> bool:
        if isinstance(other, ApexExperimentAssignment):
            return self.experiment == other.experiment and self.unit_id == other.unit_id
        return NotImplemented

    @property
    def flags(self) -> ApexExperimentFlags:
        """:class:`ApexExperimentFlags`: The flags for the assignment."""
        return ApexExperimentFlags._from_value(self._flags)


class ApexExperiment:
    """Represents an Apex experiment.

    Apex experiments are a new experiment system that completely replaces
    the previous guild and user experiment systems.

    They use "variants" instead of "buckets" or "treatments" and send much more
    limited data about the experiment, with no public rollout information.

    They also introduce the concept of per-installation experiments, which are experiments
    that are assigned to a unique client installation ID instead of a user or guild.

    .. container:: operations

        .. describe:: x == y

            Checks if two experiments are equal.

        .. describe:: x != y

            Checks if two experiments are not equal.

        .. describe:: hash(x)

            Returns the experiment's hash.

    .. versionadded:: 2.2

    Attributes
    -----------
    unit_type: :class:`ApexExperimentUnitType`
        The type of unit (i.e. user, guild, installation, etc.) this experiment applies to.
    hash: :class:`int`
        The 32-bit unsigned Murmur3 hash of the experiment's name.
    revision: :class:`int`
        The current revision of the experiment rollout.
    tracked_variant_id: Optional[:class:`int`]
        The variant ID that is currently being tracked.
    """

    __slots__ = ('_state', '_name', 'unit_type', 'hash', 'revision', 'tracked_variant_id', '_flags', '_assignments')

    def __init__(self, *, state: ConnectionState, data: ApexExperimentAssignmentPayload, unit_type: ApexExperimentUnitType):
        self._state = state
        self._name: Optional[str] = None
        self.unit_type: ApexExperimentUnitType = unit_type
        self.hash: int = data[0]
        self.revision: int = data[3]
        self.tracked_variant_id: Optional[int] = data[4] if len(data) > 4 else None
        self._flags: int = data[2] or 0  # Some of these are prolly global, but I'm not going to expose for now
        self._assignments: Dict[int, ApexExperimentAssignment] = {}

    @classmethod
    def parse(
        cls, state: ConnectionState, data: Optional[ApexExperimentResponsePayload], /
    ) -> Tuple[Dict[int, ApexExperiment], Dict[int, List[ApexExperimentAssignment]], Optional[str]]:
        # Apex experiments are given as a map of unit type -> map of unit ID -> assignments
        # This is a terrible format, so we're flattening each experiment mention within the assignments to one
        # ApexExperiment that holds a list of all assignments to it

        if not data:
            return {}, {}, None

        experiments: Dict[int, ApexExperiment] = {}
        assignments: Dict[int, List[ApexExperimentAssignment]] = {}

        # Sort unit types in descending order (e.g., Guild -> Installation -> User)
        # This guarantees Guild experiments are registered with the correct primary unit_type,
        # preventing them from being erroneously marked as User experiments due to underlying
        # UseAsEligibility or IsOverride assignment entries
        sorted_assignments = sorted(data.get('assignments', {}).items(), key=lambda x: int(x[0]), reverse=True)

        for _unit_type, unit_map in sorted_assignments:
            unit_type = try_enum(ApexExperimentUnitType, int(_unit_type))
            for _unit_id, assignment_data in unit_map.items():
                unit_id = int(_unit_id)
                evaluation_id = assignment_data.get('evaluation_id')
                for assignment_item in assignment_data.get('assignments', []):
                    experiment_hash = assignment_item[0]
                    try:
                        experiment = experiments[experiment_hash]
                    except KeyError:
                        experiment = experiments[experiment_hash] = ApexExperiment(
                            state=state, data=assignment_item, unit_type=unit_type
                        )

                    # evaluation_id is treated as nullable by the client, but I don't think it is
                    assignment = ApexExperimentAssignment(experiment, unit_id, evaluation_id or '', assignment_item)
                    experiment._assignments[unit_id] = assignment
                    try:
                        assignments[unit_id].append(assignment)
                    except KeyError:
                        assignments[unit_id] = [assignment]

        return experiments, assignments, data.get('installation')

    def __hash__(self) -> int:
        return self.hash

    def __eq__(self, other: object, /) -> bool:
        if isinstance(other, ApexExperiment):
            return self.hash == other.hash
        return NotImplemented

    def __repr__(self) -> str:
        return f'<ApexExperiment unit_type={self.unit_type!r} hash={self.hash}{f" name={self._name!r}" if self._name else ""} revision={self.revision}>'

    @property
    def name(self) -> Optional[str]:
        """Optional[:class:`str`]: The unique name of the experiment.

        This data is not available via the API, and must be set manually for using related functions.
        """
        return self._name

    @name.setter
    def name(self, value: Optional[str], /) -> None:
        if not value:
            self._name = None
        elif murmurhash32(value, signed=False) != self.hash:
            raise ValueError('The name provided does not match the experiment hash')
        else:
            self._name = value

    @property
    def assignments(self) -> Sequence[ApexExperimentAssignment]:
        """Sequence[:class:`ApexExperimentAssignment`]: The assignments for the experiment."""
        return SequenceProxy(self._assignments.values())

    def assignment_for(self, unit: Union[Snowflake, Client], /) -> Optional[ApexExperimentAssignment]:
        """Returns the experiment assignment for a given unit.

        Parameters
        -----------
        unit: Union[:class:`~discord.abc.Snowflake`, :class:`~discord.Client`]
            The unit to get the assignment for.
            Can be a variety of different objects depending on the unit type.
            Supports a :class:`~discord.Client` for installation-based experiments.

        Returns
        -------
        Optional[:class:`ApexExperimentAssignment`]
            The experiment assignment for the unit, or None if not assigned.
        """
        assignment = self._assignments.get(unit.id)  # type: ignore

        if self.unit_type == ApexExperimentUnitType.guild:
            user_assignment = self._assignments.get(self._state.self_id)

            # User assignment overrides take priority
            if user_assignment is not None and user_assignment.flags.override:
                resolved_assignment = user_assignment

            # Guild assignment overrides skip the eligibility gate
            elif assignment is not None and assignment.flags.override:
                resolved_assignment = assignment

            # For regular guild assignments, we need to pass the eligibility gate
            elif user_assignment is not None and user_assignment.flags.use_as_eligibility and assignment is not None:
                resolved_assignment = assignment

            # Neither override nor valid eligibility gate was found
            else:
                resolved_assignment = None

        else:
            # User or Installation experiments
            resolved_assignment = assignment

        # If the finalized assignment has the UseAsEligibility flag, we must ignore the assignment
        # as it is only meant to be used as an eligibility gate for other assignments
        if resolved_assignment is not None and resolved_assignment.flags.use_as_eligibility:
            return None

        return resolved_assignment

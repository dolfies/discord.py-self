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

import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from . import utils
from .channel import GroupChannel
from .enums import JoinRequestStatus, MemberVerificationFieldType, try_enum
from .mixins import Hashable
from .utils import MISSING

if TYPE_CHECKING:
    from typing_extensions import Self

    from .discovery import GuildProfile
    from .guild import Guild
    from .state import ConnectionState
    from .types.member_verification import (
        JoinRequest as JoinRequestPayload,
        MemberVerification as MemberVerificationPayload,
        MemberVerificationFormField as MemberVerificationFormFieldPayload,
    )
    from .user import User

__all__ = (
    'MemberVerificationFormField',
    'MemberVerification',
    'JoinRequest',
)


class MemberVerificationFormField:
    """Represents a question on a guild's :class:`MemberVerification`.

    .. versionadded:: 2.2

    .. container:: operations

        .. describe:: str(x)

            Returns the form field's label.

    Parameters
    -----------
    type: :class:`MemberVerificationFieldType`
        The type of question being asked.
    label: :class:`str`
        The label of the form field. Can be up to 300 characters long.
    choices: Optional[List[:class:`str`]]
        The multiple choice answers to the question. There can be up to 8 choices,
        each up to 150 characters long.

        Only applicable to :attr:`MemberVerificationFieldType.multiple_choice`.
    values: Optional[List[:class:`str`]]
        The rules the user must agree to.

        Only applicable to :attr:`MemberVerificationFieldType.terms`.
    required: :class:`bool`
        Whether the question must be answered for the application to be submitted.
    description: Optional[:class:`str`]
        The subtext of the form field.
    placeholder: Optional[:class:`str`]
        The placeholder text shown in the field's response area.

        Only applicable to :attr:`MemberVerificationFieldType.text_input` and
        :attr:`MemberVerificationFieldType.paragraph`.

    Attributes
    -----------
    type: :class:`MemberVerificationFieldType`
        The type of question being asked.
    label: :class:`str`
        The label of the form field.
    choices: Optional[List[:class:`str`]]
        The multiple choice answers to the question.
    values: Optional[List[:class:`str`]]
        The rules the user must agree to.
    required: :class:`bool`
        Whether the question must be answered for the application to be submitted.
    description: Optional[:class:`str`]
        The subtext of the form field.
    placeholder: Optional[:class:`str`]
        The placeholder text shown in the field's response area.
    """

    __slots__ = (
        'type',
        'label',
        'choices',
        'values',
        'required',
        'description',
        'automations',
        'placeholder',
        '_response',
    )

    def __init__(
        self,
        *,
        type: MemberVerificationFieldType,
        label: str,
        choices: Optional[List[str]] = None,
        values: Optional[List[str]] = None,
        required: bool = True,
        description: Optional[str] = None,
        automations: Optional[List[str]] = None,
        placeholder: Optional[str] = None,
    ) -> None:
        self.type: MemberVerificationFieldType = type
        self.label: str = label
        self.choices: Optional[List[str]] = choices
        self.values: Optional[List[str]] = values
        self.required: bool = required
        self.description: Optional[str] = description
        self.automations: Optional[List[str]] = automations
        self.placeholder: Optional[str] = placeholder
        self._response: Optional[Union[str, bool]] = None

    def __repr__(self) -> str:
        return f'<MemberVerificationFormField type={self.type!r} label={self.label!r} required={self.required}>'

    def __str__(self) -> str:
        return self.label

    @property
    def response(self) -> Optional[Union[str, bool]]:
        """Optional[Union[:class:`str`, :class:`bool`]]: The response to the question,
        if any.

        For :attr:`MemberVerificationFieldType.terms` this should be ``True``, and for
        :attr:`MemberVerificationFieldType.multiple_choice` this is the text of the
        selected :attr:`choices` entry.

        Raises
        -------
        TypeError
            A multiple choice response was not a :class:`str` or an :class:`int`.
        ValueError
            The given choice does not exist on this field.
        """
        return self._response

    @response.setter
    def response(self, value: Optional[Union[str, int, bool]]) -> None:
        if value is not None and self.type is MemberVerificationFieldType.multiple_choice:
            choices = self.choices or []

            if isinstance(value, bool) or not isinstance(value, (str, int)):
                raise TypeError(f'Multiple choice response must be a str or int, not {value.__class__.__name__}')

            if isinstance(value, int):
                if not 0 <= value < len(choices):
                    raise ValueError(f'Choice index {value} is out of range')
                value = choices[value]
            elif value not in choices:
                available = ', '.join(map(repr, choices)) if choices else 'none'
                raise ValueError(f'{value!r} is not one of the available choices: {available}')

        self._response = value  # type: ignore

    @classmethod
    def _from_data(cls, data: MemberVerificationFormFieldPayload) -> Self:
        self = cls(
            type=try_enum(MemberVerificationFieldType, data['field_type']),
            label=data['label'],
            choices=data.get('choices'),
            values=data.get('values'),
            required=data['required'],
            description=data.get('description'),
            automations=data.get('automations'),
            placeholder=data.get('placeholder'),
        )

        response = data.get('response')
        if self.type is MemberVerificationFieldType.multiple_choice and isinstance(response, int):
            choices = self.choices or []
            if 0 <= response < len(choices):
                response = choices[response]
        self._response = response  # type: ignore # Unresolvable responses are kept as-is

        return self

    def to_dict(self) -> MemberVerificationFormFieldPayload:
        payload: MemberVerificationFormFieldPayload = {
            'field_type': self.type.value,
            'label': self.label,
            'required': self.required,
            'description': self.description,
            'automations': self.automations,
        }
        if self.choices is not None:
            payload['choices'] = self.choices
        if self.values is not None:
            payload['values'] = self.values
        if self.placeholder is not None:
            payload['placeholder'] = self.placeholder

        response = self._response
        if response is not None:
            if self.type is MemberVerificationFieldType.multiple_choice:
                choices = self.choices or []
                response = choices.index(response) if response in choices else response
            payload['response'] = response

        return payload


class MemberVerification:
    """Represents a guild's member verification gate.

    This is the set of questions a user must answer before they are able to
    participate in a guild.

    .. versionadded:: 2.2

    .. container:: operations

        .. describe:: len(x)

            Returns the number of form fields.

        .. describe:: iter(x)

            Returns an iterator over the form fields.

    Attributes
    -----------
    version: Optional[:class:`datetime.datetime`]
        When the member verification was last modified.
    form_fields: List[:class:`MemberVerificationFormField`]
        The questions the user must answer.
    description: Optional[:class:`str`]
        A description of what the guild is about. This can be different than
        the guild's own description.
    guild: Optional[:class:`Guild`]
        The guild this member verification is for, if known.

        When the current user is not a member of the guild and it was requested,
        this is a partial guild with only a handful of attributes filled in.
    profile: Optional[:class:`GuildProfile`]
        The profile of the guild this member verification is for, if available.
    """

    __slots__ = ('_state', 'version', 'form_fields', 'description', 'guild', 'profile')

    def __init__(
        self,
        *,
        data: MemberVerificationPayload,
        state: ConnectionState,
        guild: Optional[Guild] = None,
    ) -> None:
        self._state: ConnectionState = state
        self.guild: Optional[Guild] = guild
        self._update(data)

    def _update(self, data: MemberVerificationPayload) -> None:
        state = self._state

        self.version: Optional[datetime.datetime] = utils.parse_time(data.get('version'))
        self.form_fields: List[MemberVerificationFormField] = [
            MemberVerificationFormField._from_data(field) for field in data.get('form_fields', [])
        ]
        self.description: Optional[str] = data.get('description')

        guild = data.get('guild')
        if guild is not None:
            self.guild = state.create_guild(guild)

        profile = data.get('profile')
        self.profile: Optional[GuildProfile] = None
        if profile is not None:
            from .discovery import GuildProfile

            self.profile = GuildProfile(data=profile, state=state)

    def __repr__(self) -> str:
        return f'<MemberVerification guild={self.guild!r} form_fields={len(self.form_fields)}>'

    def __len__(self) -> int:
        return len(self.form_fields)

    def __iter__(self):
        return iter(self.form_fields)

    @property
    def enabled(self) -> bool:
        """:class:`bool`: Whether the member verification gate is enabled."""
        guild = self.guild
        if guild is None:
            return True  # Cannot fetch another guild's disabled obj if we aren't members (cache may kill this)
        return 'MEMBER_VERIFICATION_GATE_ENABLED' in guild.features

    @property
    def manual_approval(self) -> bool:
        """:class:`bool`: Whether join requests for this guild must be manually approved."""
        return any(field.type != MemberVerificationFieldType.terms for field in self.form_fields)

    async def edit(
        self,
        *,
        enabled: bool = MISSING,
        form_fields: List[MemberVerificationFormField] = MISSING,
        description: Optional[str] = MISSING,
        bulk_action: JoinRequestStatus = MISSING,
        reason: Optional[str] = None,
    ) -> MemberVerification:
        """|coro|

        Edits the member verification.

        You must have :attr:`~Permissions.manage_guild` to do this.

        All parameters are optional.

        Parameters
        -----------
        enabled: :class:`bool`
            Whether the member verification gate is enabled.
        form_fields: List[:class:`MemberVerificationFormField`]
            The questions the user must answer. There can be up to 5 questions.

            Using a field type other than :attr:`MemberVerificationFieldType.terms`
            requires the guild to have the ``MEMBER_VERIFICATION_MANUAL_APPROVAL`` feature.
        description: Optional[:class:`str`]
            A description of what the guild is about. Can be up to 300 characters long.
        bulk_action: :class:`JoinRequestStatus`
            What to do with the pending join requests when disabling the gate.
            Only :attr:`JoinRequestStatus.approved` and :attr:`JoinRequestStatus.rejected`
            can be used. Defaults to approving.
        reason: Optional[:class:`str`]
            The reason for editing the member verification. Shows up on the audit log.

        Raises
        -------
        ValueError
            An invalid ``bulk_action`` was passed.
        Forbidden
            You do not have permissions to edit the member verification.
        HTTPException
            Editing the member verification failed.

        Returns
        --------
        :class:`MemberVerification`
            The newly updated member verification.
        """
        guild = self.guild
        if guild is None:
            raise TypeError('MemberVerification is not attached to a guild')

        payload: Dict[str, Any] = {}
        if enabled is not MISSING:
            payload['enabled'] = enabled
        if form_fields is not MISSING:
            payload['form_fields'] = [field.to_dict() for field in form_fields]
        if description is not MISSING:
            payload['description'] = description
        if bulk_action is not MISSING:
            if bulk_action not in (JoinRequestStatus.approved, JoinRequestStatus.rejected):
                raise ValueError('bulk_action must be either JoinRequestStatus.approved or JoinRequestStatus.rejected')
            payload['bulk_action'] = bulk_action.value

        data = await self._state.http.edit_member_verification(guild.id, payload, reason=reason)
        self._update(data)
        return self


class JoinRequest(Hashable):
    """Represents a request to join a guild with member verification enabled.

    .. versionadded:: 2.2

    .. container:: operations

        .. describe:: x == y

            Checks if two join requests are equal.

        .. describe:: x != y

            Checks if two join requests are not equal.

        .. describe:: hash(x)

            Returns the join request's hash.

    Attributes
    -----------
    id: :class:`int`
        The join request's ID.
    guild_id: :class:`int`
        The ID of the guild this join request is for.
    user_id: :class:`int`
        The ID of the user who created this join request.
    user: Optional[:class:`User`]
        The user who created this join request, if available.
    status: :class:`JoinRequestStatus`
        The status of the join request.
    created_at: :class:`datetime.datetime`
        When the join request was created.
    form_responses: Optional[List[:class:`MemberVerificationFormField`]]
        The user's responses to the guild's member verification questions,
        if available.
    last_seen: Optional[:class:`datetime.datetime`]
        When the join request was acknowledged by the user, if it has been.
    actioned_at: Optional[:class:`datetime.datetime`]
        When the join request was actioned, if it has been.
    actioned_by: Optional[:class:`User`]
        The moderator who actioned the join request, if available.
    rejection_reason: Optional[:class:`str`]
        Why the join request was rejected, if it was.
    interview_channel_id: Optional[:class:`int`]
        The ID of the channel where an interview regarding this join request
        may be conducted, if any.
    """

    __slots__ = (
        '_state',
        'id',
        'guild_id',
        'user_id',
        'user',
        'status',
        'created_at',
        'form_responses',
        'last_seen',
        'actioned_at',
        'actioned_by',
        'rejection_reason',
        'interview_channel_id',
    )

    def __init__(self, *, data: JoinRequestPayload, state: ConnectionState) -> None:
        self._state: ConnectionState = state
        self._update(data)

    def _update(self, data: JoinRequestPayload) -> None:
        state = self._state

        self.id: int = int(data.get('id') or data['join_request_id'])
        self.guild_id: int = int(data['guild_id'])
        self.user_id: int = int(data['user_id'])
        self.status: JoinRequestStatus = try_enum(JoinRequestStatus, data['application_status'])
        self.created_at: datetime.datetime = utils.parse_time(data['created_at'])
        self.last_seen: Optional[datetime.datetime] = utils.parse_time(data.get('last_seen'))
        self.rejection_reason: Optional[str] = data.get('rejection_reason')
        self.interview_channel_id: Optional[int] = utils._get_as_snowflake(data, 'interview_channel_id')

        # actioned_at snowflake is deprecated in favour of the reviewed_at timestamp
        self.actioned_at: Optional[datetime.datetime] = utils.parse_time(data.get('reviewed_at'))

        form_responses = data.get('form_responses')
        self.form_responses: Optional[List[MemberVerificationFormField]] = (
            [MemberVerificationFormField._from_data(field) for field in form_responses]
            if form_responses is not None
            else None
        )

        user = data.get('user')
        self.user: Optional[User] = state.store_user(user) if user is not None else state.get_user(self.user_id)

        actioned_by = data.get('actioned_by_user')
        self.actioned_by: Optional[User] = state.store_user(actioned_by) if actioned_by is not None else None

    def __repr__(self) -> str:
        return f'<JoinRequest id={self.id} user_id={self.user_id} status={self.status!r}>'

    @property
    def guild(self) -> Optional[Guild]:
        """Optional[:class:`Guild`]: The guild this join request is for."""
        return self._state._get_guild(self.guild_id)

    @property
    def interview_channel(self) -> Optional[GroupChannel]:
        """Optional[:class:`GroupChannel`]: The channel where an interview regarding
        this join request may be conducted, if any and it is cached.
        """
        channel_id = self.interview_channel_id
        if channel_id is None:
            return None
        return self._state._get_private_channel(channel_id)  # type: ignore # Always a GroupChannel

    def is_acked(self) -> bool:
        """:class:`bool`: Whether the join request has been acknowledged by the user."""
        return self.last_seen is not None

    async def approve(self) -> JoinRequest:
        """|coro|

        Approves the join request.

        You must have :attr:`~Permissions.kick_members` to do this.

        Raises
        -------
        Forbidden
            You do not have permissions to action the join request.
        HTTPException
            Actioning the join request failed.

        Returns
        --------
        :class:`JoinRequest`
            The newly updated join request.
        """
        data = await self._state.http.action_join_request(self.guild_id, self.id, JoinRequestStatus.approved.value)
        self._update(data)
        return self

    async def reject(self, *, reason: Optional[str] = None) -> JoinRequest:
        """|coro|

        Rejects the join request.

        You must have :attr:`~Permissions.kick_members` to do this.

        Parameters
        -----------
        reason: Optional[:class:`str`]
            The reason for rejecting the join request. Can be up to 160 characters long.

        Raises
        -------
        Forbidden
            You do not have permissions to action the join request.
        HTTPException
            Actioning the join request failed.

        Returns
        --------
        :class:`JoinRequest`
            The newly updated join request.
        """
        data = await self._state.http.action_join_request(
            self.guild_id, self.id, JoinRequestStatus.rejected.value, rejection_reason=reason
        )
        self._update(data)
        return self

    async def ack(self) -> None:
        """|coro|

        Acknowledges the join request.

        You can only acknowledge your own approved join requests. Once acknowledged,
        the join request is no longer considered active.

        Raises
        -------
        Forbidden
            You do not have permissions to acknowledge the join request.
        HTTPException
            Acknowledging the join request failed.
        """
        # This API is a mess... an @me endpoint ALSO exists
        await self._state.http.ack_join_request(self.guild_id, self.id)

    async def reset(self) -> JoinRequest:
        """|coro|

        Resets the join request, creating a fresh one in its place.

        You can only reset your own join request.

        Raises
        -------
        Forbidden
            You do not have permissions to reset the join request.
        HTTPException
            Resetting the join request failed.

        Returns
        --------
        :class:`JoinRequest`
            The newly created join request.
        """
        state = self._state
        data = await state.http.reset_join_request(self.guild_id)
        return JoinRequest(data=data, state=state)

    async def delete(self) -> Optional[JoinRequest]:
        """|coro|

        Deletes the join request.

        You can only delete your own join request. If the guild has previewing
        enabled, this instead behaves like :meth:`reset`.

        Raises
        -------
        Forbidden
            You do not have permissions to delete the join request.
        HTTPException
            Deleting the join request failed.

        Returns
        --------
        Optional[:class:`JoinRequest`]
            The newly created join request, if it was reset instead of deleted.
        """
        state = self._state
        data = await state.http.delete_join_request(self.guild_id)
        return JoinRequest(data=data, state=state) if data else None

    async def create_interview(self) -> GroupChannel:
        """|coro|

        Creates or joins a private interview channel for the join request.

        You must have :attr:`~Permissions.kick_members` to do this.

        Raises
        -------
        Forbidden
            You do not have permissions to create an interview.
        HTTPException
            Creating the interview failed.

        Returns
        --------
        :class:`GroupChannel`
            The interview channel that was created or joined.
        """
        state = self._state
        data = await state.http.create_join_request_interview(self.id)
        return GroupChannel(me=state.user, data=data, state=state)  # type: ignore # user is always present when logged in

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

from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional

from .flags import SKUFlags
from .mixins import Hashable
from .store import StoreListing
from .subscriptions import SubscriptionTrial
from .utils import _get_as_snowflake, parse_time, utcnow

if TYPE_CHECKING:
    from .state import ConnectionState

__all__ = (
    'Promotion',
    'Gift',
    'TrialOffer',
)


class Promotion(Hashable):
    """Represents a Discord promotion.

    .. container:: operations

        .. describe:: x == y

            Checks if two promotions are equal.

        .. describe:: x != y

            Checks if two promotions are not equal.

        .. describe:: hash(x)

            Returns the promotion's hash.

        .. describe:: str(x)

            Returns the outbound promotion's name.

    .. versionadded:: 2.0

    Attributes
    ----------
    id: :class:`int`
        The promotion ID.
    trial_id: :class:`int`
        The trial ID of the inbound promotion, if applicable.
    starts_at: :class:`datetime.datetime`
        When the promotion starts.
    ends_at: :class:`datetime.datetime`
        When the promotion ends.
    claimed_at: Optional[:class:`datetime.datetime`]
        When the promotion was claimed.
        Only available for claimed promotions.
    code: :class:`str`
        The promotion's claim code.
    outbound_title: :class:`str`
        The title of the outbound promotion.
    outbound_description: :class:`str`
        The description of the outbound promotion.
    outbound_link: :class:`str`
        The redemption page of the outbound promotion, used to claim it.
    outbound_restricted_countries: List[:class:`str`]
        The countries that the outbound promotion is not available in.
    inbound_title: Optional[:class:`str`]
        The title of the inbound promotion. This is usually Discord Nitro.
    inbound_description: Optional[:class:`str`]
        The description of the inbound promotion.
    inbound_link: Optional[:class:`str`]
        The Discord help center link of the inbound promotion.
    inbound_restricted_countries: List[:class:`str`]
        The countries that the inbound promotion is not available in.
    terms_and_conditions: :class:`str`
        The terms and conditions of the promotion.
    """

    def __init__(self, *, data: dict, state: ConnectionState) -> None:
        self._state = state
        self._update(data)

    def __str__(self) -> str:
        return self.outbound_title

    def __repr__(self) -> str:
        return f'<Promotion id={self.id} title={self.outbound_title!r}>'

    def _update(self, data: dict) -> None:
        promotion = data.get('promotion', data)

        self.id: int = int(promotion['id'])
        self.trial_id: Optional[int] = _get_as_snowflake(promotion, 'trial_id')
        self.starts_at: datetime = parse_time(promotion['start_date'])  # type: ignore # Should always be a datetime
        self.ends_at: datetime = parse_time(promotion['end_date'])  # type: ignore # Should always be a datetime
        self.claimed_at: Optional[datetime] = parse_time(data.get('claimed_at'))
        self.code: Optional[str] = data.get('code')
        self._flags: int = promotion.get('flags', 0)

        self.outbound_title: str = promotion['outbound_title']
        self.outbound_description: str = promotion['outbound_redemption_modal_body']
        self.outbound_link: str = promotion['outbound_redemption_page_link']
        self.outbound_restricted_countries: List[str] = promotion.get('outbound_restricted_countries', [])
        self.inbound_title: Optional[str] = promotion.get('inbound_header_text')
        self.inbound_description: Optional[str] = promotion.get('inbound_body_text')
        self.inbound_link: Optional[str] = promotion.get('inbound_help_center_link')
        self.inbound_restricted_countries: List[str] = promotion.get('inbound_restricted_countries', [])
        self.terms_and_conditions: str = promotion['outbound_terms_and_conditions']

    @property
    def flags(self) -> SKUFlags:
        """:class:`SKUFlags`: Returns the promotion's SKU flags."""
        return SKUFlags._from_value(self._flags)

    def is_claimed(self) -> bool:
        """:class:`bool`: Checks if the promotion has been claimed.

        Only accurate if the promotion was fetched from :meth:`Client.claimed_promotions` or :meth:`claim` was just called.
        """
        return self.claimed_at is not None

    def is_active(self) -> bool:
        """:class:`bool`: Checks if the promotion is active."""
        return self.starts_at <= utcnow() <= self.ends_at

    async def claim(self) -> str:
        """|coro|

        Claims the promotion.

        Sets :attr:`claimed_at` and :attr:`code`.

        Raises
        ------
        Forbidden
            You are not allowed to claim the promotion.
        HTTPException
            Claiming the promotion failed.

        Returns
        -------
        :class:`str`
            The claim code for the outbound promotion.
        """
        data = await self._state.http.claim_promotion(self.id)
        self._update(data)
        return data['code']


class Gift:
    """Represents a Discord gift.

    .. container:: operations

        .. describe:: x == y

            Checks if two gifts are equal.

        .. describe:: x != y

            Checks if two gifts are not equal.

        .. describe:: hash(x)

            Returns the gift's hash.

    .. versionadded:: 2.0

    Attributes
    ----------
    code: :class:`str`
        The gift's code.
    expires_at: Optional[:class:`datetime.datetime`]
        When the gift expires.
    application_id: Optional[:class:`int`]
        The ID of the application that owns the SKU the gift is for.
    batch_id: Optional[:class:`int`]
        The ID of the batch the gift is from.
    sku_id: :class:`int`
        The ID of the SKU the gift is for.
    entitlement_branches: List[:class:`int`]
        A list of entitlements the gift is for.
    max_uses: :class:`int`
        The maximum number of times the gift can be used.
    uses: :class:`int`
        The number of times the gift has been used.
    redeemed: :class:`bool`
        Whether the user has redeemed the gift.
    store_listing: :class:`StoreListing`
        The store listing for the SKU the gift is for.
    promotion: Optional[:class:`Promotion`]
        The promotion the gift is a part of, if any.
    subscription_trial: Optional[:class:`SubscriptionTrial`]
        The subscription trial the gift is a part of, if any.
    subscription_plan: Optional[:class:`SubscriptionPlan`]
        The subscription plan the gift is for, if any.
    """

    def __init__(self, *, data: dict, state: ConnectionState) -> None:
        self._state = state
        self._update(data)

    def _update(self, data: dict) -> None:
        self.code: str = data['code']
        self.expires_at: Optional[datetime] = parse_time(data.get('expires_at'))
        self.application_id: Optional[int] = _get_as_snowflake(data, 'application_id')
        self.batch_id: int = int(data['batch_id'])
        self.plan_id: Optional[int] = _get_as_snowflake(data, 'subscription_plan_id')
        self.sku_id: int = int(data['sku_id'])
        self.entitlement_branches: List[int] = [int(x) for x in data.get('entitlement_branches', [])]
        self._flags: int = data.get('flags', 0)

        self.max_uses: int = data.get('max_uses', 0)
        self.uses: int = data.get('uses', 0)
        self.redeemed: bool = data.get('redeemed', False)

        self.store_listing: StoreListing = StoreListing(data=data['store_listing'], state=self._state)
        self.promotion: Optional[Promotion] = (
            Promotion(data=data['promotion'], state=self._state) if 'promotion' in data else None
        )
        self.subscription_trial: Optional[SubscriptionTrial] = SubscriptionTrial(data['subscription_trial']) if data.get('subscription_trial') else None
        self.subscription_plan = ...

    def __repr__(self) -> str:
        return f'<Gift code={self.code!r} sku_id={self.sku_id} uses={self.uses} max_uses={self.max_uses} redeemed={self.redeemed}>'

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Gift) and other.code == self.code

    def __ne__(self, other: Any) -> bool:
        if isinstance(other, Gift):
            return other.code != self.code
        return True

    def __hash__(self) -> int:
        return hash(self.code)

    @property
    def id(self) -> str:
        """:class:`str`: Returns the code portion of the gift."""
        return self.code

    @property
    def url(self) -> str:
        """:class:`str`: Returns the gift's URL."""
        return f'https://discord.gift/{self.code}'

    @property
    def flags(self) -> SKUFlags:
        """:class:`SKUFlags`: Returns the gift's SKU flags. These are not available for all gifts."""
        return SKUFlags._from_value(self._flags)

    def is_used(self) -> bool:
        """:class:`bool`: Checks if the gift has been used up."""
        return self.uses >= self.max_uses if self.max_uses else False


class TrialOffer(Hashable):
    """Represents a Discord user trial offer.

    .. container:: operations

        .. describe:: x == y

            Checks if two trial offers are equal.

        .. describe:: x != y

            Checks if two trial offers are not equal.

        .. describe:: hash(x)

            Returns the trial offer's hash.

    .. versionadded:: 2.0

    Attributes
    ----------
    id: :class:`int`
        The ID of the trial offer.
    expires_at: :class:`datetime`
        When the trial offer expires.
    trial_id: :class:`int`
        The ID of the trial.
    trial: :class:`SubscriptionTrial`
        The trial offered.
    """

    def __init__(self, data: dict) -> None:
        self.id: int = int(data['id'])
        self.expires_at: datetime = parse_time(data['expires_at'])  # type: ignore # Should always be a datetime
        self.trial_id: int = int(data['trial_id'])
        self.trial: SubscriptionTrial = SubscriptionTrial(data['subscription_trial'])

    def __repr__(self) -> str:
        return f'<TrialOffer id={self.id} trial={self.trial!r}>'


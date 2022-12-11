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

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from datetime import datetime

from .asset import Asset, AssetMixin
from .enums import ContentRatingAgency, Locale, SKUAccessLevel, SKUFeature, SKUGenre, SKUType, OperatingSystem, try_enum
from .flags import SKUFlags
from .mixins import Hashable
from .utils import _get_as_snowflake, _get_extension_for_mime_type, get, parse_date, parse_time, utcnow

if TYPE_CHECKING:
    from datetime import date

    from .appinfo import Application, PartialApplication
    from .guild import Guild
    from .state import ConnectionState
    from .types.appinfo import StoreAsset as StoreAssetPayload
    from .types.snowflake import Snowflake

__all__ = (
    'StoreAsset',
    'StoreListing',
    'SKU',
)

THE_GAME_AWARDS_WINNERS = [500428425362931713, 451550535720501248, 471376328319303681, 466696214818193408]


class StoreAsset(AssetMixin, Hashable):
    """Represents an application store asset.

    .. container:: operations

        .. describe:: x == y

            Checks if two assets are equal.

        .. describe:: x != y

            Checks if two assets are not equal.

        .. describe:: hash(x)

            Returns the asset's hash.

    .. versionadded:: 2.0

    Attributes
    -----------
    parent: Union[:class:`StoreListing`, :class:`Application`]
        The store listing or application that this asset belongs to.
    id: Union[:class:`int`, :class:`str`]
        The asset's ID or YouTube video ID.
    size: :class:`int`
        The asset's size in bytes, or 0 if it's a YouTube video.
    height: :class:`int`
        The asset's height in pixels, or 0 if it's a YouTube video.
    width: :class:`int`
        The asset's width in pixels, or 0 if it's a YouTube video.
    mime_type: :class:`str`
        The asset's mime type, or "video/youtube" if it is a YouTube video.
    """

    __slots__ = ('_state', 'parent', 'id', 'size', 'height', 'width', 'mime_type')

    def __init__(self, *, data: StoreAssetPayload, state: ConnectionState, parent: Union[StoreListing, Application]) -> None:
        self._state: ConnectionState = state
        self.parent = parent
        self.size: int = data['size']
        self.height: int = data['height']
        self.width: int = data['width']
        self.mime_type: str = data['mime_type']

        self.id: Snowflake
        try:
            self.id = int(data['id'])
        except ValueError:
            self.id = data['id']

    @classmethod
    def _from_id(
        cls, *, id: Snowflake, mime_type: str = '', state: ConnectionState, parent: Union[StoreListing, Application]
    ) -> StoreAsset:
        data: StoreAssetPayload = {'id': id, 'size': 0, 'height': 0, 'width': 0, 'mime_type': mime_type}
        return cls(data=data, state=state, parent=parent)

    @classmethod
    def _from_carousel_item(cls, *, data: dict, state: ConnectionState, store_listing: StoreListing) -> StoreAsset:
        asset_id = _get_as_snowflake(data, 'asset_id')
        if asset_id:
            return get(store_listing.assets, id=asset_id) or StoreAsset._from_id(
                id=asset_id, state=state, parent=store_listing
            )
        else:
            return cls._from_id(id=data['youtube_video_id'], mime_type='video/youtube', state=state, parent=store_listing)

    def __repr__(self) -> str:
        return f'<ApplicationAsset id={self.id} height={self.height} width={self.width}>'

    @property
    def application_id(self) -> int:
        parent = self.parent
        return parent.sku.application_id if hasattr(parent, 'sku') else parent.id  # type: ignore # Type checker doesn't understand

    @property
    def animated(self) -> bool:
        """:class:`bool`: Indicates if the store asset is animated."""
        return self.mime_type in {'video/youtube', 'image/gif', 'video/mp4'}

    @property
    def url(self) -> str:
        """:class:`str`: Returns the URL of the store asset."""
        if self.is_youtube_video():
            return f'https://youtube.com/watch?v={self.id}'
        return (
            f'{Asset.BASE}/app-assets/{self.application_id}/store/{self.id}.{_get_extension_for_mime_type(self.mime_type)}'
        )

    def is_youtube_video(self) -> bool:
        """:class:`bool`: Indicates if the asset is a YouTube video."""
        return self.mime_type == 'video/youtube'

    async def read(self) -> bytes:
        if self.is_youtube_video():
            raise ValueError('StoreAsset is not a real asset')

        return await super().read()

    async def delete(self) -> None:
        """|coro|

        Deletes the asset.

        Raises
        ------
        ValueError
            The asset is a YouTube video.
        Forbidden
            You are not allowed to delete this asset.
        HTTPException
            Deleting the asset failed.
        """
        if self.is_youtube_video():
            raise ValueError('StoreAsset is not a real asset')

        await self._state.http.delete_store_asset(self.application_id, self.id)


class SystemRequirements:
    """Represents system requirements.

    .. versionadded:: 2.0

    Attributes
    -----------
    os: :class:`OperatingSystem`
        The operating system these requirements apply to.
    minimum_os_version: :class:`str`
        The minimum operating system version required.
    recommended_os_version: :class:`str`
        The recommended operating system version.
    minimum_cpu: :class:`str`
        The minimum CPU specifications required.
    recommended_cpu: :class:`str`
        The recommended CPU specifications.
    minimum_gpu: :class:`str`
        The minimum GPU specifications required.
    recommended_gpu: :class:`str`
        The recommended GPU specifications.
    minimum_ram: :class:`int`
        The minimum RAM size in megabytes.
    recommended_ram: :class:`int`
        The recommended RAM size in megabytes.
    minimum_disk: :class:`int`
        The minimum free storage space in megabytes.
    recommended_disk: :class:`int`
        The recommended free storage space in megabytes.
    minimum_sound_card: Optional[:class:`str`]
        The minimum sound card specifications required, if any.
    recommended_sound_card: Optional[:class:`str`]
        The recommended sound card specifications, if any.
    minimum_directx: Optional[:class:`str`]
        The minimum DirectX version required, if any.
    recommended_directx: Optional[:class:`str`]
        The recommended DirectX version, if any.
    minimum_network: Optional[:class:`str`]
        The minimum network specifications required, if any.
    recommended_network: Optional[:class:`str`]
        The recommended network specifications, if any.
    minimum_notes: Optional[:class:`str`]
        Any extra notes on minimum requirements.
    recommended_notes: Optional[:class:`str`]
        Any extra notes on recommended requirements.

    The non-prefixed properties on this class prefer the requirements values and fall back to the minimum requirements.
    """

    __slots__ = (
        'os',
        'minimum_os_version',
        'recommended_os_version',
        'minimum_cpu',
        'recommended_cpu',
        'minimum_gpu',
        'recommended_gpu',
        'minimum_ram',
        'recommended_ram',
        'minimum_disk',
        'recommended_disk',
        'minimum_sound_card',
        'recommended_sound_card',
        'minimum_directx',
        'recommended_directx',
        'minimum_network',
        'recommended_network',
        'minimum_notes',
        'recommended_notes',
    )

    def __init__(self, os: OperatingSystem, data: dict) -> None:
        minimum = data['minimum']
        recommended = data.get('recommended', minimum)

        self.os: OperatingSystem = os
        self.minimum_os_version: str = minimum['operating_system_version']
        self.recommended_os_version: str = recommended['operating_system_version']
        self.minimum_cpu: str = minimum['cpu']
        self.recommended_cpu: str = recommended['cpu']
        self.minimum_gpu: str = minimum['gpu']
        self.recommended_gpu: str = recommended['gpu']
        self.minimum_ram: int = minimum['ram']
        self.recommended_ram: int = recommended['ram']
        self.minimum_disk: int = minimum['disk']
        self.recommended_disk: int = recommended['disk']
        self.minimum_sound_card: Optional[str] = minimum.get('sound_card')
        self.recommended_sound_card: Optional[str] = recommended.get('sound_card')
        self.minimum_directx: Optional[str] = minimum['directx']
        self.recommended_directx: Optional[str] = recommended['directx']
        self.minimum_network: Optional[str] = minimum['network']
        self.recommended_network: Optional[str] = recommended['network']
        self.minimum_notes: Optional[str] = minimum.get('notes')
        self.recommended_notes: Optional[str] = recommended.get('notes')

    def __repr__(self) -> str:
        return f'<SystemRequirements os={self.os!r} cpu={self.cpu!r} gpu={self.gpu!r} ram={self.ram} disk={self.disk}>'

    @property
    def os_version(self) -> str:
        """:class:`str`: The recommended operating system version."""
        return self.recommended_os_version

    @property
    def cpu(self) -> str:
        """:class:`str`: The recommended CPU."""
        return self.recommended_cpu

    @property
    def gpu(self) -> str:
        """:class:`str`: The recommended GPU."""
        return self.recommended_gpu

    @property
    def ram(self) -> int:
        """:class:`int`: The recommended RAM."""
        return self.recommended_ram

    @property
    def disk(self) -> int:
        """:class:`int`: The recommended disk space."""
        return self.recommended_disk

    @property
    def sound_card(self) -> Optional[str]:
        """Optional[:class:`str`]: The recommended sound card."""
        return self.recommended_sound_card or self.minimum_sound_card

    @property
    def directx(self) -> Optional[str]:
        """Optional[:class:`str`]: The recommended DirectX version."""
        return self.recommended_directx or self.minimum_directx

    @property
    def network(self) -> Optional[str]:
        """Optional[:class:`str`]: The recommended network connection."""
        return self.recommended_network or self.minimum_network

    @property
    def notes(self) -> Optional[str]:
        """Optional[:class:`str`]: Extra requirement notes."""
        return self.recommended_notes or self.minimum_notes


class StoreListing(Hashable):
    """Represents a store listing.

    .. container:: operations

        .. describe:: x == y

            Checks if two listings are equal.

        .. describe:: x != y

            Checks if two listings are not equal.

        .. describe:: hash(x)

            Returns the listing's hash.

        .. describe:: str(x)

            Returns the listing's summary.

    .. versionadded:: 2.0

    Attributes
    -----------
    id: :class:`int`
        The listing's ID.
    summary: :class:`str`
        The listing's summary.
    description: :class:`str`
        The listing's description.
    tagline: :class:`str`
        The listing's tagline.
    flavor: Optional[:class:`str`]
        The listing's flavor text.
    sku: :class:`SKU`
        The SKU attached to this listing.
    child_skus: List[:class:`SKU`]
        The child SKUs attached to this listing.
    alternative_skus: List[:class:`SKU`]
        Alternative SKUs to the one attached to this listing.
    guild: Optional[:class:`Guild`]
        The guild tied to this listing, if any.
    published: :class:`bool`
        Whether the listing is published and publicly visible.
    assets: List[:class:`StoreAsset`]
        A list of assets used in this listing.
    carousel_items: List[:class:`StoreAsset`]
        A list of assets displayed in the carousel.
    preview_video: Optional[:class:`StoreAsset`]
        The preview video of the store listing.
    header_background: Optional[:class:`StoreAsset`]
        The header background image.
    hero_background: Optional[:class:`StoreAsset`]
        The hero background image.
    box_art: Optional[:class:`StoreAsset`]
        The box art of the product.
    thumbnail: Optional[:class:`StoreAsset`]
        The listing's thumbnail.
    header_logo_light: Optional[:class:`StoreAsset`]
        The header logo image for light backgrounds.
    header_logo_dark: Optional[:class:`StoreAsset`]
        The header logo image for dark backgrounds.
    """

    __slots__ = (
        '_state',
        'id',
        'summary',
        'description',
        'tagline',
        'flavor',
        'sku',
        'child_skus',
        'alternative_skus',
        'entitlement_branch_id',
        'guild',
        'published',
        'assets',
        'carousel_items',
        'preview_video',
        'header_background',
        'hero_background',
        'hero_video',
        'box_art',
        'thumbnail',
        'header_logo_light',
        'header_logo_dark',
    )

    def __init__(self, *, data: dict, state: ConnectionState) -> None:
        self._state = state
        self._update(data)

    def __str__(self) -> str:
        return self.summary

    def __repr__(self) -> str:
        return f'<StoreListing id={self.id} summary={self.summary!r} sku={self.sku!r}>'

    def _update(self, data: dict) -> None:
        from .guild import Guild

        state = self._state

        self.id: int = data['id']
        # These seems to be required, but have been observed to be missing in rare cases
        # The default is ' ', as it's been seen used as a default
        self.summary: str = data.get('summary', ' ')
        self.description: str = data.get('description', ' ')
        self.tagline: str = data.get('tagline', ' ')
        self.flavor: Optional[str] = data.get('flavor_text')
        self.sku: SKU = SKU(data=data['sku'], state=state)
        self.child_skus: List[SKU] = [SKU(data=sku, state=state) for sku in data.get('child_skus', [])]
        self.alternative_skus: List[SKU] = [SKU(data=sku, state=state) for sku in data.get('alternative_skus', [])]
        self.entitlement_branch_id: Optional[int] = _get_as_snowflake(data, 'entitlement_branch_id')
        self.guild: Optional[Guild] = Guild(data=data['guild'], state=state) if data.get('guild') else None
        self.published: bool = data.get('published', True)

        self.assets: List[StoreAsset] = [
            StoreAsset(data=asset, state=state, parent=self) for asset in data.get('assets', [])
        ]
        self.carousel_items: List[StoreAsset] = [  # Youtube videos?
            StoreAsset._from_carousel_item(data=asset, state=state, store_listing=self)
            for asset in data.get('carousel_items', [])
        ]
        self.preview_video: Optional[StoreAsset] = (
            StoreAsset(data=data['preview_video'], state=state, parent=self) if data.get('preview_video') else None
        )
        self.header_background: Optional[StoreAsset] = (
            StoreAsset(data=data['header_background'], state=state, parent=self) if data.get('header_background') else None
        )
        self.hero_background: Optional[StoreAsset] = (
            StoreAsset(data=data['hero_background'], state=state, parent=self) if data.get('hero_background') else None
        )
        self.hero_video: Optional[StoreAsset] = (
            StoreAsset(data=data['hero_video'], state=state, parent=self) if data.get('hero_video') else None
        )
        self.box_art: Optional[StoreAsset] = (
            StoreAsset(data=data['box_art'], state=state, parent=self) if data.get('box_art') else None
        )
        self.thumbnail: Optional[StoreAsset] = (
            StoreAsset(data=data['thumbnail'], state=state, parent=self) if data.get('thumbnail') else None
        )
        self.header_logo_light: Optional[StoreAsset] = (
            StoreAsset(data=data['header_logo_light_theme'], state=state, parent=self)
            if 'header_logo_light_theme' in data
            else None
        )
        self.header_logo_dark: Optional[StoreAsset] = (
            StoreAsset(data=data['header_logo_dark_theme'], state=state, parent=self)
            if 'header_logo_dark_theme' in data
            else None
        )

    @property
    def url(self) -> str:
        """:class:`str`: Returns the URL of the store listing. This is the URL of the primary SKU."""
        return self.sku.url


class SKUPrice:
    """Represents a SKU's price.

    .. container:: operations

        .. describe:: bool(x)

            Checks if a SKU costs anything.

        .. describe:: int(x)

            Returns the price of the SKU.

    .. versionadded:: 2.0

    Attributes
    -----------
    currency: :class:`str`
        The currency of the price.
    amount: :class:`int`
        The price of the SKU.
    sale_amount: Optional[:class:`int`]
        The price of the SKU with discounts applied, if any.
    sale_percentage: :class:`int`
        The percentage of the price discounted, if any.
    premium: :class:`bool`
        Whether the price of the SKU is premium.
    """

    __slots__ = ('currency', 'amount', 'sale_amount', 'sale_percentage', 'premium')

    def __init__(self, data: dict) -> None:
        self.currency: str = data.get('currency', 'USD')
        self.amount: int = data.get('amount', 0)
        self.sale_amount: Optional[int] = data.get('sale_amount')
        self.sale_percentage: int = data.get('sale_percentage', 0)
        self.premium: bool = data.get('premium', False)

    def __repr__(self) -> str:
        return f'<SKUPrice amount={self.amount} currency={self.currency!r}>'

    def __bool__(self) -> bool:
        return self.amount > 0

    def __int__(self) -> int:
        return self.amount

    def is_discounted(self) -> bool:
        """:class:`bool`: Checks whether the SKU is discounted."""
        return self.sale_percentage > 0

    def is_free(self) -> bool:
        """:class:`bool`: Checks whether the SKU is free."""
        return self.amount == 0

    @property
    def discounts(self) -> int:
        """:class:`int`: Returns the amount of discounts applied to the SKU price."""
        return self.amount - (self.sale_amount or self.amount)


class ContentRating:
    """Represents a SKU's content rating.

    .. versionadded:: 2.0

    Attributes
    -----------
    agency: :class:`ContentRatingAgency`
        The agency that rated the content.
    rating: :class:`int`
        The rating of the content.
    descriptors: List[:class:`str`]
        Extra descriptors for the content rating.
    """

    __slots__ = ('agency', 'rating', 'descriptors')

    def __init__(self, data: dict, agency: int) -> None:
        self.agency: ContentRatingAgency = try_enum(ContentRatingAgency, agency)
        self.rating: int = data.get('rating', 0)
        self.descriptors: List[str] = data.get('descriptors', [])

    def __repr__(self) -> str:
        return f'<ContentRating agency={self.agency!r} rating={self.rating}>'


class SKU(Hashable):
    """Represents a store SKU.

        .. container:: operations

        .. describe:: x == y

            Checks if two SKUs are equal.

        .. describe:: x != y

            Checks if two SKUs are not equal.

        .. describe:: hash(x)

            Returns the SKU's hash.

        .. describe:: str(x)

            Returns the SKU's name.

    .. versionadded:: 2.0

    Attributes
    -----------
    id: :class:`int`
        The SKU's ID.
    name: :class:`str`
        The name of the SKU.
    name_localizations: Dict[:class:`Locale`, :class:`str`]
        The name of the SKU localized to different languages.
    summary: Optional[:class:`str`]
        The SKU's summary, if any.
    summary_localizations: Dict[:class:`Locale`, :class:`str`]
        The summary of the SKU localized to different languages.
    legal_notice: Optional[:class:`str`]
        The SKU's legal notice, if any.
    legal_notice_localizations: Dict[:class:`Locale`, :class:`str`]
        The legal notice of the SKU localized to different languages.
    type: :class:`SKUType`
        The type of the SKU.
    slug: :class:`str`
        The URL slug of the SKU.
    price: :class:`SKUPrice`
        The price of the SKU.
    dependent_sku_id: Optional[:class:`int`]
        The ID of the SKU that this SKU is dependent on, if any.
    application_id: :class:`int`
        The ID of the application that owns this SKU.
    application: Optional[:class:`PartialApplication`]
        The application that owns this SKU, if available.
    access_level: :class:`SKUAccessLevel`
        The access level of the SKU.
    features: List[:class:`SKUFeature`]
        A list of features that this SKU has.
    locales: List[:class:`Locale`]
        The locales that this SKU is available in.
    genres: List[:class:`SKUGenre`]
        The genres that apply to this SKU.
    available_regions: Optional[List[:class:`str`]]
        The regions that this SKU is available in.
        If this is ``None``, then the SKU is available everywhere.
    content_rating: Optional[:class:`ContentRating`]
        The content rating of the SKU, if any.
    system_requirements: Dict[:class:`OperatingSystem`, :class:`SystemRequirements`]
        A dict of the system requirements of the SKU by operating system, if any.
    release_date: Optional[:class:`datetime.date`]
        The date that the SKU will released, if any.
    preorder_release_date: Optional[:class:`datetime.date`]
        The approximate date that the SKU will released for pre-order, if any.
    preorder_released_at: Optional[:class:`datetime.datetime`]
        The date that the SKU was released for pre-order, if any.
    external_purchase_url: Optional[:class:`str`]
        An external URL to purchase the SKU at, if applicable.
    premium: :class:`bool`
        Whether this SKU is a premium perk.
    restricted: :class:`bool`
        Whether this SKU is restricted.
    exclusive: :class:`bool`
        Whether this SKU is exclusive to Discord.
    show_age_gate: :class:`bool`
        Whether the client should prompt the user to verify their age.
    bundled_skus: List[:class:`SKU`]
        A list of SKUs bundled with this SKU. This is only present if the SKU is a bundle.
    """

    def __init__(self, *, data: dict, state: ConnectionState, application: Optional[PartialApplication] = None) -> None:
        self._state = state
        self.application = application
        self._update(data)

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f'<SKU id={self.id} name={self.name!r} type={self.type!r}>'

    def _update(self, data: dict) -> None:
        from .appinfo import PartialApplication

        state = self._state

        self.id: int = data['id']
        self.name: str = data['name']
        self.summary: Optional[str] = data.get('summary')
        self.legal_notice: Optional[str] = data.get('legal_notice')
        self.type: SKUType = try_enum(SKUType, data['type'])
        self.slug: str = data['slug']
        self.price: SKUPrice = SKUPrice(data.get('price', {}))
        self.dependent_sku_id: Optional[int] = _get_as_snowflake(data, 'dependent_sku_id')
        self.application_id: int = data['application_id']
        self.application: Optional[PartialApplication] = (
            PartialApplication(data=data['application'], state=state)
            if data.get('application')
            else (
                state.premium_subscriptions_application
                if self.application_id == state.premium_subscriptions_application.id
                else self.application
            )
        )
        self._flags: int = data.get('flags', 0)

        self.access_level: SKUAccessLevel = try_enum(SKUAccessLevel, data.get('access_type', 1))
        self.features: List[SKUFeature] = [try_enum(SKUFeature, feature) for feature in data.get('features', [])]
        self.locales: List[Locale] = [try_enum(Locale, locale) for locale in data.get('locales', ['en-US'])]
        self.genres: List[SKUGenre] = [try_enum(SKUGenre, genre) for genre in data.get('genres', [])]
        self.available_regions: Optional[List[str]] = data.get('available_regions')
        self.content_rating: Optional[ContentRating] = (
            ContentRating(data['content_rating'], data['content_rating_agency']) if data.get('content_rating') else None
        )
        self.system_requirements: Dict[OperatingSystem, SystemRequirements] = {
            try_enum(OperatingSystem, int(os)): SystemRequirements(try_enum(OperatingSystem, int(os)), reqs)
            for os, reqs in data.get('system_requirements', {}).items()
        }

        self.release_date: Optional[date] = parse_date(data.get('release_date'))
        self.preorder_release_date: Optional[date] = parse_date(data.get('preorder_approximate_release_date'))
        self.preorder_released_at: Optional[datetime] = parse_time(data.get('preorder_release_at'))
        self.external_purchase_url: Optional[str] = data.get('external_purchase_url')

        self.premium: bool = data.get('premium', False)
        self.restricted: bool = data.get('restricted', False)
        self.exclusive: bool = data.get('exclusive', False)
        self.show_age_gate: bool = data.get('show_age_gate', False)
        self.bundled_skus: List[SKU] = [
            SKU(data=sku, state=state, application=self.application) for sku in data.get('bundled_skus', [])
        ]

        # TODO: Manifests/branches/builds
        self.manifest_labels: Any = data.get('manifest_labels')
        self.manifests: Any = data.get('manifests')

    def is_free(self) -> bool:
        """:class:`bool`: Checks if the SKU is free."""
        return self.price.is_free() and not self.premium

    def is_paid(self) -> bool:
        """:class:`bool`: Checks if the SKU requires payment."""
        return not self.price.is_free() and not self.premium

    def is_preorder(self) -> bool:
        """:class:`bool`: Checks if this SKU is a preorder."""
        return self.preorder_release_date is not None or self.preorder_released_at is not None

    def is_released(self) -> bool:
        """:class:`bool`: Checks if the SKU is released."""
        return self.release_date is not None and self.release_date <= utcnow()

    def is_giftable(self) -> bool:
        """:class:`bool`: Checks if this SKU is giftable."""
        return self.type == SKUType.durable_primary and self.flags.available and not self.external_purchase_url and self.is_paid()

    def is_premium_subscription(self) -> bool:
        """:class:`bool`: Checks if the SKU is a premium subscription (e.g. Nitro or Server Boosts)."""
        return self.application_id == self._state.premium_subscriptions_application.id

    def is_game_awards_winner(self) -> bool:
        """:class:`bool`: Checks if the SKU is a winner of The Game Awards."""
        return self.id in THE_GAME_AWARDS_WINNERS

    @property
    def url(self) -> str:
        """:class:`str`: Returns the URL of the SKU."""
        return f'https://discord.com/store/skus/{self.id}/{self.slug}'

    @property
    def flags(self) -> SKUFlags:
        """:class:`SKUFlags`: Returns the SKU's flags."""
        return SKUFlags._from_value(self._flags)

    @property
    def supported_operating_systems(self) -> List[OperatingSystem]:
        """List[:class:`OperatingSystem`]: A list of supported operating systems."""
        return list(self.system_requirements.keys()) if self.system_requirements else [OperatingSystem.windows]

    async def store_listings(self) -> List[StoreListing]:
        r"""|coro|

        Returns a list of :class:`StoreListing`\s for this SKU.

        Raises
        ------
        Forbidden
            You do not have access to fetch store listings.
        HTTPException
            Getting the store listings failed.

        Returns
        -------
        List[:class:`StoreListing`]
            The store listings for this SKU.
        """
        data = await self._state.http.get_sku_store_listings(self.id)
        return [StoreListing(data=listing, state=self._state) for listing in data]

    async def preview_purchase(self): ...

    async def purchase(self): ...


class SubscriptionPlan:
    """Represents a subscription plan for a :class:`SKU`.

    .. versionadded:: 2.0



    """

    def __init__(self, *, data: dict, state: ConnectionState) -> None:
        self._state = state

"""
NearKart — PostGIS Geo Utility Functions

Algorithms implemented:
  2. Weighted Relevance Ranking — multi-factor store scoring
     (distance × rating × open-status × offer × popularity)
  4. XFetch integration        — anti-stampede cache refresh on hot geo queries
  fix: distinct() removed from products query (replaced with Exists subquery)
"""
import logging
import requests
from datetime import date
from django.conf import settings
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from django.db.models import (
    Count, Avg, Prefetch, Exists, OuterRef, Q,
    ExpressionWrapper, FloatField, Case, When, F, Value,
)
from django.db.models.functions import Coalesce

logger = logging.getLogger(__name__)


def build_point(lat: float, lng: float) -> Point:
    """Build a PostGIS Point from lat/lng. Note: Point takes (lng, lat)."""
    return Point(lng, lat, srid=4326)


def get_nearby_stores(lat: float, lng: float,
                      radius_km: int = 2, category: str = None,
                      store_type: str = None,
                      limit: int = 50) -> list:
    """
    Find stores within radius using PostGIS ST_DWithin (GIST index).

    Ranked by weighted relevance score (Algorithm 2):
      40 % — inverse distance  (closer = higher)
      25 % — avg review rating
      20 % — currently open
      10 % — has active offer
       5 % — follower popularity (capped)

    Uses XFetch (Algorithm 4) to prevent cache stampede on expiry.
    """
    from apps.stores.models import Store, StoreHours, StoreOffer
    from core.utils.cache import CacheService

    cache_key = CacheService.nearby_stores_key(lat, lng, radius_km, category or 'all', store_type or 'all')

    def _fetch():
        user_point = build_point(lat, lng)

        has_offer_sq = StoreOffer.objects.filter(store=OuterRef('pk'), is_active=True)

        qs = Store.objects.filter(
            is_active=True,
            is_verified=True,
            privacy_mode=False,
            location__dwithin=(user_point, D(km=radius_km)),
        ).annotate(
            distance=Distance('location', user_point),
            follower_count=Count('followers', distinct=True),
            avg_rating=Avg('reviews__rating'),
            review_count_ann=Count('reviews', distinct=True),
            has_active_offer=Exists(has_offer_sq),
            # Weighted relevance score
            # distance is in metres (geography=True on PointField)
            relevance_score=ExpressionWrapper(
                # Inverse-distance decay (400 / (d_m + 10))
                # at   10 m → 36.4,  500 m → 0.79,  2 km → 0.20
                Value(400.0) / (F('distance') + Value(10.0)) +
                # Rating: 0–5 linear (Coalesce handles NULL)
                Value(0.25) * Coalesce(F('avg_rating'), Value(0.0)) +
                # Open-now bonus
                Case(When(is_open=True, then=Value(2.0)),
                     default=Value(0.0), output_field=FloatField()) +
                # Active-offer bonus
                Case(When(has_active_offer=True, then=Value(1.0)),
                     default=Value(0.0), output_field=FloatField()) +
                # Popularity: capped at 100 followers → max 0.5 pts
                Case(
                    When(follower_count__gt=100, then=Value(0.5)),
                    default=ExpressionWrapper(
                        F('follower_count') * Value(0.005),
                        output_field=FloatField(),
                    ),
                    output_field=FloatField(),
                ),
                output_field=FloatField(),
            ),
        ).prefetch_related(
            Prefetch('hours', queryset=StoreHours.objects.filter(is_closed=False)),
            Prefetch('offers', queryset=StoreOffer.objects.filter(
                is_active=True
            ).filter(
                Q(valid_till__isnull=True) | Q(valid_till__gte=date.today())
            ).order_by('-created_at')),
        ).order_by('-relevance_score')

        if category and category != 'all':
            qs = qs.filter(category=category)

        if store_type and store_type in ('product', 'service', 'home'):
            qs = qs.filter(store_type=store_type)

        return list(qs[:limit])

    # XFetch: recompute probabilistically before TTL expires to prevent stampede
    return CacheService.get_or_compute(
        cache_key, _fetch, ttl=CacheService.TTL_NEARBY_STORES
    )


def get_nearby_products(lat: float, lng: float,
                        radius_km: int = 2, category: str = None,
                        store_id: str = None, limit: int = 50) -> list:
    """
    Find active, visible products from stores within radius.

    distinct() replaced with Exists subquery (fix): the old JOIN on
    variants__stock_quantity__gt=0 produced duplicate rows per variant
    and required DISTINCT + ORDER BY, which is expensive at scale.
    """
    from apps.products.models import Product, ProductVariant
    from core.utils.cache import CacheService

    store_suffix = store_id or 'all'
    cache_key = (
        CacheService.nearby_products_key(lat, lng, radius_km, category or 'all')
        + f'_store_{store_suffix}'
    )
    cached = CacheService.get(cache_key)
    if cached is not None:
        return cached[:limit]

    user_point  = build_point(lat, lng)
    has_stock   = Exists(
        ProductVariant.objects.filter(product=OuterRef('pk'), stock_quantity__gt=0)
    )

    qs = Product.objects.filter(
        status='active',
        is_visible=True,
        store__is_active=True,
        store__is_verified=True,
    ).filter(has_stock).select_related('store').prefetch_related(
        'variants', 'images',
    ).annotate(
        distance=Distance('store__location', user_point),
    ).order_by('distance')

    if store_id:
        qs = qs.filter(store_id=store_id)
    else:
        qs = qs.filter(store__location__dwithin=(user_point, D(km=radius_km)))

    if category:
        qs = qs.filter(category=category)

    # Cache up to 200 items so paginated views can slice without a cache miss
    result = list(qs[:200])
    CacheService.set(cache_key, result, timeout=CacheService.TTL_PRODUCT_SEARCH)
    return result[:limit]


def reverse_geocode(lat: float, lng: float) -> str:
    """
    Convert lat/lng to locality name using Google Maps Geocoding API.
    Returns locality string e.g. "Kukatpally, Hyderabad".
    Falls back to "Unknown area" on failure.
    """
    try:
        url    = 'https://maps.googleapis.com/maps/api/geocode/json'
        params = {
            'latlng':      f'{lat},{lng}',
            'key':         settings.GOOGLE_MAPS_API_KEY,
            'result_type': 'sublocality|locality',
            'language':    'en',
        }
        response = requests.get(url, params=params, timeout=5)
        data     = response.json()
        if data.get('status') == 'OK' and data.get('results'):
            return data['results'][0].get('formatted_address', 'Unknown area')
    except Exception as e:
        logger.warning('Reverse geocode failed for %s,%s: %s', lat, lng, e)
    return 'Unknown area'

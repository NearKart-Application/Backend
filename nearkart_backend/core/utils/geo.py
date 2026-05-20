"""
NearKart — PostGIS Geo Utility Functions
"""
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def build_point(lat: float, lng: float) -> Point:
    """Build a PostGIS Point from lat/lng. Note: Point takes (lng, lat)."""
    return Point(lng, lat, srid=4326)


def get_nearby_stores(lat: float, lng: float,
                      radius_km: int = 2, category: str = None,
                      limit: int = 50) -> list:
    """
    Find stores within radius using PostGIS ST_DWithin (uses GIST index).
    Returns queryset ordered by distance ASC.
    """
    from apps.stores.models import Store
    from core.utils.cache import CacheService

    cache_key = CacheService.nearby_stores_key(lat, lng, radius_km, category or 'all')
    cached = CacheService.get(cache_key)
    if cached is not None:
        return cached

    user_point = build_point(lat, lng)

    from apps.stores.models import StoreHours, StoreOffer
    from django.db.models import Count, Avg, Prefetch

    qs = Store.objects.filter(
        is_active=True,
        is_verified=True,
        location__dwithin=(user_point, D(km=radius_km))
    ).annotate(
        distance=Distance('location', user_point),
        follower_count=Count('followers', distinct=True),
        avg_rating=Avg('reviews__rating'),
        review_count_ann=Count('reviews', distinct=True),
    ).prefetch_related(
        Prefetch('hours', queryset=StoreHours.objects.filter(is_closed=False)),
        Prefetch('offers', queryset=StoreOffer.objects.filter(is_active=True).order_by('-created_at')),
    ).order_by('distance')

    if category and category != 'all':
        qs = qs.filter(category=category)

    result = list(qs[:limit])
    CacheService.set(cache_key, result, timeout=CacheService.TTL_NEARBY_STORES)
    return result


def get_nearby_products(lat: float, lng: float,
                        radius_km: int = 2, category: str = None,
                        store_id: str = None, limit: int = 50) -> list:
    """
    Find active, visible products from stores within radius.
    Optionally filter to a single store (store_id) or category.
    """
    from apps.products.models import Product
    from core.utils.cache import CacheService

    store_suffix = store_id or 'all'
    cache_key = CacheService.nearby_products_key(lat, lng, radius_km, category or 'all') + f'_store_{store_suffix}'
    cached = CacheService.get(cache_key)
    if cached is not None:
        return cached

    user_point = build_point(lat, lng)
    qs = Product.objects.filter(
        status='active',
        is_visible=True,
        store__is_active=True,
        store__is_verified=True,
        variants__stock_quantity__gt=0,
    ).select_related('store').prefetch_related('variants', 'images').annotate(
        distance=Distance('store__location', user_point)
    ).order_by('distance').distinct()

    if store_id:
        qs = qs.filter(store_id=store_id)
    else:
        qs = qs.filter(store__location__dwithin=(user_point, D(km=radius_km)))

    if category:
        qs = qs.filter(category=category)

    result = list(qs[:limit])
    CacheService.set(cache_key, result, timeout=CacheService.TTL_PRODUCT_SEARCH)
    return result


def reverse_geocode(lat: float, lng: float) -> str:
    """
    Convert lat/lng to locality name using Google Maps Geocoding API.
    Returns locality string e.g. "Kukatpally, Hyderabad"
    Falls back to "Unknown area" on failure.
    """
    try:
        url = 'https://maps.googleapis.com/maps/api/geocode/json'
        params = {
            'latlng': f'{lat},{lng}',
            'key': settings.GOOGLE_MAPS_API_KEY,
            'result_type': 'sublocality|locality',
            'language': 'en',
        }
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        if data.get('status') == 'OK' and data.get('results'):
            return data['results'][0].get('formatted_address', 'Unknown area')
    except Exception as e:
        logger.warning(f'Reverse geocode failed for {lat},{lng}: {e}')

    return 'Unknown area'

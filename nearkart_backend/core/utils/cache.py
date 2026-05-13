"""
NearKart — Redis Cache Key Management
Centralised cache key builders and invalidation helpers
"""
import hashlib
from django.core.cache import cache


class CacheService:
    """All Redis cache key patterns in one place."""

    # ── TTL CONSTANTS ─────────────────────────────────────────
    TTL_NEARBY_STORES = 300    # 5 minutes
    TTL_VIDEO_FEED = 120       # 2 minutes
    TTL_PRODUCT_SEARCH = 60    # 1 minute
    TTL_STORE_DETAIL = 600     # 10 minutes

    # ── KEY BUILDERS ──────────────────────────────────────────
    @staticmethod
    def nearby_stores_key(lat: float, lng: float,
                          radius: int, category: str = 'all') -> str:
        """Round lat/lng to 3 decimals = ~100m grid squares."""
        raw = f'stores:nearby:{round(lat,3)}:{round(lng,3)}:{radius}:{category}'
        return hashlib.md5(raw.encode()).hexdigest()

    @staticmethod
    def video_feed_key(locality: str) -> str:
        """All users in same locality share feed cache."""
        return f'feed:nearby:{hashlib.md5(locality.encode()).hexdigest()}'

    @staticmethod
    def product_search_key(query: str, lat: float, lng: float) -> str:
        raw = f'products:search:{query}:{round(lat,3)}:{round(lng,3)}'
        return hashlib.md5(raw.encode()).hexdigest()

    @staticmethod
    def store_detail_key(store_id: str) -> str:
        return f'store:detail:{store_id}'

    # ── GET / SET ─────────────────────────────────────────────
    @staticmethod
    def get(key: str):
        return cache.get(key)

    @staticmethod
    def set(key: str, value, timeout: int = 300):
        cache.set(key, value, timeout)

    @staticmethod
    def delete(key: str):
        cache.delete(key)

    # ── INVALIDATION ──────────────────────────────────────────
    @staticmethod
    def invalidate_video_feed(locality: str):
        """Call when vendor posts new video in an area."""
        cache.delete(CacheService.video_feed_key(locality))

    @staticmethod
    def invalidate_store_caches(lat: float, lng: float):
        """Call when store location or details change."""
        for radius in [1, 2, 3, 5]:
            for category in ['all', 'fashion', 'jewellery', 'footwear',
                              'decor', 'furniture', 'gifts', 'beauty']:
                cache.delete(
                    CacheService.nearby_stores_key(lat, lng, radius, category)
                )

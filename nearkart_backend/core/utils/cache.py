"""
NearKart — Redis Cache Key Management

Algorithms implemented:
  1. H3 Hexagonal Geohash      — smarter spatial cache partitioning
  3. Two-Level Cache (L1 + L2) — in-process TTLCache + Redis
  4. XFetch                    — probabilistic anti-stampede refresh
  5. HyperLogLog               — O(1) unique visitor counting
  6. Sliding Window Rate Limit — true rolling window, no burst gap
"""
import hashlib
import math
import random
import threading
import time

from django.core.cache import cache
from cachetools import TTLCache

# ── H3 with version-agnostic import ──────────────────────────────────────────
try:
    import h3 as _h3lib
    def _h3_cell(lat: float, lng: float, resolution: int = 9) -> str:
        """Convert lat/lng to an H3 hexagonal cell ID (resolution 9 ≈ 170 m)."""
        try:
            return _h3lib.latlng_to_cell(lat, lng, resolution)   # h3 >= 4.0
        except AttributeError:
            return _h3lib.geo_to_h3(lat, lng, resolution)        # h3 < 4.0
    _H3_AVAILABLE = True
except ImportError:
    _H3_AVAILABLE = False
    def _h3_cell(lat: float, lng: float, resolution: int = 9) -> str:
        """Fallback: ~100 m grid squares when h3 is not installed."""
        return f'{round(lat, 3)}_{round(lng, 3)}'

# ── L1 In-Process Cache (Two-Level Cache, Layer 1) ────────────────────────────
# 500 keys × 30 s TTL keeps the hottest nearby-store responses out of Redis.
_L1: TTLCache = TTLCache(maxsize=500, ttl=30)
_L1_LOCK      = threading.Lock()


class CacheService:
    """All Redis cache key patterns and helper algorithms in one place."""

    # ── TTL constants ─────────────────────────────────────────────────────────
    TTL_NEARBY_STORES    = 300    # 5 min  — geo results shift when stores open/close
    TTL_VIDEO_FEED       = 120    # 2 min  — near-you feed; new uploads appear quickly
    TTL_VIDEO_TRENDING   = 300    # 5 min  — trending changes slowly
    TTL_VIDEO_FOLLOWING  = 60     # 1 min  — following feed; user expects fresh content
    TTL_PRODUCT_SEARCH   = 60     # 1 min  — search results
    TTL_PRODUCT_DETAIL   = 300    # 5 min  — product detail; changes infrequently
    TTL_STORE_DETAIL     = 600    # 10 min — store detail; invalidated on update
    TTL_STORE_REVIEWS    = 300    # 5 min  — reviews; invalidated on new review
    TTL_STORE_OFFERS     = 300    # 5 min  — offers; invalidated on create/delete

    # ── Key builders (H3-based) ───────────────────────────────────────────────

    @staticmethod
    def nearby_stores_key(lat: float, lng: float,
                          radius: int, category: str = 'all',
                          store_type: str = 'all') -> str:
        cell = _h3_cell(lat, lng)
        raw  = f'stores:nearby:{cell}:{radius}:{category}:{store_type}'
        return hashlib.md5(raw.encode()).hexdigest()

    @staticmethod
    def video_feed_key(locality: str) -> str:
        return f'feed:nearby:{hashlib.md5(locality.encode()).hexdigest()}'

    @staticmethod
    def product_search_key(query: str, lat: float, lng: float) -> str:
        cell = _h3_cell(lat, lng)
        raw  = f'products:search:{query}:{cell}'
        return hashlib.md5(raw.encode()).hexdigest()

    @staticmethod
    def store_detail_key(store_id: str) -> str:
        return f'store:detail:{store_id}'

    @staticmethod
    def nearby_products_key(lat: float, lng: float,
                            radius: int, category: str = 'all') -> str:
        cell = _h3_cell(lat, lng)
        raw  = f'products:nearby:{cell}:{radius}:{category}'
        return hashlib.md5(raw.encode()).hexdigest()

    @staticmethod
    def product_detail_key(product_id: str) -> str:
        return f'product:detail:{product_id}'

    @staticmethod
    def store_reviews_key(store_id: str) -> str:
        return f'store:reviews:{store_id}'

    @staticmethod
    def store_offers_key(store_id: str) -> str:
        return f'store:offers:{store_id}'

    @staticmethod
    def video_feed_near_you_key(lat: float, lng: float, radius: int = 5) -> str:
        cell = _h3_cell(lat, lng, resolution=7)   # resolution 7 ≈ 5 km cells
        raw  = f'video:feed:nearby:{cell}:{radius}'
        return hashlib.md5(raw.encode()).hexdigest()

    @staticmethod
    def video_feed_trending_key() -> str:
        return 'video:feed:trending'

    @staticmethod
    def video_feed_following_key(user_id: str) -> str:
        return f'video:feed:following:{user_id}'

    # ── Two-Level Get / Set / Delete ──────────────────────────────────────────

    @staticmethod
    def get(key: str):
        with _L1_LOCK:
            if key in _L1:
                return _L1[key]
        value = cache.get(key)
        if value is not None:
            with _L1_LOCK:
                _L1[key] = value
        return value

    @staticmethod
    def set(key: str, value, timeout: int = 300):
        cache.set(key, value, timeout)
        with _L1_LOCK:
            _L1[key] = value

    @staticmethod
    def delete(key: str):
        cache.delete(key)
        with _L1_LOCK:
            _L1.pop(key, None)

    # ── XFetch — Probabilistic Anti-Stampede Refresh ──────────────────────────
    #
    # When a key is about to expire, XFetch probabilistically decides to
    # recompute *before* it expires so concurrent requests never all miss at once.
    # Paper: "Optimal Probabilistic Cache Stampede Prevention" — Vattani et al.

    @staticmethod
    def get_or_compute(key: str, compute_fn, ttl: int, beta: float = 1.0):
        value = CacheService.get(key)
        if value is not None:
            remaining = cache.ttl(key) or 0
            if isinstance(remaining, int) and remaining > 0:
                # Keep cached value unless XFetch says refresh now
                if -beta * math.log(max(random.random(), 1e-10)) < remaining:
                    return value
        # Recompute and re-cache
        value = compute_fn()
        if value is not None:
            CacheService.set(key, value, timeout=ttl)
        return value

    # ── HyperLogLog — O(1) Unique Visitor Counting ───────────────────────────
    #
    # Counts unique store visitors with ~1 % error using only 12 KB per key.
    # Redis built-in: PFADD / PFCOUNT. No user IDs stored — privacy safe.

    @staticmethod
    def record_store_visit(store_id: str, user_id: str) -> None:
        try:
            from django_redis import get_redis_connection
            from django.utils import timezone
            r     = get_redis_connection('default')
            today = timezone.now().strftime('%Y-%m-%d')
            key   = f'nearkart:hll:store:{store_id}:{today}'
            r.pfadd(key, str(user_id))
            r.expire(key, 86400 * 30)   # 30-day retention
        except Exception:
            pass   # analytics — never block the request

    @staticmethod
    def get_unique_visitors(store_id: str, date: str = None) -> int:
        try:
            from django_redis import get_redis_connection
            from django.utils import timezone
            r    = get_redis_connection('default')
            date = date or timezone.now().strftime('%Y-%m-%d')
            return int(r.pfcount(f'nearkart:hll:store:{store_id}:{date}'))
        except Exception:
            return 0

    @staticmethod
    def get_unique_visitors_range(store_id: str, days: int = 7) -> dict:
        """Return unique visitor counts for the last N days as {date: count}."""
        try:
            from django_redis import get_redis_connection
            from django.utils import timezone
            import datetime
            r      = get_redis_connection('default')
            today  = timezone.now().date()
            result = {}
            for i in range(days):
                d   = (today - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
                cnt = r.pfcount(f'nearkart:hll:store:{store_id}:{d}')
                result[d] = int(cnt)
            return result
        except Exception:
            return {}

    # ── Sliding Window Rate Limiter ───────────────────────────────────────────
    #
    # True rolling window using Redis sorted set (ZSET).
    # Eliminates the burst vulnerability of fixed-window counters:
    # with fixed windows a user can fire max_requests at 11:59 and
    # max_requests again at 12:01 — this implementation prevents that.

    @staticmethod
    def is_rate_limited(key: str, max_requests: int, window_secs: int) -> bool:
        """
        Returns True if the caller has exceeded max_requests in the last
        window_secs seconds. Fails open (returns False) on Redis error.
        """
        try:
            from django_redis import get_redis_connection
            r         = get_redis_connection('default')
            now       = time.time()
            win_start = now - window_secs
            full_key  = f'nearkart:ratelimit:{key}'
            member    = f'{now}:{random.random()}'   # unique per call
            pipe      = r.pipeline()
            pipe.zremrangebyscore(full_key, 0, win_start)  # remove stale
            pipe.zadd(full_key, {member: now})             # add current
            pipe.zcard(full_key)                           # count in window
            pipe.expire(full_key, window_secs)
            results = pipe.execute()
            return int(results[2]) > max_requests
        except Exception:
            return False   # fail open — never block on Redis error

    # ── Invalidation helpers ──────────────────────────────────────────────────

    @staticmethod
    def invalidate_video_feed(locality: str):
        CacheService.delete(CacheService.video_feed_key(locality))

    @staticmethod
    def invalidate_store_reviews(store_id: str):
        CacheService.delete(CacheService.store_reviews_key(store_id))

    @staticmethod
    def invalidate_store_offers(store_id: str):
        CacheService.delete(CacheService.store_offers_key(store_id))

    @staticmethod
    def invalidate_product_detail(product_id: str):
        CacheService.delete(CacheService.product_detail_key(product_id))

    @staticmethod
    def invalidate_video_feeds(user_id: str = None):
        CacheService.delete(CacheService.video_feed_trending_key())
        if user_id:
            CacheService.delete(CacheService.video_feed_following_key(user_id))

    @staticmethod
    def invalidate_store_caches(lat: float, lng: float):
        """Bust all nearby-store cache keys for the grid cell containing this location."""
        for radius in [1, 2, 3, 5, 10]:
            for category in ['all', 'fashion', 'jewellery', 'footwear',
                              'decor', 'furniture', 'gifts', 'beauty',
                              'food', 'electronics']:
                CacheService.delete(
                    CacheService.nearby_stores_key(lat, lng, radius, category)
                )

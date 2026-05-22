"""
NearKart — Upload Rate Tracker

Algorithm: Atomic Redis Lua check-and-increment.
Eliminates the race condition of INCR-then-check-then-maybe-decrement.

Key pattern:
    nearkart:uploads:{media_type}:{vendor_id}:{YYYY-MM-DD}

TTL: 2 days — daily key ensures counts reset naturally at midnight IST.
     2-day TTL (not 1-day) so a key written at 23:59 survives until the
     next day's logic can still read it for analytics.

Fail-open design: Redis errors never block uploads. A cache outage should
not prevent vendors from uploading — billing limits still apply via DB.
"""
import logging

from django.utils import timezone

logger = logging.getLogger(__name__)

# Atomic Lua script: checks current count against limit, increments only if
# under limit. Returns [1, new_count] if allowed, [0, current_count] if not.
# limit=0 means unlimited — always returns [1, 0] without touching Redis.
_LUA_CHECK_AND_INCREMENT = """
local key   = KEYS[1]
local limit = tonumber(ARGV[1])
local ttl   = tonumber(ARGV[2])
if limit == 0 then
    return {1, 0}
end
local current = tonumber(redis.call('GET', key) or '0')
if current >= limit then
    return {0, current}
end
local new_val = redis.call('INCR', key)
if new_val == 1 then
    redis.call('EXPIRE', key, ttl)
end
return {1, new_val}
"""


class UploadTracker:
    """
    Per-vendor per-day upload counter backed by Redis.

    Usage:
        allowed, count = UploadTracker.check_and_increment(
            vendor_id=str(request.user.id),
            media_type=UploadTracker.MEDIA_VIDEO,
            daily_limit=settings.VIDEO_DAILY_UPLOAD_LIMIT,
        )
        if not allowed:
            return Response({'error': 'daily_limit_reached'}, status=429)
    """

    MEDIA_VIDEO = 'video'
    MEDIA_PHOTO = 'photo'

    # 2-day TTL — see module docstring
    _TTL = 86400 * 2

    @staticmethod
    def _key(vendor_id: str, media_type: str) -> str:
        today = timezone.now().strftime('%Y-%m-%d')
        return f'nearkart:uploads:{media_type}:{vendor_id}:{today}'

    @staticmethod
    def check_and_increment(vendor_id: str, media_type: str, daily_limit: int) -> tuple[bool, int]:
        """
        Atomically check the daily limit and increment if allowed.

        Returns:
            (True, new_count)    — upload is allowed
            (False, cur_count)   — daily limit reached
            (True, 0)            — Redis error, fail-open
        """
        try:
            from django_redis import get_redis_connection
            r   = get_redis_connection('default')
            key = UploadTracker._key(str(vendor_id), media_type)
            result = r.eval(
                _LUA_CHECK_AND_INCREMENT,
                1,                         # number of keys
                key,                       # KEYS[1]
                daily_limit,               # ARGV[1]
                UploadTracker._TTL,        # ARGV[2]
            )
            return bool(int(result[0])), int(result[1])
        except Exception as exc:
            logger.warning('UploadTracker.check_and_increment failed — failing open: %s', exc)
            return True, 0

    @staticmethod
    def get_today_count(vendor_id: str, media_type: str) -> int:
        """Return today's upload count without modifying it."""
        try:
            from django_redis import get_redis_connection
            r   = get_redis_connection('default')
            val = r.get(UploadTracker._key(str(vendor_id), media_type))
            return int(val) if val else 0
        except Exception:
            return 0

    @staticmethod
    def get_stats(vendor_id: str) -> dict:
        """Return today's upload counts for both media types (used by analytics endpoint)."""
        return {
            'videos_today': UploadTracker.get_today_count(vendor_id, UploadTracker.MEDIA_VIDEO),
            'photos_today': UploadTracker.get_today_count(vendor_id, UploadTracker.MEDIA_PHOTO),
        }

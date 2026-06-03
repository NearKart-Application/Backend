"""
NearKart — Middleware
  - JWTAuthMiddleware      : authenticates WebSocket connections via JWT query param
  - RequestLoggingMiddleware: logs every HTTP request to requests.log + app.log
"""
import time
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken
import logging

logger = logging.getLogger(__name__)

# Paths we never log — too noisy, zero business value
_SKIP_PREFIXES = ('/health/', '/static/', '/media/', '/favicon')


class JWTAuthMiddleware(BaseMiddleware):
    """
    Authenticates WebSocket connections using JWT token
    passed as query parameter: ws://...?token=eyJhbGc...
    Sets scope['user'] = User instance or None
    """

    async def __call__(self, scope, receive, send):
        query_string = scope.get('query_string', b'').decode()
        params = parse_qs(query_string)
        token_key = params.get('token', [None])[0]
        scope['user'] = await self._get_user(token_key)
        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def _get_user(self, token_key):
        if not token_key:
            return None
        try:
            token = AccessToken(token_key)
            from apps.auth_app.models import User
            return User.objects.get(id=token['user_id'])
        except (TokenError, Exception) as e:
            logger.debug(f'WebSocket JWT auth failed: {e}')
            return None


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)


# Paths that contain user-specific data and must never be cached by the client.
# Pattern is matched as a substring of the request path.
_NO_CACHE_API_PATHS = (
    '/auth/me',
    '/stores/mine',
    '/products/vendor',
    '/profile/wishlist',
    '/stores/mine/staff',
    '/stores/mine/invoices',
    '/loyalty/',
    '/wallet/',
    '/reservations/',
    '/notifications/',
)


class NoCachePersonalizedDataMiddleware:
    """
    Sets Cache-Control: no-store on API responses that contain user-specific data.
    This is a server-side safety net — the mobile OkHttp interceptor also excludes
    these paths from caching, but belt-and-suspenders here prevents stale reads from
    any client (web, other mobile versions, etc.) that might cache these responses.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (request.method == 'GET' and
                request.path.startswith('/api/') and
                any(segment in request.path for segment in _NO_CACHE_API_PATHS) and
                'Cache-Control' not in response):
            response['Cache-Control'] = 'no-store'
        return response


class RequestLoggingMiddleware:
    """
    Logs every HTTP request to requests.log (human-readable) and app.log (JSON).

    Each line captures: method, path, status, duration_ms, user_id, role.
    Health checks, static files, and media are skipped to keep logs clean.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if any(request.path.startswith(p) for p in _SKIP_PREFIXES):
            return self.get_response(request)

        start    = time.monotonic()
        response = self.get_response(request)
        duration = int((time.monotonic() - start) * 1000)

        user = getattr(request, 'user', None)
        authed = user is not None and user.is_authenticated

        level = 'info'
        if response.status_code >= 500:
            level = 'error'
        elif response.status_code >= 400:
            level = 'warning'

        from core.logging import log_event, SLOW_REQUEST_MS
        log_event(
            'requests',
            level       = level,
            action      = 'http_request',
            method      = request.method,
            path        = request.path,
            status      = response.status_code,
            duration_ms = duration,
            user_id     = str(user.id)   if authed else None,
            role        = user.role      if authed else None,
        )

        # ── Security channel: 401 / 403 / 429 are threat signals ─────────
        if response.status_code in (401, 403, 429):
            security_action = {
                401: 'unauthorized_access',
                403: 'forbidden_access',
                429: 'rate_limit_exceeded',
            }[response.status_code]
            log_event(
                'security',
                level   = 'warning',
                action  = security_action,
                method  = request.method,
                path    = request.path,
                status  = response.status_code,
                ip      = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '')),
                user_id = str(user.id) if authed else None,
            )

        # ── Performance channel: flag slow responses ──────────────────────
        if duration >= SLOW_REQUEST_MS:
            log_event(
                'performance',
                level       = 'warning',
                action      = 'slow_request',
                method      = request.method,
                path        = request.path,
                status      = response.status_code,
                duration_ms = duration,
                threshold_ms= SLOW_REQUEST_MS,
            )

        return response

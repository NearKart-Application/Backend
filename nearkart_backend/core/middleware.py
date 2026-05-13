"""
NearKart — JWT Authentication Middleware for WebSocket
"""
from urllib.parse import parse_qs
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError
import logging

logger = logging.getLogger(__name__)


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

"""
NearKart — Custom Authentication

SoftJWTAuthentication: same as JWTAuthentication but invalid/expired tokens
degrade to anonymous instead of raising 401. This lets AllowAny endpoints
work even when the client sends a stale or dev-bypass token.
"""
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class SoftJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except (InvalidToken, TokenError):
            return None

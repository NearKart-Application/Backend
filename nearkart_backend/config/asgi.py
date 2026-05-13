"""
NearKart — ASGI Configuration
Handles both HTTP (REST API) and WebSocket (chat)
"""
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

# Must be imported after setting DJANGO_SETTINGS_MODULE
django_asgi_app = get_asgi_application()

from core.middleware import JWTAuthMiddlewareStack  # noqa
from apps.chat.routing import chat_urlpatterns       # noqa
from apps.groups.routing import group_urlpatterns   # noqa

application = ProtocolTypeRouter({
    # REST API → standard Django
    'http': django_asgi_app,

    # WebSocket → Django Channels with JWT auth
    'websocket': AllowedHostsOriginValidator(
        JWTAuthMiddlewareStack(
            URLRouter(
                chat_urlpatterns +
                group_urlpatterns
            )
        )
    ),
})

from django.urls import re_path

from .consumers import ChatConsumer

chat_urlpatterns = [
    re_path(r'^ws/conversations/(?P<conversation_id>[0-9a-f-]{36})/$', ChatConsumer.as_asgi()),
]

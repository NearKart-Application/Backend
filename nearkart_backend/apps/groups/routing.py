from django.urls import re_path

from .consumers import GroupConsumer

group_urlpatterns = [
    re_path(r'^ws/groups/(?P<group_id>[0-9a-f-]{36})/$', GroupConsumer.as_asgi()),
]

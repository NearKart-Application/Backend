from django.urls import path
from .views import (
    PlatformStatsView,
    AdminStoreListView,
    AdminStoreUpdateView,
    AdminUserListView,
    AdminUserToggleActiveView,
)

urlpatterns = [
    path('stats/',                           PlatformStatsView.as_view(),          name='admin-stats'),
    path('stores/',                          AdminStoreListView.as_view(),          name='admin-store-list'),
    path('stores/<uuid:store_id>/',          AdminStoreUpdateView.as_view(),        name='admin-store-update'),
    path('users/',                           AdminUserListView.as_view(),           name='admin-user-list'),
    path('users/<uuid:user_id>/toggle-active/', AdminUserToggleActiveView.as_view(), name='admin-user-toggle'),
]

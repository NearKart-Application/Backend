from django.urls import path
from .views import (
    NearbyStoresView, StoreDetailView, StoreCreateView,
    StoreUpdateView, StoreFollowView, StoreReviewView, StoreQRCodeView,
)
from apps.blacklist.views import BlacklistToggleView, BlacklistListView

urlpatterns = [
    path('nearby/',                  NearbyStoresView.as_view(),  name='stores-nearby'),
    path('',                         StoreCreateView.as_view(),   name='store-create'),
    path('<uuid:store_id>/',         StoreDetailView.as_view(),   name='store-detail'),
    path('<uuid:store_id>/update/',  StoreUpdateView.as_view(),   name='store-update'),
    path('<uuid:store_id>/follow/',  StoreFollowView.as_view(),   name='store-follow'),
    path('<uuid:store_id>/review/',  StoreReviewView.as_view(),   name='store-review'),
    path('<uuid:store_id>/qr-code/', StoreQRCodeView.as_view(),   name='store-qr-code'),
    # Sprint 6 — Blacklist
    path('<uuid:store_id>/blacklist/',                           BlacklistListView.as_view(),   name='store-blacklist-list'),
    path('<uuid:store_id>/blacklist/<uuid:customer_id>/',        BlacklistToggleView.as_view(), name='store-blacklist-toggle'),
]


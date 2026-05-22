from django.urls import path
from .views import (
    NearbyStoresView, StoreDetailView, StoreCreateView, StoreMyView,
    StoreUpdateView, StoreFollowView, StoreReviewView, StoreQRCodeView,
    StoreHoursView, StoreReviewListView, StoreOfferView, StoreOfferDeleteView,
)
from apps.blacklist.views import BlacklistToggleView, BlacklistListView

urlpatterns = [
    path('nearby/',                  NearbyStoresView.as_view(),  name='stores-nearby'),
    path('mine/',                    StoreMyView.as_view(),       name='store-mine'),
    path('',                         StoreCreateView.as_view(),   name='store-create'),
    path('<uuid:store_id>/',         StoreDetailView.as_view(),   name='store-detail'),
    path('<uuid:store_id>/update/',  StoreUpdateView.as_view(),   name='store-update'),
    path('<uuid:store_id>/follow/',  StoreFollowView.as_view(),   name='store-follow'),
    path('<uuid:store_id>/review/',  StoreReviewView.as_view(),   name='store-review'),
    path('<uuid:store_id>/reviews/', StoreReviewListView.as_view(), name='store-reviews-list'),
    path('<uuid:store_id>/offers/',  StoreOfferView.as_view(),    name='store-offers'),
    path('<uuid:store_id>/offers/<uuid:offer_id>/', StoreOfferDeleteView.as_view(), name='store-offer-delete'),
    path('<uuid:store_id>/qr-code/', StoreQRCodeView.as_view(),   name='store-qr-code'),
    path('<uuid:store_id>/hours/',   StoreHoursView.as_view(),    name='store-hours'),
    # Blacklist
    path('<uuid:store_id>/blacklist/',                           BlacklistListView.as_view(),   name='store-blacklist-list'),
    path('<uuid:store_id>/blacklist/<uuid:customer_id>/',        BlacklistToggleView.as_view(), name='store-blacklist-toggle'),
]


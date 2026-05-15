from django.urls import path
from .views import (
    NearbyStoresView, StoreDetailView, StoreCreateView,
    StoreUpdateView, StoreFollowView, StoreReviewView, StoreQRCodeView,
)

urlpatterns = [
    path('nearby/',                  NearbyStoresView.as_view(),  name='stores-nearby'),
    path('',                         StoreCreateView.as_view(),   name='store-create'),
    path('<uuid:store_id>/',         StoreDetailView.as_view(),   name='store-detail'),
    path('<uuid:store_id>/update/',  StoreUpdateView.as_view(),   name='store-update'),
    path('<uuid:store_id>/follow/',  StoreFollowView.as_view(),   name='store-follow'),
    path('<uuid:store_id>/review/',  StoreReviewView.as_view(),   name='store-review'),
    path('<uuid:store_id>/qr-code/', StoreQRCodeView.as_view(),   name='store-qr-code'),
]


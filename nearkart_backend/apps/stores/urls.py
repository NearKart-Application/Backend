from django.urls import path
from .views import (
    NearbyStoresView, StoreDetailView, StoreCreateView, StoreMyView, StoreVisitedView,
    StoreUpdateView, StoreFollowView, StoreReviewView, StoreQRCodeView,
    StoreHoursView, StoreReviewListView, StoreOfferView, StoreOfferDeleteView, StoreStatsView,
    VendorReviewReplyView, VendorReviewsListView, MyReviewsView,
)
from apps.blacklist.views import BlacklistToggleView, BlacklistListView

urlpatterns = [
    path('nearby/',                  NearbyStoresView.as_view(),  name='stores-nearby'),
    path('mine/',                    StoreMyView.as_view(),       name='store-mine'),
    path('mine/stats/',              StoreStatsView.as_view(),    name='store-mine-stats'),
    path('mine/reviews/',            MyReviewsView.as_view(),     name='my-reviews'),
    path('visited/',                 StoreVisitedView.as_view(),  name='store-visited'),
    path('',                         StoreCreateView.as_view(),   name='store-create'),
    path('<uuid:store_id>/',         StoreDetailView.as_view(),   name='store-detail'),
    path('<uuid:store_id>/update/',  StoreUpdateView.as_view(),   name='store-update'),
    path('<uuid:store_id>/follow/',  StoreFollowView.as_view(),   name='store-follow'),
    path('<uuid:store_id>/review/',  StoreReviewView.as_view(),   name='store-review'),
    path('<uuid:store_id>/reviews/', StoreReviewView.as_view(),   name='store-reviews'),
    path('<uuid:store_id>/reviews/vendor/',                                  VendorReviewsListView.as_view(),  name='store-reviews-vendor'),
    path('<uuid:store_id>/reviews/<uuid:review_id>/reply/',                  VendorReviewReplyView.as_view(),  name='store-review-reply'),
    path('<uuid:store_id>/offers/',  StoreOfferView.as_view(),    name='store-offers'),
    path('<uuid:store_id>/offers/<uuid:offer_id>/', StoreOfferDeleteView.as_view(), name='store-offer-delete'),
    path('<uuid:store_id>/qr-code/', StoreQRCodeView.as_view(),   name='store-qr-code'),
    path('<uuid:store_id>/hours/',   StoreHoursView.as_view(),    name='store-hours'),
    # Blacklist
    path('<uuid:store_id>/blacklist/',                           BlacklistListView.as_view(),   name='store-blacklist-list'),
    path('<uuid:store_id>/blacklist/<uuid:customer_id>/',        BlacklistToggleView.as_view(), name='store-blacklist-toggle'),
]


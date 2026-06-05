from django.urls import path
from .views import (
    NearbyStoresView, StoreDetailView, StoreCreateView, StoreMyView, StoreVisitedView,
    StoreUpdateView, StoreFollowView, StoreReviewView, StoreQRCodeView,
    StoreHoursView, StoreReviewListView, StoreOfferView, StoreOfferDeleteView, StoreStatsView,
    VendorReviewReplyView, VendorReviewsListView, MyReviewsView, StoreInvoiceListCreateView,
    VendorStoresListView, StoreLocationsView, WebsiteRequestView,
    StaffListCreateView, StaffRemoveView, StoreImagesUploadView,
    VendorDiscountCodeListCreateView, VendorDiscountCodeUpdateView, ApplyDiscountCodeView,
    VendorBroadcastChannelListCreateView, VendorBroadcastPostListCreateView,
    CustomerBroadcastChannelListView, CustomerBroadcastPostListView,
)
from apps.blacklist.views import BlacklistToggleView, BlacklistListView
from apps.admin_panel.views import PublicOfferTemplateListView

urlpatterns = [
    path('offer-templates/',         PublicOfferTemplateListView.as_view(), name='store-offer-templates'),
    path('nearby/',                  NearbyStoresView.as_view(),         name='stores-nearby'),
    path('mine/',                    StoreMyView.as_view(),               name='store-mine'),
    path('mine/all/',                VendorStoresListView.as_view(),      name='store-mine-all'),
    path('mine/website-request/',    WebsiteRequestView.as_view(),        name='store-website-request'),
    path('mine/images/',             StoreImagesUploadView.as_view(),              name='store-images-upload'),
    path('mine/broadcast-channels/',                                          VendorBroadcastChannelListCreateView.as_view(), name='broadcast-channels-list'),
    path('mine/broadcast-channels/<uuid:channel_id>/posts/',                  VendorBroadcastPostListCreateView.as_view(),     name='broadcast-posts-list'),
    path('mine/discount-codes/',     VendorDiscountCodeListCreateView.as_view(),   name='discount-codes-list'),
    path('mine/discount-codes/<uuid:code_id>/', VendorDiscountCodeUpdateView.as_view(), name='discount-code-detail'),
    path('mine/staff/',              StaffListCreateView.as_view(),       name='store-staff-list'),
    path('mine/staff/<uuid:staff_id>/', StaffRemoveView.as_view(),        name='store-staff-remove'),
    path('mine/stats/',              StoreStatsView.as_view(),            name='store-mine-stats'),
    path('mine/reviews/',            MyReviewsView.as_view(),             name='my-reviews'),
    path('mine/invoices/',           StoreInvoiceListCreateView.as_view(), name='store-invoices'),
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
    path('<uuid:store_id>/apply-discount/', ApplyDiscountCodeView.as_view(), name='apply-discount'),
    path('<uuid:store_id>/broadcast-channels/',                               CustomerBroadcastChannelListView.as_view(),  name='customer-broadcast-channels'),
    path('<uuid:store_id>/broadcast-channels/<uuid:channel_id>/posts/',       CustomerBroadcastPostListView.as_view(),     name='customer-broadcast-posts'),
    path('<uuid:store_id>/qr-code/', StoreQRCodeView.as_view(),   name='store-qr-code'),
    path('<uuid:store_id>/hours/',      StoreHoursView.as_view(),       name='store-hours'),
    path('<uuid:store_id>/locations/', StoreLocationsView.as_view(),   name='store-locations'),
    # Blacklist
    path('<uuid:store_id>/blacklist/',                           BlacklistListView.as_view(),   name='store-blacklist-list'),
    path('<uuid:store_id>/blacklist/<uuid:customer_id>/',        BlacklistToggleView.as_view(), name='store-blacklist-toggle'),
]


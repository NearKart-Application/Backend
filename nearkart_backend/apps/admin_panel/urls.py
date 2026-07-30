from django.urls import path
from .views import (
    PlatformStatsView,
    AdminStoreListView, AdminStoreUpdateView,
    AdminStoreVideoListView, AdminDeleteVideoView,
    AdminUserListView, AdminUserToggleActiveView,
    AdminCreateUserView, AdminUserSuspendView,
    PublicBannersView,
    AdminBannerListCreateView, AdminBannerDetailView, AdminBannerToggleView,
    AdminUserManageView, AdminUserDeleteView,
    AdminProductListView, AdminProductDetailView,
    AdminWebsiteRequestListView, AdminWebsiteRequestUpdateView,
    AdminActivityLogView,
    AdminCategoryListCreateView, AdminCategoryDetailView, PublicCategoryListView,
    AdminOfferTemplateListCreateView, AdminOfferTemplateDetailView, PublicOfferTemplateListView,
    AdminCouponListCreateView, AdminCouponDetailView, AdminVendorSearchView,
    AdminPlanListView, AdminPlanDetailView,
    AdminReferralConfigListView, AdminReferralConfigDetailView,
    AdminBlacklistListView,
    AdminLoyaltyListView, AdminLoyaltyAdjustView,
    AdminSubscriptionListView,
)

urlpatterns = [
    path('stats/',                                PlatformStatsView.as_view(),              name='admin-stats'),

    # Store management
    path('stores/',                               AdminStoreListView.as_view(),              name='admin-store-list'),
    path('stores/<uuid:store_id>/',               AdminStoreUpdateView.as_view(),            name='admin-store-update'),
    path('stores/<uuid:store_id>/videos/',        AdminStoreVideoListView.as_view(),         name='admin-store-videos'),

    # Video management
    path('videos/<uuid:video_id>/',               AdminDeleteVideoView.as_view(),            name='admin-video-delete'),

    # User management
    path('users/',                                AdminUserListView.as_view(),               name='admin-user-list'),
    path('users/create/',                         AdminCreateUserView.as_view(),             name='admin-user-create'),
    path('users/<uuid:user_id>/toggle-active/',   AdminUserToggleActiveView.as_view(),       name='admin-user-toggle'),
    path('users/<uuid:user_id>/suspend/',         AdminUserSuspendView.as_view(),            name='admin-user-suspend'),

    # Promo banners
    path('banners/active/',                       PublicBannersView.as_view(),               name='banners-public'),
    path('banners/',                              AdminBannerListCreateView.as_view(),       name='admin-banner-list'),
    path('banners/<uuid:banner_id>/',             AdminBannerDetailView.as_view(),           name='admin-banner-detail'),
    path('banners/<uuid:banner_id>/toggle/',      AdminBannerToggleView.as_view(),           name='admin-banner-toggle'),

    # Products
    path('products/',                             AdminProductListView.as_view(),            name='admin-product-list'),
    path('products/<uuid:product_id>/',           AdminProductDetailView.as_view(),          name='admin-product-detail'),

    # Website requests
    path('website-requests/',                     AdminWebsiteRequestListView.as_view(),     name='admin-website-request-list'),
    path('website-requests/<uuid:request_id>/',   AdminWebsiteRequestUpdateView.as_view(),   name='admin-website-request-update'),

    # Admin user management (master only)
    path('admins/',                               AdminUserManageView.as_view(),             name='admin-admins-list'),
    path('admins/<uuid:user_id>/',                AdminUserDeleteView.as_view(),             name='admin-admins-delete'),

    # Activity log
    path('activity-log/',                         AdminActivityLogView.as_view(),            name='admin-activity-log'),

    # Categories
    path('categories/public/',                    PublicCategoryListView.as_view(),          name='categories-public'),
    path('categories/',                           AdminCategoryListCreateView.as_view(),     name='admin-category-list'),
    path('categories/<uuid:category_id>/',        AdminCategoryDetailView.as_view(),         name='admin-category-detail'),

    # Offer Templates
    path('offer-templates/public/',               PublicOfferTemplateListView.as_view(),     name='offer-templates-public'),
    path('offer-templates/',                      AdminOfferTemplateListCreateView.as_view(), name='admin-offer-template-list'),
    path('offer-templates/<uuid:template_id>/',   AdminOfferTemplateDetailView.as_view(),    name='admin-offer-template-detail'),

    # Vendor-specific coupons
    path('coupons/',                              AdminCouponListCreateView.as_view(),        name='admin-coupon-list'),
    path('coupons/<uuid:coupon_id>/',             AdminCouponDetailView.as_view(),            name='admin-coupon-detail'),
    path('vendors/search/',                       AdminVendorSearchView.as_view(),            name='admin-vendor-search'),

    # Plan management (master admin only)
    path('plans/',                                AdminPlanListView.as_view(),                name='admin-plan-list'),
    path('plans/<slug:slug>/',                    AdminPlanDetailView.as_view(),              name='admin-plan-detail'),

    # Referral reward config (admin + master admin)
    path('referral-config/',                      AdminReferralConfigListView.as_view(),      name='admin-referral-config-list'),
    path('referral-config/<uuid:config_id>/',     AdminReferralConfigDetailView.as_view(),    name='admin-referral-config-detail'),

    # Blacklist management
    path('blacklist/',                            AdminBlacklistListView.as_view(),           name='admin-blacklist-list'),

    # Loyalty account management
    path('loyalty/',                              AdminLoyaltyListView.as_view(),             name='admin-loyalty-list'),
    path('loyalty/<uuid:account_id>/adjust/',     AdminLoyaltyAdjustView.as_view(),           name='admin-loyalty-adjust'),

    # Subscription management
    path('subscriptions/',                        AdminSubscriptionListView.as_view(),        name='admin-subscription-list'),
]

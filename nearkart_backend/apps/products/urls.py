from django.urls import path
from .views import (
    NearbyProductsView, ProductSearchView, ProductDetailView,
    ProductCreateView, ProductUpdateView, ProductWishlistView,
    WishlistListView, VendorProductListView, ProductReserveView,
    FollowingFeedView,
    VariantListView, VariantStockUpdateView, StockLogView,
    StockAlertsView, StockWatchView, ProductImageUploadView,
    ProductImageDeleteView,
    GenerateProductCodeView, ProductReviewView,
)
from apps.admin_panel.views import PublicCategoryListView

urlpatterns = [
    path('categories/',                PublicCategoryListView.as_view(),   name='product-categories'),
    path('nearby/',                    NearbyProductsView.as_view(),      name='products-nearby'),
    path('search/',                    ProductSearchView.as_view(),        name='products-search'),
    path('following/',                 FollowingFeedView.as_view(),        name='products-following'),
    path('wishlist/',                  WishlistListView.as_view(),         name='wishlist-list'),
    path('vendor/',                    VendorProductListView.as_view(),    name='vendor-products'),
    path('vendor/generate-code/',      GenerateProductCodeView.as_view(),  name='generate-product-code'),
    path('vendor/stock-alerts/',       StockAlertsView.as_view(),          name='stock-alerts'),
    path('',                           ProductCreateView.as_view(),        name='product-create'),
    path('<uuid:product_id>/',              ProductDetailView.as_view(),   name='product-detail'),
    path('<uuid:product_id>/update/',       ProductUpdateView.as_view(),   name='product-update'),
    path('<uuid:product_id>/wishlist/',     ProductWishlistView.as_view(), name='product-wishlist'),
    path('<uuid:product_id>/reserve/',      ProductReserveView.as_view(),  name='product-reserve'),
    path('<uuid:product_id>/watch/',        StockWatchView.as_view(),      name='stock-watch'),
    path('<uuid:product_id>/stock-log/',    StockLogView.as_view(),        name='stock-log'),
    path('<uuid:product_id>/images/',                       ProductImageUploadView.as_view(),  name='product-images'),
    path('<uuid:product_id>/images/<uuid:image_id>/',      ProductImageDeleteView.as_view(),  name='product-image-delete'),
    path('<uuid:product_id>/variants/',     VariantListView.as_view(),     name='variant-list'),
    path('<uuid:product_id>/variants/<uuid:variant_id>/',
         VariantStockUpdateView.as_view(), name='variant-stock-update'),
    path('<uuid:product_id>/reviews/',  ProductReviewView.as_view(),  name='product-reviews'),
]

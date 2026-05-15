from django.urls import path
from .views import (
    NearbyProductsView, ProductSearchView, ProductDetailView,
    ProductCreateView, ProductUpdateView, ProductWishlistView,
)

urlpatterns = [
    path('nearby/',                    NearbyProductsView.as_view(),  name='products-nearby'),
    path('search/',                    ProductSearchView.as_view(),   name='products-search'),
    path('',                           ProductCreateView.as_view(),   name='product-create'),
    path('<uuid:product_id>/',         ProductDetailView.as_view(),   name='product-detail'),
    path('<uuid:product_id>/update/',  ProductUpdateView.as_view(),   name='product-update'),
    path('<uuid:product_id>/wishlist/', ProductWishlistView.as_view(), name='product-wishlist'),
]


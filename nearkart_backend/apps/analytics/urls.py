from django.urls import path
from .views import VendorDashboardView, VendorVideoStatsView, VendorProductStatsView

urlpatterns = [
    path('vendor/',          VendorDashboardView.as_view(),    name='analytics-vendor-dashboard'),
    path('vendor/videos/',   VendorVideoStatsView.as_view(),   name='analytics-vendor-videos'),
    path('vendor/products/', VendorProductStatsView.as_view(), name='analytics-vendor-products'),
]

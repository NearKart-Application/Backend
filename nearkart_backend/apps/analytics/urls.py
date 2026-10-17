from django.urls import path
from .views import (
    VendorDashboardView, VendorVideoStatsView, VendorProductStatsView,
    VendorTimeSeriesView, VendorRevenueView, VendorCustomerStatsView,
    VendorAnalyticsExportView,
)

urlpatterns = [
    path('vendor/',            VendorDashboardView.as_view(),       name='analytics-vendor-dashboard'),
    path('vendor/videos/',     VendorVideoStatsView.as_view(),      name='analytics-vendor-videos'),
    path('vendor/products/',   VendorProductStatsView.as_view(),    name='analytics-vendor-products'),
    path('vendor/timeseries/', VendorTimeSeriesView.as_view(),      name='analytics-vendor-timeseries'),
    path('vendor/revenue/',    VendorRevenueView.as_view(),         name='analytics-vendor-revenue'),
    path('vendor/customers/',  VendorCustomerStatsView.as_view(),   name='analytics-vendor-customers'),
    path('vendor/export/',     VendorAnalyticsExportView.as_view(), name='analytics-vendor-export'),
]

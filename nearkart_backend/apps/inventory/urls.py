from django.urls import path
from .views import (
    StockMovementLogView,
    SupplierListView, SupplierDetailView,
    PurchaseOrderListView, PurchaseOrderDetailView,
    StockAuditListView, StockAuditDetailView,
    StockWatchlistView,
)

app_name = 'inventory'

urlpatterns = [
    path('movements/',              StockMovementLogView.as_view(),     name='movement-log'),
    path('suppliers/',              SupplierListView.as_view(),          name='supplier-list'),
    path('suppliers/<uuid:supplier_id>/', SupplierDetailView.as_view(), name='supplier-detail'),
    path('purchase-orders/',        PurchaseOrderListView.as_view(),     name='po-list'),
    path('purchase-orders/<uuid:po_id>/', PurchaseOrderDetailView.as_view(), name='po-detail'),
    path('audits/',                 StockAuditListView.as_view(),        name='audit-list'),
    path('audits/<uuid:audit_id>/', StockAuditDetailView.as_view(),     name='audit-detail'),
    path('watchlist/',              StockWatchlistView.as_view(),        name='watchlist'),
]

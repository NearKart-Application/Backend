from django.urls import path
from .views import (
    StockMovementLogView,
    SupplierListView, SupplierDetailView,
    PurchaseOrderListView, PurchaseOrderDetailView,
    StockAuditListView, StockAuditDetailView,
    StockWatchlistView,
    CompositeProductListView, CompositeProductDetailView,
    SerialNumberListView, SerialNumberDetailView,
    BulkStockAdjustView, StockValuationView, InventoryExportView, DeadStockView,
    GroceryBatchListView, GroceryBatchDetailView, WastageRecordView, NearExpiryAlertView,
    PurchaseSourceListView, PurchaseSourceDetailView,
    UomListView, UomDetailView,
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
    path('bundles/',                        CompositeProductListView.as_view(),   name='bundle-list'),
    path('bundles/<uuid:comp_id>/',         CompositeProductDetailView.as_view(), name='bundle-detail'),
    path('serial-numbers/',                 SerialNumberListView.as_view(),       name='serial-list'),
    path('serial-numbers/<uuid:sn_id>/',    SerialNumberDetailView.as_view(),     name='serial-detail'),
    path('bulk-adjust/',  BulkStockAdjustView.as_view(),  name='bulk-adjust'),
    path('valuation/',    StockValuationView.as_view(),   name='valuation'),
    path('export/',       InventoryExportView.as_view(),  name='export'),
    path('dead-stock/',   DeadStockView.as_view(),        name='dead-stock'),
    # Unit of Measure catalog
    path('uom/',              UomListView.as_view(),   name='uom-list'),
    path('uom/<uuid:uom_id>/', UomDetailView.as_view(), name='uom-detail'),
    # Purchase Sources (informal / mandi markets)
    path('purchase-sources/',              PurchaseSourceListView.as_view(),   name='purchase-source-list'),
    path('purchase-sources/<uuid:ps_id>/', PurchaseSourceDetailView.as_view(), name='purchase-source-detail'),
    # Grocery / Perishable
    path('grocery-batches/',                                  GroceryBatchListView.as_view(),  name='grocery-batch-list'),
    path('grocery-batches/<uuid:batch_id>/',                  GroceryBatchDetailView.as_view(), name='grocery-batch-detail'),
    path('grocery-batches/<uuid:batch_id>/wastage/',          WastageRecordView.as_view(),      name='wastage-record'),
    path('grocery-batches/near-expiry/',                      NearExpiryAlertView.as_view(),    name='near-expiry'),
]

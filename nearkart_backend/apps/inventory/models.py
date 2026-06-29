"""
Nearspot — Inventory Models
StockMovementLog, StockWatchlist, Supplier, PurchaseOrder,
StockAudit, CompositeProduct, SerialNumber
"""
from django.conf import settings
from django.db import models
from core.models import BaseModel
from apps.products.models import Product, ProductVariant


class StockMovementReason(models.TextChoices):
    MANUAL      = 'manual',      'Manual Update'
    RESERVATION = 'reservation', 'Reservation Placed'
    RESTORATION = 'restoration', 'Reservation Cancelled/Expired'
    INVOICE     = 'invoice',     'Invoice Sale'
    PURCHASE    = 'purchase',    'Purchase Order Received'
    RETURN      = 'return',      'Customer Return'
    DAMAGE      = 'damage',      'Damaged / Written Off'
    CORRECTION  = 'correction',  'Stock Audit Correction'


class StockMovementLog(BaseModel):
    """Immutable audit trail of every stock change. Never delete rows."""
    variant    = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, related_name='stock_movements')
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    old_qty    = models.PositiveIntegerField()
    new_qty    = models.PositiveIntegerField()
    delta      = models.IntegerField(help_text='new_qty - old_qty; negative = stock reduced')
    reason     = models.CharField(max_length=20, choices=StockMovementReason.choices)
    note       = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = 'inv_stock_movement_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['variant', '-created_at'], name='inv_sml_variant_date_idx'),
            models.Index(fields=['changed_by', '-created_at'], name='inv_sml_user_date_idx'),
        ]

    def __str__(self):
        return f'{self.reason} {self.delta:+d} → {self.new_qty} ({self.variant})'


class StockWatchlist(BaseModel):
    """Customer back-in-stock watchlist."""
    customer    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='inv_stock_watchlist')
    product     = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inv_watchers')
    notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'inv_stock_watchlists'
        unique_together = [('customer', 'product')]

    def __str__(self):
        return f'{self.customer.phone_number} watching {self.product.name}'


class Supplier(BaseModel):
    """Vendor's suppliers for purchase orders and restocking."""
    store              = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='suppliers')
    name               = models.CharField(max_length=200)
    contact_name       = models.CharField(max_length=200, blank=True)
    phone              = models.CharField(max_length=15)
    whatsapp           = models.CharField(max_length=15, blank=True)
    address            = models.TextField(blank=True)
    product_categories = models.CharField(max_length=500, blank=True)
    notes              = models.TextField(blank=True)
    is_active          = models.BooleanField(default=True)

    class Meta:
        db_table = 'inv_suppliers'
        ordering = ['name']
        indexes = [models.Index(fields=['store', 'is_active'], name='inv_sup_store_active_idx')]

    def __str__(self):
        return f'{self.name} ({self.store.name})'


class PurchaseOrderStatus(models.TextChoices):
    DRAFT     = 'draft',     'Draft'
    SENT      = 'sent',      'Sent to Supplier'
    RECEIVED  = 'received',  'Stock Received'
    CANCELLED = 'cancelled', 'Cancelled'


class PurchaseOrder(BaseModel):
    """Vendor purchase orders to suppliers."""
    store       = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='purchase_orders')
    supplier    = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    status      = models.CharField(max_length=10, choices=PurchaseOrderStatus.choices, default=PurchaseOrderStatus.DRAFT)
    items       = models.JSONField(default=list, help_text='[{product_id, variant_id, sku, qty, unit_cost}]')
    total_cost  = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes       = models.TextField(blank=True)
    expected_by = models.DateField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'inv_purchase_orders'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['store', 'status'], name='inv_po_store_status_idx')]

    def __str__(self):
        return f'PO-{self.pk} {self.store.name} ({self.status})'


class StockAuditStatus(models.TextChoices):
    IN_PROGRESS = 'in_progress', 'In Progress'
    COMPLETED   = 'completed',   'Completed'
    CANCELLED   = 'cancelled',   'Cancelled'


class StockAudit(BaseModel):
    """Physical stock count reconciliation."""
    store             = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='stock_audits')
    conducted_by      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    status            = models.CharField(max_length=15, choices=StockAuditStatus.choices, default=StockAuditStatus.IN_PROGRESS)
    items             = models.JSONField(default=list, help_text='[{variant_id, sku, system_qty, counted_qty, discrepancy}]')
    total_discrepancy = models.IntegerField(default=0)
    notes             = models.TextField(blank=True)
    completed_at      = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'inv_stock_audits'
        ordering = ['-created_at']

    def __str__(self):
        return f'Audit {self.pk} — {self.store.name} ({self.status})'


class CompositeProduct(BaseModel):
    """Bundle products — track stock of each component."""
    bundle_product    = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='bundle_components')
    component_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='used_in_bundles')
    quantity          = models.PositiveIntegerField(help_text='Units of this component per bundle')

    class Meta:
        db_table = 'inv_composite_products'
        unique_together = [('bundle_product', 'component_variant')]

    def __str__(self):
        return f'{self.bundle_product.name} ← {self.quantity}x {self.component_variant.name}'


class SerialNumberStatus(models.TextChoices):
    AVAILABLE = 'available', 'Available'
    RESERVED  = 'reserved',  'Reserved'
    SOLD      = 'sold',      'Sold'
    RETURNED  = 'returned',  'Returned'
    DAMAGED   = 'damaged',   'Damaged'


class SerialNumber(BaseModel):
    """Individual unit tracking for high-value electronics."""
    variant       = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='serial_numbers')
    serial_number = models.CharField(max_length=200, unique=True)
    status        = models.CharField(max_length=10, choices=SerialNumberStatus.choices, default=SerialNumberStatus.AVAILABLE)
    sold_at       = models.DateTimeField(null=True, blank=True)
    notes         = models.TextField(blank=True)

    class Meta:
        db_table = 'inv_serial_numbers'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['variant', 'status'], name='inv_sn_variant_status_idx')]

    def __str__(self):
        return f'{self.serial_number} ({self.variant.name}) — {self.status}'

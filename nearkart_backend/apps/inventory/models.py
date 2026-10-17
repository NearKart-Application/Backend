"""
Nearspot — Inventory Models
StockMovementLog, StockWatchlist, Supplier, PurchaseOrder,
StockAudit, CompositeProduct, SerialNumber
"""
from django.conf import settings
from django.db import models
from core.models import BaseModel
from apps.products.models import (
    Product, ProductVariant,
    StockMovementLog, StockMovementReason,  # canonical — do not redefine here
)


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


# ── Grocery / Perishable Inventory ────────────────────────────────────────────

class TemperatureZone(models.TextChoices):
    AMBIENT     = 'ambient',     'Ambient (Room Temp)'
    REFRIGERATED = 'refrigerated', 'Refrigerated (2–8°C)'
    FROZEN      = 'frozen',      'Frozen (< −18°C)'


class WeightUnit(models.TextChoices):
    KG    = 'kg',    'Kilogram (kg)'
    GRAM  = 'g',     'Gram (g)'
    LITRE = 'l',     'Litre (L)'
    ML    = 'ml',    'Millilitre (mL)'
    PIECE = 'piece', 'Piece / Unit'


class GroceryBatch(BaseModel):
    """
    Batch / lot record for perishable and weight-sold products.
    Each batch corresponds to a stock intake event for one variant.
    """
    variant         = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='grocery_batches')
    batch_number    = models.CharField(max_length=100, blank=True)
    quantity        = models.DecimalField(max_digits=12, decimal_places=3)
    remaining_qty   = models.DecimalField(max_digits=12, decimal_places=3)
    unit            = models.CharField(max_length=10, choices=WeightUnit.choices, default=WeightUnit.PIECE)
    unit_price      = models.DecimalField(max_digits=10, decimal_places=2)
    manufacture_date = models.DateField(null=True, blank=True)
    expiry_date     = models.DateField(null=True, blank=True)
    is_perishable   = models.BooleanField(default=False)
    temperature_zone = models.CharField(max_length=15, choices=TemperatureZone.choices, default=TemperatureZone.AMBIENT, blank=True)
    notes           = models.TextField(blank=True)

    class Meta:
        db_table = 'inv_grocery_batches'
        ordering = ['expiry_date', '-created_at']
        indexes  = [models.Index(fields=['variant', 'expiry_date'], name='inv_gb_variant_expiry_idx')]

    def __str__(self):
        return f'{self.variant.name} batch {self.batch_number or str(self.id)[:8]} (exp {self.expiry_date})'

    @property
    def is_expired(self):
        from datetime import date
        return self.expiry_date is not None and self.expiry_date < date.today()

    @property
    def days_to_expiry(self):
        from datetime import date
        if not self.expiry_date:
            return None
        return (self.expiry_date - date.today()).days


class WastageRecord(BaseModel):
    """Records spoilage / wastage for a grocery batch."""
    REASONS = [
        ('expired',   'Expired'),
        ('damaged',   'Damaged'),
        ('spillage',  'Spillage'),
        ('other',     'Other'),
    ]
    batch       = models.ForeignKey(GroceryBatch, on_delete=models.CASCADE, related_name='wastage_records')
    quantity    = models.DecimalField(max_digits=12, decimal_places=3)
    reason      = models.CharField(max_length=20, choices=REASONS, default='expired')
    notes       = models.TextField(blank=True)
    recorded_by = models.ForeignKey('auth_app.User', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'inv_wastage_records'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        from django.db import transaction as db_transaction
        from django.db.models import Sum
        with db_transaction.atomic():
            # Lock batch row before saving to prevent concurrent over-deduction
            batch = GroceryBatch.objects.select_for_update().get(pk=self.batch_id)
            super().save(*args, **kwargs)
            # Keep remaining_qty in sync
            used = WastageRecord.objects.filter(batch=batch).aggregate(t=Sum('quantity'))['t'] or 0
            batch.remaining_qty = max(batch.quantity - used, 0)
            batch.save(update_fields=['remaining_qty'])


# ── Unit of Measure (#56) ─────────────────────────────────────────────────────

class UoMCategory(models.TextChoices):
    WEIGHT = 'weight', 'Weight'
    VOLUME = 'volume', 'Volume'
    COUNT  = 'count',  'Count / Unit'
    LENGTH = 'length', 'Length'


class UnitOfMeasure(BaseModel):
    """
    Phase-1 UoM catalogue. Products and variants reference this to standardise
    stock quantities across purchase orders, stock movements, and display.
    """
    name              = models.CharField(max_length=50, unique=True)
    symbol            = models.CharField(max_length=10, unique=True)
    category          = models.CharField(max_length=10, choices=UoMCategory.choices, default=UoMCategory.COUNT)
    conversion_factor = models.DecimalField(
        max_digits=15, decimal_places=6, default=1.0,
        help_text='Multiply by this factor to convert to the base unit of the same category',
    )
    is_base_unit      = models.BooleanField(default=False, help_text='True for kg, litre, piece, metre')
    notes             = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'inv_units_of_measure'
        ordering = ['category', 'name']
        indexes  = [models.Index(fields=['category', 'is_base_unit'], name='inv_uom_cat_base_idx')]

    def __str__(self):
        return f'{self.name} ({self.symbol})'


# ── PurchaseSource — Informal Markets (#58) ───────────────────────────────────

class MarketType(models.TextChoices):
    INFORMAL   = 'informal',   'Informal / Street Market'
    WHOLESALE  = 'wholesale',  'Wholesale Market'
    MANDI      = 'mandi',      'Mandi / Agricultural Market'
    DIRECT     = 'direct',     'Direct from Farmer / Producer'
    ONLINE     = 'online',     'Online Supplier'
    FORMAL     = 'formal',     'Formal Distributor'


class PurchaseSource(BaseModel):
    """
    Tracks where vendors source their stock — including informal markets, mandis,
    and street wholesalers that don't issue formal invoices (Supplier FK is optional).
    """
    store        = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='purchase_sources')
    name         = models.CharField(max_length=200, help_text='e.g. Crawford Market, Azadpur Mandi')
    market_type  = models.CharField(max_length=20, choices=MarketType.choices, default=MarketType.INFORMAL)
    contact_name = models.CharField(max_length=200, blank=True)
    phone        = models.CharField(max_length=15, blank=True)
    address      = models.TextField(blank=True)
    notes        = models.TextField(blank=True)
    is_active    = models.BooleanField(default=True)

    class Meta:
        db_table = 'inv_purchase_sources'
        ordering = ['name']
        indexes  = [models.Index(fields=['store', 'market_type', 'is_active'], name='inv_ps_store_type_idx')]

    def __str__(self):
        return f'{self.name} ({self.get_market_type_display()}) — {self.store.name}'


# ── StockLedger — Consolidated Daily Movements (#59) ─────────────────────────

class StockLedger(BaseModel):
    """
    Daily consolidated ledger row per (store, variant). Aggregates all stock
    movements for a period into a single opening/closing balance record, enabling
    fast period-based queries without scanning StockMovementLog.
    """
    store       = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='stock_ledger_entries')
    variant     = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='ledger_entries')
    period_date = models.DateField(help_text='Calendar date this entry summarises')
    opening_qty = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    in_qty      = models.DecimalField(max_digits=12, decimal_places=3, default=0,
                                      help_text='Total stock received (purchases + returns) this day')
    out_qty     = models.DecimalField(max_digits=12, decimal_places=3, default=0,
                                      help_text='Total stock dispatched (sales + wastage) this day')
    closing_qty = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    notes       = models.TextField(blank=True)

    class Meta:
        db_table        = 'inv_stock_ledger'
        unique_together = [('store', 'variant', 'period_date')]
        ordering        = ['-period_date']
        indexes         = [
            models.Index(fields=['store', 'period_date'], name='inv_sl_store_date_idx'),
            models.Index(fields=['variant', 'period_date'], name='inv_sl_variant_date_idx'),
        ]

    def __str__(self):
        return (
            f'{self.variant.name} @ {self.store.name} on {self.period_date}: '
            f'open={self.opening_qty} in={self.in_qty} out={self.out_qty} close={self.closing_qty}'
        )

    @property
    def net_movement(self):
        return self.in_qty - self.out_qty

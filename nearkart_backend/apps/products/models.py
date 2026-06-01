"""
NearKart — Product Models
Product, ProductVariant, ProductImage, Wishlist, StockMovementLog, StockWatchlist
"""
from django.conf import settings
from django.db import models
from django.contrib.postgres.indexes import GinIndex

from core.models import BaseModel
from apps.auth_app.models import User
from apps.stores.models import Store


class ProductStatus(models.TextChoices):
    DRAFT        = 'draft',        'Draft'
    ACTIVE       = 'active',       'Active'
    INACTIVE     = 'inactive',     'Inactive'
    OUT_OF_STOCK = 'out_of_stock', 'Out of Stock'


class Product(BaseModel):
    store          = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='products')
    name           = models.CharField(max_length=200)
    description    = models.TextField(blank=True)
    category       = models.CharField(max_length=50, blank=True)
    subcategory    = models.CharField(max_length=100, blank=True)
    status         = models.CharField(max_length=20, choices=ProductStatus.choices, default=ProductStatus.DRAFT)
    is_visible     = models.BooleanField(default=True, db_index=True)
    base_price     = models.DecimalField(max_digits=10, decimal_places=2)
    last_updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        db_table = 'products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'is_visible'], name='product_status_visible_idx'),
            GinIndex(fields=['name'], opclasses=['gin_trgm_ops'], name='product_name_gin_idx'),
        ]

    def __str__(self):
        return self.name


class ProductVariant(BaseModel):
    product        = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name           = models.CharField(max_length=100)
    sku            = models.CharField(max_length=100, unique=True)
    price          = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        db_table = 'product_variants'
        ordering = ['name']

    def __str__(self):
        return f'{self.product.name} — {self.name}'


class ProductImage(BaseModel):
    product    = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image_url  = models.URLField()
    s3_key     = models.CharField(max_length=500)
    is_primary = models.BooleanField(default=False)
    order      = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'product_images'
        ordering = ['order']

    def __str__(self):
        return f'{self.product.name} image {self.order}'


class Wishlist(BaseModel):
    user    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by')

    class Meta:
        db_table        = 'wishlists'
        unique_together = [('user', 'product')]
        ordering        = ['-created_at']


class StockMovementReason(models.TextChoices):
    MANUAL      = 'manual',      'Manual Update'
    RESERVATION = 'reservation', 'Reservation Deduction'
    RESTORATION = 'restoration', 'Reservation Restore'
    RESTOCK     = 'restock',     'Restock'
    INVOICE     = 'invoice',     'Invoice Sale'


class StockMovementLog(BaseModel):
    variant    = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='stock_logs')
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name='stock_changes')
    old_qty    = models.IntegerField()
    new_qty    = models.IntegerField()
    delta      = models.IntegerField()
    reason     = models.CharField(max_length=20, choices=StockMovementReason.choices,
                                  default=StockMovementReason.MANUAL)
    note       = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'stock_movement_logs'
        ordering = ['-created_at']
        indexes  = [models.Index(fields=['variant', 'created_at'], name='stock_log_variant_idx')]

    def __str__(self):
        return f'{self.variant} {self.old_qty}→{self.new_qty} ({self.reason})'


class StockWatchlist(BaseModel):
    """Customer subscribes to back-in-stock notification for a product."""
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 related_name='stock_watches')
    product  = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_watchers')

    class Meta:
        db_table        = 'stock_watchlist'
        unique_together = [('customer', 'product')]
        ordering        = ['-created_at']

    def __str__(self):
        return f'{self.customer} watching {self.product.name}'

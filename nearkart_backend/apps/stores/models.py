"""
NearKart — Store Models
Store, StoreHours, StoreFollow, StoreReview, StoreOffer, Invoice
"""
from django.contrib.gis.db import models as gis_models
from django.db import models
from django.contrib.postgres.indexes import GinIndex

from core.models import BaseModel
from apps.auth_app.models import User


class StoreCategory(models.TextChoices):
    FASHION     = 'fashion',     'Fashion'
    JEWELLERY   = 'jewellery',   'Jewellery'
    FOOTWEAR    = 'footwear',    'Footwear'
    DECOR       = 'decor',       'Home Decor'
    FURNITURE   = 'furniture',   'Furniture'
    GIFTS       = 'gifts',       'Gifts'
    BEAUTY      = 'beauty',      'Beauty'
    FOOD        = 'food',        'Food'
    ELECTRONICS = 'electronics', 'Electronics'
    OTHER       = 'other',       'Other'


class Store(BaseModel):
    owner       = models.OneToOneField(User, on_delete=models.CASCADE, related_name='store')
    name        = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category    = models.CharField(max_length=20, choices=StoreCategory.choices, default=StoreCategory.OTHER)
    phone       = models.CharField(max_length=15, blank=True)
    address     = models.TextField()
    locality    = models.CharField(max_length=200, blank=True)
    location    = gis_models.PointField(srid=4326, spatial_index=True, geography=True)
    logo_url    = models.URLField(blank=True)
    banner_url  = models.URLField(blank=True)
    qr_code_url = models.URLField(blank=True)

    is_active         = models.BooleanField(default=True)
    is_verified       = models.BooleanField(default=False)
    is_open           = models.BooleanField(default=False)
    performance_score = models.FloatField(default=0.0)
    wallet_balance    = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = 'stores'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', 'is_verified'], name='store_active_verified_idx'),
            models.Index(fields=['category'], name='store_category_idx'),
            GinIndex(fields=['name'], opclasses=['gin_trgm_ops'], name='store_name_gin_idx'),
        ]

    def __str__(self):
        return self.name


class StoreHours(models.Model):
    DAY_CHOICES = [
        (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'),
        (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday'),
    ]
    store      = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='hours')
    day        = models.PositiveSmallIntegerField(choices=DAY_CHOICES)
    open_time  = models.TimeField()
    close_time = models.TimeField()
    is_closed  = models.BooleanField(default=False)

    class Meta:
        db_table        = 'store_hours'
        unique_together = [('store', 'day')]
        ordering        = ['day']

    def __str__(self):
        return f'{self.store.name} - {self.get_day_display()}'


class StoreFollow(BaseModel):
    user  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following_stores')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='followers')

    class Meta:
        db_table        = 'store_follows'
        unique_together = [('user', 'store')]
        ordering        = ['-created_at']


class StoreReview(BaseModel):
    user    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='store_reviews')
    store   = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='reviews')
    rating  = models.PositiveSmallIntegerField()  # 1–5
    comment = models.TextField(blank=True)
    vendor_reply    = models.TextField(blank=True, default='')
    vendor_reply_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table        = 'store_reviews'
        unique_together = [('user', 'store')]
        ordering        = ['-created_at']

    def __str__(self):
        return f'{self.store.name} — {self.rating}★'


class StoreOffer(BaseModel):
    store        = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='offers')
    title        = models.CharField(max_length=200)
    description  = models.TextField(blank=True)
    discount_pct = models.PositiveSmallIntegerField(null=True, blank=True)  # e.g. 20 = 20% off
    valid_till   = models.DateField(null=True, blank=True)
    image_url    = models.URLField(blank=True)
    is_active    = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = 'store_offers'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.store.name} — {self.title}'


class Invoice(BaseModel):
    store          = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='invoices')
    customer_name  = models.CharField(max_length=200)
    customer_phone = models.CharField(max_length=20, blank=True)
    items          = models.JSONField(default=list)  # [{"name": ..., "price": ..., "qty": ...}]
    notes          = models.TextField(blank=True)
    total          = models.DecimalField(max_digits=10, decimal_places=2)
    is_sent        = models.BooleanField(default=False)

    class Meta:
        db_table = 'store_invoices'
        ordering = ['-created_at']

    def __str__(self):
        return f'Invoice #{str(self.id)[:8]} — {self.store.name} → {self.customer_name}'

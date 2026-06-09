"""
NearKart — Billing Models
Plan, Subscription, Transaction, Coupon
"""
from django.db import models

from core.models import BaseModel
from apps.stores.models import Store


class Plan(BaseModel):
    SLUG_FREE    = 'free'
    SLUG_BASIC   = 'basic'
    SLUG_PREMIUM = 'premium'

    name          = models.CharField(max_length=20, unique=True)   # 'free' / 'basic' / 'premium'
    display_name  = models.CharField(max_length=50)                # 'Free', 'Basic Plan', …
    price         = models.DecimalField(max_digits=8, decimal_places=2)  # monthly price (₹)
    duration_days = models.PositiveIntegerField(default=30)
    video_limit   = models.PositiveIntegerField(default=3)         # 0 = unlimited
    product_limit = models.PositiveIntegerField(default=10)        # 0 = unlimited
    description   = models.TextField(blank=True)
    is_active     = models.BooleanField(default=True)              # show in plan listing

    class Meta:
        db_table = 'billing_plans'
        ordering = ['price']

    def __str__(self):
        return self.display_name

    @property
    def has_video_limit(self):
        return self.video_limit > 0

    @property
    def has_product_limit(self):
        return self.product_limit > 0


class Subscription(BaseModel):
    """One active subscription per store. Updated in-place on renewal/upgrade."""
    store      = models.OneToOneField(Store, on_delete=models.CASCADE, related_name='subscription')
    plan       = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='subscriptions')
    started_at = models.DateTimeField()
    expires_at = models.DateTimeField(db_index=True)
    is_active  = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = 'billing_subscriptions'

    def __str__(self):
        status = 'active' if self.is_active else 'expired'
        return f'{self.store.name} — {self.plan.display_name} ({status})'


class Transaction(BaseModel):
    TYPE_TOPUP        = 'topup'
    TYPE_SUBSCRIPTION = 'subscription'
    TYPE_REFUND       = 'refund'
    TYPE_CHOICES = [
        (TYPE_TOPUP,        'Wallet Top-up'),
        (TYPE_SUBSCRIPTION, 'Subscription Purchase'),
        (TYPE_REFUND,       'Refund'),
    ]

    store         = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='transactions')
    type          = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount        = models.DecimalField(max_digits=10, decimal_places=2)  # + credit / - debit
    description   = models.CharField(max_length=255)
    reference_id  = models.CharField(max_length=100, blank=True)         # Razorpay order ID in prod
    balance_after = models.DecimalField(max_digits=10, decimal_places=2) # wallet snapshot

    class Meta:
        db_table = 'billing_transactions'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.store.name} — {self.type} ₹{self.amount}'


class Coupon(BaseModel):
    """Discount coupon — 100% off = free subscription without payment."""
    code             = models.CharField(max_length=50, unique=True, db_index=True)
    discount_percent = models.PositiveIntegerField(default=100)          # 1–100; 100 = free
    applicable_plans = models.ManyToManyField(Plan, blank=True,          # empty = all plans
                                              related_name='coupons')
    max_uses         = models.PositiveIntegerField(default=0)            # 0 = unlimited
    used_count       = models.PositiveIntegerField(default=0)
    expires_at       = models.DateTimeField(null=True, blank=True)
    is_active        = models.BooleanField(default=True)

    class Meta:
        db_table = 'billing_coupons'

    def __str__(self):
        return f'{self.code} ({self.discount_percent}% off)'

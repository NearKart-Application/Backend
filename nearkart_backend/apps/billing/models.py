"""
NearKart — Billing Models
Plan, Subscription, Transaction, Coupon, CouponRedemption,
ReferralConfig, ReferralCode, UserReferralLink, VendorReferral
"""
from decimal import Decimal
from django.db import models
from django.conf import settings

from core.models import BaseModel
from apps.stores.models import Store


class Plan(BaseModel):
    SLUG_BASIC   = 'basic'
    SLUG_PREMIUM = 'premium'

    TRACK_BOTH    = 'both'
    TRACK_PRODUCT = 'product'
    TRACK_SERVICE = 'service'
    TRACK_CHOICES = [
        (TRACK_BOTH,    'All Vendors'),
        (TRACK_PRODUCT, 'Product Vendors Only'),
        (TRACK_SERVICE, 'Service Vendors Only'),
    ]

    name          = models.CharField(max_length=20, unique=True)   # 'basic' / 'premium'
    display_name  = models.CharField(max_length=50)                # 'Free', 'Basic Plan', …
    price         = models.DecimalField(max_digits=8, decimal_places=2)  # monthly price (₹)
    duration_days = models.PositiveIntegerField(default=30)
    video_limit   = models.PositiveIntegerField(default=3)         # 0 = unlimited
    product_limit = models.PositiveIntegerField(default=10)        # 0 = unlimited
    store_track   = models.CharField(max_length=10, choices=TRACK_CHOICES, default=TRACK_BOTH)
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
    TYPE_REFERRAL     = 'referral'
    TYPE_CHOICES = [
        (TYPE_TOPUP,        'Wallet Top-up'),
        (TYPE_SUBSCRIPTION, 'Subscription Purchase'),
        (TYPE_REFUND,       'Refund'),
        (TYPE_REFERRAL,     'Referral Reward'),
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
    """Discount coupon — 100% off = free subscription without payment.
    If target_store is set, only that store can redeem it (single-use vendor coupon).
    """
    code             = models.CharField(max_length=50, unique=True, db_index=True)
    discount_percent = models.PositiveIntegerField(default=100)          # 1–100; 100 = free
    applicable_plans = models.ManyToManyField(Plan, blank=True,          # empty = all plans
                                              related_name='coupons')
    max_uses         = models.PositiveIntegerField(default=0)            # 0 = unlimited; 1 = single-use
    used_count       = models.PositiveIntegerField(default=0)
    expires_at       = models.DateTimeField(null=True, blank=True)
    is_active        = models.BooleanField(default=True)
    # Vendor-specific targeting (null = general coupon available to all)
    target_store     = models.ForeignKey(
        Store, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='targeted_coupons',
    )
    created_by       = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_coupons',
    )

    class Meta:
        db_table = 'billing_coupons'

    def __str__(self):
        return f'{self.code} ({self.discount_percent}% off)'

    @property
    def is_vendor_specific(self):
        return self.target_store_id is not None

    @property
    def is_availed(self):
        return self.used_count > 0


class CouponRedemption(BaseModel):
    """Full audit trail for every coupon redemption."""
    coupon         = models.ForeignKey(Coupon, on_delete=models.PROTECT, related_name='redemptions')
    store          = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='coupon_redemptions')
    subscription   = models.ForeignKey('Subscription', on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name='redemptions')
    plan_name      = models.CharField(max_length=20)       # snapshot: plan slug at time of use
    plan_display   = models.CharField(max_length=50)       # snapshot: plan display_name
    original_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_given = models.DecimalField(max_digits=10, decimal_places=2)
    price_paid     = models.DecimalField(max_digits=10, decimal_places=2)
    redeemed_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'billing_coupon_redemptions'
        ordering = ['-redeemed_at']

    def __str__(self):
        return f'{self.coupon.code} → {self.store.name} ({self.redeemed_at.date()})'


class ReferralConfig(BaseModel):
    """Global (city='') or per-city referral reward amounts + range that city admins can set."""
    city = models.CharField(max_length=150, blank=True, default='', db_index=True, unique=True)

    vendor_reward   = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('50.00'))
    customer_reward = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('20.00'))

    vendor_reward_min   = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('10.00'))
    vendor_reward_max   = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('200.00'))
    customer_reward_min = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('10.00'))
    customer_reward_max = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('200.00'))

    class Meta:
        db_table = 'billing_referral_configs'

    def __str__(self):
        return f'ReferralConfig({self.city or "global"})'


class ReferralCode(BaseModel):
    """One unique referral code per store, created on demand."""
    store = models.OneToOneField(Store, on_delete=models.CASCADE, related_name='referral')
    code  = models.CharField(max_length=16, unique=True, db_index=True)

    class Meta:
        db_table = 'billing_referral_codes'

    def __str__(self):
        return f'{self.code} → {self.store.name}'


class UserReferralLink(BaseModel):
    """Records which vendor store referred a user at signup. One per user."""
    REWARD_VENDOR   = 'vendor'
    REWARD_CUSTOMER = 'customer'
    REWARD_CHOICES  = [
        (REWARD_VENDOR,   'Vendor Referral'),
        (REWARD_CUSTOMER, 'Customer Referral'),
    ]

    user            = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referral_link',
    )
    referrer_store  = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='referred_users')
    reward_type     = models.CharField(max_length=20, choices=REWARD_CHOICES)
    reward_credited = models.BooleanField(default=False)

    class Meta:
        db_table = 'billing_user_referral_links'

    def __str__(self):
        return f'{self.referrer_store.name} → {self.user}'


class VendorReferral(BaseModel):
    """Audit record created each time a referral reward is paid out."""
    referrer_store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='referral_earnings')
    referred_user  = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='referral_reward',
    )
    reward_type   = models.CharField(max_length=20)
    reward_amount = models.DecimalField(max_digits=8, decimal_places=2)
    transaction   = models.ForeignKey(
        Transaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='referral_record',
    )

    class Meta:
        db_table = 'billing_vendor_referrals'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.referrer_store.name} earned ₹{self.reward_amount}'

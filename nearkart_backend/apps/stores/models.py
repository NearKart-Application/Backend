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


class StoreType(models.TextChoices):
    PRODUCT  = 'product', 'Product Store'
    SERVICE  = 'service', 'Service Store'
    HOME     = 'home',    'Home Business'


class VendorType(models.TextChoices):
    PRODUCT = 'product', 'Product Vendor'
    SERVICE = 'service', 'Service Vendor'


class Store(BaseModel):
    owner       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stores')
    name        = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category    = models.CharField(max_length=20, choices=StoreCategory.choices, default=StoreCategory.OTHER)
    store_type  = models.CharField(max_length=10, choices=StoreType.choices, default=StoreType.PRODUCT)
    phone       = models.CharField(max_length=15, blank=True)
    address     = models.TextField()
    locality    = models.CharField(max_length=200, blank=True)
    area        = models.CharField(max_length=200, blank=True, default='')
    city        = models.CharField(max_length=150, blank=True, default='')
    district    = models.CharField(max_length=150, blank=True, default='')
    state       = models.CharField(max_length=150, blank=True, default='')
    country     = models.CharField(max_length=100, blank=True, default='India')
    location    = gis_models.PointField(srid=4326, spatial_index=True, geography=True)
    logo_url    = models.URLField(blank=True)
    banner_url  = models.URLField(blank=True)
    qr_code_url = models.URLField(blank=True)
    license_url = models.URLField(blank=True)
    gst_url     = models.URLField(blank=True)

    is_active         = models.BooleanField(default=True)
    is_verified       = models.BooleanField(default=False)
    is_open           = models.BooleanField(default=False)
    is_women_owned    = models.BooleanField(default=False)
    privacy_mode      = models.BooleanField(default=False)
    holiday_mode      = models.BooleanField(default=False)
    performance_score = models.FloatField(default=0.0)
    wallet_balance    = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    vendor_type   = models.CharField(
        max_length=10, choices=VendorType.choices, default=VendorType.PRODUCT,
        help_text='PRODUCT = sells physical goods with inventory. SERVICE = provides skills/time with service catalogue.'
    )
    is_home_based = models.BooleanField(
        default=False,
        help_text='If True: address hidden publicly, shown only after accepted visit reservation.'
    )

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
    is_verified     = models.BooleanField(default=False)  # True when gated by invoice NS code

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
    DISCOUNT_AMOUNT  = 'amount'
    DISCOUNT_PERCENT = 'percent'
    DISCOUNT_CHOICES = [(DISCOUNT_AMOUNT, 'Fixed Amount'), (DISCOUNT_PERCENT, 'Percentage')]

    store             = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='invoices')
    customer_name     = models.CharField(max_length=200)
    customer_phone    = models.CharField(max_length=20, blank=True)
    customer_ns_code  = models.CharField(max_length=30, blank=True)  # NSC-XX-XX-XXXX — used to send in-app notification
    items             = models.JSONField(default=list)  # [{"name": ..., "price": ..., "qty": ..., "product_id": ...}]
    notes             = models.TextField(blank=True)
    total             = models.DecimalField(max_digits=10, decimal_places=2)
    is_sent           = models.BooleanField(default=False)
    discount_type     = models.CharField(max_length=10, choices=DISCOUNT_CHOICES, null=True, blank=True)
    discount_value    = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gstin             = models.CharField(max_length=15, blank=True)  # 15-char GST registration number
    gst_rate          = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # e.g. 18.00 for 18%

    class Meta:
        db_table = 'store_invoices'
        ordering = ['-created_at']

    def __str__(self):
        return f'Invoice #{str(self.id)[:8]} — {self.store.name} → {self.customer_name}'


class StaffRole(models.TextChoices):
    MANAGER = 'manager', 'Manager'
    STAFF   = 'staff',   'Staff'


class StaffMember(BaseModel):
    """A user who is a staff member of a store (invited by the store owner)."""
    store      = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='staff_members')
    user       = models.ForeignKey(User,  on_delete=models.CASCADE, related_name='staff_roles')
    role       = models.CharField(max_length=20, choices=StaffRole.choices, default=StaffRole.STAFF)
    is_active  = models.BooleanField(default=True)
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='invited_staff')

    class Meta:
        db_table       = 'store_staff_members'
        unique_together = [('store', 'user')]
        ordering        = ['created_at']

    def __str__(self):
        return f'{self.user.full_name or self.user.phone_number} @ {self.store.name} ({self.role})'


class WebsiteRequest(BaseModel):
    STATUS_PENDING  = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES  = [
        (STATUS_PENDING,  'Pending Review'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    store             = models.OneToOneField(Store, on_delete=models.CASCADE, related_name='website_request')
    status            = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    domain_preference = models.CharField(max_length=100, blank=True)
    notes             = models.TextField(blank=True)
    admin_notes       = models.TextField(blank=True)
    reviewed_at       = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'store_website_requests'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.store.name} — website ({self.status})'


class DiscountCode(BaseModel):
    PERCENT = 'percent'
    FLAT    = 'flat'
    TYPE_CHOICES = [(PERCENT, 'Percent off'), (FLAT, 'Flat amount off')]

    store             = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='discount_codes')
    code              = models.CharField(max_length=20)
    description       = models.CharField(max_length=100, blank=True)
    discount_type     = models.CharField(max_length=10, choices=TYPE_CHOICES, default=PERCENT)
    value             = models.DecimalField(max_digits=8, decimal_places=2)
    min_order_amount  = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_uses          = models.PositiveIntegerField(null=True, blank=True)
    uses_count        = models.PositiveIntegerField(default=0)
    valid_from        = models.DateField(null=True, blank=True)
    valid_till        = models.DateField(null=True, blank=True)
    is_active         = models.BooleanField(default=True, db_index=True)
    created_by        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_discount_codes')

    class Meta:
        db_table        = 'discount_codes'
        unique_together = [('store', 'code')]
        ordering        = ['-created_at']

    def __str__(self):
        return f'{self.store.name} — {self.code}'

    def is_valid(self, order_amount=None):
        from django.utils import timezone
        today = timezone.now().date()
        if not self.is_active:
            return False, 'code_inactive'
        if self.max_uses is not None and self.uses_count >= self.max_uses:
            return False, 'max_uses_reached'
        if self.valid_from and today < self.valid_from:
            return False, 'not_started'
        if self.valid_till and today > self.valid_till:
            return False, 'expired'
        if order_amount is not None and self.min_order_amount and order_amount < self.min_order_amount:
            return False, 'below_minimum'
        return True, None

    def calculate_discount(self, order_amount):
        if self.discount_type == self.PERCENT:
            return round(float(order_amount) * float(self.value) / 100, 2)
        return min(float(self.value), float(order_amount))


class BroadcastChannel(BaseModel):
    store          = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='broadcast_channels')
    name           = models.CharField(max_length=100)
    description    = models.TextField(blank=True)
    auto_subscribe = models.BooleanField(default=True)

    class Meta:
        db_table = 'broadcast_channels'
        ordering = ['-created_at']

    @property
    def subscriber_count(self):
        """
        Returns the number of store followers (potential broadcast reach), NOT
        per-channel subscribers.  Calling this in a loop causes an N+1 query.
        In list views, annotate the queryset instead:
          BroadcastChannel.objects.annotate(follower_count=Count('store__followers', distinct=True))
        and use follower_count rather than this property.
        """
        return self.store.followers.count()

    @property
    def post_count(self):
        return self.posts.count()

    def __str__(self):
        return f'{self.store.name} — {self.name}'


class BroadcastPost(BaseModel):
    channel   = models.ForeignKey(BroadcastChannel, on_delete=models.CASCADE, related_name='posts')
    content   = models.TextField()
    image_url = models.URLField(blank=True)

    class Meta:
        db_table = 'broadcast_posts'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.channel.name} — {self.content[:40]}'


class CustomerBlockedStore(BaseModel):
    """A customer blocking a store — hides the store from their feed and prevents notifications."""
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_stores')
    store    = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='blocked_by_customers')

    class Meta:
        db_table      = 'customer_blocked_stores'
        unique_together = [('customer', 'store')]
        ordering      = ['-created_at']

    def __str__(self):
        return f'{self.customer.phone_number} blocked {self.store.name}'


class ServiceCatalogue(BaseModel):
    """
    Services offered by Service Vendors.
    Only relevant when store.vendor_type == 'service'.
    """
    store            = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='services')
    name             = models.CharField(max_length=200)
    slug             = models.SlugField(max_length=220, blank=True)
    description      = models.TextField(blank=True)
    price_from       = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_to         = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True, help_text='Estimated service duration in minutes')
    is_active        = models.BooleanField(default=True)
    image_url        = models.URLField(blank=True)
    sort_order       = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'service_catalogue'
        ordering = ['sort_order', 'name']
        unique_together = [('store', 'slug')]

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.store.name} — {self.name}'

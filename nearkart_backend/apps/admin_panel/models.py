"""
NearKart — Admin Panel Models
PromoBanner: platform-level promotional banners shown on customer home screen.
"""
from django.conf import settings
from django.db import models

from core.models import BaseModel


class PromoBanner(BaseModel):
    LINK_STORE    = 'store'
    LINK_PRODUCT  = 'product'
    LINK_CATEGORY = 'category'
    LINK_EXTERNAL = 'external'
    LINK_NONE     = 'none'
    LINK_CHOICES  = [
        (LINK_STORE,    'Open Store'),
        (LINK_PRODUCT,  'Open Product'),
        (LINK_CATEGORY, 'Filter Category'),
        (LINK_EXTERNAL, 'External URL'),
        (LINK_NONE,     'No Action'),
    ]

    title         = models.CharField(max_length=100)
    subtitle      = models.CharField(max_length=200, blank=True)
    badge_text    = models.CharField(max_length=20, blank=True)   # e.g. "SALE", "NEW", "HOT"
    image_url     = models.URLField(blank=True)
    link_type     = models.CharField(max_length=20, choices=LINK_CHOICES, default=LINK_NONE)
    link_value    = models.CharField(max_length=500, blank=True)  # store_id / product_id / category / url
    target_city   = models.CharField(max_length=100, blank=True)   # empty = show globally
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    is_active     = models.BooleanField(default=True, db_index=True)
    starts_at     = models.DateTimeField(null=True, blank=True)
    ends_at       = models.DateTimeField(null=True, blank=True)
    is_paid       = models.BooleanField(default=False)
    created_by    = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='banners_created',
    )

    class Meta:
        db_table = 'admin_promo_banners'
        ordering = ['display_order', '-created_at']

    def __str__(self):
        return f'{self.title} ({"active" if self.is_active else "inactive"})'


class AdminActivityLog(BaseModel):
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='admin_actions',
    )
    action       = models.CharField(max_length=50)
    target_type  = models.CharField(max_length=50, blank=True)   # 'user', 'store', 'product', 'video'
    target_id    = models.CharField(max_length=100, blank=True)
    target_label = models.CharField(max_length=200, blank=True)  # human-readable identifier
    detail       = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = 'admin_activity_log'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.admin} — {self.action} — {self.target_label}'


class Category(BaseModel):
    name          = models.CharField(max_length=100, unique=True)
    slug          = models.SlugField(max_length=100, unique=True)
    icon          = models.CharField(max_length=10, blank=True)   # emoji e.g. "👗"
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    is_active     = models.BooleanField(default=True, db_index=True)
    created_by    = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, related_name='categories_created',
    )

    class Meta:
        db_table = 'admin_categories'
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name


class OfferTemplate(BaseModel):
    name                 = models.CharField(max_length=200)
    description_template = models.TextField(blank=True)
    default_discount_pct = models.PositiveSmallIntegerField(null=True, blank=True)
    badge_text           = models.CharField(max_length=20, blank=True)   # "SALE", "HOT", "DIWALI"
    emoji                = models.CharField(max_length=10, blank=True)   # "✨"
    image_url            = models.URLField(blank=True)
    is_active            = models.BooleanField(default=True, db_index=True)
    is_default           = models.BooleanField(default=False, db_index=True)
    display_order        = models.PositiveIntegerField(default=0, db_index=True)
    created_by           = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, related_name='offer_templates_created',
    )

    class Meta:
        db_table = 'admin_offer_templates'
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name


class AdminLevel(models.TextChoices):
    MASTER   = 'master',   'Master Admin'
    LOCATION = 'location', 'Location Admin'


class AdminProfile(BaseModel):
    """
    One AdminProfile per admin User.
    Master Admin: platform-wide access.
    Location Admin: restricted to their assigned district.
    """
    user              = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='admin_profile'
    )
    admin_level       = models.CharField(max_length=10, choices=AdminLevel.choices, default=AdminLevel.LOCATION)
    assigned_district = models.CharField(max_length=200, blank=True, help_text='For LOCATION admins — district they manage. Empty for MASTER admins.')
    assigned_city     = models.CharField(max_length=200, blank=True)
    is_active         = models.BooleanField(default=True)

    class Meta:
        db_table = 'admin_profiles'

    def __str__(self):
        return f'{self.user.phone_number} — {self.admin_level} ({self.assigned_district or "all"})'

    @property
    def is_master(self):
        return self.admin_level == AdminLevel.MASTER

    @property
    def is_location(self):
        return self.admin_level == AdminLevel.LOCATION

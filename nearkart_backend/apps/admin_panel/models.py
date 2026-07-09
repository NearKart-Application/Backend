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
    MASTER   = 'master',   'Master Admin'      # sees everything
    STATE    = 'state',    'State Admin'       # e.g. Andhra Pradesh
    DISTRICT = 'district', 'District Admin'    # e.g. Visakhapatnam
    CITY     = 'city',     'City Admin'        # e.g. Gajuwaka
    AREA     = 'area',     'Area / Village Admin'  # e.g. Kommadi


class AdminProfile(BaseModel):
    """
    One AdminProfile per admin User.
    Access scope is determined by admin_level + assigned_* fields.
    A State Admin with assigned_state='Andhra Pradesh' sees ONLY AP data.
    A District Admin with assigned_state='AP' + assigned_district='Visakhapatnam'
    sees only Vizag data. And so on down to village level.
    """
    user          = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='admin_profile'
    )
    admin_level   = models.CharField(
        max_length=10, choices=AdminLevel.choices, default=AdminLevel.DISTRICT,
        help_text='Determines the scope of data this admin can see and modify.'
    )

    # Geographic scope — fill only the levels relevant to this admin's level.
    # e.g. State Admin: fill assigned_state only.
    # District Admin: fill assigned_state + assigned_district.
    # City Admin: fill assigned_state + assigned_district + assigned_city.
    assigned_state    = models.CharField(max_length=150, blank=True, default='',
        help_text='Required for State/District/City/Area admins.')
    assigned_district = models.CharField(max_length=200, blank=True, default='',
        help_text='Required for District/City/Area admins.')
    assigned_city     = models.CharField(max_length=200, blank=True, default='',
        help_text='Required for City/Area admins.')
    assigned_area     = models.CharField(max_length=200, blank=True, default='',
        help_text='Required for Area/Village admins.')

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'admin_profiles'

    def __str__(self):
        scope = self.assigned_area or self.assigned_city or self.assigned_district or self.assigned_state or 'all'
        return f'{self.user.phone_number} — {self.get_admin_level_display()} ({scope})'

    @property
    def is_master(self):
        return self.admin_level == AdminLevel.MASTER

    @property
    def scope_filter_for_stores(self):
        """Returns a dict of filter kwargs to scope Store queryset to this admin's area."""
        level = self.admin_level
        if level == AdminLevel.MASTER:
            return {}
        if level == AdminLevel.STATE:
            return {'state': self.assigned_state}
        if level == AdminLevel.DISTRICT:
            return {'state': self.assigned_state, 'district': self.assigned_district}
        if level == AdminLevel.CITY:
            return {'state': self.assigned_state, 'district': self.assigned_district, 'city': self.assigned_city}
        if level == AdminLevel.AREA:
            return {'state': self.assigned_state, 'district': self.assigned_district,
                    'city': self.assigned_city, 'area': self.assigned_area}
        return {}

    @property
    def scope_filter_for_users(self):
        """Returns a dict of filter kwargs to scope User queryset to this admin's area."""
        level = self.admin_level
        if level == AdminLevel.MASTER:
            return {}
        if level == AdminLevel.STATE:
            return {'location_state': self.assigned_state}
        if level == AdminLevel.DISTRICT:
            return {'location_state': self.assigned_state, 'location_district': self.assigned_district}
        if level == AdminLevel.CITY:
            return {'location_state': self.assigned_state, 'location_district': self.assigned_district,
                    'location_city': self.assigned_city}
        if level == AdminLevel.AREA:
            return {'location_state': self.assigned_state, 'location_district': self.assigned_district,
                    'location_city': self.assigned_city}
        return {}

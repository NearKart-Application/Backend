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

"""
NearKart — Reservation Model
Customers hold a product at a store for RESERVATION_HOLD_HOURS (default 2h).
Vendor confirms, rejects, or marks completed. Celery expires stale holds.
"""
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta

from core.models import BaseModel
from apps.stores.models import Store
from apps.products.models import Product, ProductVariant


class ReservationStatus(models.TextChoices):
    PENDING   = 'pending',   'Pending'
    CONFIRMED = 'confirmed', 'Confirmed'
    CANCELLED = 'cancelled', 'Cancelled'
    EXPIRED   = 'expired',   'Expired'
    COMPLETED = 'completed', 'Completed'


class Reservation(BaseModel):
    store       = models.ForeignKey(Store,   on_delete=models.CASCADE, related_name='reservations')
    customer    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reservations')
    product     = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reservations')
    variant     = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name='reservations')
    quantity    = models.PositiveIntegerField(default=1)
    note        = models.TextField(blank=True)         # customer note to vendor
    vendor_note = models.TextField(blank=True)         # vendor response
    status      = models.CharField(
        max_length=20,
        choices=ReservationStatus.choices,
        default=ReservationStatus.PENDING,
        db_index=True,
    )
    expires_at      = models.DateTimeField(db_index=True)
    points_redeemed = models.PositiveIntegerField(default=0)
    discount_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    class Meta:
        db_table = 'reservations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['store', 'status'],    name='res_store_status_idx'),
            models.Index(fields=['customer', 'status'], name='res_customer_status_idx'),
        ]

    def __str__(self):
        return f'{self.customer} → {self.product.name} ({self.status})'

    @property
    def is_pending(self):
        return self.status == ReservationStatus.PENDING

    @property
    def hours_left(self):
        if self.status != ReservationStatus.PENDING:
            return 0
        delta = self.expires_at - timezone.now()
        return max(0, round(delta.total_seconds() / 3600, 1))

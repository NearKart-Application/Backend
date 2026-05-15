"""
NearKart — Blacklist Model
A vendor's store can block a customer from interacting with it.
"""
from django.conf import settings
from django.db import models

from core.models import BaseModel
from apps.stores.models import Store


class Blacklist(BaseModel):
    store    = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='blacklisted_customers')
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blacklisted_by_stores')
    reason   = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = 'blacklists'
        unique_together = [('store', 'customer')]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.store.name} blocked {self.customer.phone_number}'

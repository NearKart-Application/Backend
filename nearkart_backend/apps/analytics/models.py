"""
NearKart — Analytics Models
DailyAnalyticsSnapshot: daily performance snapshot per store for trend charts.
"""
from django.db import models
from core.models import BaseModel


class DailyAnalyticsSnapshot(BaseModel):
    """One row per store per day, created by the Celery beat snapshot task."""
    store             = models.ForeignKey(
        'stores.Store', on_delete=models.CASCADE,
        related_name='analytics_snapshots',
    )
    snapshot_date     = models.DateField(db_index=True)
    reservation_count = models.PositiveIntegerField(default=0)
    completed_count   = models.PositiveIntegerField(default=0)
    revenue           = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    follower_count    = models.PositiveIntegerField(default=0)
    product_count     = models.PositiveIntegerField(default=0)
    video_view_count  = models.PositiveIntegerField(default=0)
    new_customer_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table        = 'analytics_daily_snapshots'
        unique_together = [('store', 'snapshot_date')]
        ordering        = ['-snapshot_date']

    def __str__(self):
        return f'{self.store.name} — {self.snapshot_date}'

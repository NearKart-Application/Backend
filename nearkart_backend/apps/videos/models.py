"""
NearKart — Video Models
Video: vendor-uploaded product video (HLS, 30-day expiry)
VideoLike: user ↔ video many-to-many like tracking
"""
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils import timezone


class Video(models.Model):
    STATUS_PENDING    = 'pending_upload'
    STATUS_PROCESSING = 'processing'
    STATUS_READY      = 'ready'
    STATUS_FAILED     = 'failed'
    STATUS_EXPIRED    = 'expired'

    STATUS_CHOICES = [
        (STATUS_PENDING,    'Pending Upload'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_READY,      'Ready'),
        (STATUS_FAILED,     'Failed'),
        (STATUS_EXPIRED,    'Expired'),
    ]

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store            = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='videos')
    title            = models.CharField(max_length=200)
    description      = models.TextField(blank=True)

    # S3 object keys
    raw_s3_key       = models.CharField(max_length=500, blank=True)
    hls_s3_key       = models.CharField(max_length=500, blank=True)

    # Public-facing URLs (filled after transcoding)
    thumbnail_url    = models.URLField(max_length=500, blank=True)
    video_url        = models.URLField(max_length=500, blank=True)  # HLS .m3u8

    status           = models.CharField(max_length=20, choices=STATUS_CHOICES,
                                        default=STATUS_PENDING, db_index=True)
    duration_seconds = models.PositiveIntegerField(default=0)

    # Location copied from store at upload time for fast geo-queries
    location         = gis_models.PointField(geography=True, null=True, blank=True)
    locality         = models.CharField(max_length=200, blank=True)

    view_count       = models.PositiveIntegerField(default=0)
    like_count       = models.PositiveIntegerField(default=0)

    is_visible       = models.BooleanField(default=True, db_index=True)
    expires_at       = models.DateTimeField(null=True, blank=True, db_index=True)

    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'is_visible']),
            models.Index(fields=['store', 'status']),
        ]

    def __str__(self):
        return f'{self.title} ({self.store.name})'

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(
                days=getattr(settings, 'VIDEO_EXPIRY_DAYS', 30)
            )
        # Inherit location from store so nearby-feed queries work
        if self.store_id and not self.location:
            try:
                store = self.store
                if store.location:
                    self.location = store.location
                    self.locality = store.locality
            except Exception:
                pass
        super().save(*args, **kwargs)


class VideoLike(models.Model):
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name='video_likes')
    video      = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'video']

    def __str__(self):
        return f'{self.user} likes {self.video}'


class VideoSave(models.Model):
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name='video_saves')
    video      = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='saves')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'video']

    def __str__(self):
        return f'{self.user} saved {self.video}'


class VideoProductTag(models.Model):
    """Product pinned to a specific position in a video (TikTok-style tap overlay)."""
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    video      = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='product_tags')
    product    = models.ForeignKey('products.Product', on_delete=models.CASCADE,
                                   related_name='video_tags')
    # Normalised 0–1 position on the video frame (e.g. 0.3 = 30% from left/top)
    x_pct      = models.FloatField(default=0.5)
    y_pct      = models.FloatField(default=0.5)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['video', 'product']
        ordering = ['created_at']

    def __str__(self):
        return f'{self.product.name} @ ({self.x_pct:.2f}, {self.y_pct:.2f}) in {self.video.title}'

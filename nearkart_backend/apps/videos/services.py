"""
NearKart — Video Services
AWSService : presigned URL generation + CDN URL helper
VideoService: business logic (upload flow, feed, likes, expiry)
"""
import logging
import uuid

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db.models import F
from django.utils import timezone

from .models import Video, VideoLike

logger = logging.getLogger(__name__)

_DEV_CREDS = ('AKIAIOSFODNN7EXAMPLE', 'wJalrXUtnFEMI')


def _is_dev_aws() -> bool:
    return settings.AWS_ACCESS_KEY_ID in _DEV_CREDS or 'EXAMPLE' in settings.AWS_ACCESS_KEY_ID


class AWSService:
    @staticmethod
    def _client():
        kwargs: dict = dict(
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        if getattr(settings, 'AWS_S3_USE_ACCELERATE', False):
            from botocore.config import Config
            kwargs['config'] = Config(s3={'use_accelerate_endpoint': True})
        return boto3.client('s3', **kwargs)

    @staticmethod
    def generate_presigned_upload_url(s3_key: str, content_type: str = 'video/mp4') -> str:
        if _is_dev_aws():
            return f'https://mock-s3.dev/{s3_key}?dev=true'
        try:
            return AWSService._client().generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': settings.AWS_S3_BUCKET,
                    'Key': s3_key,
                    'ContentType': content_type,
                },
                ExpiresIn=settings.AWS_PRESIGNED_URL_EXPIRY,
            )
        except ClientError as exc:
            logger.error('S3 presigned URL error: %s', exc)
            return ''

    @staticmethod
    def generate_presigned_download_url(s3_key: str, expiry_seconds: int = 3600) -> str:
        """Presigned GET URL so vendor can download the original MP4 locally."""
        if _is_dev_aws():
            return f'https://mock-s3.dev/{s3_key}?download=true&dev=true'
        try:
            return AWSService._client().generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': settings.AWS_S3_BUCKET,
                    'Key': s3_key,
                    'ResponseContentDisposition': 'attachment',
                },
                ExpiresIn=expiry_seconds,
            )
        except ClientError as exc:
            logger.error('S3 presigned download URL error: %s', exc)
            return ''

    @staticmethod
    def cdn_url(s3_key: str) -> str:
        if not s3_key:
            return ''
        domain = settings.AWS_CDN_DOMAIN or (
            f'{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com'
        )
        return f'https://{domain}/{s3_key}'


class VideoService:
    @staticmethod
    def request_upload(store, title: str, description: str = '') -> tuple:
        """Create Video record + presigned S3 PUT URL. Returns (video, upload_url)."""
        video_id = uuid.uuid4()
        s3_key   = f'videos/raw/{store.id}/{video_id}/original.mp4'
        upload_url = AWSService.generate_presigned_upload_url(s3_key)

        video = Video.objects.create(
            id=video_id,
            store=store,
            title=title,
            description=description,
            raw_s3_key=s3_key,
            status=Video.STATUS_PENDING,
        )
        return video, upload_url

    @staticmethod
    def confirm_upload(video: Video, duration_seconds: int = 0) -> Video:
        """Mark video as processing and enqueue the Celery transcoding task."""
        from .tasks import transcode_video
        video.duration_seconds = duration_seconds
        video.status = Video.STATUS_PROCESSING
        video.save(update_fields=['duration_seconds', 'status', 'updated_at'])
        transcode_video.delay(str(video.id))
        return video

    @staticmethod
    def get_feed(lat: float, lng: float, radius_km: int = 5, store_id=None):
        """Return ready, visible, non-expired videos sorted by distance."""
        point = Point(lng, lat, srid=4326)
        from django.contrib.gis.db.models.functions import Distance
        qs = (
            Video.objects
            .filter(
                status=Video.STATUS_READY,
                is_visible=True,
                expires_at__gt=timezone.now(),
            )
            .filter(location__dwithin=(point, D(km=radius_km)))
            .select_related('store')
            .prefetch_related('product_tags__product')
            .annotate(distance=Distance('location', point))
            .order_by('distance', '-created_at')
        )
        if store_id:
            qs = qs.filter(store_id=store_id)
        return qs[:50]

    @staticmethod
    def get_following_feed(user):
        """Return videos from stores the user follows, newest first."""
        from apps.stores.models import StoreFollow
        followed_store_ids = StoreFollow.objects.filter(user=user).values_list('store_id', flat=True)
        return (
            Video.objects
            .filter(
                store_id__in=followed_store_ids,
                status=Video.STATUS_READY,
                is_visible=True,
                expires_at__gt=timezone.now(),
            )
            .select_related('store')
            .prefetch_related('product_tags__product')
            .order_by('-created_at')[:50]
        )

    @staticmethod
    def get_trending_feed():
        """Return globally trending videos (no radius limit) by combined view + like score."""
        return (
            Video.objects
            .filter(
                status=Video.STATUS_READY,
                is_visible=True,
                expires_at__gt=timezone.now(),
            )
            .select_related('store')
            .prefetch_related('product_tags__product')
            .order_by('-view_count', '-like_count', '-created_at')[:50]
        )

    @staticmethod
    def toggle_save(user, video: Video) -> bool:
        """Toggle save (bookmark). Returns True if saved, False if unsaved."""
        from .models import VideoSave
        save, created = VideoSave.objects.get_or_create(user=user, video=video)
        if not created:
            save.delete()
            return False
        return True

    @staticmethod
    def increment_view(video: Video) -> None:
        Video.objects.filter(id=video.id).update(view_count=F('view_count') + 1)

    @staticmethod
    def toggle_like(user, video: Video) -> bool:
        """Toggle like. Returns True if liked, False if unliked."""
        like, created = VideoLike.objects.get_or_create(user=user, video=video)
        if created:
            Video.objects.filter(id=video.id).update(like_count=F('like_count') + 1)
            return True
        like.delete()
        Video.objects.filter(id=video.id).update(
            like_count=F('like_count') - 1
        )
        return False

    @staticmethod
    def expire_old_videos() -> int:
        """Mark videos past expires_at as expired. Called by Celery Beat."""
        return Video.objects.filter(
            expires_at__lt=timezone.now(),
            status__in=[Video.STATUS_READY, Video.STATUS_PROCESSING],
        ).update(status=Video.STATUS_EXPIRED, is_visible=False)

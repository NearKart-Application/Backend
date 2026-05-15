"""
NearKart — Video Celery Tasks
transcode_video   : FFmpeg raw → HLS, updates Video record
delete_expired_videos : daily beat task to expire old videos
"""
import logging
import os
import shutil
import subprocess

import boto3
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)

_DEV_CREDS = ('AKIAIOSFODNN7EXAMPLE', 'wJalrXUtnFEMI')


def _is_dev_aws() -> bool:
    return settings.AWS_ACCESS_KEY_ID in _DEV_CREDS or 'EXAMPLE' in settings.AWS_ACCESS_KEY_ID


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def transcode_video(self, video_id: str):
    """Transcode an uploaded video to HLS using FFmpeg and upload segments to S3."""
    from .models import Video
    from .services import AWSService

    try:
        video = Video.objects.select_related('store__owner').get(id=video_id)
    except Video.DoesNotExist:
        logger.error('transcode_video: video %s not found', video_id)
        return

    # Dev mode: fake AWS creds — skip real FFmpeg work, mark ready immediately
    if _is_dev_aws():
        video.status       = Video.STATUS_READY
        video.video_url    = f'https://mock-s3.dev/videos/hls/{video_id}/master.m3u8?dev=true'
        video.thumbnail_url = f'https://mock-s3.dev/videos/thumbnails/{video_id}/thumb.jpg?dev=true'
        video.save(update_fields=['status', 'video_url', 'thumbnail_url', 'updated_at'])
        logger.info('transcode_video: dev mode — video %s marked ready', video_id)
        from apps.notifications.services import NotificationService
        NotificationService.notify_video_ready(video.store.owner, video.title, str(video.id))
        return

    local_input   = f'/tmp/{video_id}_input.mp4'
    local_hls_dir = f'/tmp/{video_id}_hls'
    local_thumb   = f'/tmp/{video_id}_thumb.jpg'

    try:
        s3 = boto3.client(
            's3',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        os.makedirs(local_hls_dir, exist_ok=True)

        # 1. Download raw file
        s3.download_file(settings.AWS_S3_BUCKET, video.raw_s3_key, local_input)

        # 2. Transcode to HLS with FFmpeg
        hls_output = f'{local_hls_dir}/master.m3u8'
        subprocess.run([
            'ffmpeg', '-i', local_input,
            '-c:v', 'libx264', '-crf', '23', '-preset', 'fast',
            '-c:a', 'aac', '-b:a', '128k',
            '-hls_time', '6', '-hls_list_size', '0',
            '-hls_segment_filename', f'{local_hls_dir}/segment_%03d.ts',
            '-f', 'hls', hls_output,
        ], check=True, timeout=300)

        # 3. Generate thumbnail at 1 second
        subprocess.run([
            'ffmpeg', '-i', local_input,
            '-ss', '00:00:01', '-vframes', '1',
            '-vf', 'scale=480:270',
            local_thumb,
        ], check=True, timeout=30)

        # 4. Upload HLS segments to S3
        hls_s3_prefix = f'videos/hls/{video.store_id}/{video_id}'
        for fname in os.listdir(local_hls_dir):
            ctype = 'application/vnd.apple.mpegurl' if fname.endswith('.m3u8') else 'video/mp2t'
            s3.upload_file(
                f'{local_hls_dir}/{fname}',
                settings.AWS_S3_BUCKET,
                f'{hls_s3_prefix}/{fname}',
                ExtraArgs={'ContentType': ctype},
            )

        # 5. Upload thumbnail
        thumb_key = f'videos/thumbnails/{video.store_id}/{video_id}/thumb.jpg'
        s3.upload_file(local_thumb, settings.AWS_S3_BUCKET, thumb_key,
                       ExtraArgs={'ContentType': 'image/jpeg'})

        hls_key           = f'{hls_s3_prefix}/master.m3u8'
        video.hls_s3_key  = hls_key
        video.video_url   = AWSService.cdn_url(hls_key)
        video.thumbnail_url = AWSService.cdn_url(thumb_key)
        video.status      = Video.STATUS_READY
        video.save(update_fields=['hls_s3_key', 'video_url', 'thumbnail_url', 'status', 'updated_at'])
        logger.info('transcode_video: video %s ready', video_id)
        from apps.notifications.services import NotificationService
        NotificationService.notify_video_ready(video.store.owner, video.title, str(video.id))

    except Exception as exc:
        logger.error('transcode_video: failed for %s — %s', video_id, exc)
        video.status = Video.STATUS_FAILED
        video.save(update_fields=['status', 'updated_at'])
        raise self.retry(exc=exc)

    finally:
        for path in [local_input, local_thumb]:
            if os.path.exists(path):
                os.remove(path)
        shutil.rmtree(local_hls_dir, ignore_errors=True)


@shared_task
def delete_expired_videos():
    """Daily Celery Beat task — expire videos past their expiry date."""
    from .services import VideoService
    count = VideoService.expire_old_videos()
    logger.info('delete_expired_videos: %d videos expired', count)
    return count

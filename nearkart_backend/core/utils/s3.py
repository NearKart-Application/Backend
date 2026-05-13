"""
NearKart — AWS S3 Utility Functions
"""
import boto3
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def get_s3_client():
    return boto3.client(
        's3',
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


def generate_presigned_upload_url(store_id: str, video_id: str,
                                   content_type: str) -> dict:
    """
    Generate a presigned S3 URL for direct video upload from client.
    Client uploads directly to S3 — zero video bytes through Django.
    """
    s3 = get_s3_client()
    key = f'videos/{store_id}/{video_id}/original.mp4'

    url = s3.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': settings.AWS_S3_BUCKET,
            'Key': key,
            'ContentType': content_type,
        },
        ExpiresIn=settings.AWS_PRESIGNED_URL_EXPIRY,
    )
    return {'upload_url': url, 's3_key': key}


def generate_presigned_image_url(store_id: str, product_id: str,
                                  filename: str, content_type: str) -> dict:
    """Generate presigned URL for product image upload."""
    s3 = get_s3_client()
    key = f'images/{store_id}/{product_id}/{filename}'

    url = s3.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': settings.AWS_S3_BUCKET,
            'Key': key,
            'ContentType': content_type,
        },
        ExpiresIn=settings.AWS_PRESIGNED_URL_EXPIRY,
    )
    return {'upload_url': url, 's3_key': key}


def delete_video_files(store_id: str, video_id: str) -> None:
    """Delete all HLS files + thumbnail for a video from S3."""
    s3 = get_s3_client()
    prefix = f'videos/{store_id}/{video_id}/'

    try:
        response = s3.list_objects_v2(
            Bucket=settings.AWS_S3_BUCKET,
            Prefix=prefix,
        )
        objects = [{'Key': obj['Key']} for obj in response.get('Contents', [])]
        if objects:
            s3.delete_objects(
                Bucket=settings.AWS_S3_BUCKET,
                Delete={'Objects': objects},
            )
            logger.info(f'Deleted {len(objects)} S3 files for video {video_id}')
    except Exception as e:
        logger.error(f'Failed to delete S3 files for video {video_id}: {e}')
        raise


def get_cdn_url(s3_key: str) -> str:
    """Convert S3 key to CDN URL."""
    if settings.AWS_CDN_DOMAIN:
        return f'https://{settings.AWS_CDN_DOMAIN}/{s3_key}'
    return f'https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}'

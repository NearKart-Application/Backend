"""
NearKart — Input Validators
"""
from django.core.exceptions import ValidationError
from django.conf import settings
import re


def validate_indian_phone(value: str) -> None:
    """Validate Indian phone number: +91 followed by 10 digits."""
    pattern = r'^\+91[6-9]\d{9}$'
    if not re.match(pattern, value):
        raise ValidationError(
            'Enter a valid Indian phone number starting with +91 '
            'followed by 10 digits (e.g. +919876543210)',
            code='INVALID_PHONE',
        )


def validate_otp(value: str) -> None:
    """Validate 6-digit OTP."""
    if not re.match(r'^\d{6}$', value):
        raise ValidationError(
            'OTP must be exactly 6 digits.',
            code='INVALID_OTP',
        )


def validate_video_content_type(value: str) -> None:
    """Validate video MIME type."""
    allowed = ['video/mp4', 'video/quicktime', 'video/x-msvideo']
    if value not in allowed:
        raise ValidationError(
            f'Invalid video type. Allowed: MP4, MOV, AVI.',
            code='INVALID_FILE_TYPE',
        )


def validate_image_content_type(value: str) -> None:
    """Validate image MIME type."""
    allowed = ['image/jpeg', 'image/png', 'image/webp']
    if value not in allowed:
        raise ValidationError(
            'Invalid image type. Allowed: JPEG, PNG, WebP.',
            code='INVALID_FILE_TYPE',
        )


def validate_video_size(size_mb: float) -> None:
    """Validate video file size."""
    max_size = settings.VIDEO_MAX_SIZE_MB
    if size_mb > max_size:
        raise ValidationError(
            f'Video too large. Maximum size is {max_size}MB.',
            code='VIDEO_TOO_LARGE',
        )


def validate_radius(value: int) -> None:
    """Validate geo radius value."""
    allowed = [1, 2, 3, 5]
    if value not in allowed:
        raise ValidationError(
            f'Radius must be one of: {allowed}',
            code='INVALID_RADIUS',
        )

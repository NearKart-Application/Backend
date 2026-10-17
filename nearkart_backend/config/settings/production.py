"""
NearKart — Production Settings
Used by: ECS production cluster
DJANGO_SETTINGS_MODULE=config.settings.production
"""
import environ
from .base import *  # noqa

env = environ.Env()

DEBUG = False

# ── HOSTS ─────────────────────────────────────────────────────
# Set ALLOWED_HOSTS=api.nearspot.in in production .env
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['api.nearspot.in'])

# ── SECURITY ──────────────────────────────────────────────────
# SSL is terminated at the AWS ALB — Django trusts the forwarded header
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = False  # ALB already enforces HTTPS; don't double-redirect

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# ── STATIC + MEDIA FILES (AWS S3 via django-storages) ─────────
# querystring_auth=False: generate permanent public URLs instead of
# presigned URLs that expire. Requires the S3 bucket objects to be
# publicly readable (set via bucket policy, not ACL — S3 Block Public
# Access must allow bucket-policy-based public reads).
# Set AWS_CDN_DOMAIN to a CloudFront domain for CDN-cached delivery.
STORAGES = {
    'default': {
        'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
        'OPTIONS': {
            'bucket_name':      env('AWS_S3_BUCKET', default='nearkart-media'),
            'region_name':      env('AWS_REGION',    default='ap-south-1'),
            'location':         'media',
            'file_overwrite':   False,
            'querystring_auth': False,
            'custom_domain':    env('AWS_CDN_DOMAIN', default=''),
        },
    },
    'staticfiles': {
        'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
        'OPTIONS': {
            'bucket_name':      env('AWS_S3_STATIC_BUCKET', default='nearkart-static'),
            'region_name':      env('AWS_REGION', default='ap-south-1'),
            'location':         'static',
            'querystring_auth': False,
            'custom_domain':    env('AWS_CDN_DOMAIN', default=''),
        },
    },
}

# ── EMAIL (SendGrid) ──────────────────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'apikey'
EMAIL_HOST_PASSWORD = env('SENDGRID_API_KEY', default='')

# ── DATABASE: production tuning ───────────────────────────────
# CONN_MAX_AGE must stay 0 — PgBouncer transaction pooling reclaims
# connections between requests; persistent connections cause errors.
DATABASES['default']['CONN_MAX_AGE'] = 0   # noqa: F405
DATABASES['default']['CONN_HEALTH_CHECKS'] = True  # noqa: F405

# ── CELERY: ensure tasks run async in production ──────────────
CELERY_TASK_ALWAYS_EAGER = False

# ── CACHES: production Redis — longer TTL ────────────────────
CACHES['default']['TIMEOUT'] = 600  # noqa: F405

# ── LOGGING: structured stdout for CloudWatch ─────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            'format': '{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
            'datefmt': '%Y-%m-%dT%H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# ── CORS: nearspot.in production domains ─────────────────────
CORS_ALLOWED_ORIGINS = [
    'https://app.nearspot.in',
    'https://vendor.nearspot.in',
]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r'^https://.*\.nearspot\.in$',
]

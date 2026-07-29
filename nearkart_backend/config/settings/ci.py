"""
NearSpot — CI Settings
Used by GitHub Actions. Mirrors testing.py but reads credentials from env vars.
"""
import os
from .base import *  # noqa

SECRET_KEY = os.environ.get('SECRET_KEY', 'ci-insecure-key')
DEBUG = False
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# ── DATABASE: PostGIS via CI service ─────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'nearspot_test',
        'USER': 'nearspot',
        'PASSWORD': 'nearspot',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# ── CACHE: in-memory ─────────────────────────────────────────
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# ── CELERY: synchronous ───────────────────────────────────────
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# ── CHANNELS: in-memory ───────────────────────────────────────
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}

# ── EXTERNAL SERVICES: all stubbed ───────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}

# Disable Sentry in CI
SENTRY_DSN = ''

# Twilio / Firebase / SendGrid — stubbed
TWILIO_ACCOUNT_SID = 'ACtest'
TWILIO_AUTH_TOKEN = 'test'
TWILIO_PHONE_NUMBER = '+10000000000'
FIREBASE_CREDENTIALS = None
SENDGRID_API_KEY = 'SG.test'

# Razorpay — test mode
RAZORPAY_KEY_ID = 'rzp_test_key'
RAZORPAY_KEY_SECRET = 'rzp_test_secret'

# AWS S3 — stubbed
AWS_ACCESS_KEY_ID = 'test'
AWS_SECRET_ACCESS_KEY = 'test'
AWS_STORAGE_BUCKET_NAME = 'test-bucket'
AWS_S3_REGION_NAME = 'ap-south-1'

# Dev OTP bypass always active in CI
DEV_FIXED_OTP = '123456'

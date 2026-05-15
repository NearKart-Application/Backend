"""
NearKart — Testing Settings
Uses SQLite (no Docker needed). Disables all external services.
Run with: pytest  (pytest.ini points here automatically)
"""
from .base import *  # noqa

# ── DATABASE: SQLite, no Docker needed ────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.spatialite',
        'NAME': ':memory:',
    }
}

# ── CACHE: in-memory, no Redis needed ─────────────────────────
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# ── CELERY: run tasks synchronously, no worker needed ─────────
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# ── CHANNELS: in-memory, no Redis needed ──────────────────────
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}

# ── DISABLE ALL EXTERNAL SERVICES ─────────────────────────────
TWILIO_ACCOUNT_SID = 'test'
TWILIO_AUTH_TOKEN = 'test'
TWILIO_FROM_NUMBER = '+10000000000'
SENDGRID_API_KEY = 'test'
AWS_ACCESS_KEY_ID = 'test'
AWS_SECRET_ACCESS_KEY = 'test'
FIREBASE_CREDENTIALS_JSON = ''
SENTRY_DSN = ''

# ── FIXED OTP FOR TESTING ─────────────────────────────────────
DEV_FIXED_OTP = '123456'

# ── SPEED UP PASSWORD HASHING IN TESTS ────────────────────────
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# ── DISABLE MIGRATIONS: use direct schema creation ────────────
class DisableMigrations:
    def __contains__(self, item):
        return True
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

SECRET_KEY = 'test-secret-key-not-for-production'
DEBUG = True
ALLOWED_HOSTS = ['*']
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

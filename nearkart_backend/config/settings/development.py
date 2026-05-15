"""
NearKart — Development Settings
Local development overrides
"""
from .base import *  # noqa
import environ

env = environ.Env()

DEBUG = True

ALLOWED_HOSTS = ['*']

# ── DISABLE SENTRY IN DEV (dummy DSN in .env causes ASGI conflicts) ──
SENTRY_DSN = ''

# ── DEV ONLY: fixed OTP bypasses Twilio ───────────────────────
DEV_FIXED_OTP = env('DEV_FIXED_OTP', default='123456')

# ── DEV ONLY: show SQL queries ────────────────────────────────
if env.bool('DEBUG_SQL', default=False):
    LOGGING['loggers']['django.db.backends'] = {
        'handlers': ['console'],
        'level': 'DEBUG',
        'propagate': False,
    }

# ── EMAIL (console backend in dev — no SendGrid needed) ───────
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ── CORS: allow all in dev ────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = True

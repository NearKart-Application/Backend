"""
NearKart — Development Settings
Local development overrides
"""
from .base import *  # noqa
import environ

env = environ.Env()

DEBUG = True

ALLOWED_HOSTS = ['*']

# ── DEV ONLY: fixed OTP bypasses Twilio ───────────────────────
DEV_FIXED_OTP = env('DEV_FIXED_OTP', default='123456')

# ── DEV ONLY: show SQL queries ────────────────────────────────
if env.bool('DEBUG_SQL', default=False):
    LOGGING['loggers']['django.db.backends'] = {
        'handlers': ['console'],
        'level': 'DEBUG',
        'propagate': False,
    }

# ── DEBUG TOOLBAR ─────────────────────────────────────────────
try:
    import debug_toolbar  # noqa
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
    INTERNAL_IPS = ['127.0.0.1']
    DEBUG_TOOLBAR_CONFIG = {'SHOW_TOOLBAR_CALLBACK': lambda r: DEBUG}
except ImportError:
    pass

# ── EMAIL (console backend in dev — no SendGrid needed) ───────
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ── CORS: allow all in dev ────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = True

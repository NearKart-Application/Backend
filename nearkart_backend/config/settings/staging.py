"""
NearKart — Staging Settings
Inherits production settings with staging-specific overrides.
Used by: ECS staging cluster
DJANGO_SETTINGS_MODULE=config.settings.staging
"""
from .production import *  # noqa

# ── HOSTS ─────────────────────────────────────────────────────
ALLOWED_HOSTS = ['api-staging.nearspot.in', 'localhost', '127.0.0.1']

# ── RELAXED HSTS FOR STAGING ──────────────────────────────────
# Short TTL so we can change domains easily during staging
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_PRELOAD = False

# ── SENTRY: use staging environment tag ──────────────────────
import sentry_sdk  # noqa
from sentry_sdk.integrations.django import DjangoIntegration  # noqa
from sentry_sdk.integrations.celery import CeleryIntegration  # noqa
from sentry_sdk.integrations.redis import RedisIntegration   # noqa
import environ  # noqa

env = environ.Env()

SENTRY_DSN = env('SENTRY_DSN', default='')
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration(), RedisIntegration()],
        environment='staging',
        traces_sample_rate=0.5,
        send_default_pii=False,
    )

# ── SWAGGER DOCS: allow in staging (not in production) ────────
SPECTACULAR_SETTINGS['SERVERS'] = [  # noqa: F405
    {'url': 'https://api-staging.nearspot.in', 'description': 'Staging'},
]

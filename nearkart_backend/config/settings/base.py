"""
NearKart — Base Django Settings
Shared across all environments (development, staging, production)
"""
import os
import platform
from pathlib import Path
import environ
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration

# ── PATHS ──────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ── GDAL / GEOS (macOS Homebrew) ───────────────────────────────
if platform.system() == "Darwin":
    _brew_prefix = "/opt/homebrew"  # Apple Silicon; Intel uses /usr/local
    GDAL_LIBRARY_PATH = os.environ.get(
        "GDAL_LIBRARY_PATH",
        f"{_brew_prefix}/lib/libgdal.dylib",
    )
    GEOS_LIBRARY_PATH = os.environ.get(
        "GEOS_LIBRARY_PATH",
        f"{_brew_prefix}/lib/libgeos_c.dylib",
    )

# ── ENVIRONMENT ────────────────────────────────────────────────
env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env')

# ── CORE ───────────────────────────────────────────────────────
SECRET_KEY = env('SECRET_KEY')
DEBUG = env.bool('DEBUG', default=False)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

# ── APPS ───────────────────────────────────────────────────────
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',          # PostGIS
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'channels',
    'django_filters',
    'django_celery_beat',
    'drf_spectacular',
]

LOCAL_APPS = [
    'core',
    'apps.auth_app',
    'apps.stores',
    'apps.products',
    'apps.videos',
    'apps.chat',
    'apps.billing',
    'apps.analytics',
    'apps.blacklist',
    'apps.notifications',
    'apps.reservations',
    'apps.groups',
    'apps.admin_panel',
    'apps.loyalty',
    'apps.inventory',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ── MIDDLEWARE ─────────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.RequestLoggingMiddleware',
    'core.middleware.NoCachePersonalizedDataMiddleware',
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# ── TEMPLATES ─────────────────────────────────────────────────
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ── DATABASE (PostgreSQL + PostGIS) ───────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': env('DB_NAME', default='nearkart'),
        'USER': env('DB_USER', default='nearkart'),
        'PASSWORD': env('DB_PASSWORD'),
        # Point to PgBouncer (port 6432), not Postgres directly.
        # PgBouncer pools connections so 10,000 app connections share 20 DB connections.
        'HOST': env('DB_HOST', default='pgbouncer'),
        'PORT': env('DB_PORT', default='6432'),
        # CONN_MAX_AGE must be 0 with PgBouncer transaction pooling.
        # Persistent connections + transaction pooling = stale connection errors.
        'CONN_MAX_AGE': 0,
        'OPTIONS': {
            'connect_timeout': 10,
            # Kill any single query that runs longer than 10 s — prevents slow
            # geo queries from holding DB connections and blocking the pool.
            'options': '-c statement_timeout=10000',
        },
    }
}

# ── CACHE (Redis) ──────────────────────────────────────────────
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': env('REDIS_CACHE_URL', default='redis://redis:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
        },
        'KEY_PREFIX': 'nearkart',
        'TIMEOUT': 300,
    }
}

# ── CHANNELS (WebSocket) ───────────────────────────────────────
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [env('REDIS_CHANNEL_URL', default='redis://redis:6379/2')],
            'capacity': 1500,
            'expiry': 60,
        },
    }
}

# ── CELERY ─────────────────────────────────────────────────────
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://redis:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://redis:6379/0')
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = env('CELERY_TIMEZONE', default='Asia/Kolkata')
CELERY_ENABLE_UTC = True
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 600
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# ── CELERY QUEUE ROUTING ────────────────────────────────────────
# transcode_video goes to the dedicated 'transcoding' queue consumed ONLY by
# celery-transcoding workers (3 FFmpeg processes, max-tasks-per-child=10).
# Every other task routes to 'default' (4 workers — notifications, SMS,
# billing, analytics, Beat-triggered jobs).
# This isolation ensures FFmpeg jobs never starve push notifications or
# reservation expiry tasks, and vice-versa.
CELERY_TASK_DEFAULT_QUEUE = 'default'
CELERY_TASK_ROUTES = {
    'apps.videos.tasks.transcode_video':           {'queue': 'transcoding'},
    'inventory.check_low_stock_all':               {'queue': 'inventory'},
    'inventory.weekly_stock_summary':              {'queue': 'inventory'},
    'inventory.check_po_due_dates':                {'queue': 'inventory'},
    'inventory.reset_watchlist_notifications':     {'queue': 'inventory'},
    'inventory.detect_dead_stock':                 {'queue': 'inventory'},
}

# ── CELERY BEAT SCHEDULE ───────────────────────────────────────
from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    'expire-subscriptions-daily': {
        'task':     'billing.expire_subscriptions',
        'schedule': crontab(hour=0, minute=0),  # midnight IST daily
    },
    'expire-reservations-hourly': {
        'task':     'reservations.expire_reservations',
        'schedule': crontab(minute=0),           # top of every hour
    },
    'notify-expiring-subscriptions-daily': {
        'task':     'notifications.notify_expiring_subscriptions',
        'schedule': crontab(hour=9, minute=0),   # 9 AM daily
    },
    'notify-expired-subscriptions-daily': {
        'task':     'notifications.notify_expired_subscriptions',
        'schedule': crontab(hour=9, minute=5),   # 9:05 AM daily
    },
    # Video expiry flow — notify 2 days before, then delete on day 30
    'notify-expiring-videos-daily': {
        'task':     'videos.notify_expiring_videos',
        'schedule': crontab(hour=9, minute=10),  # 9:10 AM daily
    },
    'delete-expired-videos-daily': {
        'task':     'videos.delete_expired_videos',
        'schedule': crontab(hour=0, minute=30),  # 12:30 AM daily
    },
    'notify-1day-reservation-expiry-daily': {
        'task':     'reservations.notify_1day_expiry',
        'schedule': crontab(hour=8, minute=0),   # 8 AM daily
    },
    'notify-price-drops-6h': {
        'task':     'products.notify_price_drops',
        'schedule': crontab(minute=0, hour='*/6'),  # every 6 hours
    },
    'inventory-check-low-stock': {
        'task': 'inventory.check_low_stock_all',
        'schedule': crontab(minute=0, hour='*/6'),
    },
    'inventory-weekly-summary': {
        'task': 'inventory.weekly_stock_summary',
        'schedule': crontab(minute=0, hour=9, day_of_week=1),
    },
    'inventory-check-po-dates': {
        'task': 'inventory.check_po_due_dates',
        'schedule': crontab(minute=0, hour=8),
    },
    'inventory-reset-watchlist': {
        'task': 'inventory.reset_watchlist_notifications',
        'schedule': crontab(minute=0, hour=0),
    },
    'inventory-detect-dead-stock': {
        'task': 'inventory.detect_dead_stock',
        'schedule': crontab(minute=0, hour=0, day_of_week=0),
    },
}

# ── AUTH ───────────────────────────────────────────────────────
AUTH_USER_MODEL = 'auth_app.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
]

# ── JWT ────────────────────────────────────────────────────────
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(
        hours=env.int('JWT_ACCESS_TOKEN_LIFETIME_HOURS', default=1)
    ),
    'REFRESH_TOKEN_LIFETIME': timedelta(
        days=env.int('JWT_REFRESH_TOKEN_LIFETIME_DAYS', default=30)
    ),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': env('JWT_SECRET_KEY', default=SECRET_KEY),
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# ── DRF ────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'core.authentication.SoftJWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'core.pagination.StandardOffsetPagination',
    'PAGE_SIZE': 20,
    'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler',
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# ── CORS ───────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = env.list(
    'CORS_ALLOWED_ORIGINS',
    default=['http://localhost:3000', 'http://localhost:19006']
)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept', 'accept-encoding', 'authorization',
    'content-type', 'dnt', 'origin', 'user-agent',
    'x-csrftoken', 'x-requested-with',
]

# ── API DOCS (Spectacular) ─────────────────────────────────────
SPECTACULAR_SETTINGS = {
    'TITLE': 'NearSpot API',
    'DESCRIPTION': (
        "India's first hyperlocal video commerce platform.\n\n"
        "## How to Authenticate\n"
        "1. Expand **Auth → POST /auth/otp/send/** → click **Try it out** → click **Execute**\n"
        "   - Sample phone is pre-filled: `+919999999999`\n"
        "2. Expand **Auth → POST /auth/otp/verify/** → click **Try it out** → click **Execute**\n"
        "   - Sample phone + OTP `123456` are pre-filled\n"
        "3. Copy the `access` value from the response (long string starting with `eyJ...`)\n"
        "4. Click **Authorize** (lock icon, top right)\n"
        "5. Paste **just the token** in the Value field — do NOT add `Bearer ` prefix\n"
        "6. Click **Authorize** → **Close** — all protected endpoints are now unlocked\n\n"
        "> **Tip:** `persistAuthorization` is on — your token survives page refresh.\n\n"
        "## Dev Notes\n"
        "- Fixed OTP is always `123456` in dev mode — no real SMS sent\n"
        "- S3 uploads return mock URLs in dev — skip the real PUT and call confirm-upload directly\n"
        "- WebSocket endpoints (`/ws/...`) cannot be tested in Swagger — use Postman or wscat"
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayRequestDuration': True,
        'filter': True,
        'tryItOutEnabled': True,
        'defaultModelsExpandDepth': -1,
    },
    'APPEND_COMPONENTS': {
        'securitySchemes': {
            'jwtAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
                'description': 'Paste your access token here (without the "Bearer " prefix)',
            }
        }
    },
    'SECURITY': [{'jwtAuth': []}],
}

# ── AWS ────────────────────────────────────────────────────────
AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY', default='')
AWS_REGION = env('AWS_REGION', default='ap-south-1')
AWS_S3_BUCKET = env('AWS_S3_BUCKET', default='nearkart-media-dev')
AWS_CDN_DOMAIN = env('AWS_CDN_DOMAIN', default='')
AWS_PRESIGNED_URL_EXPIRY = env.int('AWS_PRESIGNED_URL_EXPIRY', default=900)
# S3 Transfer Acceleration — routes uploads to the nearest AWS edge node.
# Requires the bucket to have Transfer Acceleration enabled in the AWS console.
# 50–500% faster for users far from ap-south-1 (Mumbai).
# Cost: $0.004/GB extra. Enable only in production after enabling on the bucket.
AWS_S3_USE_ACCELERATE = env.bool('AWS_S3_USE_ACCELERATE', default=False)

# ── RAZORPAY ───────────────────────────────────────────────────
RAZORPAY_KEY_ID      = env('RAZORPAY_KEY_ID',      default='rzp_test_PLACEHOLDER')
RAZORPAY_KEY_SECRET  = env('RAZORPAY_KEY_SECRET',  default='PLACEHOLDER_SECRET')
RAZORPAY_WEBHOOK_SECRET = env('RAZORPAY_WEBHOOK_SECRET', default='PLACEHOLDER_WEBHOOK_SECRET')

# ── TWILIO ─────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID = env('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN = env('TWILIO_AUTH_TOKEN', default='')
TWILIO_FROM_NUMBER = env('TWILIO_FROM_NUMBER', default='')

# ── FIREBASE ───────────────────────────────────────────────────
FIREBASE_CREDENTIALS_JSON = env('FIREBASE_CREDENTIALS_JSON', default='')

# ── SENDGRID ───────────────────────────────────────────────────
SENDGRID_API_KEY = env('SENDGRID_API_KEY', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='hello@nearspot.in')
DEFAULT_FROM_NAME = env('DEFAULT_FROM_NAME', default='NearSpot')

# ── GOOGLE MAPS ────────────────────────────────────────────────
GOOGLE_MAPS_API_KEY = env('GOOGLE_MAPS_API_KEY', default='')

# ── RATE LIMITS ────────────────────────────────────────────────
OTP_SEND_RATE_LIMIT    = env.int('OTP_SEND_RATE_LIMIT',    default=5)
OTP_VERIFY_RATE_LIMIT  = env.int('OTP_VERIFY_RATE_LIMIT',  default=10)
VIDEO_UPLOAD_RATE_LIMIT = env.int('VIDEO_UPLOAD_RATE_LIMIT', default=10)

# ── UPLOAD DAILY LIMITS ─────────────────────────────────────────
# Per-vendor per-day upload caps enforced by UploadTracker (Redis Lua counter).
# 0 = unlimited. These are protection limits — BillingService enforces plan
# quotas (total videos/products stored) separately.
VIDEO_DAILY_UPLOAD_LIMIT = env.int('VIDEO_DAILY_UPLOAD_LIMIT', default=10)
PHOTO_DAILY_UPLOAD_LIMIT = env.int('PHOTO_DAILY_UPLOAD_LIMIT', default=50)

# ── DEV OTP BYPASS ─────────────────────────────────────────────
# When DEBUG=True these phones skip OTP rate limiting entirely so load
# tests and QA sessions can authenticate freely without hitting the
# 5-per-hour ceiling. Never populated in production (DEBUG=False).
DEV_BYPASS_PHONES: set[str] = set(env.list('DEV_BYPASS_PHONES', default=[])) if DEBUG else set()

# ── BUSINESS LOGIC CONSTANTS ───────────────────────────────────
BLACKLIST_INACTIVE_DAYS = env.int('BLACKLIST_INACTIVE_DAYS', default=30)
BLACKLIST_WARNING_DAY = env.int('BLACKLIST_WARNING_DAY', default=20)
BLACKLIST_FINAL_WARNING_DAY = env.int('BLACKLIST_FINAL_WARNING_DAY', default=27)
RESERVATION_HOLD_HOURS = env.int('RESERVATION_HOLD_HOURS', default=2)
VIDEO_MAX_DURATION_SECONDS = env.int('VIDEO_MAX_DURATION_SECONDS', default=60)
VIDEO_MAX_SIZE_MB = env.int('VIDEO_MAX_SIZE_MB', default=100)
VIDEO_EXPIRY_DAYS = env.int('VIDEO_EXPIRY_DAYS', default=30)

# ── STATIC / MEDIA ─────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Public-facing base URL — used to build absolute media URLs in dev (when S3 is not configured).
# Set to your machine's local IP in .env: SITE_URL=http://192.168.29.165
# In production this should be your domain: SITE_URL=https://api.nearspot.in
SITE_URL = env('SITE_URL', default='http://localhost')

# ── INTERNATIONALISATION ───────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# ── DEFAULT PK ─────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── LOGGING ────────────────────────────────────────────────────
_LOG_DIR = BASE_DIR.parent / 'logs'
try:
    _LOG_DIR.mkdir(exist_ok=True)
except PermissionError:
    import tempfile
    _LOG_DIR = Path(tempfile.mkdtemp(prefix='nearkart_logs_'))


def _rotating(filename: str, formatter: str = 'entity') -> dict:
    return {
        'class':       'logging.handlers.RotatingFileHandler',
        'filename':    str(_LOG_DIR / filename),
        'maxBytes':    10 * 1024 * 1024,  # rotate at 10 MB
        'backupCount': 7,                  # keep 7 compressed backups (~70 MB max per log)
        'encoding':    'utf-8',
        'formatter':   formatter,
    }


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        # Instagram-style: single JSON line per event — query with jq
        'json': {
            '()': 'core.logging.JsonFormatter',
        },
        # Human-readable key=value lines — for entity-specific log files
        'entity': {
            '()': 'core.logging.EntityFormatter',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style':  '{',
        },
    },
    'handlers': {
        'console': {
            'class':     'logging.StreamHandler',
            'formatter': 'simple',
        },
        # ── Global JSON stream (all events) ──────────────────────
        'app_file':         {**_rotating('app.log',          'json')},
        # ── Errors only (all apps, ERROR+) ───────────────────────
        'error_file':       {**_rotating('error.log'),       **{'level': 'ERROR'}},
        # ── Per-entity text logs ──────────────────────────────────
        'auth_file':         {**_rotating('auth.log')},
        'stores_file':       {**_rotating('stores.log')},
        'products_file':     {**_rotating('products.log')},
        'customers_file':    {**_rotating('customers.log')},
        'reservations_file': {**_rotating('reservations.log')},
        'videos_file':       {**_rotating('videos.log')},
        'billing_file':      {**_rotating('billing.log')},
        'requests_file':     {**_rotating('requests.log')},
        # ── Security & Performance (always WARNING+) ──────────────
        'security_file':       {**_rotating('security.log'),       **{'level': 'WARNING'}},
        'performance_file':    {**_rotating('performance.log'),    **{'level': 'WARNING'}},
        'client_events_file':  {**_rotating('client_events.log'),  **{'level': 'WARNING'}},
    },
    'root': {
        'handlers': ['console', 'error_file'],
        'level':    'WARNING',
    },
    'loggers': {
        'django': {
            'handlers':  ['console', 'error_file'],
            'level':     'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers':  ['console'],
            'level':     'DEBUG',
            'propagate': False,
        },
        'celery': {
            'handlers':  ['console'],
            'level':     'INFO',
            'propagate': False,
        },
        # ── Global JSON stream ────────────────────────────────────
        'nearkart.app': {
            'handlers':  ['app_file'],
            'level':     'DEBUG',
            'propagate': False,
        },
        # ── Entity-specific text loggers ──────────────────────────
        'nearkart.auth': {
            'handlers':  ['auth_file'],
            'level':     'DEBUG',
            'propagate': False,
        },
        'nearkart.stores': {
            'handlers':  ['stores_file'],
            'level':     'DEBUG',
            'propagate': False,
        },
        'nearkart.products': {
            'handlers':  ['products_file'],
            'level':     'DEBUG',
            'propagate': False,
        },
        'nearkart.customers': {
            'handlers':  ['customers_file'],
            'level':     'DEBUG',
            'propagate': False,
        },
        'nearkart.reservations': {
            'handlers':  ['reservations_file'],
            'level':     'DEBUG',
            'propagate': False,
        },
        'nearkart.videos': {
            'handlers':  ['videos_file'],
            'level':     'DEBUG',
            'propagate': False,
        },
        'nearkart.billing': {
            'handlers':  ['billing_file'],
            'level':     'DEBUG',
            'propagate': False,
        },
        'nearkart.requests': {
            'handlers':  ['requests_file'],
            'level':     'DEBUG',
            'propagate': False,
        },
        # ── Security: failed auth, 4xx anomalies, brute-force signals ─
        'nearkart.security': {
            'handlers':  ['security_file', 'error_file'],
            'level':     'WARNING',
            'propagate': False,
        },
        # ── Performance: slow requests, slow DB queries ───────────────
        'nearkart.performance': {
            'handlers':  ['performance_file'],
            'level':     'WARNING',
            'propagate': False,
        },
        # ── Client events: security events shipped from mobile app ────
        'nearkart.client_events': {
            'handlers':  ['client_events_file', 'security_file'],
            'level':     'WARNING',
            'propagate': False,
        },
    },
}

# ── SENTRY ─────────────────────────────────────────────────────
SENTRY_DSN = env('SENTRY_DSN', default='')
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(transaction_style='url'),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        environment=env('SENTRY_ENVIRONMENT', default='development'),
        traces_sample_rate=0.1,
        send_default_pii=False,
    )

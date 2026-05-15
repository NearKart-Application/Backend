"""
NearKart — Base Django Settings
Shared across all environments (development, staging, production)
"""
import os
from pathlib import Path
import environ
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration

# ── PATHS ──────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent

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
        'HOST': env('DB_HOST', default='postgres'),
        'PORT': env('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 60,
        'OPTIONS': {
            'connect_timeout': 10,
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
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# ── DRF ────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
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
    'TITLE': 'NearKart API',
    'DESCRIPTION': (
        "India's first hyperlocal video commerce platform.\n\n"
        "## Authentication\n"
        "1. Call **POST /auth/otp/send/** with your phone number\n"
        "2. Call **POST /auth/otp/verify/** with OTP `123456` (dev fixed OTP)\n"
        "3. Copy the `access` token from the response\n"
        "4. Click **Authorize** (top right), enter: `Bearer <paste token here>`\n"
        "5. All protected endpoints will now work"
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayRequestDuration': True,
        'filter': True,
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

# ── TWILIO ─────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID = env('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN = env('TWILIO_AUTH_TOKEN', default='')
TWILIO_FROM_NUMBER = env('TWILIO_FROM_NUMBER', default='')

# ── FIREBASE ───────────────────────────────────────────────────
FIREBASE_CREDENTIALS_JSON = env('FIREBASE_CREDENTIALS_JSON', default='')

# ── SENDGRID ───────────────────────────────────────────────────
SENDGRID_API_KEY = env('SENDGRID_API_KEY', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='hello@nearkart.in')
DEFAULT_FROM_NAME = env('DEFAULT_FROM_NAME', default='NearKart')

# ── GOOGLE MAPS ────────────────────────────────────────────────
GOOGLE_MAPS_API_KEY = env('GOOGLE_MAPS_API_KEY', default='')

# ── RATE LIMITS ────────────────────────────────────────────────
OTP_SEND_RATE_LIMIT = env.int('OTP_SEND_RATE_LIMIT', default=5)
OTP_VERIFY_RATE_LIMIT = env.int('OTP_VERIFY_RATE_LIMIT', default=10)
VIDEO_UPLOAD_RATE_LIMIT = env.int('VIDEO_UPLOAD_RATE_LIMIT', default=10)

# ── BUSINESS LOGIC CONSTANTS ───────────────────────────────────
BLACKLIST_INACTIVE_DAYS = env.int('BLACKLIST_INACTIVE_DAYS', default=30)
BLACKLIST_WARNING_DAY = env.int('BLACKLIST_WARNING_DAY', default=20)
BLACKLIST_FINAL_WARNING_DAY = env.int('BLACKLIST_FINAL_WARNING_DAY', default=27)
RESERVATION_HOLD_HOURS = env.int('RESERVATION_HOLD_HOURS', default=2)
VIDEO_MAX_DURATION_SECONDS = env.int('VIDEO_MAX_DURATION_SECONDS', default=60)
STORY_MAX_DURATION_SECONDS = env.int('STORY_MAX_DURATION_SECONDS', default=30)
VIDEO_MAX_SIZE_MB = env.int('VIDEO_MAX_SIZE_MB', default=100)
STORY_MAX_SIZE_MB = env.int('STORY_MAX_SIZE_MB', default=50)
STORY_EXPIRY_HOURS = env.int('STORY_EXPIRY_HOURS', default=24)
VIDEO_EXPIRY_DAYS = env.int('VIDEO_EXPIRY_DAYS', default=30)

# ── STATIC / MEDIA ─────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ── INTERNATIONALISATION ───────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# ── DEFAULT PK ─────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── LOGGING ────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console'],
            'level': 'INFO',
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

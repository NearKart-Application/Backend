"""
NearKart — Docker Testing Settings
Uses the real PostGIS database inside Docker (creates an isolated test DB).
Run with: DJANGO_SETTINGS_MODULE=config.settings.testing_docker pytest  (inside docker compose run)
"""
from .testing import *  # noqa — inherits all stubs/speed-ups

# Override with the real PostGIS engine and Docker Postgres connection
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME':     'nearkart',
        'USER':     'nearkart',
        'PASSWORD': 'nearkart_dev_password_change_in_prod',
        'HOST':     'postgres',
        'PORT':     '5432',
        'TEST': {
            'NAME': 'test_nearkart',
        },
    }
}

# Use real migrations so PostGIS + pg_trgm extensions are created correctly
MIGRATION_MODULES = {}

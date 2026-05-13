"""
NearKart — Celery Configuration
All scheduled tasks (Beat) and async worker tasks
"""
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

app = Celery('nearkart')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# ── BEAT SCHEDULE ──────────────────────────────────────────────
app.conf.beat_schedule = {

    # 🔴 BLACKLIST ENGINE — midnight daily
    'check-inactive-products': {
        'task': 'apps.blacklist.tasks.check_inactive_products',
        'schedule': crontab(hour=0, minute=0),
    },

    # 🎬 VIDEO AUTO-DELETE — 1am daily
    'delete-expired-videos': {
        'task': 'apps.videos.tasks.delete_expired_videos',
        'schedule': crontab(hour=1, minute=0),
    },

    # 📊 ANALYTICS AGGREGATION — 3am daily
    'aggregate-daily-analytics': {
        'task': 'apps.analytics.tasks.aggregate_daily_stats',
        'schedule': crontab(hour=3, minute=0),
    },

    # 📅 RESERVATION EXPIRY — every 15 minutes
    'expire-reservations': {
        'task': 'apps.reservations.tasks.expire_reservations',
        'schedule': crontab(minute='*/15'),
    },

    # 🏪 STORE OPEN/CLOSE STATUS — every 30 minutes
    'update-store-open-status': {
        'task': 'apps.stores.tasks.update_all_store_statuses',
        'schedule': crontab(minute='*/30'),
    },

    # 📧 WEEKLY ANALYTICS DIGEST — Monday 9am IST
    'send-weekly-digest': {
        'task': 'apps.analytics.tasks.send_weekly_digest_emails',
        'schedule': crontab(hour=9, minute=0, day_of_week=1),
    },
}

app.conf.timezone = 'Asia/Kolkata'

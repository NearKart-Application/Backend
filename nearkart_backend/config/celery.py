"""
NearKart — Celery Configuration
All scheduled tasks (Beat) and async worker tasks
"""
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

app = Celery('nearkart')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Beat schedule is defined in settings/base.py under CELERY_BEAT_SCHEDULE.
# Do NOT add app.conf.beat_schedule here — it creates a second source that
# duplicates tasks and causes double-firing with DatabaseScheduler.

app.conf.timezone = 'Asia/Kolkata'

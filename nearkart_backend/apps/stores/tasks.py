"""
NearKart — Stores Celery Tasks
update_all_store_statuses: runs every 30 min, auto open/close based on StoreHours.
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name='stores.update_all_store_statuses')
def update_all_store_statuses():
    """
    Runs every 30 minutes via Celery Beat.
    For every active store that has StoreHours defined, set is_open=True if current
    IST time falls within today's hours, False otherwise.
    Stores with no hours defined are left untouched (vendor toggles manually).
    """
    from django.utils import timezone
    from django.db.models import Prefetch
    from .models import Store, StoreHours

    now_ist = timezone.localtime(timezone.now())
    today   = now_ist.weekday()      # 0 = Monday … 6 = Sunday
    now_t   = now_ist.time()

    # Only stores that have at least one StoreHours row
    stores_with_hours = Store.objects.filter(
        is_active=True,
        hours__day=today,
    ).prefetch_related(
        Prefetch('hours', queryset=StoreHours.objects.filter(day=today), to_attr='today_hours')
    ).distinct()

    opened = closed = skipped = 0
    for store in stores_with_hours:
        today_hours = store.today_hours
        if not today_hours:
            skipped += 1
            continue

        hours = today_hours[0]
        if hours.is_closed:
            should_be_open = False
        else:
            should_be_open = hours.open_time <= now_t < hours.close_time

        if store.is_open != should_be_open:
            Store.objects.filter(pk=store.pk).update(is_open=should_be_open)
            if should_be_open:
                opened += 1
                # Notify followers the store just opened
                try:
                    from apps.notifications.services import NotificationService
                    followers = [f.user for f in store.followers.select_related('user').all()]
                    NotificationService.notify_store_opened(followers, store.name, str(store.id))
                except Exception as exc:
                    logger.warning('update_store_statuses: notification failed for store %s: %s', store.id, exc)
            else:
                closed += 1

    logger.info('[stores] open/close update: opened=%d closed=%d skipped=%d', opened, closed, skipped)
    return {'opened': opened, 'closed': closed, 'skipped': skipped}

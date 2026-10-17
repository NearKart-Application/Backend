"""
NearKart — Reservation Celery Tasks
expire_reservations: runs hourly, marks stale pending holds as expired.
notify_1day_expiry:  runs daily at 8 AM, sends push+in-app for holds expiring in next 24 h.
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='reservations.expire_reservations', max_retries=2, default_retry_delay=60, time_limit=300, soft_time_limit=270)
def expire_reservations(self):
    try:
        from .services import ReservationService
        count = ReservationService.expire_pending()
        logger.info('[reservations] expired %d reservation(s)', count)
        return {'expired': count}
    except Exception as exc:
        logger.error('[reservations] expire_reservations failed, retrying: %s', exc)
        raise self.retry(exc=exc)


@shared_task(name='reservations.notify_30min_expiry', time_limit=120, soft_time_limit=100)
def notify_30min_expiry():
    """Runs every 15 min. Notifies customers whose reservation expires in 25–35 min."""
    from django.core.cache import cache
    from django.utils import timezone
    from datetime import timedelta
    from .models import Reservation
    from apps.notifications.services import NotificationService

    now = timezone.now()
    window_start = now + timedelta(minutes=25)
    window_end   = now + timedelta(minutes=35)

    qs = Reservation.objects.filter(
        status__in=['pending', 'confirmed'],
        expires_at__gte=window_start,
        expires_at__lte=window_end,
    ).select_related('customer', 'product', 'product__store')

    notified = 0
    for res in qs:
        cache_key = f'notified_30min_{res.id}'
        if cache.get(cache_key):
            continue  # already notified this reservation in the current window
        try:
            NotificationService.notify_reservation_expiring_soon(
                customer       = res.customer,
                store_name     = res.product.store.name,
                reservation_id = str(res.id),
                product_name   = res.product.name,
                time_label     = 'soon',
                time_body      = '~30 minutes',
            )
            cache.set(cache_key, True, timeout=7200)  # 2-hour TTL covers the expiry window
            notified += 1
        except Exception as exc:
            logger.warning('[notify_30min_expiry] failed for res %s: %s', res.id, exc)

    logger.info('[reservations] sent %d 30-min expiry notification(s)', notified)
    return {'notified': notified}


@shared_task(name='reservations.notify_1day_expiry', time_limit=300, soft_time_limit=270)
def notify_1day_expiry():
    from django.utils import timezone
    from datetime import timedelta
    from .models import Reservation
    from apps.notifications.services import NotificationService

    now = timezone.now()
    window_start = now + timedelta(hours=20)   # between 20 h from now …
    window_end   = now + timedelta(hours=28)   # … and 28 h from now (centred on 24 h)

    qs = Reservation.objects.filter(
        status='pending',
        expires_at__gte=window_start,
        expires_at__lte=window_end,
    ).select_related('customer', 'product', 'product__store')

    notified = 0
    for res in qs:
        try:
            NotificationService.notify_reservation_expiring_soon(
                customer       = res.customer,
                store_name     = res.product.store.name,
                reservation_id = str(res.id),
                product_name   = res.product.name,
            )
            notified += 1
        except Exception as exc:
            logger.warning('[notify_1day_expiry] failed for res %s: %s', res.id, exc)

    logger.info('[reservations] sent %d expiry-soon notification(s)', notified)
    return {'notified': notified}

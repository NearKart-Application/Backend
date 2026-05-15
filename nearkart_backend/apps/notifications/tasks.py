"""
NearKart — Notifications Celery Tasks
"""
import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task(name='notifications.notify_expiring_subscriptions', time_limit=300, soft_time_limit=270)
def notify_expiring_subscriptions():
    """
    Runs daily at 9 AM. Notifies vendors whose subscription expires in exactly 3 days.
    """
    from apps.billing.models import Subscription
    from .services import NotificationService

    window_start = timezone.now() + timedelta(days=2, hours=23)
    window_end   = timezone.now() + timedelta(days=3, hours=1)

    expiring = Subscription.objects.filter(
        is_active=True,
        expires_at__gte=window_start,
        expires_at__lte=window_end,
    ).select_related('store__owner', 'plan')

    count = 0
    for sub in expiring:
        days_left = (sub.expires_at - timezone.now()).days + 1
        NotificationService.notify_subscription_expiring(
            vendor=sub.store.owner,
            store_name=sub.store.name,
            days_left=days_left,
        )
        count += 1

    logger.info(f'[notifications] expiring subscriptions notified: {count}')
    return {'notified': count}


@shared_task(name='notifications.notify_expired_subscriptions', time_limit=300, soft_time_limit=270)
def notify_expired_subscriptions():
    """
    Runs daily at 9 AM. Notifies vendors whose subscription expired in the last 24h.
    """
    from apps.billing.models import Subscription
    from .services import NotificationService

    since = timezone.now() - timedelta(hours=24)

    recently_expired = Subscription.objects.filter(
        is_active=False,
        expires_at__gte=since,
        expires_at__lt=timezone.now(),
    ).select_related('store__owner')

    count = 0
    for sub in recently_expired:
        NotificationService.notify_subscription_expired(
            vendor=sub.store.owner,
            store_name=sub.store.name,
        )
        count += 1

    logger.info(f'[notifications] expired subscriptions notified: {count}')
    return {'notified': count}

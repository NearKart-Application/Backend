"""
NearKart — Billing Celery Tasks
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='billing.expire_subscriptions', max_retries=2, default_retry_delay=60)
def expire_subscriptions(self):
    """
    Runs daily via Celery Beat.
    Marks all subscriptions past their expiry date as inactive.
    """
    try:
        from .services import BillingService
        count = BillingService.expire_overdue_subscriptions()
        logger.info('[billing] expired %d subscription(s)', count)
        return {'expired': count}
    except Exception as exc:
        logger.error('[billing] expire_subscriptions failed, retrying: %s', exc)
        raise self.retry(exc=exc)


@shared_task(name='billing.notify_expiring_subscriptions')
def notify_expiring_subscriptions():
    """
    Runs daily via Celery Beat.
    Notifies vendors whose subscription expires in exactly 7 or 3 days.
    """
    from django.utils import timezone
    from datetime import timedelta
    from .models import Subscription
    from apps.notifications.services import NotificationService

    now = timezone.now()
    notified = 0

    for days_left in (7, 3):
        window_start = now + timedelta(days=days_left)
        window_end   = window_start + timedelta(hours=24)

        expiring = Subscription.objects.filter(
            is_active=True,
            expires_at__gte=window_start,
            expires_at__lt=window_end,
        ).select_related('store__owner', 'plan')

        for sub in expiring:
            vendor = sub.store.owner
            if not vendor:
                continue
            try:
                NotificationService.notify_subscription_expiring(
                    vendor=vendor,
                    store_name=sub.store.name,
                    days_left=days_left,
                )
                notified += 1
            except Exception as exc:
                logger.warning('[billing] expiry notify failed for store %s: %s', sub.store.id, exc)

    logger.info('[billing] expiry notifications sent: %d', notified)
    return {'notified': notified}

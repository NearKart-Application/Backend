"""
NearKart — Billing Celery Tasks
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name='billing.expire_subscriptions')
def expire_subscriptions():
    """
    Runs daily via Celery Beat.
    Marks all subscriptions past their expiry date as inactive.
    """
    from .services import BillingService
    count = BillingService.expire_overdue_subscriptions()
    logger.info(f'[billing] expired {count} subscription(s)')
    return {'expired': count}

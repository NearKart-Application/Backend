"""
NearKart — Notifications Celery Tasks
"""
import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task(name='notifications.send_weekly_digest', time_limit=600, soft_time_limit=540)
def send_weekly_digest():
    """
    Runs every Monday at 9 AM. Sends a weekly activity digest to all active vendors.
    Covers: reservations, revenue, new followers, and top product for the last 7 days.
    """
    from apps.stores.models import Store, Invoice
    from apps.reservations.models import Reservation
    from .services import NotificationService
    from .models import NotificationType

    week_start = timezone.now() - timedelta(days=7)
    count = 0

    for store in Store.objects.filter(is_active=True).select_related('owner'):
        try:
            reservations = Reservation.objects.filter(
                store=store, created_at__gte=week_start
            )
            total_reservations = reservations.count()
            completed = reservations.filter(status='completed').count()

            from django.db.models import Sum as _Sum
            invoice_total = float(Invoice.objects.filter(
                store=store, created_at__gte=week_start,
            ).aggregate(t=_Sum('total'))['t'] or 0)

            new_followers = store.followers.filter(created_at__gte=week_start).count() if hasattr(store, 'followers') else 0

            body_parts = [f'{total_reservations} reservations ({completed} completed)']
            if invoice_total > 0:
                body_parts.append(f'₹{invoice_total:,.0f} in invoices')
            if new_followers > 0:
                body_parts.append(f'{new_followers} new follower{"s" if new_followers != 1 else ""}')

            if not body_parts:
                continue

            NotificationService.send(
                recipient=store.owner,
                notification_type=NotificationType.WEEKLY_DIGEST,
                title=f'📊 {store.name} — Weekly Summary',
                body='Last 7 days: ' + ' · '.join(body_parts),
                data={'store_id': str(store.id), 'type': 'weekly_digest'},
            )
            count += 1
        except Exception as exc:
            logger.warning('[weekly_digest] store %s failed: %s', store.id, exc)

    logger.info('[notifications] weekly digest sent to %d vendors', count)
    return {'sent': count}


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

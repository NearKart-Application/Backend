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

    to_open  = []
    to_close = []
    skipped  = 0

    for store in stores_with_hours:
        today_hours = store.today_hours
        if not today_hours:
            skipped += 1
            continue

        hours = today_hours[0]
        should_be_open = (
            False if hours.is_closed
            else hours.open_time <= now_t < hours.close_time
        )

        if store.is_open != should_be_open:
            if should_be_open:
                to_open.append(store)
            else:
                to_close.append(store)

    if to_open:
        Store.objects.filter(pk__in=[s.pk for s in to_open]).update(is_open=True)
        for store in to_open:
            try:
                from apps.notifications.services import NotificationService
                followers = [f.user for f in store.followers.select_related('user').all()]
                NotificationService.notify_store_opened(followers, store.name, str(store.id))
            except Exception as exc:
                logger.warning('update_store_statuses: notification failed for store %s: %s', store.id, exc)

    if to_close:
        Store.objects.filter(pk__in=[s.pk for s in to_close]).update(is_open=False)

    opened = len(to_open)
    closed = len(to_close)
    logger.info('[stores] open/close update: opened=%d closed=%d skipped=%d', opened, closed, skipped)
    return {'opened': opened, 'closed': closed, 'skipped': skipped}


@shared_task(name='stores.purge_store_questions')
def purge_store_questions():
    """
    Daily Q&A retention cleanup.

    - Answered questions are deleted 30 days after they were answered (silent —
      the customer already received the reply).
    - Unanswered questions are deleted 90 days after they were asked. Two days
      before that (asked 88–89 days ago), both the customer and the vendor are
      notified so the vendor still has a chance to reply. On deletion the customer
      is told it was removed without a reply and invited to ask again.

    The 88–89 day warning window (mirroring the video-expiry flow) means a daily
    run notifies each question exactly once without needing a per-row flag.
    """
    from datetime import timedelta
    from django.utils import timezone
    from .models import StoreQuestion
    from apps.notifications.services import NotificationService

    now = timezone.now()

    # 1) Answered → delete 30 days after being answered
    answered_deleted, _ = StoreQuestion.objects.filter(
        answered_at__isnull=False,
        answered_at__lt=now - timedelta(days=30),
    ).delete()

    # 2) Unanswered → warn customer + vendor 2 days before the 90-day deletion
    warn_qs = (
        StoreQuestion.objects
        .filter(
            answered_at__isnull=True,
            created_at__lte=now - timedelta(days=88),
            created_at__gt=now - timedelta(days=89),
        )
        .select_related('store', 'store__owner', 'user')
    )
    warned = 0
    for q in warn_qs:
        try:
            NotificationService.notify_question_expiring_customer(
                q.user, q.store.name, str(q.store_id), str(q.id),
            )
            NotificationService.notify_question_expiring_vendor(
                q.store.owner, q.store.name,
                getattr(q.user, 'full_name', None) or 'A customer',
                str(q.store_id), str(q.id),
            )
            warned += 1
        except Exception as exc:
            logger.error('purge_store_questions: warn failed for %s — %s', q.id, exc)

    # 3) Unanswered → delete 90 days after asked, notifying the customer first
    expire_qs = (
        StoreQuestion.objects
        .filter(answered_at__isnull=True, created_at__lt=now - timedelta(days=90))
        .select_related('store', 'user')
    )
    expired = 0
    for q in list(expire_qs):
        try:
            NotificationService.notify_question_deleted(q.user, q.store.name, str(q.store_id))
        except Exception as exc:
            logger.error('purge_store_questions: delete-notify failed for %s — %s', q.id, exc)
        q.delete()
        expired += 1

    logger.info(
        '[stores] purge_store_questions: answered_deleted=%s warned=%s expired=%s',
        answered_deleted, warned, expired,
    )
    return {'answered_deleted': answered_deleted, 'warned': warned, 'expired': expired}

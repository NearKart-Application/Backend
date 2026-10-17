"""
NearKart — Analytics Celery Tasks
aggregate_daily_stats:      runs 3am daily, computes performance_score for each store.
send_weekly_digest_emails:  runs Monday 9am IST, sends weekly in-app digest to vendors.
snapshot_daily_analytics:   runs 1am daily, writes DailyAnalyticsSnapshot rows for trend charts.
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='analytics.aggregate_daily_stats', max_retries=2, default_retry_delay=120)
def aggregate_daily_stats(self):
    """
    Runs at 3am daily via Celery Beat.
    Computes a performance_score (0–100) for every active store and saves it.

    Score formula (all normalised to 100):
      40% — avg star rating (store reviews, scale 1-5 → 0-40)
      30% — follower count  (log-scaled, capped at 30)
      20% — active product count (capped at 20)
      10% — review count    (log-scaled, capped at 10)
    """
    try:
        import math
        from django.db.models import Avg, Count
        from apps.stores.models import Store

        stores = Store.objects.filter(is_active=True).annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews', distinct=True),
            follower_count=Count('followers', distinct=True),
            product_count=Count('products', distinct=True),
        )

        updated = 0
        for store in stores:
            avg_rating     = float(store.avg_rating or 0)
            review_count   = store.review_count   or 0
            follower_count = store.follower_count or 0
            product_count  = store.product_count  or 0

            rating_score   = (avg_rating / 5.0) * 40
            follower_score = min(math.log1p(follower_count) / math.log1p(500) * 30, 30)
            product_score  = min(product_count / 50 * 20, 20)
            review_score   = min(math.log1p(review_count) / math.log1p(100) * 10, 10)

            score = round(rating_score + follower_score + product_score + review_score, 2)
            Store.objects.filter(pk=store.pk).update(performance_score=score)
            updated += 1

        logger.info('[analytics] daily stats aggregated: %d stores updated', updated)
        return {'stores_updated': updated}
    except Exception as exc:
        logger.error('[analytics] aggregate_daily_stats failed, retrying: %s', exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, name='analytics.snapshot_daily_analytics', max_retries=2, default_retry_delay=120)
def snapshot_daily_analytics(self):
    """
    Runs 1am daily. Writes one DailyAnalyticsSnapshot row per active store for yesterday.
    Idempotent — uses update_or_create so re-runs don't duplicate.
    """
    try:
        import datetime
        from decimal import Decimal
        from django.db.models import Count, Sum, Q
        from django.utils import timezone
        from apps.stores.models import Store
        from apps.reservations.models import Reservation, ReservationStatus
        from .models import DailyAnalyticsSnapshot

        yesterday = (timezone.now() - datetime.timedelta(days=1)).date()
        stores = Store.objects.filter(is_active=True)

        updated = 0
        for store in stores:
            res_qs = Reservation.objects.filter(store=store, created_at__date=yesterday)
            completed_qs = res_qs.filter(status=ReservationStatus.COMPLETED)
            reservation_count = res_qs.count()
            completed_count = completed_qs.count()
            revenue = completed_qs.aggregate(
                total=Sum('actual_selling_price')
            )['total'] or Decimal('0')

            follower_count = store.followers.count()
            product_count = store.products.filter(status='active').count()
            video_view_count = store.videos.aggregate(s=Sum('view_count'))['s'] or 0

            # New customers: customers whose first-ever reservation with this store was yesterday
            new_customer_count = completed_qs.exclude(
                customer__in=Reservation.objects.filter(
                    store=store, created_at__date__lt=yesterday
                ).values('customer')
            ).values('customer').distinct().count()

            DailyAnalyticsSnapshot.objects.update_or_create(
                store=store,
                snapshot_date=yesterday,
                defaults={
                    'reservation_count': reservation_count,
                    'completed_count': completed_count,
                    'revenue': revenue,
                    'follower_count': follower_count,
                    'product_count': product_count,
                    'video_view_count': video_view_count,
                    'new_customer_count': new_customer_count,
                },
            )
            updated += 1

        logger.info('[analytics] snapshot_daily_analytics: %d stores snapshotted for %s', updated, yesterday)
        return {'stores_snapshotted': updated, 'date': str(yesterday)}
    except Exception as exc:
        logger.error('[analytics] snapshot_daily_analytics failed: %s', exc)
        raise self.retry(exc=exc)


@shared_task(name='analytics.send_weekly_digest_emails')
def send_weekly_digest_emails():
    """
    Runs Monday 9am IST via Celery Beat.
    Sends an in-app notification to every active vendor with their weekly store stats.
    """
    from django.db.models import Avg, Count
    from apps.stores.models import Store
    from apps.notifications.services import NotificationService

    stores = Store.objects.filter(is_active=True).select_related('owner').annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews', distinct=True),
        follower_count=Count('followers', distinct=True),
        product_count=Count('products', distinct=True),
    )

    sent = skipped = 0
    for store in stores:
        vendor = store.owner
        if not vendor:
            skipped += 1
            continue

        avg_rating     = round(float(store.avg_rating or 0), 1)
        followers      = store.follower_count or 0
        products       = store.product_count  or 0
        reviews        = store.review_count   or 0
        score          = store.performance_score

        try:
            NotificationService.send_bulk(
                recipients=[vendor],
                notification_type='weekly_digest',
                title='Your Weekly Store Summary',
                body=(
                    f'{store.name}: {followers} followers · {products} products · '
                    f'{reviews} reviews · ⭐ {avg_rating} · Score {score:.0f}/100'
                ),
                data={'store_id': str(store.id), 'type': 'weekly_digest'},
            )
            sent += 1
        except Exception as exc:
            logger.warning('[analytics] weekly digest failed for store %s: %s', store.id, exc)
            skipped += 1

    logger.info('[analytics] weekly digest: sent=%d skipped=%d', sent, skipped)
    return {'sent': sent, 'skipped': skipped}

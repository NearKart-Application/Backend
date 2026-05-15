"""
Tests — Celery Tasks
Covers: expire subscriptions, expire reservations, notify/delete expiring videos
"""
import pytest
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta


# ── Billing: Expire Subscriptions ─────────────────────────────────────────────

@pytest.mark.django_db
def test_expire_subscriptions_task(store, plan_basic):
    from apps.billing.models import Subscription
    sub = Subscription.objects.create(
        store=store, plan=plan_basic,
        started_at=timezone.now() - timedelta(days=31),
        expires_at=timezone.now() - timedelta(days=1),
        is_active=True,
    )
    from apps.billing.tasks import expire_subscriptions
    expire_subscriptions()
    sub.refresh_from_db()
    assert sub.is_active is False


@pytest.mark.django_db
def test_active_subscription_not_expired(store, plan_basic):
    from apps.billing.models import Subscription
    sub = Subscription.objects.create(
        store=store, plan=plan_basic,
        started_at=timezone.now(),
        expires_at=timezone.now() + timedelta(days=29),
        is_active=True,
    )
    from apps.billing.tasks import expire_subscriptions
    expire_subscriptions()
    sub.refresh_from_db()
    assert sub.is_active is True


# ── Reservations: Expire ───────────────────────────────────────────────────────

@pytest.mark.django_db
def test_expire_old_reservations(customer, store):
    from apps.products.models import Product
    from apps.reservations.models import Reservation
    product = Product.objects.create(
        store=store, name='Hold Me', price='100.00',
        category='fashion', is_available=True,
    )
    r = Reservation.objects.create(
        customer=customer, product=product, store=store,
        status=Reservation.STATUS_PENDING, quantity=1,
    )
    r.created_at = timezone.now() - timedelta(hours=3)
    r.save(update_fields=['created_at'])

    from apps.reservations.tasks import expire_reservations
    expire_reservations()
    r.refresh_from_db()
    assert r.status == Reservation.STATUS_EXPIRED


# ── Videos: Notify Expiring ───────────────────────────────────────────────────

@pytest.mark.django_db
def test_notify_expiring_videos_task(store, vendor_user):
    from apps.videos.models import Video
    from apps.notifications.models import Notification, NotificationType

    video = Video.objects.create(
        store=store, title='Expiring Soon Video',
        status=Video.STATUS_READY, is_visible=True,
        location=store.location,
        raw_s3_key='videos/raw/test/original.mp4',
        expires_at=timezone.now() + timedelta(hours=25),
    )

    from apps.videos.tasks import notify_expiring_videos
    count = notify_expiring_videos()
    assert count >= 1
    assert Notification.objects.filter(
        recipient=vendor_user,
        notification_type=NotificationType.VIDEO_EXPIRING_SOON,
    ).exists()


@pytest.mark.django_db
def test_notify_expiring_videos_not_yet_due(store):
    from apps.videos.models import Video
    from apps.notifications.models import Notification, NotificationType

    Video.objects.create(
        store=store, title='Far Future Video',
        status=Video.STATUS_READY, is_visible=True,
        location=store.location,
        expires_at=timezone.now() + timedelta(days=20),
    )

    from apps.videos.tasks import notify_expiring_videos
    count = notify_expiring_videos()
    assert count == 0


# ── Videos: Delete Expired ────────────────────────────────────────────────────

@pytest.mark.django_db
def test_delete_expired_videos_task(store):
    from apps.videos.models import Video

    video = Video.objects.create(
        store=store, title='Expired Video',
        status=Video.STATUS_READY, is_visible=True,
        location=store.location,
        expires_at=timezone.now() - timedelta(hours=1),
    )

    from apps.videos.tasks import delete_expired_videos
    count = delete_expired_videos()
    assert count >= 1
    video.refresh_from_db()
    assert video.status == Video.STATUS_EXPIRED
    assert video.is_visible is False


@pytest.mark.django_db
def test_delete_expired_leaves_active_videos(store):
    from apps.videos.models import Video

    video = Video.objects.create(
        store=store, title='Active Video',
        status=Video.STATUS_READY, is_visible=True,
        location=store.location,
        expires_at=timezone.now() + timedelta(days=15),
    )

    from apps.videos.tasks import delete_expired_videos
    delete_expired_videos()
    video.refresh_from_db()
    assert video.status == Video.STATUS_READY
    assert video.is_visible is True


# ── Notifications: Subscription Alerts ───────────────────────────────────────

@pytest.mark.django_db
def test_notify_expiring_subscriptions_task(store, plan_basic, vendor_user):
    from apps.billing.models import Subscription
    from apps.notifications.models import Notification, NotificationType

    Subscription.objects.create(
        store=store, plan=plan_basic,
        started_at=timezone.now() - timedelta(days=28),
        expires_at=timezone.now() + timedelta(days=2),
        is_active=True,
    )

    from apps.notifications.tasks import notify_expiring_subscriptions
    notify_expiring_subscriptions()
    assert Notification.objects.filter(
        recipient=vendor_user,
        notification_type=NotificationType.SUBSCRIPTION_EXPIRING,
    ).exists()

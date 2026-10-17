"""
Tests — Notifications Module
Covers: inbox list, unread count, mark read, mark all read, device token
"""
import pytest
from apps.notifications.models import Notification, NotificationType


BASE = '/api/v1/notifications'


@pytest.fixture
def notif(db, customer):
    return Notification.objects.create(
        recipient=customer,
        notification_type=NotificationType.NEW_MESSAGE,
        title='New message',
        body='You have a message.',
        data={'conversation_id': 'abc'},
        is_read=False,
    )


@pytest.fixture
def read_notif(db, customer):
    return Notification.objects.create(
        recipient=customer,
        notification_type=NotificationType.VIDEO_LIKED,
        title='Liked',
        body='Someone liked your video.',
        is_read=True,
    )


# ── Inbox ─────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_inbox_returns_notifications(customer_client, notif):
    response = customer_client.get(f'{BASE}/')
    assert response.status_code == 200
    results = response.json().get('results', response.json())
    assert any(n['title'] == 'New message' for n in (results if isinstance(results, list) else []))


@pytest.mark.django_db
def test_inbox_requires_auth(anon_client):
    response = anon_client.get(f'{BASE}/')
    assert response.status_code == 401


@pytest.mark.django_db
def test_inbox_only_own_notifications(customer_client, vendor_user):
    Notification.objects.create(
        recipient=vendor_user,
        notification_type=NotificationType.WALLET_TOPUP,
        title='Vendor notif', body='Not yours.',
    )
    response = customer_client.get(f'{BASE}/')
    results = response.json().get('results', response.json())
    assert all(n['title'] != 'Vendor notif' for n in (results if isinstance(results, list) else []))


# ── Unread Count ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_unread_count(customer_client, notif, read_notif):
    response = customer_client.get(f'{BASE}/unread-count/')
    assert response.status_code == 200
    assert response.json()['unread_count'] == 1


@pytest.mark.django_db
def test_unread_count_zero_when_all_read(customer_client, read_notif):
    response = customer_client.get(f'{BASE}/unread-count/')
    assert response.json()['unread_count'] == 0


# ── Mark Read ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_mark_notification_read(customer_client, notif):
    response = customer_client.post(f'{BASE}/{notif.id}/read/')
    assert response.status_code == 200
    notif.refresh_from_db()
    assert notif.is_read is True


@pytest.mark.django_db
def test_mark_other_users_notification_read(vendor_client, notif):
    response = vendor_client.post(f'{BASE}/{notif.id}/read/')
    assert response.status_code == 404


# ── Mark All Read ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_mark_all_read(customer_client, customer, notif):
    Notification.objects.create(
        recipient=customer,
        notification_type=NotificationType.NEW_FOLLOWER,
        title='New follower', body='Someone followed you.', is_read=False,
    )
    response = customer_client.post(f'{BASE}/read-all/')
    assert response.status_code == 200
    assert Notification.objects.filter(recipient=customer, is_read=False).count() == 0


# ── Device Token ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_register_device_token_via_notifications(customer_client, customer):
    response = customer_client.post(f'{BASE}/device-token/', {
        'fcm_token': 'notif-fcm-tok-001',
        'device_type': 'android',
    })
    assert response.status_code in (200, 201)


# ── Notification Service ──────────────────────────────────────────────────────

@pytest.mark.django_db
def test_notification_service_creates_record(customer):
    from apps.notifications.services import NotificationService
    notif = NotificationService.notify_new_message(customer, 'Vendor X', 'conv-123')
    assert Notification.objects.filter(
        recipient=customer,
        notification_type=NotificationType.NEW_MESSAGE,
    ).exists()


@pytest.mark.django_db
def test_video_expiring_soon_notification(vendor_user):
    from apps.notifications.services import NotificationService
    NotificationService.notify_video_expiring_soon(
        vendor_user, 'Summer Sale', 'vid-001', '2026-06-14T00:00:00+05:30'
    )
    notif = Notification.objects.get(recipient=vendor_user,
                                      notification_type=NotificationType.VIDEO_EXPIRING_SOON)
    assert notif.data['action'] == 'download_prompt'
    assert notif.data['video_id'] == 'vid-001'

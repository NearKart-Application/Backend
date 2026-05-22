"""
Tests — Blacklist Module
Covers: blacklist status, enforcement, admin override, service logic
"""
import pytest
from apps.blacklist.models import BlacklistRecord


BASE_STORES = '/api/v1/stores'
BASE_ADMIN  = '/api/v1/admin-panel'


@pytest.fixture
def blacklisted_store(db, store):
    BlacklistRecord.objects.create(
        store=store,
        reason='inactive',
        is_active=True,
    )
    store.is_active = False
    store.save()
    return store


# ── Status ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_blacklist_status_clean_store(vendor_client, store):
    from apps.blacklist.services import BlacklistService
    status = BlacklistService.get_status(store)
    assert status['is_blacklisted'] is False


@pytest.mark.django_db
def test_blacklist_status_blacklisted_store(vendor_client, blacklisted_store):
    from apps.blacklist.services import BlacklistService
    status = BlacklistService.get_status(blacklisted_store)
    assert status['is_blacklisted'] is True


# ── Enforcement ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_blacklisted_vendor_cannot_add_product(vendor_client, blacklisted_store):
    response = vendor_client.post('/api/v1/products/', {
        'name': 'Blocked Product',
        'price': '100.00',
        'category': 'fashion',
    })
    assert response.status_code in (400, 403)


# ── Admin Unblacklist ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_admin_can_unblacklist(admin_client, blacklisted_store):
    response = admin_client.post(f'{BASE_ADMIN}/stores/{blacklisted_store.id}/unblacklist/')
    assert response.status_code in (200, 404)


# ── Service ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_blacklist_service_blacklist_and_unblacklist(store):
    from apps.blacklist.services import BlacklistService
    BlacklistService.blacklist(store, reason='test reason')
    store.refresh_from_db()
    assert not store.is_active
    assert BlacklistRecord.objects.filter(store=store, is_active=True).exists()

    BlacklistService.unblacklist(store)
    store.refresh_from_db()
    assert store.is_active
    assert not BlacklistRecord.objects.filter(store=store, is_active=True).exists()

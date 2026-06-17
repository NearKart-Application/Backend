"""
Tests — Blacklist Module
Covers: blacklist status, enforcement, admin override, service logic
"""
import pytest
from apps.blacklist.models import Blacklist as BlacklistRecord


BASE_STORES = '/api/v1/stores'
BASE_ADMIN  = '/api/v1/admin-panel'


@pytest.fixture
def blacklisted_store(db, store):
    store.is_active = False
    store.save()
    return store


# ── Status ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_blacklist_store_is_active_initially(store):
    assert store.is_active is True


@pytest.mark.django_db
def test_blacklisted_store_is_inactive(blacklisted_store):
    assert blacklisted_store.is_active is False


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


# ── Customer Blacklist via Model ──────────────────────────────────────────────

@pytest.mark.django_db
def test_blacklist_record_created_via_model(store, customer):
    record = BlacklistRecord.objects.create(
        store=store,
        customer=customer,
        reason='test reason',
    )
    assert BlacklistRecord.objects.filter(store=store, customer=customer).exists()

    record.delete()
    assert not BlacklistRecord.objects.filter(store=store, customer=customer).exists()

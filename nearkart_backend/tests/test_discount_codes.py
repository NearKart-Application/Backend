"""
Tests — Discount Codes + Broadcast Channels  (Sprints 23 & 25)
Covers: vendor create/list/delete discount codes, customer apply code, broadcast channels + posts
"""
import pytest
from apps.stores.models import DiscountCode, BroadcastChannel, BroadcastPost, StoreFollow


MINE_BASE   = '/api/v1/stores/mine'
STORES_BASE = '/api/v1/stores'


@pytest.fixture
def discount_code(db, store):
    return DiscountCode.objects.create(
        store=store,
        code='SAVE20',
        discount_type=DiscountCode.PERCENT,
        value=20,
        max_uses=50,
        is_active=True,
    )


@pytest.fixture
def broadcast_channel(db, store):
    return BroadcastChannel.objects.create(
        store=store,
        name="Deal Alerts",
    )


# ── Vendor: List Discount Codes ───────────────────────────────────────────────

@pytest.mark.django_db
def test_vendor_list_discount_codes(vendor_client, discount_code):
    response = vendor_client.get(f'{MINE_BASE}/discount-codes/')
    assert response.status_code == 200
    data = response.json()
    results = data if isinstance(data, list) else data.get('results', [])
    codes = [c['code'] for c in results]
    assert 'SAVE20' in codes


@pytest.mark.django_db
def test_discount_code_list_requires_vendor(customer_client):
    response = customer_client.get(f'{MINE_BASE}/discount-codes/')
    assert response.status_code == 403


@pytest.mark.django_db
def test_discount_code_list_requires_auth(anon_client):
    response = anon_client.get(f'{MINE_BASE}/discount-codes/')
    assert response.status_code == 401


# ── Vendor: Create Discount Code ──────────────────────────────────────────────

@pytest.mark.django_db
def test_vendor_create_discount_code(vendor_client, store):
    response = vendor_client.post(f'{MINE_BASE}/discount-codes/', {
        'code': 'NEWYEAR25',
        'discount_type': 'percent',
        'value': 25,
        'max_uses': 100,
    })
    assert response.status_code == 201
    assert DiscountCode.objects.filter(store=store, code='NEWYEAR25').exists()


@pytest.mark.django_db
def test_vendor_create_duplicate_code(vendor_client, discount_code):
    response = vendor_client.post(f'{MINE_BASE}/discount-codes/', {
        'code': 'SAVE20',
        'discount_type': 'percent',
        'value': 10,
    })
    assert response.status_code == 400


@pytest.mark.django_db
def test_customer_cannot_create_code(customer_client):
    response = customer_client.post(f'{MINE_BASE}/discount-codes/', {
        'code': 'NOPE',
        'discount_type': 'percent',
        'value': 10,
    })
    assert response.status_code == 403


# ── Vendor: Delete Discount Code ──────────────────────────────────────────────

@pytest.mark.django_db
def test_vendor_delete_discount_code(vendor_client, discount_code):
    code_id = discount_code.id
    response = vendor_client.delete(f'{MINE_BASE}/discount-codes/{code_id}/')
    assert response.status_code in (200, 204)
    assert not DiscountCode.objects.filter(id=code_id).exists()


@pytest.mark.django_db
def test_other_vendor_cannot_delete_code(vendor2_client, discount_code):
    response = vendor2_client.delete(f'{MINE_BASE}/discount-codes/{discount_code.id}/')
    assert response.status_code in (400, 403, 404)


# ── Customer: Apply Discount Code ─────────────────────────────────────────────

@pytest.mark.django_db
def test_customer_apply_valid_code(customer_client, store, discount_code):
    response = customer_client.post(f'{STORES_BASE}/{store.id}/apply-discount/', {
        'code': 'SAVE20',
    })
    assert response.status_code == 200
    data = response.json()
    assert data.get('valid') is True
    assert 'value' in data or 'discount_type' in data


@pytest.mark.django_db
def test_customer_apply_invalid_code(customer_client, store):
    response = customer_client.post(f'{STORES_BASE}/{store.id}/apply-discount/', {
        'code': 'FAKECODE',
    })
    data = response.json()
    assert response.status_code in (200, 400)
    if response.status_code == 200:
        assert data.get('valid') is False


@pytest.mark.django_db
def test_apply_code_from_wrong_store(customer_client, store2, discount_code):
    response = customer_client.post(f'{STORES_BASE}/{store2.id}/apply-discount/', {
        'code': 'SAVE20',
    })
    data = response.json()
    assert response.status_code in (200, 400)
    if response.status_code == 200:
        assert data.get('valid') is False


@pytest.mark.django_db
def test_apply_code_requires_auth(anon_client, store, discount_code):
    response = anon_client.post(f'{STORES_BASE}/{store.id}/apply-discount/', {
        'code': 'SAVE20',
    })
    assert response.status_code == 401


# ── Vendor: Broadcast Channels ────────────────────────────────────────────────

@pytest.mark.django_db
def test_vendor_create_broadcast_channel(vendor_client, store):
    response = vendor_client.post(f'{MINE_BASE}/broadcast-channels/', {
        'name': 'Flash Deals',
    })
    assert response.status_code == 201
    assert BroadcastChannel.objects.filter(store=store, name='Flash Deals').exists()


@pytest.mark.django_db
def test_vendor_list_broadcast_channels(vendor_client, broadcast_channel):
    response = vendor_client.get(f'{MINE_BASE}/broadcast-channels/')
    assert response.status_code == 200
    data = response.json()
    results = data if isinstance(data, list) else data.get('results', [])
    names = [c['name'] for c in results]
    assert 'Deal Alerts' in names


@pytest.mark.django_db
def test_broadcast_channel_requires_vendor(customer_client):
    response = customer_client.post(f'{MINE_BASE}/broadcast-channels/', {'name': 'Nope'})
    assert response.status_code == 403


# ── Vendor: Broadcast Posts ───────────────────────────────────────────────────

@pytest.mark.django_db
def test_vendor_create_broadcast_post(vendor_client, store, broadcast_channel):
    response = vendor_client.post(
        f'{MINE_BASE}/broadcast-channels/{broadcast_channel.id}/posts/',
        {'content': 'Flash sale tomorrow!'},
    )
    assert response.status_code == 201
    assert BroadcastPost.objects.filter(channel=broadcast_channel).exists()


@pytest.mark.django_db
def test_vendor_list_broadcast_posts(vendor_client, store, broadcast_channel):
    BroadcastPost.objects.create(channel=broadcast_channel, content='Hello followers!')
    response = vendor_client.get(f'{MINE_BASE}/broadcast-channels/{broadcast_channel.id}/posts/')
    assert response.status_code == 200


# ── Customer: Read Broadcast Channels ────────────────────────────────────────

@pytest.mark.django_db
def test_customer_list_store_channels(customer_client, store, broadcast_channel):
    response = customer_client.get(f'{STORES_BASE}/{store.id}/broadcast-channels/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_customer_list_channel_posts(customer_client, store, broadcast_channel):
    BroadcastPost.objects.create(channel=broadcast_channel, content='Big sale!')
    response = customer_client.get(
        f'{STORES_BASE}/{store.id}/broadcast-channels/{broadcast_channel.id}/posts/'
    )
    assert response.status_code == 200
    data = response.json()
    results = data if isinstance(data, list) else data.get('results', [])
    assert isinstance(results, list)

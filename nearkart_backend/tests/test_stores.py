"""
Tests — Store Module
Covers: create store, get/update store, nearby search, follow/unfollow, store hours
"""
import pytest
from django.contrib.gis.geos import Point
from apps.stores.models import Store, StoreFollow, StoreHours


BASE = '/api/v1/stores'


# ── Create Store ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_create_store(vendor_client, vendor_user):
    response = vendor_client.post(f'{BASE}/', {
        'name': 'My New Store',
        'description': 'Great products',
        'category': 'fashion',
        'address': '1 Main St, Chennai',
        'latitude': 13.0827,
        'longitude': 80.2707,
    })
    assert response.status_code == 201
    assert Store.objects.filter(owner=vendor_user).exists()


@pytest.mark.django_db
def test_create_store_customer_forbidden(customer_client):
    response = customer_client.post(f'{BASE}/', {
        'name': 'Not Allowed',
        'category': 'fashion',
        'address': '1 Main St',
        'latitude': 13.0, 'longitude': 80.0,
    })
    assert response.status_code == 403


@pytest.mark.django_db
def test_create_store_unauthenticated(anon_client):
    response = anon_client.post(f'{BASE}/', {'name': 'Store'})
    assert response.status_code == 401


@pytest.mark.django_db
def test_vendor_cannot_create_two_stores(vendor_client, store):
    response = vendor_client.post(f'{BASE}/', {
        'name': 'Second Store',
        'category': 'food',
        'address': '2 St',
        'latitude': 13.0, 'longitude': 80.0,
    })
    assert response.status_code == 400


# ── Get / Update Store ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_get_store_detail(customer_client, store):
    response = customer_client.get(f'{BASE}/{store.id}/')
    assert response.status_code == 200
    assert response.json()['name'] == 'Test Store'


@pytest.mark.django_db
def test_update_store_owner(vendor_client, store):
    response = vendor_client.put(f'{BASE}/{store.id}/update/', {
        'name': 'Updated Store',
        'category': 'fashion',
        'address': '123 Test Street, Chennai',
        'latitude': 13.0827,
        'longitude': 80.2707,
    })
    assert response.status_code == 200
    store.refresh_from_db()
    assert store.name == 'Updated Store'


@pytest.mark.django_db
def test_update_store_other_vendor_forbidden(vendor2_client, store):
    response = vendor2_client.put(f'{BASE}/{store.id}/update/', {
        'name': 'Hijacked',
        'category': 'fashion',
        'address': 'x',
        'latitude': 13.0, 'longitude': 80.0,
    })
    assert response.status_code in (403, 404)


# ── Nearby Search ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
@pytest.mark.xfail(reason='Spatial DWithin with km units not supported by SpatiaLite', strict=False, raises=Exception)
def test_nearby_stores_returns_results(customer_client, store):
    response = customer_client.get(f'{BASE}/nearby/?lat=13.0827&lng=80.2707&radius=5')
    assert response.status_code == 200


@pytest.mark.django_db
def test_nearby_stores_missing_params(customer_client):
    response = customer_client.get(f'{BASE}/nearby/')
    assert response.status_code == 400


# ── Follow / Unfollow ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_follow_store(customer_client, customer, store):
    response = customer_client.post(f'{BASE}/{store.id}/follow/')
    assert response.status_code == 200
    assert StoreFollow.objects.filter(user=customer, store=store).exists()


@pytest.mark.django_db
def test_unfollow_store(customer_client, customer, store):
    StoreFollow.objects.create(user=customer, store=store)
    response = customer_client.delete(f'{BASE}/{store.id}/follow/')
    assert response.status_code == 200
    assert not StoreFollow.objects.filter(user=customer, store=store).exists()


@pytest.mark.django_db
def test_follow_requires_auth(anon_client, store):
    response = anon_client.post(f'{BASE}/{store.id}/follow/')
    assert response.status_code == 401


# ── Store Hours ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_set_store_hours(vendor_client, store):
    payload = [
        {'day': 0, 'open_time': '09:00', 'close_time': '21:00', 'is_closed': False},
        {'day': 6, 'open_time': '10:00', 'close_time': '18:00', 'is_closed': False},
    ]
    response = vendor_client.put(f'{BASE}/{store.id}/hours/', payload, format='json')
    assert response.status_code == 200
    assert StoreHours.objects.filter(store=store).count() == 2


@pytest.mark.django_db
def test_get_store_hours(vendor_client, store):
    StoreHours.objects.create(store=store, day=0, open_time='09:00', close_time='21:00', is_closed=False)
    response = vendor_client.get(f'{BASE}/{store.id}/hours/')
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.django_db
def test_set_hours_other_vendor_forbidden(vendor2_client, store):
    response = vendor2_client.put(f'{BASE}/{store.id}/hours/', [], format='json')
    assert response.status_code in (403, 404)

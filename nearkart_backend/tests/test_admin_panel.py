"""
Tests — Admin Panel Module
Covers: list users, toggle active, list stores, verify store — admin only
"""
import pytest

BASE = '/api/v1/admin-panel'


# ── Users ─────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_admin_list_users(admin_client, customer, vendor_user):
    response = admin_client.get(f'{BASE}/users/')
    assert response.status_code == 200
    results = response.json().get('results', response.json())
    assert len(results) >= 2


@pytest.mark.django_db
def test_non_admin_cannot_list_users(customer_client):
    response = customer_client.get(f'{BASE}/users/')
    assert response.status_code == 403


@pytest.mark.django_db
def test_list_users_requires_auth(anon_client):
    response = anon_client.get(f'{BASE}/users/')
    assert response.status_code == 401


@pytest.mark.django_db
def test_admin_toggle_user_active(admin_client, customer):
    response = admin_client.post(f'{BASE}/users/{customer.id}/toggle-active/')
    assert response.status_code == 200
    customer.refresh_from_db()
    assert customer.is_active is False


@pytest.mark.django_db
def test_toggle_active_non_admin_forbidden(customer_client, customer2):
    response = customer_client.post(f'{BASE}/users/{customer2.id}/toggle-active/')
    assert response.status_code == 403


# ── Stores ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_admin_list_stores(admin_client, store):
    response = admin_client.get(f'{BASE}/stores/')
    assert response.status_code == 200
    results = response.json().get('results', response.json())
    assert any(s['name'] == 'Test Store' for s in (results if isinstance(results, list) else []))


@pytest.mark.django_db
def test_non_admin_cannot_list_stores(vendor_client):
    response = vendor_client.get(f'{BASE}/stores/')
    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_verify_store(admin_client, store):
    store.is_verified = False
    store.save()
    response = admin_client.post(f'{BASE}/stores/{store.id}/verify/')
    assert response.status_code == 200
    store.refresh_from_db()
    assert store.is_verified is True

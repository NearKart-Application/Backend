"""
Tests — Analytics Module
Covers: vendor dashboard endpoint
"""
import pytest

BASE = '/api/v1/analytics'


@pytest.mark.django_db
def test_vendor_dashboard(vendor_client, store):
    response = vendor_client.get(f'{BASE}/dashboard/')
    assert response.status_code == 200
    data = response.json()
    assert 'store' in data or 'total_views' in data or 'overview' in data


@pytest.mark.django_db
def test_dashboard_requires_vendor(customer_client):
    response = customer_client.get(f'{BASE}/dashboard/')
    assert response.status_code == 403


@pytest.mark.django_db
def test_dashboard_requires_auth(anon_client):
    response = anon_client.get(f'{BASE}/dashboard/')
    assert response.status_code == 401


@pytest.mark.django_db
def test_dashboard_no_store(vendor_client, vendor_user):
    response = vendor_client.get(f'{BASE}/dashboard/')
    assert response.status_code in (200, 404)

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
    response = admin_client.patch(f'{BASE}/stores/{store.id}/', {'is_verified': True}, format='json')
    assert response.status_code == 200
    store.refresh_from_db()
    assert store.is_verified is True


# ── Create User — Sprint 20 ───────────────────────────────────────────────────

@pytest.mark.django_db
def test_admin_create_user(admin_client):
    from apps.auth_app.models import User
    response = admin_client.post(f'{BASE}/users/create/', {
        'phone_number': '+919700000001',
        'role': 'customer',
        'full_name': 'Created User',
    })
    assert response.status_code == 201
    assert User.objects.filter(phone_number='+919700000001').exists()


@pytest.mark.django_db
def test_admin_create_user_duplicate_phone(admin_client, customer):
    response = admin_client.post(f'{BASE}/users/create/', {
        'phone_number': customer.phone_number,
        'role': 'customer',
    })
    assert response.status_code in (400, 409)


@pytest.mark.django_db
def test_non_admin_cannot_create_user(customer_client):
    response = customer_client.post(f'{BASE}/users/create/', {
        'phone_number': '+919700000002',
        'role': 'customer',
    })
    assert response.status_code == 403


# ── Suspend User — Sprint 20 ──────────────────────────────────────────────────

@pytest.mark.django_db
def test_admin_suspend_user(admin_client, customer):
    response = admin_client.post(f'{BASE}/users/{customer.id}/suspend/', {
        'reason': 'Policy violation',
    })
    assert response.status_code == 200
    customer.refresh_from_db()
    assert customer.is_suspended is True


@pytest.mark.django_db
def test_non_admin_cannot_suspend(customer_client, customer2):
    response = customer_client.post(f'{BASE}/users/{customer2.id}/suspend/', {
        'reason': 'Not allowed',
    })
    assert response.status_code == 403


# ── Activity Log — Sprint 20 ──────────────────────────────────────────────────

@pytest.mark.django_db
def test_admin_activity_log(admin_client):
    response = admin_client.get(f'{BASE}/activity-log/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_activity_log_requires_admin(customer_client):
    response = customer_client.get(f'{BASE}/activity-log/')
    assert response.status_code == 403


# ── Platform Stats — Sprint 20 ────────────────────────────────────────────────

@pytest.mark.django_db
def test_admin_platform_stats(admin_client):
    response = admin_client.get(f'{BASE}/stats/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_stats_requires_admin(customer_client):
    response = customer_client.get(f'{BASE}/stats/')
    assert response.status_code == 403


# ── Banners — Sprint 21 ───────────────────────────────────────────────────────

@pytest.mark.django_db
def test_admin_create_banner(admin_client):
    response = admin_client.post(f'{BASE}/banners/', {
        'title': 'Summer Sale',
        'display_order': 1,
        'is_active': True,
    })
    assert response.status_code == 201


@pytest.mark.django_db
def test_admin_list_banners(admin_client):
    response = admin_client.get(f'{BASE}/banners/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_public_banners_no_auth(anon_client):
    response = anon_client.get(f'{BASE}/banners/active/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_non_admin_cannot_create_banner(customer_client):
    response = customer_client.post(f'{BASE}/banners/', {'title': 'Nope'})
    assert response.status_code == 403


# ── Categories — Sprint 21 ────────────────────────────────────────────────────

@pytest.mark.django_db
def test_public_categories(anon_client):
    response = anon_client.get(f'{BASE}/categories/public/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_create_category(admin_client):
    response = admin_client.post(f'{BASE}/categories/', {
        'name': 'Test Category',
        'slug': 'test-category',
    })
    assert response.status_code == 201


@pytest.mark.django_db
def test_admin_list_categories(admin_client):
    response = admin_client.get(f'{BASE}/categories/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_non_admin_cannot_create_category(vendor_client):
    response = vendor_client.post(f'{BASE}/categories/', {'name': 'Nope'})
    assert response.status_code == 403


# ── Offer Templates — Sprint 21 ───────────────────────────────────────────────

@pytest.mark.django_db
def test_public_offer_templates(customer_client):
    response = customer_client.get(f'{BASE}/offer-templates/public/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_create_offer_template(admin_client):
    response = admin_client.post(f'{BASE}/offer-templates/', {
        'name': 'Weekend Sale',
        'default_discount_pct': 20,
    })
    assert response.status_code == 201


@pytest.mark.django_db
def test_admin_list_offer_templates(admin_client):
    response = admin_client.get(f'{BASE}/offer-templates/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_non_admin_cannot_create_template(vendor_client):
    response = vendor_client.post(f'{BASE}/offer-templates/', {'name': 'Nope'})
    assert response.status_code == 403


# ── Admin Coupons — Sprint 21 ─────────────────────────────────────────────────

@pytest.mark.django_db
def test_admin_create_coupon(admin_client, store):
    from django.utils import timezone
    from datetime import timedelta
    expires = (timezone.now() + timedelta(days=7)).isoformat()
    response = admin_client.post(f'{BASE}/coupons/', {
        'store_id': str(store.id),
        'discount_pct': 10,
        'expires_at': expires,
    })
    assert response.status_code == 201


@pytest.mark.django_db
def test_admin_list_coupons(admin_client):
    response = admin_client.get(f'{BASE}/coupons/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_non_admin_cannot_create_coupon(vendor_client):
    response = vendor_client.post(f'{BASE}/coupons/', {'code': 'NOPE'})
    assert response.status_code == 403


# ── Billing Plans — Sprint 21 ─────────────────────────────────────────────────

@pytest.mark.django_db
def test_admin_list_plans(master_admin_client, plan_basic):
    response = master_admin_client.get(f'{BASE}/plans/')
    assert response.status_code == 200
    data = response.json()
    results = data if isinstance(data, list) else data.get('results', [])
    assert any(p['name'] == 'basic' for p in results)


@pytest.mark.django_db
def test_non_admin_cannot_list_admin_plans(customer_client):
    response = customer_client.get(f'{BASE}/plans/')
    assert response.status_code == 403

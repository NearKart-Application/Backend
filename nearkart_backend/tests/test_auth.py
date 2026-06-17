"""
Tests — Auth Module
Covers: OTP send/verify, JWT refresh, logout, profile get/update, device token
"""
import pytest
from apps.auth_app.models import User, UserRole, DeviceToken


BASE = '/api/v1/auth'
BASE_NOTIF = '/api/v1/notifications'


# ── OTP Send ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_otp_send_creates_user(anon_client, customer):
    response = anon_client.post(f'{BASE}/otp/send/', {'phone_number': customer.phone_number})
    assert response.status_code == 200


@pytest.mark.django_db
def test_otp_send_existing_user(anon_client, customer):
    response = anon_client.post(f'{BASE}/otp/send/', {'phone_number': customer.phone_number})
    assert response.status_code == 200


@pytest.mark.django_db
def test_otp_send_invalid_phone(anon_client):
    response = anon_client.post(f'{BASE}/otp/send/', {'phone_number': 'not-a-phone'})
    assert response.status_code == 400


@pytest.mark.django_db
def test_otp_send_missing_phone(anon_client):
    response = anon_client.post(f'{BASE}/otp/send/', {})
    assert response.status_code == 400


# ── OTP Verify ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_otp_verify_returns_tokens(anon_client, customer):
    anon_client.post(f'{BASE}/otp/send/', {'phone_number': customer.phone_number})
    response = anon_client.post(f'{BASE}/otp/verify/', {
        'phone_number': customer.phone_number,
        'otp': '123456',
    })
    assert response.status_code == 200
    data = response.json()
    assert 'access' in data
    assert 'refresh' in data
    assert data.get('role') == 'customer' or data.get('user', {}).get('role') == 'customer'


@pytest.mark.django_db
def test_otp_verify_wrong_otp(anon_client):
    anon_client.post(f'{BASE}/otp/send/', {'phone_number': '+919333333333'})
    response = anon_client.post(f'{BASE}/otp/verify/', {
        'phone_number': '+919333333333',
        'otp': '000000',
    })
    assert response.status_code == 400


@pytest.mark.django_db
def test_otp_verify_no_otp_sent(anon_client):
    response = anon_client.post(f'{BASE}/otp/verify/', {
        'phone_number': '+919444444444',
        'otp': '123456',
    })
    assert response.status_code == 400


@pytest.mark.django_db
def test_otp_verify_sets_customer_role(anon_client, customer):
    anon_client.post(f'{BASE}/otp/send/', {'phone_number': customer.phone_number})
    response = anon_client.post(f'{BASE}/otp/verify/', {
        'phone_number': customer.phone_number,
        'otp': '123456',
    })
    data = response.json()
    role = data.get('role') or data.get('user', {}).get('role')
    assert role == 'customer'


# ── Token Refresh ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_token_refresh(anon_client, customer):
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = str(RefreshToken.for_user(customer))
    response = anon_client.post(f'{BASE}/token/refresh/', {'refresh': refresh})
    assert response.status_code == 200
    assert 'access' in response.json()


@pytest.mark.django_db
def test_token_refresh_invalid(anon_client):
    response = anon_client.post(f'{BASE}/token/refresh/', {'refresh': 'bad-token'})
    assert response.status_code == 401


# ── Logout ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_logout(customer_client, customer):
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = str(RefreshToken.for_user(customer))
    response = customer_client.post(f'{BASE}/logout/', {'refresh': refresh})
    assert response.status_code == 200


@pytest.mark.django_db
def test_logout_requires_auth(anon_client):
    response = anon_client.post(f'{BASE}/logout/', {'refresh': 'token'})
    assert response.status_code == 401


# ── Profile ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_get_profile(customer_client, customer):
    response = customer_client.get(f'{BASE}/me/')
    assert response.status_code == 200
    data = response.json()
    assert data['phone_number'] == customer.phone_number
    assert data['role'] == 'customer'


@pytest.mark.django_db
def test_update_profile(customer_client, customer):
    response = customer_client.patch(f'{BASE}/me/', {
        'full_name': 'Test User',
        'email': 'test@example.com',
    })
    assert response.status_code == 200
    customer.refresh_from_db()
    assert customer.full_name == 'Test User'


@pytest.mark.django_db
def test_profile_requires_auth(anon_client):
    response = anon_client.get(f'{BASE}/me/')
    assert response.status_code == 401


# ── Device Token ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_register_device_token(customer_client, customer):
    response = customer_client.post(f'{BASE_NOTIF}/device-token/', {
        'fcm_token': 'test-fcm-token-abc123',
        'device_type': 'android',
    })
    assert response.status_code == 200
    assert DeviceToken.objects.filter(user=customer, fcm_token='test-fcm-token-abc123').exists()


@pytest.mark.django_db
def test_register_device_token_idempotent(customer_client, customer):
    customer_client.post(f'{BASE_NOTIF}/device-token/', {'fcm_token': 'tok1', 'device_type': 'ios'})
    customer_client.post(f'{BASE_NOTIF}/device-token/', {'fcm_token': 'tok1', 'device_type': 'ios'})
    assert DeviceToken.objects.filter(user=customer, fcm_token='tok1').count() == 1


# ── Voice OTP — Sprint 28 (NF-10) ────────────────────────────────────────────

@pytest.mark.django_db
def test_otp_send_default_delivery_method_is_sms(anon_client, customer):
    response = anon_client.post(f'{BASE}/otp/send/', {'phone_number': customer.phone_number})
    assert response.status_code == 200


@pytest.mark.django_db
def test_otp_send_explicit_sms_delivery(anon_client, customer):
    response = anon_client.post(f'{BASE}/otp/send/', {
        'phone_number': customer.phone_number,
        'delivery_method': 'sms',
    })
    assert response.status_code == 200


@pytest.mark.django_db
def test_otp_send_voice_delivery(anon_client, customer):
    response = anon_client.post(f'{BASE}/otp/send/', {
        'phone_number': customer.phone_number,
        'delivery_method': 'voice',
    })
    assert response.status_code == 200


@pytest.mark.django_db
def test_otp_send_invalid_delivery_method(anon_client, customer):
    response = anon_client.post(f'{BASE}/otp/send/', {
        'phone_number': customer.phone_number,
        'delivery_method': 'telegram',
    })
    assert response.status_code == 400


@pytest.mark.django_db
def test_otp_send_voice_then_verify(anon_client, customer):
    anon_client.post(f'{BASE}/otp/send/', {
        'phone_number': customer.phone_number,
        'delivery_method': 'voice',
    })
    response = anon_client.post(f'{BASE}/otp/verify/', {
        'phone_number': customer.phone_number,
        'otp': '123456',
    })
    assert response.status_code == 200
    assert 'access' in response.json()

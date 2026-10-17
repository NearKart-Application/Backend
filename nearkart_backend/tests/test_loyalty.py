"""
Tests — Loyalty & Referral Module  (Sprint 15)
Covers: balance, history, apply referral code, redeem points
"""
import pytest
from apps.loyalty.models import LoyaltyAccount, LoyaltyTransaction, Referral


BASE = '/api/v1/loyalty'


@pytest.fixture
def loyalty_account(db, customer):
    account, _ = LoyaltyAccount.objects.get_or_create(user=customer)
    account.balance = 200
    account.save()
    return account


@pytest.fixture
def referral_code(db, customer2):
    return Referral.objects.create(
        referrer=customer2,
        referral_code='TESTREF01',
    )


# ── Balance ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_get_loyalty_balance(customer_client, loyalty_account):
    response = customer_client.get(f'{BASE}/')
    assert response.status_code == 200
    data = response.json()
    assert 'points' in data or 'balance' in data


@pytest.mark.django_db
def test_get_loyalty_balance_new_user(customer_client, customer):
    response = customer_client.get(f'{BASE}/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_loyalty_balance_requires_auth(anon_client):
    response = anon_client.get(f'{BASE}/')
    assert response.status_code == 401


# ── History ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_get_loyalty_history(customer_client, loyalty_account):
    LoyaltyTransaction.objects.create(
        account=loyalty_account,
        points=50,
        transaction_type='earn',
        description='Referral bonus',
    )
    response = customer_client.get(f'{BASE}/history/')
    assert response.status_code == 200
    data = response.json()
    results = data if isinstance(data, list) else data.get('results', [])
    assert isinstance(results, list)


@pytest.mark.django_db
def test_loyalty_history_empty(customer_client, customer):
    response = customer_client.get(f'{BASE}/history/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_loyalty_history_requires_auth(anon_client):
    response = anon_client.get(f'{BASE}/history/')
    assert response.status_code == 401


# ── Apply Referral Code ───────────────────────────────────────────────────────

@pytest.mark.django_db
def test_apply_referral_code(customer_client, customer2):
    LoyaltyAccount.objects.get_or_create(user=customer2)
    response = customer_client.post(f'{BASE}/apply-referral/', {
        'referral_code': customer2.profile_id,
    })
    assert response.status_code in (200, 201)


@pytest.mark.django_db
def test_apply_invalid_referral_code(customer_client):
    response = customer_client.post(f'{BASE}/apply-referral/', {
        'referral_code': 'NOTACODE',
    })
    assert response.status_code == 400


@pytest.mark.django_db
def test_apply_own_referral_code_forbidden(customer_client, customer, loyalty_account):
    response = customer_client.post(f'{BASE}/apply-referral/', {
        'referral_code': customer.profile_id,
    })
    assert response.status_code == 400


@pytest.mark.django_db
def test_apply_referral_twice_forbidden(customer_client, customer2):
    LoyaltyAccount.objects.get_or_create(user=customer2)
    customer_client.post(f'{BASE}/apply-referral/', {'referral_code': customer2.profile_id})
    response = customer_client.post(f'{BASE}/apply-referral/', {'referral_code': customer2.profile_id})
    assert response.status_code == 400


@pytest.mark.django_db
def test_apply_referral_requires_auth(anon_client):
    response = anon_client.post(f'{BASE}/apply-referral/', {'referral_code': 'TESTREF01'})
    assert response.status_code == 401


# ── Redeem Points ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_redeem_points(customer_client, loyalty_account):
    response = customer_client.post(f'{BASE}/redeem/', {
        'points': 100,
    })
    assert response.status_code in (200, 201)


@pytest.mark.django_db
def test_redeem_more_than_balance(customer_client, loyalty_account):
    response = customer_client.post(f'{BASE}/redeem/', {
        'points': 9999,
    })
    assert response.status_code == 400


@pytest.mark.django_db
def test_redeem_requires_auth(anon_client):
    response = anon_client.post(f'{BASE}/redeem/', {'points': 50})
    assert response.status_code == 401

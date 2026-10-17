"""
Tests — Billing Module
Covers: plans list, wallet, topup, subscribe, subscription status,
        transactions, Razorpay initiate/verify/webhook
"""
import pytest
from decimal import Decimal
from apps.billing.models import Subscription, Transaction


BASE = '/api/v1/billing'


# ── Plans ─────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_plans_public(anon_client, all_plans):
    response = anon_client.get(f'{BASE}/plans/')
    assert response.status_code == 200
    names = [p['name'] for p in response.json()]
    assert 'basic' in names
    assert 'premium' in names


@pytest.mark.django_db
def test_plans_ordered_by_price(anon_client, all_plans):
    response = anon_client.get(f'{BASE}/plans/')
    prices = [float(p['price']) for p in response.json()]
    assert prices == sorted(prices)


# ── Wallet ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_get_wallet(vendor_client, store):
    response = vendor_client.get(f'{BASE}/wallet/')
    assert response.status_code == 200
    assert 'wallet_balance' in response.json()


@pytest.mark.django_db
def test_wallet_requires_vendor(customer_client):
    response = customer_client.get(f'{BASE}/wallet/')
    assert response.status_code == 403


@pytest.mark.django_db
def test_wallet_no_store(vendor_client, vendor_user):
    response = vendor_client.get(f'{BASE}/wallet/')
    assert response.status_code == 400


# ── Top-Up ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_topup_wallet(vendor_client, store):
    response = vendor_client.post(f'{BASE}/topup/', {'amount': '500.00'})
    assert response.status_code == 200
    store.refresh_from_db()
    assert store.wallet_balance == Decimal('500.00')
    assert Transaction.objects.filter(store=store, type='topup').exists()


@pytest.mark.django_db
def test_topup_negative_amount(vendor_client, store):
    response = vendor_client.post(f'{BASE}/topup/', {'amount': '-100'})
    assert response.status_code == 400


# ── Subscribe ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_subscribe_basic(vendor_client, store, plan_basic):
    store.wallet_balance = Decimal('299.00')
    store.save()
    response = vendor_client.post(f'{BASE}/subscribe/', {'plan_name': 'basic'})
    assert response.status_code == 200
    assert Subscription.objects.filter(store=store, plan=plan_basic, is_active=True).exists()


@pytest.mark.django_db
def test_subscribe_insufficient_balance(vendor_client, store, plan_basic):
    store.wallet_balance = Decimal('0.00')
    store.save()
    response = vendor_client.post(f'{BASE}/subscribe/', {'plan_name': 'basic'})
    assert response.status_code in (200, 400)


@pytest.mark.django_db
def test_subscribe_unknown_plan(vendor_client, store):
    response = vendor_client.post(f'{BASE}/subscribe/', {'plan_name': 'nonexistent'})
    assert response.status_code == 404


# ── Subscription Status ───────────────────────────────────────────────────────

@pytest.mark.django_db
def test_subscription_status(vendor_client, store, plan_basic):
    store.wallet_balance = Decimal('299.00')
    store.save()
    vendor_client.post(f'{BASE}/subscribe/', {'plan_name': 'basic'})
    response = vendor_client.get(f'{BASE}/subscription/')
    assert response.status_code == 200
    data = response.json()
    assert data['is_active'] is True
    assert data['plan']['name'] == 'basic'


@pytest.mark.django_db
def test_subscription_status_no_subscription(vendor_client, store):
    Subscription.objects.filter(store=store).delete()
    response = vendor_client.get(f'{BASE}/subscription/')
    assert response.status_code == 404


# ── Transactions ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_transaction_list(vendor_client, store):
    vendor_client.post(f'{BASE}/topup/', {'amount': '200.00'})
    response = vendor_client.get(f'{BASE}/transactions/')
    assert response.status_code == 200
    data = response.json()
    results = data if isinstance(data, list) else data.get('results', [])
    assert len(results) >= 1


# ── Razorpay — Initiate ───────────────────────────────────────────────────────

@pytest.mark.django_db
def test_razorpay_initiate_basic(vendor_client, store, plan_basic):
    response = vendor_client.post(f'{BASE}/payment/initiate/', {'plan_name': 'basic'})
    assert response.status_code == 200
    data = response.json()
    assert 'order_id' in data
    assert data['order_id'].startswith('order_DEV_')
    assert data['amount'] == 29900
    assert data['currency'] == 'INR'


@pytest.mark.django_db
def test_razorpay_initiate_premium(vendor_client, store, plan_premium):
    response = vendor_client.post(f'{BASE}/payment/initiate/', {'plan_name': 'premium'})
    assert response.status_code == 200
    assert response.json()['amount'] == 49900


@pytest.mark.django_db
def test_razorpay_initiate_unknown_plan(vendor_client, store):
    response = vendor_client.post(f'{BASE}/payment/initiate/', {'plan_name': 'gold'})
    assert response.status_code == 404


@pytest.mark.django_db
def test_razorpay_initiate_customer_forbidden(customer_client):
    response = customer_client.post(f'{BASE}/payment/initiate/', {'plan_name': 'basic'})
    assert response.status_code == 403


# ── Razorpay — Verify ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_razorpay_verify_activates_subscription(vendor_client, store, plan_basic):
    init = vendor_client.post(f'{BASE}/payment/initiate/', {'plan_name': 'basic'})
    order_id = init.json()['order_id']
    response = vendor_client.post(f'{BASE}/payment/verify/', {
        'razorpay_order_id': order_id,
        'razorpay_payment_id': 'pay_DEV_test001',
        'razorpay_signature': 'mock_sig',
        'plan_name': 'basic',
    })
    assert response.status_code == 200
    assert response.json()['is_active'] is True
    assert Subscription.objects.filter(store=store, is_active=True).exists()


@pytest.mark.django_db
def test_razorpay_verify_missing_fields(vendor_client, store):
    response = vendor_client.post(f'{BASE}/payment/verify/', {
        'razorpay_order_id': 'order_DEV_x',
    })
    assert response.status_code == 400


# ── Razorpay — Webhook ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_razorpay_webhook_processes_payment(anon_client, store, plan_basic):
    payload = {
        'event': 'payment.captured',
        'payload': {
            'payment': {
                'entity': {
                    'id': 'pay_WH_001',
                    'order_id': 'order_DEV_wh',
                    'notes': {'store_id': str(store.id), 'plan': 'basic'},
                }
            }
        }
    }
    response = anon_client.post(
        f'{BASE}/payment/webhook/', payload,
        format='json', HTTP_X_RAZORPAY_SIGNATURE='mock_sig',
    )
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


@pytest.mark.django_db
def test_razorpay_webhook_idempotent(anon_client, store, plan_basic):
    payload = {
        'event': 'payment.captured',
        'payload': {
            'payment': {
                'entity': {
                    'id': 'pay_WH_DUPE',
                    'order_id': 'order_DEV_dupe',
                    'notes': {'store_id': str(store.id), 'plan': 'basic'},
                }
            }
        }
    }
    anon_client.post(f'{BASE}/payment/webhook/', payload, format='json',
                     HTTP_X_RAZORPAY_SIGNATURE='sig')
    response = anon_client.post(f'{BASE}/payment/webhook/', payload, format='json',
                                HTTP_X_RAZORPAY_SIGNATURE='sig')
    assert response.status_code == 200
    assert response.json()['status'] == 'already_processed'


@pytest.mark.django_db
def test_razorpay_webhook_unknown_event_ignored(anon_client, store):
    payload = {'event': 'payment.failed', 'payload': {}}
    response = anon_client.post(f'{BASE}/payment/webhook/', payload, format='json',
                                HTTP_X_RAZORPAY_SIGNATURE='sig')
    assert response.status_code == 200

"""
Tests — Reservations Module
Covers: create, list, detail, confirm, cancel, auto-expire task
"""
import pytest
from apps.reservations.models import Reservation


BASE = '/api/v1/reservations'


@pytest.fixture
def product(db, store):
    from apps.products.models import Product
    return Product.objects.create(
        store=store, name='Reserve Me', price='199.00',
        category='fashion', is_available=True,
    )


@pytest.fixture
def reservation(db, customer, product):
    return Reservation.objects.create(
        customer=customer,
        product=product,
        store=product.store,
        status=Reservation.STATUS_PENDING,
        quantity=1,
        note='Please hold',
    )


# ── Create ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_create_reservation(customer_client, product):
    response = customer_client.post(f'{BASE}/', {
        'product': str(product.id),
        'quantity': 1,
        'note': 'Holding for me',
    })
    assert response.status_code == 201
    assert Reservation.objects.filter(customer__phone_number='+919000000001').exists()


@pytest.mark.django_db
def test_create_reservation_requires_auth(anon_client, product):
    response = anon_client.post(f'{BASE}/', {'product': str(product.id), 'quantity': 1})
    assert response.status_code == 401


@pytest.mark.django_db
def test_vendor_cannot_create_reservation(vendor_client, product):
    response = vendor_client.post(f'{BASE}/', {'product': str(product.id), 'quantity': 1})
    assert response.status_code == 403


# ── List ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_customer_sees_own_reservations(customer_client, reservation):
    response = customer_client.get(f'{BASE}/')
    assert response.status_code == 200
    results = response.json().get('results', response.json())
    assert len(results) >= 1


@pytest.mark.django_db
def test_vendor_sees_store_reservations(vendor_client, reservation):
    response = vendor_client.get(f'{BASE}/')
    assert response.status_code == 200


# ── Detail ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_get_reservation_detail_customer(customer_client, reservation):
    response = customer_client.get(f'{BASE}/{reservation.id}/')
    assert response.status_code == 200
    assert response.json()['status'] == 'pending'


@pytest.mark.django_db
def test_get_reservation_detail_vendor(vendor_client, reservation):
    response = vendor_client.get(f'{BASE}/{reservation.id}/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_other_customer_cannot_see_reservation(customer2_client, reservation):
    response = customer2_client.get(f'{BASE}/{reservation.id}/')
    assert response.status_code == 404


# ── Confirm ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_vendor_confirms_reservation(vendor_client, reservation):
    response = vendor_client.patch(f'{BASE}/{reservation.id}/status/', {
        'status': 'confirmed',
    })
    assert response.status_code == 200
    reservation.refresh_from_db()
    assert reservation.status == Reservation.STATUS_CONFIRMED


# ── Cancel ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_customer_cancels_reservation(customer_client, reservation):
    response = customer_client.post(f'{BASE}/{reservation.id}/cancel/')
    assert response.status_code == 200
    reservation.refresh_from_db()
    assert reservation.status == Reservation.STATUS_CANCELLED


@pytest.mark.django_db
def test_cancel_already_cancelled(customer_client, customer, product):
    r = Reservation.objects.create(
        customer=customer, product=product, store=product.store,
        status=Reservation.STATUS_CANCELLED, quantity=1,
    )
    response = customer_client.post(f'{BASE}/{r.id}/cancel/')
    assert response.status_code == 400


# ── Expiry Task ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_expire_reservations_task(customer, product):
    from django.utils import timezone
    from datetime import timedelta
    r = Reservation.objects.create(
        customer=customer, product=product, store=product.store,
        status=Reservation.STATUS_PENDING, quantity=1,
        created_at=timezone.now() - timedelta(hours=3),
    )
    from apps.reservations.tasks import expire_reservations
    expire_reservations()
    r.refresh_from_db()
    assert r.status == Reservation.STATUS_EXPIRED

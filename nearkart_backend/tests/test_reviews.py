"""
Tests — Reviews & Ratings Module  (Sprint 16)
Covers: create review, list reviews, vendor reply, vendor list, eligibility, customer list
"""
import pytest
from apps.stores.models import StoreReview
from apps.reservations.models import Reservation


BASE_STORES = '/api/v1/stores'


@pytest.fixture
def completed_reservation(db, store, customer):
    import uuid
    from django.utils import timezone
    from datetime import timedelta
    from apps.products.models import Product
    product = Product.objects.create(
        store=store, name='Review Product', base_price='199.00',
        category='fashion', status='active', is_visible=True,
        product_code=f'NS-REV-{uuid.uuid4().hex[:6].upper()}',
    )
    return Reservation.objects.create(
        store=store,
        customer=customer,
        product=product,
        status='completed',
        quantity=1,
        expires_at=timezone.now() + timedelta(days=1),
    )


@pytest.fixture
def existing_review(db, store, customer):
    return StoreReview.objects.create(
        store=store,
        user=customer,
        rating=4,
        comment='Good store!',
    )


# ── Create Review ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_customer_can_submit_review(customer_client, store, completed_reservation):
    response = customer_client.post(f'{BASE_STORES}/{store.id}/review/', {
        'rating': 5,
        'comment': 'Excellent service!',
    })
    assert response.status_code in (200, 201)
    assert StoreReview.objects.filter(store=store, rating=5).exists()


@pytest.mark.django_db
def test_review_rating_required(customer_client, store, completed_reservation):
    response = customer_client.post(f'{BASE_STORES}/{store.id}/review/', {
        'comment': 'No rating',
    })
    assert response.status_code == 400


@pytest.mark.django_db
def test_review_rating_out_of_range(customer_client, store, completed_reservation):
    response = customer_client.post(f'{BASE_STORES}/{store.id}/review/', {
        'rating': 6,
        'comment': 'Too high',
    })
    assert response.status_code == 400


@pytest.mark.django_db
def test_vendor_cannot_review_own_store(vendor_client, store):
    response = vendor_client.post(f'{BASE_STORES}/{store.id}/review/', {
        'rating': 5,
        'comment': 'My own store',
    })
    assert response.status_code in (400, 403)


@pytest.mark.django_db
def test_review_requires_auth(anon_client, store):
    response = anon_client.post(f'{BASE_STORES}/{store.id}/review/', {
        'rating': 4,
        'comment': 'Anonymous',
    })
    assert response.status_code == 401


# ── List Reviews ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_store_reviews_public(anon_client, store, existing_review):
    response = anon_client.get(f'{BASE_STORES}/{store.id}/reviews/')
    assert response.status_code == 200
    results = response.json().get('results', response.json())
    assert isinstance(results, list)
    assert len(results) >= 1


@pytest.mark.django_db
def test_list_reviews_empty_store(anon_client, store):
    response = anon_client.get(f'{BASE_STORES}/{store.id}/reviews/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_review_shows_masked_username(anon_client, store, existing_review):
    response = anon_client.get(f'{BASE_STORES}/{store.id}/reviews/')
    results = response.json().get('results', response.json())
    if results:
        name = results[0].get('user_name', '')
        assert '****' in name or len(name) <= 10


# ── Vendor Reply ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_vendor_can_reply_to_review(vendor_client, store, existing_review):
    response = vendor_client.post(
        f'{BASE_STORES}/{store.id}/reviews/{existing_review.id}/reply/',
        {'reply': 'Thank you for your feedback!'},
    )
    assert response.status_code == 200
    existing_review.refresh_from_db()
    assert existing_review.vendor_reply == 'Thank you for your feedback!'


@pytest.mark.django_db
def test_vendor_reply_updates_on_repost(vendor_client, store, existing_review):
    vendor_client.post(
        f'{BASE_STORES}/{store.id}/reviews/{existing_review.id}/reply/',
        {'reply': 'First reply'},
    )
    response = vendor_client.post(
        f'{BASE_STORES}/{store.id}/reviews/{existing_review.id}/reply/',
        {'reply': 'Updated reply'},
    )
    assert response.status_code == 200
    existing_review.refresh_from_db()
    assert existing_review.vendor_reply == 'Updated reply'


@pytest.mark.django_db
def test_other_vendor_cannot_reply(vendor2_client, store, existing_review):
    response = vendor2_client.post(
        f'{BASE_STORES}/{store.id}/reviews/{existing_review.id}/reply/',
        {'reply': 'Hijack'},
    )
    assert response.status_code in (403, 404)


@pytest.mark.django_db
def test_customer_cannot_reply_as_vendor(customer_client, store, existing_review):
    response = customer_client.post(
        f'{BASE_STORES}/{store.id}/reviews/{existing_review.id}/reply/',
        {'reply': 'Not allowed'},
    )
    assert response.status_code == 403


# ── Vendor Review List ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_vendor_can_list_own_store_reviews(vendor_client, store, existing_review):
    response = vendor_client.get(f'{BASE_STORES}/{store.id}/reviews/vendor/')
    assert response.status_code == 200
    results = response.json().get('results', response.json())
    assert isinstance(results, list)


@pytest.mark.django_db
def test_other_vendor_cannot_list_reviews(vendor2_client, store):
    response = vendor2_client.get(f'{BASE_STORES}/{store.id}/reviews/vendor/')
    assert response.status_code in (403, 404)


# ── Review Eligibility ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_review_eligibility_with_reservation(customer_client, store, completed_reservation):
    response = customer_client.get(f'{BASE_STORES}/{store.id}/review-eligibility/')
    assert response.status_code == 200
    data = response.json()
    assert 'eligible' in data or 'can_review_shop' in data


@pytest.mark.django_db
def test_review_eligibility_requires_auth(anon_client, store):
    response = anon_client.get(f'{BASE_STORES}/{store.id}/review-eligibility/')
    assert response.status_code == 401

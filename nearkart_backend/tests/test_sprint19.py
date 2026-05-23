"""
Tests — Sprint 19
Covers:
  A) Search filters & sort  (min_price, max_price, min_rating, has_offer, ordering)
  B) Following feed          (GET /products/following/)
  C) Vendor invoices         (GET + POST /stores/mine/invoices/)
"""
import pytest
from apps.products.models import Product
from apps.stores.models import Store, StoreFollow, StoreOffer, StoreReview, Invoice


SEARCH_URL   = '/api/v1/products/search/'
FOLLOW_URL   = '/api/v1/products/following/'
INVOICE_URL  = '/api/v1/stores/mine/invoices/'


# ── Shared fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def cheap_product(db, store):
    return Product.objects.create(
        store=store, name='Budget Shirt', base_price='199.00',
        category='fashion', status='active', is_visible=True,
    )


@pytest.fixture
def expensive_product(db, store):
    return Product.objects.create(
        store=store, name='Premium Shirt', base_price='2999.00',
        category='fashion', status='active', is_visible=True,
    )


@pytest.fixture
def active_offer(db, store):
    return StoreOffer.objects.create(
        store=store, title='Sale', discount_pct=10, is_active=True,
    )


@pytest.fixture
def store_review(db, store, customer):
    return StoreReview.objects.create(store=store, user=customer, rating=5)


# ══════════════════════════════════════════════════════════════════════════════
# A — Search Filters & Sort
# ══════════════════════════════════════════════════════════════════════════════

class TestSearchFilters:

    @pytest.mark.django_db
    def test_search_no_filters_returns_results(self, customer_client, cheap_product):
        r = customer_client.get(SEARCH_URL, {'q': 'Shirt'})
        assert r.status_code == 200
        names = [p['name'] for p in r.json().get('results', [])]
        assert 'Budget Shirt' in names

    @pytest.mark.django_db
    def test_min_price_filter(self, customer_client, cheap_product, expensive_product):
        r = customer_client.get(SEARCH_URL, {'q': 'Shirt', 'min_price': '500'})
        assert r.status_code == 200
        names = [p['name'] for p in r.json().get('results', [])]
        assert 'Budget Shirt' not in names
        assert 'Premium Shirt' in names

    @pytest.mark.django_db
    def test_max_price_filter(self, customer_client, cheap_product, expensive_product):
        r = customer_client.get(SEARCH_URL, {'q': 'Shirt', 'max_price': '500'})
        assert r.status_code == 200
        names = [p['name'] for p in r.json().get('results', [])]
        assert 'Budget Shirt' in names
        assert 'Premium Shirt' not in names

    @pytest.mark.django_db
    def test_price_range_filter(self, customer_client, cheap_product, expensive_product):
        r = customer_client.get(SEARCH_URL, {'q': 'Shirt', 'min_price': '100', 'max_price': '500'})
        assert r.status_code == 200
        names = [p['name'] for p in r.json().get('results', [])]
        assert 'Budget Shirt' in names
        assert 'Premium Shirt' not in names

    @pytest.mark.django_db
    def test_min_rating_filter_excludes_unrated(self, customer_client, cheap_product, expensive_product):
        # store has no reviews → avg rating is None/0; min_rating=4 should exclude it
        r = customer_client.get(SEARCH_URL, {'q': 'Shirt', 'min_rating': '4'})
        assert r.status_code == 200
        # no reviews on the store → results should be empty or exclude both products
        names = [p['name'] for p in r.json().get('results', [])]
        assert 'Budget Shirt' not in names

    @pytest.mark.django_db
    def test_min_rating_filter_includes_rated(self, customer_client, cheap_product, store_review):
        # store now has rating=5; min_rating=4 should include it
        r = customer_client.get(SEARCH_URL, {'q': 'Shirt', 'min_rating': '4'})
        assert r.status_code == 200
        names = [p['name'] for p in r.json().get('results', [])]
        assert 'Budget Shirt' in names

    @pytest.mark.django_db
    def test_has_offer_filter(self, customer_client, cheap_product, expensive_product, active_offer):
        r = customer_client.get(SEARCH_URL, {'q': 'Shirt', 'has_offer': 'true'})
        assert r.status_code == 200
        names = [p['name'] for p in r.json().get('results', [])]
        # both products belong to the same store which has an active offer
        assert 'Budget Shirt' in names

    @pytest.mark.django_db
    def test_ordering_price_asc(self, customer_client, cheap_product, expensive_product):
        r = customer_client.get(SEARCH_URL, {'q': 'Shirt', 'ordering': 'price_asc'})
        assert r.status_code == 200
        results = r.json().get('results', [])
        prices = [float(p['price']) for p in results if p['name'] in ('Budget Shirt', 'Premium Shirt')]
        assert prices == sorted(prices)

    @pytest.mark.django_db
    def test_ordering_price_desc(self, customer_client, cheap_product, expensive_product):
        r = customer_client.get(SEARCH_URL, {'q': 'Shirt', 'ordering': 'price_desc'})
        assert r.status_code == 200
        results = r.json().get('results', [])
        prices = [float(p['price']) for p in results if p['name'] in ('Budget Shirt', 'Premium Shirt')]
        assert prices == sorted(prices, reverse=True)

    @pytest.mark.django_db
    def test_search_is_public(self, anon_client):
        # Search is intentionally public so browsing guests can discover products
        r = anon_client.get(SEARCH_URL, {'q': 'anything'})
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# B — Following Feed
# ══════════════════════════════════════════════════════════════════════════════

class TestFollowingFeed:

    @pytest.fixture
    def followed_product(self, db, store):
        return Product.objects.create(
            store=store, name='Followed Store Product', base_price='399.00',
            category='fashion', status='active', is_visible=True,
        )

    @pytest.fixture
    def follow(self, db, customer, store):
        return StoreFollow.objects.create(user=customer, store=store)

    @pytest.mark.django_db
    def test_following_feed_empty_when_no_follows(self, customer_client, followed_product):
        r = customer_client.get(FOLLOW_URL)
        assert r.status_code == 200
        assert r.json()['count'] == 0
        assert r.json()['results'] == []

    @pytest.mark.django_db
    def test_following_feed_returns_products_from_followed_stores(
        self, customer_client, follow, followed_product,
    ):
        r = customer_client.get(FOLLOW_URL)
        assert r.status_code == 200
        names = [p['name'] for p in r.json()['results']]
        assert 'Followed Store Product' in names

    @pytest.mark.django_db
    def test_following_feed_excludes_unfollowed_stores(
        self, customer_client, followed_product, store2,
    ):
        # customer follows no stores → nothing returned
        r = customer_client.get(FOLLOW_URL)
        assert r.status_code == 200
        assert r.json()['count'] == 0

    @pytest.mark.django_db
    def test_following_feed_excludes_inactive_products(self, customer_client, follow, store):
        Product.objects.create(
            store=store, name='Hidden Product', base_price='100.00',
            category='fashion', status='inactive', is_visible=False,
        )
        r = customer_client.get(FOLLOW_URL)
        assert r.status_code == 200
        names = [p['name'] for p in r.json()['results']]
        assert 'Hidden Product' not in names

    @pytest.mark.django_db
    def test_following_feed_requires_auth(self, anon_client):
        r = anon_client.get(FOLLOW_URL)
        assert r.status_code == 401

    @pytest.mark.django_db
    def test_following_feed_vendor_can_call(self, vendor_client, store):
        # vendor calling their own following feed — should return 200 (empty)
        r = vendor_client.get(FOLLOW_URL)
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# C — Vendor Invoices
# ══════════════════════════════════════════════════════════════════════════════

class TestVendorInvoices:

    VALID_PAYLOAD = {
        'customer_name': 'Ravi Kumar',
        'customer_phone': '+919876543210',
        'items': [
            {'name': 'Blue Shirt', 'price': 499, 'qty': 2},
            {'name': 'Black Jeans', 'price': 999, 'qty': 1},
        ],
        'notes': 'Urgent delivery',
    }

    # ── List ──────────────────────────────────────────────────────────────────

    @pytest.mark.django_db
    def test_list_invoices_empty_initially(self, vendor_client, store):
        r = vendor_client.get(INVOICE_URL)
        assert r.status_code == 200
        assert r.json()['count'] == 0
        assert r.json()['results'] == []

    @pytest.mark.django_db
    def test_list_invoices_shows_created_invoice(self, vendor_client, store):
        Invoice.objects.create(
            store=store,
            customer_name='Test Customer',
            items=[{'name': 'Item', 'price': 100, 'qty': 1}],
            total='100.00',
        )
        r = vendor_client.get(INVOICE_URL)
        assert r.status_code == 200
        assert r.json()['count'] == 1
        assert r.json()['results'][0]['customer_name'] == 'Test Customer'

    @pytest.mark.django_db
    def test_list_invoices_customer_forbidden(self, customer_client):
        r = customer_client.get(INVOICE_URL)
        assert r.status_code in (403, 404)

    @pytest.mark.django_db
    def test_list_invoices_unauthenticated(self, anon_client):
        r = anon_client.get(INVOICE_URL)
        assert r.status_code == 401

    # ── Create ────────────────────────────────────────────────────────────────

    @pytest.mark.django_db
    def test_create_invoice_success(self, vendor_client, store):
        r = vendor_client.post(INVOICE_URL, self.VALID_PAYLOAD, format='json')
        assert r.status_code == 201
        data = r.json()
        assert data['customer_name'] == 'Ravi Kumar'
        assert 'id' in data
        assert Invoice.objects.filter(store=store, customer_name='Ravi Kumar').exists()

    @pytest.mark.django_db
    def test_create_invoice_total_computed_correctly(self, vendor_client, store):
        # 499×2 + 999×1 = 1997
        r = vendor_client.post(INVOICE_URL, self.VALID_PAYLOAD, format='json')
        assert r.status_code == 201
        invoice = Invoice.objects.get(store=store, customer_name='Ravi Kumar')
        assert float(invoice.total) == pytest.approx(1997.0)

    @pytest.mark.django_db
    def test_create_invoice_no_customer_name_rejected(self, vendor_client, store):
        payload = {**self.VALID_PAYLOAD, 'customer_name': ''}
        r = vendor_client.post(INVOICE_URL, payload, format='json')
        assert r.status_code == 400

    @pytest.mark.django_db
    def test_create_invoice_empty_items_allowed(self, vendor_client, store):
        # items is optional — total should be 0
        payload = {'customer_name': 'No Items', 'items': [], 'notes': ''}
        r = vendor_client.post(INVOICE_URL, payload, format='json')
        assert r.status_code == 201
        invoice = Invoice.objects.get(store=store, customer_name='No Items')
        assert float(invoice.total) == 0.0

    @pytest.mark.django_db
    def test_create_invoice_customer_forbidden(self, customer_client):
        r = customer_client.post(INVOICE_URL, self.VALID_PAYLOAD, format='json')
        assert r.status_code in (403, 404)

    @pytest.mark.django_db
    def test_create_invoice_unauthenticated(self, anon_client):
        r = anon_client.post(INVOICE_URL, self.VALID_PAYLOAD, format='json')
        assert r.status_code == 401

    @pytest.mark.django_db
    def test_create_invoice_appears_in_list(self, vendor_client, store):
        vendor_client.post(INVOICE_URL, self.VALID_PAYLOAD, format='json')
        r = vendor_client.get(INVOICE_URL)
        assert r.status_code == 200
        assert r.json()['count'] == 1

    @pytest.mark.django_db
    def test_vendor_only_sees_own_invoices(self, vendor_client, vendor2_client, store, store2):
        vendor_client.post(INVOICE_URL, self.VALID_PAYLOAD, format='json')
        r = vendor2_client.get(INVOICE_URL)
        assert r.status_code == 200
        assert r.json()['count'] == 0

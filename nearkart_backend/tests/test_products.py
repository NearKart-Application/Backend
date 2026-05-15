"""
Tests — Products Module
Covers: create, list, detail, update, delete products
"""
import pytest
from apps.products.models import Product


BASE = '/api/v1/products'


@pytest.fixture
def product(db, store):
    return Product.objects.create(
        store=store,
        name='Test Product',
        description='A great product',
        price='299.00',
        category='fashion',
        is_available=True,
    )


# ── Create ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_create_product(vendor_client, store):
    response = vendor_client.post(f'{BASE}/', {
        'name': 'New Product',
        'description': 'Fresh stock',
        'price': '499.00',
        'category': 'fashion',
    })
    assert response.status_code == 201
    assert Product.objects.filter(store=store, name='New Product').exists()


@pytest.mark.django_db
def test_create_product_requires_store(vendor_client, vendor_user):
    response = vendor_client.post(f'{BASE}/', {
        'name': 'No Store Product',
        'price': '100.00',
        'category': 'fashion',
    })
    assert response.status_code in (400, 404)


@pytest.mark.django_db
def test_create_product_customer_forbidden(customer_client):
    response = customer_client.post(f'{BASE}/', {
        'name': 'Nope',
        'price': '10.00',
        'category': 'food',
    })
    assert response.status_code == 403


@pytest.mark.django_db
def test_create_product_unauthenticated(anon_client):
    response = anon_client.post(f'{BASE}/', {'name': 'x', 'price': '10', 'category': 'food'})
    assert response.status_code == 401


# ── List / Detail ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_products_by_store(customer_client, product, store):
    response = customer_client.get(f'{BASE}/?store={store.id}')
    assert response.status_code == 200
    results = response.json().get('results', response.json())
    names = [p['name'] for p in (results if isinstance(results, list) else [])]
    assert 'Test Product' in names


@pytest.mark.django_db
def test_get_product_detail(customer_client, product):
    response = customer_client.get(f'{BASE}/{product.id}/')
    assert response.status_code == 200
    assert response.json()['name'] == 'Test Product'


@pytest.mark.django_db
def test_get_nonexistent_product(customer_client):
    response = customer_client.get(f'{BASE}/00000000-0000-0000-0000-000000000000/')
    assert response.status_code == 404


# ── Update ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_update_product_owner(vendor_client, product):
    response = vendor_client.put(f'{BASE}/{product.id}/', {
        'name': 'Updated Product',
        'description': 'Updated desc',
        'price': '599.00',
        'category': 'fashion',
        'is_available': True,
    })
    assert response.status_code == 200
    product.refresh_from_db()
    assert product.name == 'Updated Product'


@pytest.mark.django_db
def test_update_product_other_vendor_forbidden(vendor2_client, product):
    response = vendor2_client.put(f'{BASE}/{product.id}/', {
        'name': 'Hijacked',
        'price': '1.00',
        'category': 'food',
    })
    assert response.status_code in (403, 404)


# ── Delete ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_delete_product_owner(vendor_client, product):
    response = vendor_client.delete(f'{BASE}/{product.id}/')
    assert response.status_code == 204
    assert not Product.objects.filter(id=product.id).exists()


@pytest.mark.django_db
def test_delete_product_other_vendor_forbidden(vendor2_client, product):
    response = vendor2_client.delete(f'{BASE}/{product.id}/')
    assert response.status_code in (403, 404)
    assert Product.objects.filter(id=product.id).exists()

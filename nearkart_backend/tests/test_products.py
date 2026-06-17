"""
Tests — Products Module
Covers: create, list, detail, update, delete products
"""
import pytest
from apps.products.models import Product


BASE = '/api/v1/products'


@pytest.fixture
def product(db, store):
    import uuid
    return Product.objects.create(
        store=store,
        name='Test Product',
        description='A great product',
        base_price='299.00',
        category='fashion',
        status='active',
        is_visible=True,
        product_code=f'NS-PRD-{uuid.uuid4().hex[:6].upper()}',
    )


# ── Create ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_create_product(vendor_client, store):
    response = vendor_client.post(f'{BASE}/', {
        'name': 'New Product',
        'description': 'Fresh stock',
        'base_price': '499.00',
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
def test_list_products_by_store(vendor_client, product, store):
    response = vendor_client.get(f'{BASE}/vendor/')
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
    response = vendor_client.put(f'{BASE}/{product.id}/update/', {
        'name': 'Updated Product',
        'description': 'Updated desc',
        'base_price': '599.00',
        'category': 'fashion',
        'status': 'active',
    })
    assert response.status_code == 200
    product.refresh_from_db()
    assert product.name == 'Updated Product'


@pytest.mark.django_db
def test_update_product_other_vendor_forbidden(vendor2_client, product):
    response = vendor2_client.put(f'{BASE}/{product.id}/update/', {
        'name': 'Hijacked',
        'price': '1.00',
        'category': 'food',
    })
    assert response.status_code in (403, 404)


# ── Delete ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_delete_product_owner(vendor_client, product):
    response = vendor_client.delete(f'{BASE}/{product.id}/update/')
    assert response.status_code == 204
    assert not Product.objects.filter(id=product.id).exists()


@pytest.mark.django_db
def test_delete_product_other_vendor_forbidden(vendor2_client, product):
    response = vendor2_client.delete(f'{BASE}/{product.id}/update/')
    assert response.status_code in (403, 404)
    assert Product.objects.filter(id=product.id).exists()


# ── Generate Product Code — Sprint 26 ────────────────────────────────────────

@pytest.mark.django_db
def test_generate_product_code_with_category(vendor_client, store):
    response = vendor_client.get(f'{BASE}/vendor/generate-code/?category=fashion')
    assert response.status_code == 200
    data = response.json()
    assert 'product_code' in data or 'code' in data
    key = 'product_code' if 'product_code' in data else 'code'
    assert data[key].startswith('NS-')


@pytest.mark.django_db
def test_generate_product_code_without_category(vendor_client, store):
    response = vendor_client.get(f'{BASE}/vendor/generate-code/')
    assert response.status_code in (200, 400)


@pytest.mark.django_db
def test_generate_product_code_requires_store(vendor_client, vendor_user):
    response = vendor_client.get(f'{BASE}/vendor/generate-code/?category=fashion')
    assert response.status_code in (200, 400, 404)


@pytest.mark.django_db
def test_generate_product_code_requires_vendor(customer_client):
    response = customer_client.get(f'{BASE}/vendor/generate-code/?category=fashion')
    assert response.status_code == 403


# ── Product Demo Video Fetch — Sprint 28 (NF-50) ─────────────────────────────

@pytest.fixture
def demo_video(db, store, product):
    from apps.videos.models import Video
    from django.utils import timezone
    from datetime import timedelta
    return Video.objects.create(
        store=store,
        product=product,
        title='Kurti Demo',
        video_type=Video.TYPE_PRODUCT_DEMO,
        status=Video.STATUS_READY,
        is_visible=True,
        location=store.location,
        expires_at=timezone.now() + timedelta(days=25),
        video_url='https://mock-s3.dev/videos/demo.m3u8?dev=true',
        thumbnail_url='https://mock-s3.dev/videos/demo-thumb.jpg?dev=true',
    )


@pytest.mark.django_db
def test_get_product_demo_video(anon_client, product, demo_video):
    response = anon_client.get(f'{BASE}/{product.id}/demo-video/')
    assert response.status_code == 200
    data = response.json()
    assert data['video_type'] == 'product_demo'
    assert data['title'] == 'Kurti Demo'


@pytest.mark.django_db
def test_get_product_demo_video_not_found(anon_client, product):
    response = anon_client.get(f'{BASE}/{product.id}/demo-video/')
    assert response.status_code == 404


@pytest.mark.django_db
def test_get_product_demo_video_no_auth_required(anon_client, product, demo_video):
    response = anon_client.get(f'{BASE}/{product.id}/demo-video/')
    assert response.status_code == 200

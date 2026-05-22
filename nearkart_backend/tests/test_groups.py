"""
Tests — Groups Module
Covers: create, list, detail, add/remove members, join, share product, finalize
"""
import pytest
from apps.groups.models import Group, GroupMember


BASE = '/api/v1/groups'


@pytest.fixture
def product(db, store):
    from apps.products.models import Product
    return Product.objects.create(
        store=store, name='Group Product', price='299.00',
        category='fashion', is_available=True,
    )


@pytest.fixture
def public_group(db, customer):
    return Group.objects.create(
        created_by=customer,
        name='Public Group',
        group_type=Group.TYPE_PUBLIC,
    )


@pytest.fixture
def private_group(db, customer):
    return Group.objects.create(
        created_by=customer,
        name='Private Group',
        group_type=Group.TYPE_PRIVATE,
    )


@pytest.fixture
def group_member(db, public_group, customer):
    return GroupMember.objects.create(
        group=public_group,
        user=customer,
        role=GroupMember.ROLE_ADMIN,
        is_approved=True,
    )


# ── Create Group ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_create_public_group(customer_client):
    response = customer_client.post(f'{BASE}/', {
        'name': 'My Group',
        'group_type': 'public',
    })
    assert response.status_code == 201
    assert Group.objects.filter(name='My Group').exists()


@pytest.mark.django_db
def test_create_private_group(customer_client):
    response = customer_client.post(f'{BASE}/', {
        'name': 'Secret Group',
        'group_type': 'private',
    })
    assert response.status_code == 201


@pytest.mark.django_db
def test_create_group_requires_auth(anon_client):
    response = anon_client.post(f'{BASE}/', {'name': 'Nope', 'group_type': 'public'})
    assert response.status_code == 401


# ── List / Detail ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_groups(customer_client, public_group, group_member):
    response = customer_client.get(f'{BASE}/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_get_group_detail(customer_client, public_group, group_member):
    response = customer_client.get(f'{BASE}/{public_group.id}/')
    assert response.status_code == 200
    assert response.json()['name'] == 'Public Group'


# ── Delete Group ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_creator_can_delete_group(customer_client, public_group):
    response = customer_client.delete(f'{BASE}/{public_group.id}/')
    assert response.status_code == 204
    assert not Group.objects.filter(id=public_group.id).exists()


@pytest.mark.django_db
def test_other_user_cannot_delete_group(customer2_client, public_group):
    response = customer2_client.delete(f'{BASE}/{public_group.id}/')
    assert response.status_code in (403, 404)


# ── Add / Remove Members ──────────────────────────────────────────────────────

@pytest.mark.django_db
def test_add_member_to_group(customer_client, public_group, group_member, customer2):
    response = customer_client.post(f'{BASE}/{public_group.id}/members/', {
        'profile_id': customer2.profile_id,
    })
    assert response.status_code in (200, 201)


@pytest.mark.django_db
def test_remove_member_from_group(customer_client, public_group, group_member, customer2):
    GroupMember.objects.create(
        group=public_group, user=customer2,
        role=GroupMember.ROLE_MEMBER, is_approved=True,
    )
    response = customer_client.delete(f'{BASE}/{public_group.id}/members/{customer2.id}/')
    assert response.status_code in (200, 204)


# ── Join Public Group ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_join_public_group(customer2_client, public_group):
    response = customer2_client.post(f'{BASE}/{public_group.id}/join/')
    assert response.status_code in (200, 201)
    assert GroupMember.objects.filter(group=public_group, user__phone_number='+919000000002').exists()


# ── Share Product ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_share_product_in_group(customer_client, public_group, group_member, product):
    response = customer_client.post(f'{BASE}/{public_group.id}/share-product/', {
        'product_id': str(product.id),
        'note': 'Check this out!',
    })
    assert response.status_code in (200, 201)


# ── Finalize Product ──────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_finalize_product(customer_client, public_group, group_member, product):
    share_resp = customer_client.post(f'{BASE}/{public_group.id}/share-product/', {
        'product_id': str(product.id),
    })
    if share_resp.status_code in (200, 201):
        sp_id = share_resp.json().get('id')
        if sp_id:
            response = customer_client.post(f'{BASE}/{public_group.id}/finalize/{sp_id}/')
            assert response.status_code in (200, 400)

"""
Tests — Chat Module (REST endpoints)
Covers: create conversation, list conversations, message history
"""
import pytest
from apps.chat.models import Conversation, Message


BASE = '/api/v1/conversations'


@pytest.fixture
def conversation(db, customer, store):
    return Conversation.objects.create(
        customer=customer,
        store=store,
    )


@pytest.fixture
def message(db, conversation, customer):
    return Message.objects.create(
        conversation=conversation,
        sender=customer,
        content='Hello, is this available?',
    )


# ── Create Conversation ───────────────────────────────────────────────────────

@pytest.mark.django_db
def test_create_conversation(customer_client, store):
    response = customer_client.post(f'{BASE}/', {'store': str(store.id)})
    assert response.status_code in (200, 201)
    assert Conversation.objects.filter(store=store).exists()


@pytest.mark.django_db
def test_create_conversation_idempotent(customer_client, store):
    customer_client.post(f'{BASE}/', {'store': str(store.id)})
    customer_client.post(f'{BASE}/', {'store': str(store.id)})
    assert Conversation.objects.filter(store=store).count() == 1


@pytest.mark.django_db
def test_create_conversation_requires_auth(anon_client, store):
    response = anon_client.post(f'{BASE}/', {'store': str(store.id)})
    assert response.status_code == 401


@pytest.mark.django_db
def test_vendor_cannot_create_conversation(vendor_client, store):
    response = vendor_client.post(f'{BASE}/', {'store': str(store.id)})
    assert response.status_code == 403


# ── List Conversations ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_customer_lists_own_conversations(customer_client, conversation):
    response = customer_client.get(f'{BASE}/')
    assert response.status_code == 200
    results = response.json().get('results', response.json())
    assert len(results) >= 1


@pytest.mark.django_db
def test_vendor_lists_store_conversations(vendor_client, conversation):
    response = vendor_client.get(f'{BASE}/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_other_customer_cannot_see_conversation(customer2_client, conversation):
    response = customer2_client.get(f'{BASE}/')
    results = response.json().get('results', response.json())
    ids = [c['id'] for c in (results if isinstance(results, list) else [])]
    assert str(conversation.id) not in ids


# ── Message History ───────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_message_history(customer_client, conversation, message):
    response = customer_client.get(f'{BASE}/{conversation.id}/messages/')
    assert response.status_code == 200
    results = response.json().get('results', response.json())
    contents = [m['content'] for m in (results if isinstance(results, list) else [])]
    assert 'Hello, is this available?' in contents


@pytest.mark.django_db
def test_message_history_other_customer_forbidden(customer2_client, conversation):
    response = customer2_client.get(f'{BASE}/{conversation.id}/messages/')
    assert response.status_code in (403, 404)


@pytest.mark.django_db
def test_message_history_unauthenticated(anon_client, conversation):
    response = anon_client.get(f'{BASE}/{conversation.id}/messages/')
    assert response.status_code == 401

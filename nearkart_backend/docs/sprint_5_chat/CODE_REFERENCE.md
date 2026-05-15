# Sprint 5 — Code Reference

All files, classes, fields, methods, and design decisions for the Chat Module.

---

## `apps/chat/models.py`

### class `Conversation`

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `id` | UUIDField | uuid4 | Primary key (from BaseModel) |
| `customer` | FK → User | — | CASCADE; `related_name='conversations_as_customer'` |
| `store` | FK → Store | — | CASCADE; `related_name='conversations'` |
| `last_message_at` | DateTimeField | null | Updated on every message send; indexed for inbox sort |
| `unread_count_customer` | PositiveIntegerField | `0` | Incremented when vendor sends; reset on customer `/read/` |
| `unread_count_vendor` | PositiveIntegerField | `0` | Incremented when customer sends; reset on vendor `/read/` |
| `is_active` | BooleanField | `True` | Soft-disable a conversation without deleting |
| `created_at` | DateTimeField | auto | From BaseModel |
| `updated_at` | DateTimeField | auto | From BaseModel |

**Constraints:**
- `unique_together = [('customer', 'store')]` — exactly one conversation per customer-store pair
- `ordering = ['-last_message_at']` — inbox sorted newest first

---

### class `Message`

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `id` | UUIDField | uuid4 | Primary key (from BaseModel) |
| `conversation` | FK → Conversation | — | CASCADE; `related_name='messages'` |
| `sender` | FK → User | — | CASCADE; `related_name='sent_messages'` |
| `content` | TextField | `''` | Plain text; blank for image/ref messages |
| `message_type` | CharField(20) | `'text'` | Enum: `text` / `image` / `product_ref` / `video_ref` |
| `media_url` | URLField(500) | `''` | S3/CDN URL for image type messages |
| `ref_id` | UUIDField | null | UUID of the referenced Product or Video |
| `is_read` | BooleanField | `False` | Marked True by the recipient's `/read/` call; indexed |
| `created_at` | DateTimeField | auto | From BaseModel; used for ordering |
| `updated_at` | DateTimeField | auto | From BaseModel |

**Message type usage:**
```
text        → content = "Hello!", media_url = "", ref_id = null
image       → content = "", media_url = "https://s3.../photo.jpg", ref_id = null
product_ref → content = "Check this out!", ref_id = <product UUID>, media_url = ""
video_ref   → content = "", ref_id = <video UUID>, media_url = ""
```

**Indexes:**
- `(conversation, created_at)` — for fast history queries

---

## `apps/chat/services.py`

### `FCMService`

**`_is_dev_fcm() → bool`**
Detects missing/example Firebase credentials by checking `FIREBASE_CREDENTIALS_PATH` setting. If absent, ends with `.json`, or contains `EXAMPLE` → dev mode.

**`FCMService.send_push(recipient, title, body, data=None)`**
- Fetches all active FCM tokens for the recipient from `auth_device_tokens`
- Dev mode → logs the push, does nothing else
- Production → calls `firebase_admin.messaging.send_each(messages)` to all tokens
- Silently handles exceptions (push failure must not break the chat flow)

---

### `ConversationService`

**`get_or_create(customer, store) → (Conversation, bool)`**
Wraps `Conversation.objects.get_or_create(customer=customer, store=store)`. Returns `(conv, True)` on create, `(conv, False)` if already exists.

**`list_for_user(user) → QuerySet`**
- Vendor → filters by `store=user.store`, returns all active conversations for that store
- Customer → filters by `customer=user`, returns all active conversations they have
- Both sorted by `-last_message_at`

**`save_message(conversation, sender, content, ...) → Message`**
- Creates `Message` record
- Atomically updates `conversation.last_message_at = now()`
- If sender is customer → `F('unread_count_vendor') + 1`
- If sender is vendor → `F('unread_count_customer') + 1`
- Both updates use `F()` expressions — safe under concurrent requests

**`mark_read(conversation, user)`**
- If user is customer → `unread_count_customer = 0`, marks all vendor's messages as `is_read=True`
- If user is vendor → `unread_count_vendor = 0`, marks all customer's messages as `is_read=True`
- Both done with bulk UPDATE — no per-row fetching

**`get_messages(conversation, before_id=None, limit=50) → list`**
- Queries messages ordered by `-created_at`, slices to 50
- If `before_id` given → fetches the pivot message's `created_at` and filters `created_at < pivot`
- Returns reversed list (oldest first, newest last)

**`user_belongs_to_conversation(user, conversation) → bool`**
- Returns True if `user.id == conversation.customer_id`
- OR if user is vendor and `conversation.store_id == user.store.id`

---

## `apps/chat/consumers.py`

### `ChatConsumer` — `AsyncJsonWebsocketConsumer`

**WebSocket URL:** `ws://localhost:8001/ws/conversations/<uuid>/?token=<jwt>`

**`connect()`**
1. Gets `user` from `scope['user']` (set by `JWTAuthMiddleware`)
2. Reads `conversation_id` from URL kwargs
3. Calls `_get_conversation()` — verifies user belongs to it
4. Joins channel group `conversation_{id}`
5. Accepts the connection; closes with code `4001` (no auth) or `4003` (not a member)

**`receive_json(content)`**
- Expects `{"type": "chat_message", "content": "..."}`
- Ignores other types and empty content silently
- Calls `_save_message()` → DB write
- Sends to channel group → all connected participants receive it
- Calls `_push_to_recipient()` → FCM to offline party

**`chat_message(event)`**
Called by the channel layer when a group_send fires. Forwards `event['message']` to the WebSocket connection.

**`disconnect(code)`**
Leaves the channel group on disconnect. Safe if group was never joined (uses `hasattr` guard).

**Serialized message shape** (sent over WebSocket):
```json
{
  "id": "uuid",
  "conversation_id": "uuid",
  "sender_id": "uuid",
  "sender_phone": "+91...",
  "sender_role": "customer",
  "content": "Hello!",
  "message_type": "text",
  "media_url": "",
  "ref_id": null,
  "is_read": false,
  "created_at": "2026-05-15T..."
}
```

---

## `apps/chat/views.py`

### `ConversationStartView` — `POST /conversations/start/`
- `permission_classes = [IsAuthenticated]`
- Customer: sends `store_id` → creates/gets conversation with that store
- Vendor: sends `customer_id` → creates/gets conversation with that customer (uses vendor's own store)
- Returns `201` on create, `200` on existing

### `ConversationListView` — `GET /conversations/`
- `permission_classes = [IsAuthenticated]`
- Delegates to `ConversationService.list_for_user(request.user)`
- Role-aware: vendor sees their store's inbox; customer sees their own inbox

### `MessageListView` — `GET /conversations/<id>/messages/`
- `permission_classes = [IsAuthenticated]`
- Checks `user_belongs_to_conversation` → 403 if not a member
- Optional `?before=<message_id>` param for paginating backwards (infinite scroll)
- Returns 50 messages max per call, oldest first

### `MarkReadView` — `PATCH /conversations/<id>/read/`
- `permission_classes = [IsAuthenticated]`
- Checks membership → 403 if not a member
- Resets caller's unread count + bulk-marks received messages as `is_read=True`

---

## `apps/chat/routing.py`

WebSocket URL pattern:
```python
re_path(r'^ws/conversations/(?P<conversation_id>[0-9a-f-]{36})/$', ChatConsumer.as_asgi())
```
Registered in `config/asgi.py` via `chat_urlpatterns`.

---

## How to Change Things in Future

### Add image message support (upload photo in chat)
1. Client gets S3 presigned URL from a new endpoint `POST /conversations/<id>/upload-url/`
2. Client PUTs the image to S3
3. Client sends WS message: `{"type": "chat_message", "message_type": "image", "media_url": "..."}`
4. Consumer saves with `message_type='image'`, `media_url=...`

### Add product sharing in chat
Client sends: `{"type": "chat_message", "message_type": "product_ref", "ref_id": "<product_uuid>", "content": "Check this out!"}`
Consumer saves with `message_type='product_ref'`, `ref_id=<uuid>`.

### Add read receipts over WebSocket
After `mark_read`, send a `group_send` event of type `read_receipt` to update the sender's chat UI.

### Change message page size
`ConversationService.get_messages(..., limit=50)` — change `50` to desired page size.

### Enable real FCM push
Set `FIREBASE_CREDENTIALS_PATH=/path/to/firebase-adminsdk.json` in `.env`. No code change needed.

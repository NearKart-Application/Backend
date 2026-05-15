# Sprint 5 — Chat (WebSocket)

**Goal:** Real-time chat between customer and vendor. Online = WebSocket. Offline = FCM push.
**Status:** Done ✅
**Completed:** 2026-05-15
**Depends on:** Sprint 3 (Store), Sprint 2 (Auth / DeviceToken)

---

## What Was Built

### Models
| Model | DB Table | Purpose |
|-------|----------|---------|
| `Conversation` | `conversations` | One per (customer, store) pair. Tracks unread counts and last_message_at for inbox sorting |
| `Message` | `messages` | Individual chat message. Types: text, image, product_ref, video_ref |

### REST Endpoints (4)
| Method | URL | Auth | What it does |
|--------|-----|------|-------------|
| POST | `/api/v1/conversations/start/` | Bearer JWT | Get or create a conversation (customer→store or vendor→customer) |
| GET | `/api/v1/conversations/` | Bearer JWT | List all my conversations sorted by last message |
| GET | `/api/v1/conversations/<id>/messages/` | Bearer JWT | Paginated message history (50/page, `?before=<id>`) |
| PATCH | `/api/v1/conversations/<id>/read/` | Bearer JWT | Reset my unread count to 0, mark messages as read |

### WebSocket Endpoint
```
ws://localhost:8001/ws/conversations/<conversation_id>/?token=<jwt_access_token>
```
- Client sends: `{"type": "chat_message", "content": "Hello!"}`
- Server broadcasts full message object to both participants in real-time
- Offline participant receives FCM push notification (dev mode: logged, not sent)

### Key Technical Decisions
- **One conversation per (customer, store)**: `unique_together` — calling start/ twice returns the same conversation (HTTP 200 vs 201 on create)
- **JWT over WebSocket**: Token passed as `?token=` query param — handled by `core.middleware.JWTAuthMiddleware` already in place
- **Channel group**: `conversation_{id}` — both participants join on connect, messages are broadcast to the group
- **Unread counts**: Separate `unread_count_customer` / `unread_count_vendor` — atomic `F()` increment on message send, reset to 0 on `/read/`
- **last_message_at indexed**: Enables fast inbox sort without full table scan
- **Dev FCM mode**: Detected by missing/example `FIREBASE_CREDENTIALS_PATH` → logs push, doesn't call Firebase SDK
- **Pagination**: `GET /messages/?before=<message_id>` — returns 50 messages older than the given ID for infinite scroll
- **Message types**: `text | image | product_ref | video_ref` — enables future sharing of products/videos in chat

---

## Files Changed
```
apps/chat/models.py        — Conversation, Message models
apps/chat/serializers.py   — ConversationSerializer, MessageSerializer
apps/chat/services.py      — ConversationService, FCMService
apps/chat/consumers.py     — ChatConsumer (AsyncJsonWebsocketConsumer)
apps/chat/routing.py       — chat_urlpatterns (WebSocket URL)
apps/chat/views.py         — 4 REST view classes
apps/chat/urls.py          — URL patterns
apps/chat/admin.py         — Admin registration
apps/chat/migrations/0001_initial.py
```

---

## Docs
- [API_TEST_FLOW.md](API_TEST_FLOW.md) — step-by-step curl + WebSocket test guide

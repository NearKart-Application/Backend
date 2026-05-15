# Sprint 6 — Blacklist Engine

**Status:** Done ✅  
**Verified on:** 2026-05-15

---

## What This Sprint Does

Vendors can block customers from interacting with their store.  
A blocked customer cannot follow, review, start a chat, or connect via WebSocket.  
Unblocking restores full access immediately.

---

## Endpoints

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| POST | `/api/v1/stores/<store_id>/blacklist/<customer_id>/` | Vendor JWT | Block or unblock (toggle) |
| GET | `/api/v1/stores/<store_id>/blacklist/` | Vendor JWT | List all blocked customers |

---

## Enforcement Points

| Action | Blocked Response |
|--------|-----------------|
| `POST /stores/<id>/follow/` | `403 blacklisted` |
| `POST /stores/<id>/review/` | `403 blacklisted` |
| `POST /conversations/start/` | `403 blacklisted` |
| WebSocket `ws://.../ws/conversations/<id>/` | Close code `4003` |

---

## Key Design Decisions

- **Per store, not per vendor account** — a vendor could own multiple stores in future; each store has its own blacklist
- **Toggle on single endpoint** — `POST` on same URL blocks then unblocks; no separate DELETE endpoint
- **Silent WS close** — blocked customer gets `4003` (same as "not a member"), no specific error code exposed
- **Read history preserved** — blocked customer can still call `GET /conversations/<id>/messages/` to read old history; only new messages are blocked
- **Only customers can be blocked** — endpoint validates `role == 'customer'`; vendor-to-vendor blocking not a use case

---

## Files Changed

| File | Change |
|------|--------|
| `apps/blacklist/models.py` | `Blacklist` model — store + customer + reason |
| `apps/blacklist/services.py` | `BlacklistService` — toggle, is_blocked, list_for_store |
| `apps/blacklist/serializers.py` | `BlacklistSerializer` |
| `apps/blacklist/views.py` | `BlacklistToggleView`, `BlacklistListView` |
| `apps/blacklist/admin.py` | Admin registration |
| `apps/blacklist/migrations/0001_initial.py` | Creates `blacklists` table |
| `apps/stores/urls.py` | Two new URL patterns added |
| `apps/stores/views.py` | Blacklist check in `StoreFollowView`, `StoreReviewView` |
| `apps/chat/views.py` | Blacklist check in `ConversationStartView` |
| `apps/chat/consumers.py` | Blacklist check in `ChatConsumer._get_conversation()` |

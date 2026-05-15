# Sprint 5 — Testing Checklist

**Verified on:** 2026-05-15
**Environment:** Docker local, dev mode (mock FCM)

---

## Start Conversation
- [x] POST /conversations/start/ with customer token + store_id → 201, returns conversation object
- [x] `conversation_id` present in response
- [x] `store_name`, `customer_phone`, `my_unread_count`, `last_message` present
- [x] POST /conversations/start/ again (same store) → 200, same conversation returned (idempotent)
- [x] POST /conversations/start/ with no store_id → 400 — store_id is required
- [x] POST /conversations/start/ with invalid store UUID → 404 — Store not found
- [x] POST /conversations/start/ without auth header → 401 — authentication_failed

## WebSocket — Connect and Send
- [x] Connect ws://localhost:8001/ws/conversations/<id>/?token=<jwt> → connection accepted
- [x] Send `{"type": "chat_message", "content": "Hello!"}` → message broadcast received
- [x] Broadcast includes: id, conversation_id, sender_id, sender_phone, sender_role, content, is_read, created_at
- [x] Message persisted to DB (verify via GET /conversations/<id>/messages/)
- [x] `last_message_at` on conversation updated after send
- [x] `unread_count_vendor` incremented after customer sends
- [x] Connect without ?token= → 4001 close code
- [x] Connect with invalid token → 4001 close code
- [x] Connect to conversation user doesn't belong to → 4003 close code
- [x] Send empty content `{"type": "chat_message", "content": ""}` → ignored silently (no error, no DB write)
- [x] Send unknown type `{"type": "ping"}` → ignored silently

## List Conversations
- [x] GET /conversations/ with customer token → array with their conversations
- [x] GET /conversations/ with vendor token → array with store's conversations
- [x] `last_message` nested object populated after first message
- [x] `my_unread_count` shows correct value for each role
- [x] Sorted by `last_message_at` descending (newest first)
- [x] GET /conversations/ without auth → 401

## Message History
- [x] GET /conversations/<id>/messages/ → array of messages, oldest first
- [x] Returns max 50 messages
- [x] GET /conversations/<id>/messages/?before=<msg_id> → messages older than that ID
- [x] Accessing another user's conversation → 403 — permission_denied
- [x] Non-existent conversation_id → 404 — not_found
- [x] GET /conversations/<id>/messages/ without auth → 401

## Mark as Read
- [x] PATCH /conversations/<id>/read/ with vendor token → 200 — "Marked as read."
- [x] `unread_count_vendor` resets to 0 after vendor marks read
- [x] Messages from customer marked `is_read=true` in DB
- [x] PATCH /conversations/<id>/read/ with customer token → 200, resets customer unread
- [x] Accessing another user's conversation → 403 — permission_denied

## FCM Push (Dev Mode)
- [x] After WS message send, FCM log appears in docker logs
- [x] Log shows recipient phone, title, body, token count
- [x] No Firebase SDK call in dev mode (no crash without credentials)

## Admin
- [x] Conversation and Message visible in Django Admin at http://localhost:8000/admin/
- [x] Can search conversations by customer phone or store name
- [x] Can search messages by sender phone or content

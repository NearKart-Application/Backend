# Sprint 5 — Postman Guide

## Environment Variables (add to NearKart Local environment)

| Variable | Value | Set by |
|----------|-------|--------|
| `base_url` | `http://localhost:8000/api/v1` | Manual |
| `ws_url` | `ws://localhost:8001` | Manual |
| `vendor_token` | (empty) | OTP verify script |
| `customer_token` | (empty) | OTP verify script |
| `store_id` | (empty) | Sprint 3 |
| `conversation_id` | (empty) | Start conversation script |

---

## Collection: Sprint 5 — Chat

### 1. Start Conversation
- **Method:** POST
- **URL:** `{{base_url}}/conversations/start/`
- **Auth:** Bearer `{{customer_token}}`
- **Body (JSON):**
```json
{
  "store_id": "{{store_id}}"
}
```
- **Tests tab (auto-save conversation_id):**
```javascript
const r = pm.response.json();
if (r.id) {
    pm.environment.set("conversation_id", r.id);
    console.log("conversation_id saved:", r.id);
}
```
- **Expected 201** on first call, **200** on subsequent calls (idempotent)

---

### 2. List Conversations (Inbox)
- **Method:** GET
- **URL:** `{{base_url}}/conversations/`
- **Auth:** Bearer `{{customer_token}}` or `{{vendor_token}}`
- **No body**
- **Expected:** Array sorted by `last_message_at` descending. Each item has `my_unread_count` and `last_message`

---

### 3. Message History
- **Method:** GET
- **URL:** `{{base_url}}/conversations/{{conversation_id}}/messages/`
- **Auth:** Bearer `{{customer_token}}`
- **No body**
- **Expected:** Array of up to 50 messages, oldest first

For older messages (pagination):
- **URL:** `{{base_url}}/conversations/{{conversation_id}}/messages/?before={{oldest_message_id}}`

---

### 4. Mark as Read
- **Method:** PATCH
- **URL:** `{{base_url}}/conversations/{{conversation_id}}/read/`
- **Auth:** Bearer `{{vendor_token}}` (or customer token)
- **No body**
- **Expected:** `{"message": "Marked as read."}`
- **Effect:** Resets caller's unread count to 0

---

## WebSocket Testing (Postman v10.10+)

Postman now supports WebSocket connections natively.

### Setup a WebSocket request:
1. Click **New** → **WebSocket**
2. URL: `ws://localhost:8001/ws/conversations/{{conversation_id}}/?token={{customer_token}}`
3. Click **Connect**
4. In the message box, type:
```json
{"type": "chat_message", "content": "Hello from Postman!"}
```
5. Click **Send**
6. You will see the broadcast in the **Messages** pane immediately

> Note: `{{conversation_id}}` and `{{customer_token}}` are resolved from your Postman environment.

### Testing two participants:
- Open two WebSocket tabs — one with `customer_token`, one with `vendor_token`
- Send from one → see it appear in the other in real-time

---

## Alternative: wscat CLI Testing

Install: `npm install -g wscat`

```bash
# Connect as customer
wscat -c "ws://localhost:8001/ws/conversations/$CONV_ID/?token=$CUSTOMER_TOKEN"

# Once connected, type and press Enter:
{"type": "chat_message", "content": "Hello!"}
```

---

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| 400 — store_id is required | Missing store_id in body | Add `"store_id": "{{store_id}}"` |
| 404 — Store not found | Invalid or inactive store_id | Check store_id is correct and store is_active=true |
| 403 — permission_denied | Accessing another user's conversation | Use the correct token for that conversation |
| 401 — authentication_failed | No Authorization header | Add `Bearer {{customer_token}}` |
| WS 4001 close | No token in query string | Add `?token={{customer_token}}` to WS URL |
| WS 4003 close | User not part of conversation | Check conversation_id belongs to that user |

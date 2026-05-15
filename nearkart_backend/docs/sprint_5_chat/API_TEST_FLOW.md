# Sprint 5 — Chat API Test Flow

**Base URL:** `http://localhost:8000/api/v1`
**WebSocket:** `ws://localhost:8001/ws/conversations/<id>/?token=<jwt>`
**Dev OTP:** always `123456`

---

## Prerequisites
1. Docker running: `docker compose up -d`
2. Vendor token (phone `+919999999999`) and store already created (Sprint 3)
3. Customer token (phone `+916000000001`)

---

## STEP 1 — Get Tokens

```bash
# Vendor token
curl -X POST http://localhost:8000/api/v1/auth/otp/send/ \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+919999999999"}'

VENDOR_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/otp/verify/ \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+919999999999", "otp": "123456"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access'])")

# Customer token
curl -X POST http://localhost:8000/api/v1/auth/otp/send/ \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+916000000001"}'

CUSTOMER_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/otp/verify/ \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+916000000001", "otp": "123456"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access'])")
```

---

## STEP 2 — Start Conversation (Customer → Store)

```bash
curl -X POST http://localhost:8000/api/v1/conversations/start/ \
  -H "Authorization: Bearer $CUSTOMER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"store_id": "<your-store-uuid>"}'
```
**Expected 201:**
```json
{
  "id": "68fe68f7-...",
  "store_id": "6c8adfdd-...",
  "store_name": "Fashion Hub",
  "customer_phone": "+916000000001",
  "my_unread_count": 0,
  "last_message": null,
  "last_message_at": null,
  "is_active": true,
  "created_at": "2026-05-15T..."
}
```
> Calling again returns 200 (same conversation — idempotent).

Save `id` as `CONV_ID`.

---

## STEP 3 — Connect WebSocket and Send Message

```python
import asyncio, json, websockets

TOKEN   = "<CUSTOMER_TOKEN>"
CONV_ID = "<your-conv-id>"

async def chat():
    uri = f"ws://localhost:8001/ws/conversations/{CONV_ID}/?token={TOKEN}"
    async with websockets.connect(uri) as ws:
        # Send a message
        await ws.send(json.dumps({"type": "chat_message", "content": "Hello!"}))
        # Receive the broadcast
        print(json.loads(await ws.recv()))

asyncio.run(chat())
```
**Expected broadcast:**
```json
{
  "id": "448b97e3-...",
  "conversation_id": "68fe68f7-...",
  "sender_id": "fbe9358d-...",
  "sender_phone": "+916000000001",
  "sender_role": "customer",
  "content": "Hello!",
  "message_type": "text",
  "media_url": "",
  "ref_id": null,
  "is_read": false,
  "created_at": "2026-05-15T..."
}
```
> Both participants (customer + vendor) connected to the same conversation receive this instantly.
> If the vendor is offline → FCM push is sent to their registered device tokens (dev mode: logged only).

---

## STEP 4 — List Conversations

```bash
# Customer sees their conversations
curl http://localhost:8000/api/v1/conversations/ \
  -H "Authorization: Bearer $CUSTOMER_TOKEN"

# Vendor sees all conversations for their store
curl http://localhost:8000/api/v1/conversations/ \
  -H "Authorization: Bearer $VENDOR_TOKEN"
```
**Expected:** Array sorted by `last_message_at` descending. Each item includes `last_message` and `my_unread_count`.

---

## STEP 5 — Message History (REST)

```bash
# Latest 50 messages
curl "http://localhost:8000/api/v1/conversations/$CONV_ID/messages/" \
  -H "Authorization: Bearer $CUSTOMER_TOKEN"

# Older messages (pagination — pass the oldest message id you have)
curl "http://localhost:8000/api/v1/conversations/$CONV_ID/messages/?before=<oldest-message-id>" \
  -H "Authorization: Bearer $CUSTOMER_TOKEN"
```
**Expected:** Array of messages, oldest first, newest last (max 50).

---

## STEP 6 — Mark as Read

```bash
curl -X PATCH "http://localhost:8000/api/v1/conversations/$CONV_ID/read/" \
  -H "Authorization: Bearer $VENDOR_TOKEN"
```
**Expected 200:**
```json
{"message": "Marked as read."}
```
> Resets `unread_count_vendor` to 0 and marks all unread messages from customer as `is_read=true`.

---

## Error Reference

| Scenario | Request | Expected |
|----------|---------|----------|
| No store_id on start | POST /start/ `{}` | 400 — store_id is required |
| Invalid store UUID | POST /start/ with non-existent store_id | 404 — Store not found |
| Unauthorized WS connect | Connect without `?token=` | 4001 close code |
| Outsider accesses conversation | GET /messages/ with unrelated user | 403 — permission_denied |
| No auth on list | GET /conversations/ — no header | 401 — authentication_failed |
| Empty message over WS | `{"type": "chat_message", "content": ""}` | Ignored silently |
| Wrong WS message type | `{"type": "ping"}` | Ignored silently |

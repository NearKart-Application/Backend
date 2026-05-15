# Sprint 6 — Postman Guide

## Environment Variables

| Variable | Value | Set by |
|----------|-------|--------|
| `base_url` | `http://localhost:8000/api/v1` | Manual |
| `vendor_token` | (empty) | OTP verify script |
| `store_id` | (empty) | Sprint 3 Create Store |
| `customer_id` | (empty) | Customer OTP verify script (see below) |

---

## Auto-Save customer_id

Paste this in the **Tests** tab of the customer Verify OTP request:

```js
const r = pm.response.json();
if (r.user && r.user.id) {
    pm.environment.set("customer_id", r.user.id);
    console.log("customer_id saved:", r.user.id);
}
```

---

## Collection: Sprint 6 — Blacklist

### 1. Block a Customer

- **Method:** POST
- **URL:** `{{base_url}}/stores/{{store_id}}/blacklist/{{customer_id}}/`
- **Auth:** Bearer `{{vendor_token}}`
- **Body:**
```json
{ "reason": "Spam reviews" }
```
- **Expected:** `{"blocked": true, "customer_id": "...", "reason": "Spam reviews", "message": "Customer blocked."}`

---

### 2. Unblock the Same Customer  (same endpoint — toggle)

- **Method:** POST
- **URL:** `{{base_url}}/stores/{{store_id}}/blacklist/{{customer_id}}/`
- **Auth:** Bearer `{{vendor_token}}`
- **Body:**
```json
{}
```
- **Expected:** `{"blocked": false, "customer_id": "...", "reason": null, "message": "Customer unblocked."}`

---

### 3. List Blocked Customers

- **Method:** GET
- **URL:** `{{base_url}}/stores/{{store_id}}/blacklist/`
- **Auth:** Bearer `{{vendor_token}}`
- **Expected:** Array of blocked customers:
```json
[
  {
    "customer_id": "...",
    "customer_phone": "+919000000002",
    "reason": "Spam reviews",
    "blocked_at": "2026-05-15T..."
  }
]
```

---

## Blacklist Enforcement — Test These Manually

After blocking `customer_id`, use `customer_token` to verify enforcement:

### 4. Blocked Customer Follows Store  (expect 403)
- **Method:** POST
- **URL:** `{{base_url}}/stores/{{store_id}}/follow/`
- **Auth:** Bearer `{{customer_token}}`
- **Expected:** `{"error": "blacklisted", "message": "You cannot follow this store."}`

### 5. Blocked Customer Reviews Store  (expect 403)
- **Method:** POST
- **URL:** `{{base_url}}/stores/{{store_id}}/review/`
- **Auth:** Bearer `{{customer_token}}`
- **Body:** `{"rating": 1, "comment": "bad"}`
- **Expected:** `{"error": "blacklisted", "message": "..."}`

### 6. Blocked Customer Starts Conversation  (expect 403)
- **Method:** POST
- **URL:** `{{base_url}}/conversations/start/`
- **Auth:** Bearer `{{customer_token}}`
- **Body:** `{"store_id": "{{store_id}}"}`
- **Expected:** `{"error": "blacklisted", "message": "You cannot start a conversation with this store."}`

---

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| 403 — permission_denied (block) | Vendor doesn't own the store | Use correct vendor token |
| 403 — Vendor access only | Using customer token to block | Use vendor token |
| 404 — Store not found | Wrong store_id | Check `store_id` env var |
| 404 — Customer not found | Wrong customer_id | Get customer_id from OTP verify |
| 401 — authentication_failed | No Authorization header | Add Bearer token |
| 403 — blacklisted | Blocked customer hitting protected endpoint | Expected — enforcement working |

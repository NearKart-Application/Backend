# Sprint 27 — Postman Guide: Store Click Tracking

**Base URL:** `http://192.168.x.x:8000/api/v1`

---

## Request 1 — Get Vendor Stats (verify new fields)

```
GET {{base_url}}/stores/mine/stats/
Authorization: Bearer {{vendor_token}}
```

**Expected 200:**
```json
{
  "store_name": "Sneha's Fashion House",
  "store_address": "123 MG Road, Banjara Hills",
  "active_reservations": 2,
  "total_products": 14,
  "follower_count": 38,
  "store_views": 127,
  "inquiries_pending": 3,
  "products_need_action": 1
}
```

**Verify:**
- `store_views` is a non-zero integer (not `0`, not missing)
- `inquiries_pending` reflects unread chat conversations
- `products_need_action` reflects active out-of-stock products

---

## Request 2 — Trigger a Store View (as customer)

```
GET {{base_url}}/stores/{{store_id}}/
Authorization: Bearer {{customer_token}}
```

**Expected 200:** Store detail response.

Call this 3 times with the same customer token — should count as **1** unique visit for today (HyperLogLog deduplication).

Call with a different customer token — `store_views` count should increase by 1 on the next stats call.

---

## Request 3 — Verify Store Views Increment

```
GET {{base_url}}/stores/mine/stats/
Authorization: Bearer {{vendor_token}}
```

After calling Request 2 with a new customer: `store_views` should be higher than before.

---

## Request 4 — Verify Inquiries Pending

### Step 1: Customer sends a message
```
POST {{base_url}}/chat/{{store_id}}/messages/
Authorization: Bearer {{customer_token}}
Content-Type: application/json
```
```json
{ "content": "Is this product available?" }
```

### Step 2: Check stats — inquiries should increase
```
GET {{base_url}}/stores/mine/stats/
Authorization: Bearer {{vendor_token}}
```
`inquiries_pending` should be ≥ 1.

### Step 3: Vendor reads the message
```
POST {{base_url}}/chat/{{conversation_id}}/read/
Authorization: Bearer {{vendor_token}}
```

### Step 4: Check stats again — inquiries should decrease
`inquiries_pending` should drop by 1.

---

## Request 5 — Verify Products Need Action

### Step 1: Set a product variant stock to 0
```
PATCH {{base_url}}/products/{{product_id}}/variants/{{variant_id}}/
Authorization: Bearer {{vendor_token}}
Content-Type: application/json
```
```json
{ "stock_quantity": 0 }
```
(If the product has multiple variants, set all to 0.)

### Step 2: Check stats
```
GET {{base_url}}/stores/mine/stats/
Authorization: Bearer {{vendor_token}}
```
`products_need_action` should increase by 1.

### Step 3: Restock the variant
```
PATCH {{base_url}}/products/{{product_id}}/variants/{{variant_id}}/
Authorization: Bearer {{vendor_token}}
Content-Type: application/json
```
```json
{ "stock_quantity": 10 }
```

### Step 4: Check stats again
`products_need_action` should decrease by 1.

---

## Request 6 — Unauthenticated Store View (should not count)

```
GET {{base_url}}/stores/{{store_id}}/
```
*(No Authorization header)*

Call stats endpoint after — `store_views` should NOT increase.

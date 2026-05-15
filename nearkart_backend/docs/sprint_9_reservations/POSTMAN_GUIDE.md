# Sprint 9 — Postman Guide

## Environment Variables

| Variable | Value | Set by |
|----------|-------|--------|
| `base_url` | `http://localhost:8000/api/v1` | Manual |
| `vendor_token` | (empty) | OTP verify script |
| `customer_token` | (empty) | OTP verify script |
| `store_id` | (empty) | Sprint 3 Create Store |
| `product_id` | (empty) | Sprint 3 Create Product |
| `reservation_id` | (empty) | Create Reservation script below |

## Auto-Save Reservation ID

Paste in the **Tests** tab of the Create Reservation request:

```js
const r = pm.response.json();
if (r.id) {
    pm.environment.set("reservation_id", r.id);
    console.log("reservation_id saved:", r.id);
}
```

---

## Collection: Sprint 9 — Reservations

### 1. Create Reservation

- **Method:** POST
- **URL:** `{{base_url}}/reservations/`
- **Auth:** Bearer `{{customer_token}}`
- **Body:**
```json
{
  "store_id": "{{store_id}}",
  "product_id": "{{product_id}}",
  "quantity": 2,
  "note": "Please keep ready by 6 PM"
}
```
- **Expected:** 201 — reservation object with `status: pending`, `hours_left: 2.0`

---

### 2. List Reservations (Customer view)

- **Method:** GET
- **URL:** `{{base_url}}/reservations/list/`
- **Auth:** Bearer `{{customer_token}}`
- **Expected:** Array of customer's reservations

---

### 3. List Reservations (Vendor view)

- **Method:** GET
- **URL:** `{{base_url}}/reservations/list/`
- **Auth:** Bearer `{{vendor_token}}`
- **Expected:** Array of all reservations received by the vendor's store

---

### 4. Reservation Detail

- **Method:** GET
- **URL:** `{{base_url}}/reservations/{{reservation_id}}/`
- **Auth:** Bearer `{{customer_token}}` or `{{vendor_token}}`
- **Expected:** Full reservation object

---

### 5. Vendor Confirms Reservation

- **Method:** PATCH
- **URL:** `{{base_url}}/reservations/{{reservation_id}}/status/`
- **Auth:** Bearer `{{vendor_token}}`
- **Body:**
```json
{ "status": "confirmed", "vendor_note": "Ready for pickup after 5 PM!" }
```
- **Expected:** `status: confirmed`, `vendor_note` populated

---

### 6. Vendor Rejects Reservation

- **Method:** PATCH
- **URL:** `{{base_url}}/reservations/{{reservation_id}}/status/`
- **Auth:** Bearer `{{vendor_token}}`
- **Body:**
```json
{ "status": "cancelled", "vendor_note": "Out of stock, sorry." }
```
- **Expected:** `status: cancelled`

---

### 7. Vendor Marks Completed

- **Method:** PATCH
- **URL:** `{{base_url}}/reservations/{{reservation_id}}/status/`
- **Auth:** Bearer `{{vendor_token}}`
- **Body:**
```json
{ "status": "completed" }
```
- **Expected:** `status: completed` (must be confirmed first)

---

### 8. Customer Cancels Reservation

- **Method:** POST
- **URL:** `{{base_url}}/reservations/{{reservation_id}}/cancel/`
- **Auth:** Bearer `{{customer_token}}`
- **Body:** (empty)
- **Expected:** `status: cancelled` (only works on pending reservations)

---

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| 404 — Product not found or not available | Wrong product_id or product not active | Use active product from the store |
| 404 — Store not found | Wrong store_id or store inactive | Check store_id |
| 403 — blacklisted | Customer blocked by this store | Use a different customer |
| 403 — Vendor access only | Customer trying to update status | Use vendor_token |
| 400 — Cannot confirmed a confirmed reservation | Already confirmed | Check current status |
| 400 — Only confirmed reservations can be completed | Trying to complete a pending reservation | Confirm first, then complete |
| 400 — Cannot cancel a completed reservation | Already done | Cannot undo completed |
| 401 — authentication_failed | No token | Add Bearer token |

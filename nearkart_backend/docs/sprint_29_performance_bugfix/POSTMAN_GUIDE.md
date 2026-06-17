# Sprint 29 — Postman Guide

No new endpoints were added. This guide covers how to verify performance changes and bug fixes
using existing endpoints.

Add a new folder inside your existing Postman collection: **"29 — Performance · Bug Fixes"**

Variables needed (should already be set from earlier sprints):

| Variable | Value |
|----------|-------|
| `base_url` | `http://localhost:8000/api/v1` |
| `vendor_token` | JWT from OTP verify (vendor account) |
| `customer_token` | JWT from OTP verify (customer account) |
| `admin_token` | JWT from OTP verify (admin account) |
| `store_id` | UUID of vendor's store |
| `product_id` | UUID of a product in vendor's store |
| `review_id` | UUID of a review on vendor's store |

---

## 1 — Pagination Verification

### Vendor Products (paginated)

```
GET {{base_url}}/vendor/products/
Authorization: Bearer {{vendor_token}}
```

Expected response shape:
```json
{
  "count": 15,
  "next": "http://localhost:8000/api/v1/vendor/products/?limit=20&offset=20",
  "previous": null,
  "results": [...]
}
```

**Tests tab:**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
const d = pm.response.json();
pm.test("Paginated", () => {
  pm.expect(d).to.have.property('count');
  pm.expect(d).to.have.property('results');
  pm.expect(d.results).to.be.an('array');
});
```

---

### Vendor Products — Custom Page Size

```
GET {{base_url}}/vendor/products/?limit=5&offset=0
Authorization: Bearer {{vendor_token}}
```

Expected: max 5 items in `results`.

---

### My Videos (paginated)

```
GET {{base_url}}/videos/my/
Authorization: Bearer {{vendor_token}}
```

Expected: paginated response with `count` + `results`.

---

### Admin Store List (paginated)

```
GET {{base_url}}/admin/stores/
Authorization: Bearer {{admin_token}}
```

Expected: paginated response.

---

### Loyalty Transactions (paginated)

```
GET {{base_url}}/loyalty/transactions/
Authorization: Bearer {{vendor_token}}
```

Expected: paginated response (previously capped at 50 hardcoded).

---

## 2 — Following Feed Performance

### Follow a Store

```
POST {{base_url}}/stores/{{store_id}}/follow/
Authorization: Bearer {{customer_token}}
```

Expected: `200 {"following": true}`

---

### Get Following Feed

```
GET {{base_url}}/products/feed/
Authorization: Bearer {{customer_token}}
```

Expected: products from followed stores, with `store` object included.

**Tests tab:**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
const d = pm.response.json();
const products = Array.isArray(d) ? d : d.results;
pm.test("Has store object", () => {
  if (products.length > 0) {
    pm.expect(products[0]).to.have.property('store');
  }
});
```

---

## 3 — Bug Fix: Review Reply (was NameError)

### Post a Review (as customer)

```
POST {{base_url}}/stores/{{store_id}}/reviews/
Authorization: Bearer {{customer_token}}
Content-Type: application/json

{
  "rating": 4,
  "comment": "Great store, fast service"
}
```

Expected: `200` or `201`

Add to Tests tab to save review_id:
```javascript
pm.test("Status 200 or 201", () => pm.expect(pm.response.code).to.be.oneOf([200, 201]));
const d = pm.response.json();
pm.collectionVariables.set("review_id", d.id);
```

---

### Reply to Review (as vendor)

```
POST {{base_url}}/stores/{{store_id}}/reviews/{{review_id}}/reply/
Authorization: Bearer {{vendor_token}}
Content-Type: application/json

{
  "reply": "Thank you for your kind words!"
}
```

Expected: `200` — NOT `500 NameError`.

---

### Reply to Review from Wrong Store

```
POST {{base_url}}/stores/{{other_store_id}}/reviews/{{review_id}}/reply/
Authorization: Bearer {{vendor_token}}
Content-Type: application/json

{
  "reply": "Test"
}
```

Expected: `404`

---

## 4 — Bug Fix: PDF Invoice Export (was AttributeError)

### Export Monthly Earnings PDF

```
GET {{base_url}}/stores/{{store_id}}/earnings/pdf/?month=2026-05
Authorization: Bearer {{vendor_token}}
```

Expected: `200` — response `Content-Type: application/pdf` — NOT `500 AttributeError`.

**Verify:**
- Download the PDF
- Invoice reference numbers appear as `#XXXXXXXX` format
- Totals show `₹XX.XX`
- Total at bottom matches sum of rows

---

## 5 — Bug Fix: Review Notification (correct store name)

### Post a Review

```
POST {{base_url}}/stores/{{store_id}}/reviews/
Authorization: Bearer {{customer_token}}
Content-Type: application/json

{
  "rating": 5,
  "comment": "Amazing!"
}
```

### Check Vendor Notifications

```
GET {{base_url}}/notifications/
Authorization: Bearer {{vendor_token}}
```

Expected: most recent notification has:
- `title` = `"New Review — <Your Store Name>"` (NOT customer phone number)
- `data.store_id` = store UUID (NOT the store name string)

**Tests tab:**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
const d = pm.response.json();
const notifs = Array.isArray(d) ? d : d.results;
const reviewNotif = notifs.find(n => n.notification_type === 'new_review');
if (reviewNotif) {
  pm.test("Title contains store name not phone", () => {
    pm.expect(reviewNotif.title).to.include('New Review');
    pm.expect(reviewNotif.title).to.not.match(/^\+91/);
  });
  pm.test("data.store_id is UUID", () => {
    pm.expect(reviewNotif.data.store_id).to.match(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
    );
  });
}
```

---

## 6 — Migration Check

```bash
python manage.py showmigrations notifications
python manage.py showmigrations products
python manage.py showmigrations reservations
python manage.py showmigrations stores
```

All four new migrations must show `[X]` (applied).

---

## Quick Reference — Changed Endpoints (shape change only)

| Endpoint | Change |
|----------|--------|
| `GET /vendor/products/` | Now paginated (`count` + `results`) |
| `GET /videos/my/` | Now paginated |
| `GET /analytics/videos/` | Now paginated |
| `GET /billing/transactions/` | Now paginated |
| `GET /admin/stores/` | Now paginated |
| `GET /admin/users/` | Now paginated |
| `GET /admin/products/` | Now paginated |
| `GET /loyalty/transactions/` | Now paginated (was hardcoded to 50) |
| `POST /stores/{id}/reviews/{id}/reply/` | Bug fixed (was 500) |
| `GET /stores/{id}/earnings/pdf/` | Bug fixed (was 500) |

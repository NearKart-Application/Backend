# Sprint 3 — Store & Product Module: API Test Flow

Base URL: `http://localhost:8000/api/v1`

All authenticated requests require the header:
```
Authorization: Bearer <access_token>
```

Obtain tokens from Sprint 2 auth endpoints before testing these.

---

## Prerequisites

1. You have a **vendor** account (user_type = `vendor`). Create one via Sprint 2 OTP flow.
2. Obtain access token from `POST /auth/token/` or `POST /auth/otp/verify/`.
3. A **customer** account is needed to test follow / wishlist / review.

---

## Store Endpoints

### 1. Create Store (Vendor only)

**POST** `/stores/`

Auth: Required (vendor JWT)

```json
{
  "name": "Fashion Hub",
  "description": "Trendy clothes for everyone",
  "category": "fashion",
  "phone": "+919876543210",
  "address": "123 Anna Salai, Chennai",
  "latitude": 13.0418,
  "longitude": 80.2341,
  "logo_url": "https://example.com/logo.png",
  "banner_url": "https://example.com/banner.png"
}
```

Expected response: `201 Created`
```json
{
  "id": "<store_uuid>",
  "name": "Fashion Hub",
  "category": "fashion",
  "locality": "Anna Salai",
  "is_verified": false,
  "is_open": false,
  "performance_score": 0.0,
  "lat": 13.0418,
  "lng": 80.2341,
  ...
}
```

> **Note:** `is_verified` is `false` by default. Nearby store queries only return verified stores.
> To test nearby queries, run: `UPDATE stores SET is_verified=true WHERE id='<store_uuid>';` via psql or Django admin.

---

### 2. Get Nearby Stores

**GET** `/stores/nearby/?lat=13.0418&lng=80.2341&radius=2`

Auth: Not required

Query params:
- `lat` (required) — user latitude
- `lng` (required) — user longitude
- `radius` (optional, default 2) — radius in km (1 / 2 / 3 / 5)
- `category` (optional) — filter by category e.g. `fashion`

Expected response: `200 OK`
```json
[
  {
    "id": "<store_uuid>",
    "name": "Fashion Hub",
    "category": "fashion",
    "locality": "Anna Salai",
    "logo_url": "...",
    "is_open": false,
    "is_verified": true,
    "performance_score": 0.0,
    "lat": 13.0418,
    "lng": 80.2341,
    "distance_km": 0.12
  }
]
```

---

### 3. Get Store Detail

**GET** `/stores/<store_uuid>/`

Auth: Not required

Expected response: `200 OK` — full store with hours, distance, follower count.

---

### 4. Update Store (Store owner only)

**PUT** `/stores/<store_uuid>/update/`

Auth: Required (owner's JWT)

Send only fields you want to change (partial update):
```json
{
  "is_open": true,
  "description": "Updated description"
}
```

Expected response: `200 OK`

---

### 5. Follow / Unfollow Store

**POST** `/stores/<store_uuid>/follow/`

Auth: Required (customer JWT)

No request body. First call follows, second call unfollows (toggle).

Expected response: `200 OK`
```json
{ "followed": true, "message": "Following store." }
```

---

### 6. Add / Update Review

**POST** `/stores/<store_uuid>/review/`

Auth: Required (customer JWT)

```json
{
  "rating": 4,
  "comment": "Great shop!"
}
```

Expected response: `200 OK`
```json
{
  "id": "<review_uuid>",
  "user_phone": "+919876543210",
  "rating": 4,
  "comment": "Great shop!",
  "created_at": "2026-05-15T..."
}
```

> Calling again with same user+store updates the existing review.
> `performance_score` on the store recalculates automatically.

---

### 7. Get / Generate QR Code

**GET** `/stores/<store_uuid>/qr-code/`

Auth: Required (store owner)

Returns existing QR URL or generates one (requires AWS S3 in production). In dev, S3 upload will fail gracefully — `qr_code_url` stays empty.

Expected response: `200 OK`
```json
{ "qr_code_url": "https://cdn.nearkart.in/qrcodes/<store_uuid>/qr.png" }
```

---

## Product Endpoints

### 8. Create Product (Vendor only — store must exist)

**POST** `/products/`

Auth: Required (vendor JWT)

```json
{
  "name": "Cotton Kurta",
  "description": "Handwoven cotton kurta",
  "category": "fashion",
  "status": "active",
  "is_visible": true,
  "base_price": "499.00",
  "variants": [
    { "name": "Small", "sku": "KT-S-001", "price": "499.00", "stock_quantity": 10 },
    { "name": "Medium", "sku": "KT-M-001", "price": "499.00", "stock_quantity": 8 }
  ]
}
```

Expected response: `201 Created`
```json
{
  "id": "<product_uuid>",
  "store_id": "<store_uuid>",
  "store_name": "Fashion Hub",
  "name": "Cotton Kurta",
  "status": "active",
  "base_price": "499.00",
  "variants": [...],
  "images": [],
  "is_wishlisted": false
}
```

---

### 9. Get Nearby Products

**GET** `/products/nearby/?lat=13.0418&lng=80.2341&radius=2`

Auth: Not required

Same params as nearby stores. Returns products from verified, active stores within radius.

---

### 10. Search Products

**GET** `/products/search/?q=kurta&lat=13.0418&lng=80.2341&radius=5`

Auth: Not required

Query params:
- `q` (required) — search term (uses trigram similarity, min 20% match)
- `lat`, `lng`, `radius` (optional) — restrict to geographic area

Expected response: `200 OK` — list sorted by similarity score.

---

### 11. Get Product Detail

**GET** `/products/<product_uuid>/`

Auth: Not required (but `is_wishlisted` is `false` without auth)

Product must have `status=active` and `is_visible=true`.

---

### 12. Update Product (Owner only)

**PUT** `/products/<product_uuid>/update/`

Auth: Required (store owner JWT)

```json
{
  "status": "active",
  "base_price": "449.00"
}
```

---

### 13. Delete Product (Owner only)

**DELETE** `/products/<product_uuid>/update/`

Auth: Required (store owner JWT)

Expected response: `204 No Content`

---

### 14. Wishlist Toggle

**POST** `/products/<product_uuid>/wishlist/`

Auth: Required (customer JWT)

No request body. First call adds, second call removes (toggle).

Expected response: `200 OK`
```json
{ "wishlisted": true, "message": "Added to wishlist." }
```

---

## Full Test Sequence

```
1.  [Vendor]   POST /auth/otp/send/        → send OTP for vendor phone
2.  [Vendor]   POST /auth/otp/verify/      → get vendor tokens
3.  [Customer] POST /auth/otp/send/        → send OTP for customer phone
4.  [Customer] POST /auth/otp/verify/      → get customer tokens
5.  [Vendor]   POST /stores/               → create store
                                            (manually set is_verified=true in DB for testing)
6.  [Vendor]   POST /products/             → create product with status=active
7.  [Public]   GET  /stores/nearby/        → should see your store
8.  [Public]   GET  /products/nearby/      → should see your product
9.  [Public]   GET  /products/search/?q=kurta → search test
10. [Customer] POST /stores/<id>/follow/   → follow store
11. [Customer] POST /stores/<id>/review/   → rate store
12. [Customer] POST /products/<id>/wishlist/ → wishlist product
13. [Vendor]   PUT  /stores/<id>/update/   → update store info
14. [Vendor]   PUT  /products/<id>/update/ → update product price/status
15. [Vendor]   GET  /stores/<id>/qr-code/  → generate QR (S3 in prod)
```

---

## Error Reference

| Code | Error | Cause |
|------|-------|-------|
| 400 | `validation_error` | Missing lat/lng, invalid rating, etc. |
| 400 | `validation_error: You already have a store` | Vendor trying to create second store |
| 400 | `validation_error: Create a store first` | Vendor creating product without store |
| 401 | Unauthorized | Missing or expired JWT |
| 403 | Forbidden | Non-vendor trying to create store/product, or non-owner trying to update |
| 404 | `not_found` | Store/product does not exist or is inactive |

---

## Swagger UI

Visit `http://localhost:8000/api/schema/swagger-ui/` to explore all endpoints interactively.
Click **Authorize** and enter: `Bearer <access_token>`

# Sprint 3 — Postman Testing Guide

## Setup

**Base URL variable:** `{{base_url}}` = `http://localhost:8000/api/v1`

Set these as Postman Collection Variables:
| Variable | Value |
|----------|-------|
| `base_url` | `http://localhost:8000/api/v1` |
| `vendor_token` | (filled after vendor login) |
| `customer_token` | (filled after customer login) |
| `store_id` | (filled after store create) |
| `product_id` | (filled after product create) |

---

## Step 1 — Get Vendor Token

**POST** `{{base_url}}/auth/otp/send/`
```json
{ "phone_number": "+919999999999" }
```
Expected: `200 { "message": "OTP sent successfully" }`

**POST** `{{base_url}}/auth/otp/verify/`
```json
{ "phone_number": "+919999999999", "otp": "123456" }
```
Expected: `200` — copy the `access` value → set as `vendor_token`

---

## Step 2 — Get Customer Token

**POST** `{{base_url}}/auth/otp/send/`
```json
{ "phone_number": "+919000000002" }
```

**POST** `{{base_url}}/auth/otp/verify/`
```json
{ "phone_number": "+919000000002", "otp": "123456" }
```
Expected: `200` — copy the `access` value → set as `customer_token`

---

## Step 3 — Create Store (Vendor)

**POST** `{{base_url}}/stores/`

Headers:
```
Authorization: Bearer {{vendor_token}}
Content-Type: application/json
```

Body:
```json
{
  "name": "Fashion Hub",
  "description": "Trendy clothes for everyone",
  "category": "fashion",
  "phone": "+919876543210",
  "address": "123 Anna Salai, Chennai",
  "latitude": 13.0418,
  "longitude": 80.2341,
  "logo_url": "https://example.com/logo.png"
}
```

Expected: `201 Created`
- Copy `id` from response → set as `store_id`
- Note: `is_verified` will be `false` — nearby queries won't return this store yet

> **To make the store appear in nearby results:**
> Go to Django Admin → `http://localhost:8000/admin/stores/store/` → find your store → tick `is_verified` → Save
> OR run: `docker compose exec -T django /venv/bin/python manage.py shell -c "from apps.stores.models import Store; Store.objects.filter(name='Fashion Hub').update(is_verified=True)"`

---

## Step 4 — Create Product (Vendor)

**POST** `{{base_url}}/products/`

Headers:
```
Authorization: Bearer {{vendor_token}}
Content-Type: application/json
```

Body:
```json
{
  "name": "Cotton Kurta",
  "description": "Handwoven cotton kurta",
  "category": "fashion",
  "status": "active",
  "is_visible": true,
  "base_price": "499.00",
  "variants": [
    { "name": "Small",  "sku": "KT-S-001", "price": "499.00", "stock_quantity": 10 },
    { "name": "Medium", "sku": "KT-M-001", "price": "499.00", "stock_quantity": 8 },
    { "name": "Large",  "sku": "KT-L-001", "price": "549.00", "stock_quantity": 5 }
  ]
}
```

Expected: `201 Created`
- Copy `id` from response → set as `product_id`

---

## Step 5 — Nearby Stores (Public)

**GET** `{{base_url}}/stores/nearby/?lat=13.0418&lng=80.2341&radius=2`

No auth required.

Expected: `200` — array with your store (if is_verified=true)

Try with category filter:
`{{base_url}}/stores/nearby/?lat=13.0418&lng=80.2341&radius=2&category=fashion`

---

## Step 6 — Nearby Products (Public)

**GET** `{{base_url}}/products/nearby/?lat=13.0418&lng=80.2341&radius=2`

No auth required.

Expected: `200` — array with your product (product must be `status=active` and store `is_verified=true`)

---

## Step 7 — Search Products (Public)

**GET** `{{base_url}}/products/search/?q=kurta`

No auth required.

Try also with location filter:
`{{base_url}}/products/search/?q=kurta&lat=13.0418&lng=80.2341&radius=5`

Expected: `200` — results sorted by name similarity

---

## Step 8 — Store Detail (Public)

**GET** `{{base_url}}/stores/{{store_id}}/`

No auth required.

Expected: `200` — full store with hours, follower_count, performance_score

---

## Step 9 — Product Detail (Public)

**GET** `{{base_url}}/products/{{product_id}}/`

No auth required (but `is_wishlisted` will be `false` without auth).

Try with customer token:
```
Authorization: Bearer {{customer_token}}
```
`is_wishlisted` will reflect the customer's wishlist state.

---

## Step 10 — Follow Store (Customer)

**POST** `{{base_url}}/stores/{{store_id}}/follow/`

Headers:
```
Authorization: Bearer {{customer_token}}
```

No body needed.

Expected: `200 { "followed": true, "message": "Following store." }`
Call again → `{ "followed": false, "message": "Unfollowed store." }` (toggle)

---

## Step 11 — Review Store (Customer)

**POST** `{{base_url}}/stores/{{store_id}}/review/`

Headers:
```
Authorization: Bearer {{customer_token}}
Content-Type: application/json
```

Body:
```json
{
  "rating": 5,
  "comment": "Excellent products and fast delivery!"
}
```

Expected: `200` — review object
Check the store detail again — `performance_score` should update.

---

## Step 12 — Wishlist Product (Customer)

**POST** `{{base_url}}/products/{{product_id}}/wishlist/`

Headers:
```
Authorization: Bearer {{customer_token}}
```

No body needed.

Expected: `200 { "wishlisted": true, "message": "Added to wishlist." }`
Call again → `{ "wishlisted": false, "message": "Removed from wishlist." }` (toggle)

---

## Step 13 — Update Store (Vendor)

**PUT** `{{base_url}}/stores/{{store_id}}/update/`

Headers:
```
Authorization: Bearer {{vendor_token}}
Content-Type: application/json
```

Body (partial — only fields you want to change):
```json
{
  "is_open": true,
  "description": "Updated description"
}
```

Expected: `200` — updated store object

---

## Step 14 — Update Product (Vendor)

**PUT** `{{base_url}}/products/{{product_id}}/update/`

Headers:
```
Authorization: Bearer {{vendor_token}}
Content-Type: application/json
```

Body:
```json
{
  "base_price": "449.00",
  "status": "active"
}
```

Expected: `200` — updated product object

---

## Step 15 — Delete Product (Vendor)

**DELETE** `{{base_url}}/products/{{product_id}}/update/`

Headers:
```
Authorization: Bearer {{vendor_token}}
```

Expected: `204 No Content`

---

## Step 16 — QR Code (Vendor)

**GET** `{{base_url}}/stores/{{store_id}}/qr-code/`

Headers:
```
Authorization: Bearer {{vendor_token}}
```

Expected: `200 { "qr_code_url": "..." }`

> In dev: `qr_code_url` will be empty string because AWS S3 is not configured.
> This works fully in production with real AWS credentials.

---

## Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `401 Unauthorized` | Missing or expired token | Re-run otp/send + otp/verify to get fresh token |
| `403 Forbidden` | Wrong role or not store owner | Use vendor token for vendor actions |
| `400 You already have a store` | Vendor tries to create second store | Each vendor can have only one store |
| `400 Create a store first` | Creating product without a store | Create store first |
| `Empty nearby results []` | Store not verified OR product not active | Set is_verified=True, status=active |
| `400 lat and lng are required` | Missing query params | Add ?lat=XX&lng=XX to the URL |

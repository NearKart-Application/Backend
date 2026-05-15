# Sprint 3 — Testing Checklist

Complete all items below before marking Sprint 3 as done.
Mark each with [x] when it passes.

---

## Prerequisites

- [ ] Docker running: `docker compose up -d`
- [ ] Health check passes: `GET http://localhost:8000/api/v1/health/` → `{"status":"ok"}`
- [ ] Migrations applied: `stores 0001_initial`, `stores 0002_store_location_geography`, `products 0001_initial`
- [ ] Have a vendor account token (use Sprint 2 OTP flow)
- [ ] Have a customer account token

---

## Store Tests

### Create Store
- [ ] `POST /stores/` with vendor JWT → `201 Created`
- [ ] Response contains `id`, `lat`, `lng`, `locality`, `is_verified: false`
- [ ] Calling again with same vendor → `400 You already have a store`
- [ ] Calling with customer token → `403 Forbidden`

### Verify Store (Required for nearby)
- [ ] Set `is_verified=True` via Django Admin or psql
- [ ] Confirm via `GET /stores/<id>/` → `"is_verified": true`

### Nearby Stores
- [ ] `GET /stores/nearby/?lat=13.0418&lng=80.2341&radius=2` → returns store
- [ ] `GET /stores/nearby/?lat=13.0418&lng=80.2341&radius=2&category=fashion` → filtered result
- [ ] Non-existent category returns `[]`
- [ ] Missing `lat` param → `400 validation_error`

### Store Detail
- [ ] `GET /stores/<uuid>/` → returns full store with `hours`, `follower_count`, `performance_score`
- [ ] Invalid UUID → `404 not_found`

### Update Store
- [ ] `PUT /stores/<uuid>/update/` with owner JWT → `200 OK` with updated fields
- [ ] Same request with different vendor's token → `403 Forbidden`

### Follow Store
- [ ] `POST /stores/<uuid>/follow/` → `{"followed": true}`
- [ ] Call again → `{"followed": false}` (unfollow toggle)
- [ ] No auth → `401 Unauthorized`

### Review Store
- [ ] `POST /stores/<uuid>/review/` with rating=5 → `200 OK`
- [ ] Call again with rating=3 → updates existing review (upsert)
- [ ] Check store detail → `performance_score` updated correctly
- [ ] Rating 0 or 6 → `400 validation_error`

### QR Code
- [ ] `GET /stores/<uuid>/qr-code/` with owner JWT → `200 {"qr_code_url": "..."}`
- [ ] In dev: `qr_code_url` may be empty (no S3) — that is expected

---

## Product Tests

### Create Product
- [ ] `POST /products/` with vendor JWT → `201 Created`
- [ ] Response contains `id`, `store_name`, `variants`, `images`
- [ ] Vendor with no store → `400 Create a store first`
- [ ] Customer token → `403 Forbidden`

### Nearby Products
- [ ] `GET /products/nearby/?lat=13.0418&lng=80.2341&radius=2` → returns product
- [ ] Product must have `status=active`, `is_visible=true`, store `is_verified=true`
- [ ] Product with `stock_quantity=0` on all variants → NOT in results

### Search Products
- [ ] `GET /products/search/?q=kurta` → returns matching products sorted by similarity
- [ ] `GET /products/search/?q=xxxxnotexist` → `[]`
- [ ] Missing `q` param → `400 validation_error`
- [ ] With location: `?q=kurta&lat=13.04&lng=80.23&radius=5` → filtered by distance

### Product Detail
- [ ] `GET /products/<uuid>/` → full product with `variants`, `images`, `is_wishlisted: false`
- [ ] With customer auth → `is_wishlisted` reflects actual wishlist state
- [ ] Product with `status=draft` → `404 not_found`
- [ ] Product with `is_visible=false` → `404 not_found`

### Update Product
- [ ] `PUT /products/<uuid>/update/` with owner JWT → `200 OK`
- [ ] Different vendor token → `403 Forbidden`

### Delete Product
- [ ] `DELETE /products/<uuid>/update/` with owner JWT → `204 No Content`
- [ ] Confirm deleted product returns `404` on GET

### Wishlist
- [ ] `POST /products/<uuid>/wishlist/` → `{"wishlisted": true}`
- [ ] Call again → `{"wishlisted": false}` (toggle)
- [ ] No auth → `401 Unauthorized`

---

## Full Flow Test (End to End)

- [ ] Vendor creates store
- [ ] Admin verifies store
- [ ] Vendor creates 2 products (status=active)
- [ ] Vendor creates 1 product (status=draft)
- [ ] Customer: GET /stores/nearby/ → sees store
- [ ] Customer: GET /products/nearby/ → sees 2 active products, NOT draft
- [ ] Customer: GET /products/search/?q=<name> → finds product by name
- [ ] Customer: follows store → `followed: true`
- [ ] Customer: reviews store → rating=4
- [ ] Customer: reviews store again → rating=5 (updates, not duplicate)
- [ ] Check store detail: `performance_score=5.0`, `follower_count=1`
- [ ] Customer: wishlist product → `wishlisted: true`
- [ ] Customer: GET product detail → `is_wishlisted: true`
- [ ] Vendor: updates product price
- [ ] Vendor: deletes one product
- [ ] GET /products/nearby/ → deleted product no longer appears

---

## Verified on (date): 2026-05-15 ✅

All 15 endpoint tests passed. Full flow test passed.
Store: Chennai Silk House | Product: Kanchipuram Silk Saree + Cotton Kurta

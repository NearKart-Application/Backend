# Sprint 19 — Postman Guide

## New / Updated Endpoints

---

### 1. Search Products with Filters (updated)

**`GET /api/v1/products/search/`**

Auth: None required (AllowAny)

| New param | Type | Example | Notes |
|-----------|------|---------|-------|
| `min_price` | float | `100` | Minimum product price |
| `max_price` | float | `1500` | Maximum product price |
| `min_rating` | float | `4.0` | Minimum store avg rating |
| `has_offer` | bool | `true` | Products from stores with active offers |
| `ordering` | string | `price_asc` | `price_asc` · `price_desc` · `rating` · (omit = relevance) |

**Example — cheapest Kurtas under ₹500 with ≥ 4★:**
```
GET {{base_url}}/products/search/?q=kurta&lat=17.4948&lng=78.3996&max_price=500&min_rating=4.0&ordering=price_asc
```

**Example — on-sale products sorted by rating:**
```
GET {{base_url}}/products/search/?q=saree&lat=17.4948&lng=78.3996&has_offer=true&ordering=rating
```

---

### 2. Following Feed (new)

**`GET /api/v1/products/following/`**

Auth: Bearer token (customer)

Returns up to 20 most recent products from stores the authenticated user follows.

```
GET {{base_url}}/products/following/
Authorization: Bearer {{customer_token}}
```

Expected response `200 OK`:
```json
{
  "count": 5,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "name": "Cotton Kurta",
      "price": "499.00",
      "store": { "id": "uuid", "name": "Sneha's Fashion House", ... },
      ...
    }
  ]
}
```

**Empty following list → `results: []`**

---

### 3. Vendor Invoices — List (new)

**`GET /api/v1/stores/mine/invoices/`**

Auth: Bearer token (vendor)

```
GET {{base_url}}/stores/mine/invoices/
Authorization: Bearer {{vendor_token}}
```

Expected response:
```json
{
  "count": 2,
  "results": [
    {
      "id": "uuid",
      "customer_name": "Ravi Kumar",
      "customer_phone": "9876543210",
      "items": [{"name": "Cotton Kurta", "price": 499.0, "qty": 2}],
      "notes": "Special packaging requested",
      "total": "998.00",
      "is_sent": false,
      "created_at": "2026-05-23T10:00:00Z"
    }
  ]
}
```

---

### 4. Vendor Invoices — Create (new)

**`POST /api/v1/stores/mine/invoices/`**

Auth: Bearer token (vendor)

```json
{
  "customer_name": "Ravi Kumar",
  "customer_phone": "9876543210",
  "items": [
    {"name": "Cotton Kurta", "price": 499.0, "qty": 2},
    {"name": "Silk Dupatta", "price": 350.0, "qty": 1}
  ],
  "notes": "Special packaging"
}
```

Expected response `201 Created`:
```json
{
  "id": "uuid",
  "customer_name": "Ravi Kumar",
  "customer_phone": "9876543210",
  "items": [...],
  "notes": "Special packaging",
  "total": "1348.00",
  "is_sent": false,
  "created_at": "2026-05-23T10:00:00Z"
}
```

**Note:** `total` is computed server-side from `items[].price × items[].qty`. Do not send `total` in the request body.

---

## Unchanged Endpoints Used by Sprint 19 Features

| Feature | Endpoint | Sprint |
|---------|----------|--------|
| Follow/Unfollow store | `POST/DELETE /stores/{id}/follow/` | S14 |
| Nearby stores (with radius) | `GET /stores/nearby/?radius=5` | S3 |

---

## Environment Variables

| Variable | Value |
|----------|-------|
| `{{base_url}}` | `http://127.0.0.1:8000/api/v1` |
| `{{customer_token}}` | JWT from customer login |
| `{{vendor_token}}` | JWT from vendor login |

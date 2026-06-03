# Sprint 23 — Postman Guide

**Base URL:** `http://192.168.x.x/api`  
**Auth header:** `Authorization: Bearer <vendor_token>`

---

## Request 1 — Get Store Hours (Public)

```
GET {{base_url}}/stores/{{store_id}}/hours/
```

**Expected 200:**
```json
[
  {"day": 0, "open_time": "10:00:00", "close_time": "21:00:00", "is_closed": false},
  {"day": 6, "open_time": "10:00:00", "close_time": "18:00:00", "is_closed": false}
]
```

---

## Request 2 — Save Store Hours (Vendor)

```
PUT {{base_url}}/stores/{{store_id}}/hours/
Authorization: Bearer {{vendor_token}}
Content-Type: application/json
```

**Body:**
```json
[
  {"day": 0, "open_time": "09:00:00", "close_time": "22:00:00", "is_closed": false},
  {"day": 1, "open_time": "09:00:00", "close_time": "22:00:00", "is_closed": false},
  {"day": 2, "open_time": "09:00:00", "close_time": "22:00:00", "is_closed": false},
  {"day": 3, "open_time": "09:00:00", "close_time": "22:00:00", "is_closed": false},
  {"day": 4, "open_time": "09:00:00", "close_time": "22:00:00", "is_closed": false},
  {"day": 5, "open_time": "10:00:00", "close_time": "20:00:00", "is_closed": false},
  {"day": 6, "open_time": "10:00:00", "close_time": "18:00:00", "is_closed": true}
]
```

**Expected 200:** Same structure.

---

## Request 3 — List Discount Codes (Vendor)

```
GET {{base_url}}/stores/mine/discount-codes/
Authorization: Bearer {{vendor_token}}
```

**Expected 200:** Array of `DiscountCode` objects.

---

## Request 4 — Create Discount Code

```
POST {{base_url}}/stores/mine/discount-codes/
Authorization: Bearer {{vendor_token}}
Content-Type: application/json
```

**Body:**
```json
{
  "code": "SAVE20",
  "description": "20% off sitewide",
  "discount_type": "percent",
  "value": "20.00",
  "min_order_amount": "500.00",
  "max_uses": 100,
  "valid_from": "2026-06-01",
  "valid_till": "2026-06-30"
}
```

**Expected 201:** Created `DiscountCode` object with `id`.

---

## Request 5 — Create Flat Discount Code

```
POST {{base_url}}/stores/mine/discount-codes/
Authorization: Bearer {{vendor_token}}
Content-Type: application/json
```

**Body:**
```json
{
  "code": "FLAT100",
  "description": "₹100 off",
  "discount_type": "flat",
  "value": "100.00",
  "min_order_amount": "800.00"
}
```

---

## Request 6 — Toggle Code Active/Inactive

```
PATCH {{base_url}}/stores/mine/discount-codes/{{code_id}}/
Authorization: Bearer {{vendor_token}}
Content-Type: application/json
```

**Body:**
```json
{ "is_active": false }
```

---

## Request 7 — Delete Discount Code

```
DELETE {{base_url}}/stores/mine/discount-codes/{{code_id}}/
Authorization: Bearer {{vendor_token}}
```

**Expected 204**

---

## Request 8 — Apply Discount Code (Customer)

```
POST {{base_url}}/stores/{{store_id}}/apply-discount/
Authorization: Bearer {{customer_token}}
Content-Type: application/json
```

**Body:**
```json
{ "code": "SAVE20", "order_amount": "1200.00" }
```

**Expected 200 (valid):**
```json
{
  "valid": true,
  "discount_type": "percent",
  "value": "20.00",
  "discount_amount": "240.00",
  "final_amount": "960.00"
}
```

**Expected 200 (invalid):**
```json
{ "valid": false, "error": "expired" }
```

---

## Request 9 — Get Product Images

```
GET {{base_url}}/products/{{product_id}}/images/
Authorization: Bearer {{any_token}}
```

**Expected 200:**
```json
[
  {"id": "uuid", "url": "http://192.168.x.x/media/products/img.jpg", "is_primary": true, "created_at": "2026-06-01T..."},
  {"id": "uuid2", "url": "http://192.168.x.x/media/products/img2.jpg", "is_primary": false, "created_at": "2026-06-01T..."}
]
```

---

## Request 10 — Delete Product Image

```
DELETE {{base_url}}/products/{{product_id}}/images/{{image_id}}/
Authorization: Bearer {{vendor_token}}
```

**Expected 200:**
```json
{
  "images": [
    {"id": "uuid2", "url": "...", "is_primary": true, "created_at": "..."}
  ]
}
```

Note: If deleted image was primary, next image is promoted automatically.

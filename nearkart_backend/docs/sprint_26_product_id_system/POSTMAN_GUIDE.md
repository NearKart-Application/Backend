# Sprint 26 — Postman Guide: Product ID System

**Base URL:** `http://192.168.x.x:8000/api/v1`
**Auth header:** `Authorization: Bearer <vendor_token>`

---

## Request 1 — Generate Code with Category

```
GET {{base_url}}/products/vendor/generate-code/?category=electronics
Authorization: Bearer {{vendor_token}}
```

**Expected 200:**
```json
{ "product_code": "NS-VE-BAN-ELEC-X7K2P" }
```

**Verify format:** `NS-{ShopAbbr}-{LocalityCode}-ELEC-{5chars}`

---

## Request 2 — Generate Code for Each Category

Run once per category and verify the correct code segment:

| Query param | Expected segment |
|-------------|-----------------|
| `?category=fashion` | `FASH` |
| `?category=jewellery` | `JEWE` |
| `?category=footwear` | `FOOT` |
| `?category=decor` | `DECO` |
| `?category=furniture` | `FURN` |
| `?category=gifts` | `GIFT` |
| `?category=beauty` | `BEAU` |
| `?category=food` | `FOOD` |
| `?category=electronics` | `ELEC` |
| `?category=unknown` | `GEN` |
| _(no category param)_ | `GEN` or `NS-{5chars}` fallback |

---

## Request 3 — Generate Code (no category)

```
GET {{base_url}}/products/vendor/generate-code/
Authorization: Bearer {{vendor_token}}
```

**Expected 200:** Code without category segment (fallback prefix).

---

## Request 4 — Create Product (code auto-assigned)

```
POST {{base_url}}/products/
Authorization: Bearer {{vendor_token}}
Content-Type: application/json
```

**Body (no product_code field):**
```json
{
  "name": "Cotton Kurti",
  "description": "Premium cotton kurti",
  "category": "fashion",
  "base_price": "599.00",
  "is_visible": true,
  "variants": [
    { "name": "M", "sku": "CK-M", "price": "599.00", "stock_quantity": 20 },
    { "name": "L", "sku": "CK-L", "price": "599.00", "stock_quantity": 15 }
  ]
}
```

**Expected 201 — verify `product_code` in response:**
```json
{
  "id": "uuid",
  "product_code": "NS-SFH-BAN-FASH-K3M9P",
  "name": "Cotton Kurti",
  ...
}
```

Code must follow `NS-{ShopAbbr}-{LocalityCode}-FASH-{Unique}` format.

---

## Request 5 — Create Product (custom code provided)

```
POST {{base_url}}/products/
Authorization: Bearer {{vendor_token}}
Content-Type: application/json
```

**Body (with explicit product_code):**
```json
{
  "name": "Custom Code Product",
  "category": "electronics",
  "base_price": "1200.00",
  "product_code": "MY-CUSTOM-CODE",
  "variants": [{ "name": "One Size", "sku": "CC-OS", "price": "1200.00", "stock_quantity": 5 }]
}
```

**Expected 201:** `product_code` in response = `"MY-CUSTOM-CODE"` (not overwritten).

---

## Request 6 — Verify Clash Safety

Call `GET generate-code/?category=fashion` 5 times rapidly.

**Expected:** Each response has a **different** `Unique` suffix (no duplicates).

---

## Request 7 — Verify Old Products Untouched

```
GET {{base_url}}/products/vendor/
Authorization: Bearer {{vendor_token}}
```

**Expected:** Products created before this sprint still show `NKP-XXXXXX` codes unchanged.

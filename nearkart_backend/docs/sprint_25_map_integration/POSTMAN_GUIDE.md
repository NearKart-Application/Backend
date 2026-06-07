# Sprint 25 — Postman Guide

**Base URL:** `http://192.168.x.x:8000/api/v1`
**Auth header:** `Authorization: Bearer <token>`

---

## Request 1 — Nearby Stores (with offer labels)

```
GET {{base_url}}/stores/nearby/?lat=12.9716&lng=77.5946&radius=3
Authorization: Bearer {{customer_token}}
```

**Expected 200 — verify `active_offer_labels` is present:**
```json
{
  "stores": [
    {
      "id": "uuid",
      "name": "Sneha's Fashion House",
      "category": "fashion",
      "active_offer_labels": [
        "Flat ₹200 off on orders above ₹1500",
        "Buy 2 Get 1 Free on kurtis"
      ],
      ...
    },
    {
      "id": "uuid2",
      "name": "Vikram Electronics",
      "active_offer_labels": [],
      ...
    }
  ]
}
```

**Verify:**
- Stores with active non-expired offers return labels
- Stores with no offers return `[]` (not null)
- Expired offers (`valid_till` < today) are NOT included
- Maximum 5 labels per store

---

## Request 2 — Create Store Offer (vendor) + verify cache bust

### Step 1: Create offer
```
POST {{base_url}}/stores/mine/offers/
Authorization: Bearer {{vendor_token}}
Content-Type: application/json
```

**Body:**
```json
{
  "label": "Weekend Special — 15% off all footwear",
  "valid_till": "2026-12-31"
}
```

**Expected 201:** Created offer object.

### Step 2: Call nearby stores again
```
GET {{base_url}}/stores/nearby/?lat={{vendor_lat}}&lng={{vendor_lng}}&radius=3
```

**Verify:** New offer label appears immediately (cache was busted on create).

---

## Request 3 — Delete Store Offer + verify cache bust

```
DELETE {{base_url}}/stores/mine/offers/{{offer_id}}/
Authorization: Bearer {{vendor_token}}
```

**Expected 204.**

Immediately call Request 1 again — deleted offer label should be gone from response.

---

## Request 4 — Update Product with Sale Price

```
PUT {{base_url}}/products/{{product_id}}/update/
Authorization: Bearer {{vendor_token}}
Content-Type: application/json
```

**Body (set sale price):**
```json
{
  "name": "Cotton Kurti",
  "base_price": "500.00",
  "sale_price": "399.00"
}
```

**Expected 200:** Updated product. First variant's price is now `399.00`.

**Verify `is_on_sale` computed correctly:**
```
GET {{base_url}}/products/{{product_id}}/
```
Response should have `is_on_sale: true` and the variant price `399.00`.

---

## Request 5 — Remove Sale Price

```
PUT {{base_url}}/products/{{product_id}}/update/
Authorization: Bearer {{vendor_token}}
Content-Type: application/json
```

**Body (sale_price >= base_price → ignored, variant reset to base_price):**
```json
{
  "sale_price": "500.00"
}
```

**Expected:** Variant price reverts to `500.00`, `is_on_sale` becomes false.

---

## Request 6 — Sale Price Validation Edge Cases

**Sale price above base price (should be ignored):**
```json
{ "sale_price": "600.00", "base_price": "500.00" }
```
Variant price should remain `500.00`.

**Invalid value (should be ignored):**
```json
{ "sale_price": "abc" }
```
No error returned, variant price unchanged.

**No sale_price key (should be ignored):**
```json
{ "name": "New Name" }
```
Variant price unchanged.

---

## Request 7 — Broadcast Channels for a Store

```
GET {{base_url}}/stores/{{store_id}}/channels/
Authorization: Bearer {{customer_token}}
```

**Expected 200:**
```json
[
  {
    "id": "uuid",
    "name": "Weekly Offers",
    "description": "Latest deals and discounts",
    "subscriber_count": 12,
    "post_count": 3
  }
]
```

---

## Request 8 — Broadcast Channel Posts

```
GET {{base_url}}/stores/{{store_id}}/channels/{{channel_id}}/posts/
Authorization: Bearer {{customer_token}}
```

**Expected 200:**
```json
[
  {
    "id": "uuid",
    "title": "Weekend Sale!",
    "body": "Get 20% off on all products this weekend.",
    "created_at": "2026-06-05T10:30:00Z"
  }
]
```

---

## Request 9 — Verify Expired Offers Excluded

Set a store offer's `valid_till` to yesterday in admin or directly via Django shell:

```python
# Django shell (docker compose exec django python manage.py shell)
from apps.stores.models import StoreOffer
from datetime import date, timedelta
offer = StoreOffer.objects.first()
offer.valid_till = date.today() - timedelta(days=1)
offer.save()
```

Then call Request 1 — that offer's label should NOT appear in `active_offer_labels`.

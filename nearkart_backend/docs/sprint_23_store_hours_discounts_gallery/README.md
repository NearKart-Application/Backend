# Sprint 23 — Store Hours, Discount Codes, Product Image Gallery

**Branch:** `sprint-23-store-hours-discounts-gallery`  
**Date:** June 2026  
**Status:** Complete

---

## Overview

Sprint 23 wires three previously missing vendor features end-to-end:

| Part | Feature | Who Benefits |
|------|---------|-------------|
| A | Store operating hours saved to server | Vendors & customers |
| B | Vendor discount code management + customer apply flow | Both |
| C | Product image gallery with per-image delete | Vendors |

---

## Part A — Store Hours Vendor Wiring

### What changed
Store hours backend (`GET`/`PUT stores/<id>/hours/`) already existed. Sprint 23 wires the mobile front-end:

- `VendorStoreSetupScreen` now pre-fills `dayHoursList` from the live API on load
- When vendor taps **Save**, hours are submitted to the server alongside the store update
- Day indices: 0 = Monday … 6 = Sunday (matches backend)

### API used
| Method | URL | Auth |
|--------|-----|------|
| GET | `/api/stores/{id}/hours/` | Any |
| PUT | `/api/stores/{id}/hours/` | Vendor |

**PUT body** — array of:
```json
[
  { "day": 0, "open_time": "10:00:00", "close_time": "21:00:00", "is_closed": false },
  { "day": 6, "open_time": "10:00:00", "close_time": "18:00:00", "is_closed": false }
]
```

---

## Part B — Vendor Discount Codes

### Backend

**Model: `DiscountCode`** — table `discount_codes`

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| store | FK → Store | |
| code | CharField(20) | unique per store |
| discount_type | `percent` / `flat` | |
| value | Decimal | percentage or flat ₹ |
| min_order_amount | Decimal (nullable) | |
| max_uses | int (nullable) | null = unlimited |
| uses_count | int | auto-incremented on apply |
| valid_from / valid_till | Date (nullable) | |
| is_active | bool | indexed |

**Methods:**
- `is_valid(order_amount=None)` → `(bool, error_code)` — checks active, dates, max uses, min order
- `calculate_discount(order_amount)` → float — percent capped at order amount

### Vendor Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/stores/mine/discount-codes/` | List all codes |
| POST | `/api/stores/mine/discount-codes/` | Create code |
| PATCH | `/api/stores/mine/discount-codes/<uuid:code_id>/` | Update (toggle active, change value/dates) |
| DELETE | `/api/stores/mine/discount-codes/<uuid:code_id>/` | Delete |

**POST body:**
```json
{
  "code": "SAVE20",
  "description": "20% off everything",
  "discount_type": "percent",
  "value": "20.00",
  "min_order_amount": "500.00",
  "max_uses": 100,
  "valid_from": "2026-06-01",
  "valid_till": "2026-06-30"
}
```

### Customer Apply Endpoint

| Method | URL | Auth |
|--------|-----|------|
| POST | `/api/stores/<uuid:store_id>/apply-discount/` | Customer |

**Request:**
```json
{ "code": "SAVE20", "order_amount": "1200.00" }
```

**Response (valid):**
```json
{
  "valid": true,
  "discount_type": "percent",
  "value": "20.00",
  "discount_amount": "240.00",
  "final_amount": "960.00"
}
```

**Response (invalid):**
```json
{ "valid": false, "error": "expired" }
```

**Error codes:** `expired`, `inactive`, `max_uses_reached`, `min_order_not_met`, `not_found`

### Mobile

- **VendorDiscountCodesScreen** — full CRUD: list view, create bottom sheet (code, type, value, min order, max uses, validity dates), toggle active switch, delete with confirm dialog
- **VendorSettingsScreen** — "Discount Codes" item added under Staff Members
- **ProductDetailScreen** — collapsible "Have a discount code?" section with code + order amount inputs; shows green savings badge on success or red error on failure

---

## Part C — Product Image Gallery Management

### Backend — `ProductImageDeleteView`

| Method | URL | Auth |
|--------|-----|------|
| GET | `/api/products/<uuid:product_id>/images/` | Any |
| DELETE | `/api/products/<uuid:product_id>/images/<uuid:image_id>/` | Vendor (store owner) |

**DELETE response:**
```json
{
  "images": [
    { "id": "uuid", "url": "https://...", "is_primary": true, "created_at": "..." },
    ...
  ]
}
```

- Deletes file from storage
- If deleted image was primary, promotes next remaining image to primary
- Invalidates product detail cache

### Mobile

- **VendorProductEditScreen** — in edit mode, loads existing product images from API on open
  - Each image shows a red ✕ delete button
  - Primary image shows "Main" badge
  - After delete, remaining images update in-place without full reload
  - New picker remains below for adding more photos

---

## Migration

```
apps/stores/migrations/0011_discount_codes.py
```

Run: `python manage.py migrate stores 0011`

---

## Files Changed

### Backend
- `apps/stores/models.py` — `DiscountCode` model
- `apps/stores/views.py` — 3 new views: list/create, update/delete, apply
- `apps/stores/urls.py` — 3 new routes
- `apps/products/views.py` — `ProductImageDeleteView`
- `apps/products/urls.py` — image delete route
- `apps/stores/migrations/0011_discount_codes.py` — migration

### Mobile
- `data/api/VendorApiService.kt` — new data classes + API methods
- `data/api/StoreApiService.kt` — `applyDiscountCode` endpoint
- `data/repository/VendorRepository.kt` — hours, discount code, image methods
- `data/repository/StoreRepository.kt` — `applyDiscountCode`
- `ui/screens/vendor/VendorStoreViewModel.kt` — hours state + save
- `ui/screens/vendor/VendorStoreSetupScreen.kt` — pre-fill + submit hours
- `ui/screens/vendor/VendorProductViewModel.kt` — existingImages + delete
- `ui/screens/vendor/VendorProductEditScreen.kt` — image gallery UI
- `ui/screens/vendor/VendorDiscountCodesViewModel.kt` — NEW
- `ui/screens/vendor/VendorDiscountCodesScreen.kt` — NEW
- `ui/screens/vendor/VendorSettingsScreen.kt` — discount codes nav item
- `ui/screens/product/ProductDetailViewModel.kt` — discount state
- `ui/screens/product/ProductDetailScreen.kt` — discount code section
- `ui/navigation/NavGraph.kt` — `VENDOR_DISCOUNT_CODES` route
- `MainActivity.kt` — composable + nav wired

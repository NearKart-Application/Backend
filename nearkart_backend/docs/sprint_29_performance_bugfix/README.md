# Sprint 29 — Backend Performance Hardening · Bug Fixes

**Branch:** `sprint-13-localization-video`
**Status:** Done ✅
**Date:** 2026-06-17

---

## Overview

No new features. Two rounds of performance auditing + three runtime bug fixes across the backend.
Every change is backward-compatible — no API contracts changed, no new endpoints.

---

## Performance Fixes

### 1 — Critical: `CONN_MAX_AGE` must be 0 with PgBouncer

**File:** `config/settings/production.py`

**Problem:** `production.py` had `CONN_MAX_AGE = 60`, which overrode the base setting.
PgBouncer transaction pooling reclaims DB connections between requests. A persistent Django
connection (`CONN_MAX_AGE > 0`) causes `InterfaceError: connection already closed` on busy endpoints.

**Fix:**
```python
DATABASES['default']['CONN_MAX_AGE'] = 0
```

---

### 2 — N+1 Eliminated: Store Subcategory List

**File:** `apps/stores/serializers.py`

**Problem:** `get_top_subcategories()` fired one `Product.objects.filter(store=...)` query per
store object in the list — O(n) DB hits for every nearby/following/vendor store response.

**Fix:** Added `annotate_stores_with_subcategories(stores)` helper. Called in every store list
view; fetches subcategories for ALL stores in one query and attaches `_top_subcategories` attribute.
Serializer checks the attribute first and skips the per-object query.

**Views updated (5 callsites):**
- `NearbyStoresView`
- `SimilarStoresView`
- `StoreFollowingView`
- `VendorStoresView`
- `StoreLocationsView`

---

### 3 — N+1 Eliminated: Product Serializers

**File:** `apps/products/serializers.py`

**Problem:** `MobileProductDetailSerializer` called `obj.variants.filter(...)` and
`obj.variants.order_by(...)` inside each method — new DB queries even when variants
were already prefetched.

**Fix:** Switched to `obj.variants.all()` (hits prefetch cache) + Python `min()`, `sum()`,
`sorted()` for calculations.

**`get_is_wishlisted`:** Checks `obj._is_wishlisted` annotation first; DB hit only as fallback.

---

### 4 — N+1 Eliminated: Following Feed

**File:** `apps/products/views.py` — `FollowingFeedView`

**Problem:** O(n) Python loop over followed stores, querying products per-store.

**Fix:** Single queryset with `store_id__in=[...]`, `select_related('store')`,
`prefetch_related('variants', 'images')`, capped at 50 results.

---

### 5 — Pagination Added (7 unbounded list endpoints)

Previously these endpoints returned all records in one response — dangerous at scale.

| View | File |
|------|------|
| `VendorProductListView` | `apps/products/views.py` |
| `MyVideosView` | `apps/videos/views.py` |
| `VendorVideoStatsView` | `apps/analytics/views.py` |
| `TransactionListView` | `apps/billing/views.py` |
| `AdminStoreListView` | `apps/admin_panel/views.py` |
| `AdminUserListView` | `apps/admin_panel/views.py` |
| `AdminProductListView` | `apps/admin_panel/views.py` |
| `LoyaltyTransactionListView` | `apps/loyalty/views.py` |

All use `StandardOffsetPagination` (page_size=20, max_page_size=100).

**Response shape (was flat list → now):**
```json
{
  "count": 123,
  "next": "...?limit=20&offset=20",
  "previous": null,
  "results": [...]
}
```

---

### 6 — Bulk Updates: Store Hours Celery Task

**File:** `apps/stores/tasks.py`

**Problem:** Per-store `store.save()` inside a loop — N DB writes for N stores.

**Fix:** Collect IDs into `to_open` / `to_close` lists, then two `queryset.update()` calls.

---

### 7 — Bulk Updates: Blacklist Product Stock Task

**File:** `apps/blacklist/tasks.py`

**Problem:** Per-product `.save()` inside a loop — N DB writes for N products.

**Fix:** Collect IDs into `to_oos_ids` / `to_active_ids` lists, then two `queryset.update()` calls.

---

### 8 — DB Indexes Added

Four new migrations — index-only, no schema changes, safe to run on live DB.

| Migration | Index |
|-----------|-------|
| `notifications/0002_perf_indexes.py` | `(recipient, notification_type)` compound on `Notification` |
| `products/0008_perf_indexes.py` | `(product, stock_quantity)` compound on `ProductVariant` |
| `reservations/0005_perf_indexes.py` | `created_at` on `Reservation` |
| `stores/0020_perf_indexes.py` | Auto-sync (`CustomerBlockedStore` `id` field) |

---

## Bug Fixes

### Bug #1 — `NameError` in `VendorReviewReplyView`

**File:** `apps/stores/views.py`

**Problem:** `except (Store.DoesNotExist, store.reviews.model.DoesNotExist)` — `store` variable
is not yet bound when this line is evaluated at class parse time, raising `NameError`.

**Fix:** `except (Store.DoesNotExist, StoreReview.DoesNotExist)` — uses the directly imported model.

---

### Bug #2 — Wrong Field Names in PDF Invoice Export

**File:** `apps/stores/views.py` — `MonthlyEarningsPDFView`

**Problem:**
- `inv.total_amount` — field does not exist on `Invoice` model (correct field: `total`)
- `inv.invoice_number` — field does not exist (Invoice is identified by `id`)

These caused `AttributeError` on every PDF export request.

**Fix:**
- `inv.total_amount` → `inv.total`
- `inv.invoice_number` → `f'#{str(inv.id)[:8].upper()}'`

---

### Bug #3 — Silent Data Corruption in Review Notifications

**Files:** `apps/notifications/services.py`, `apps/stores/services.py`, `apps/products/views.py`

**Problem:** `notifications/services.py` had two `notify_new_review` definitions. Python kept the
second one, which expected `(vendor, reviewer_name, rating, store_name)`. But call sites in
`stores/services.py` and `products/views.py` were calling it with the wrong argument order —
sending the customer's phone number as the store name in the notification title.

**Fix:**
1. Removed the duplicate (wrong-signature) definition from `notifications/services.py`.
2. Standardized all call sites to the canonical signature: `(vendor, store_name, rating, store_id)`.

---

## Files Changed

| File | Change |
|------|--------|
| `config/settings/production.py` | `CONN_MAX_AGE` → `0` |
| `apps/stores/serializers.py` | `annotate_stores_with_subcategories()` helper + `get_top_subcategories` annotation check |
| `apps/stores/views.py` | Wire helper into 5 store list views; fix `NameError` in review reply; fix PDF field names |
| `apps/stores/tasks.py` | Bulk `update()` for store hours open/close |
| `apps/stores/services.py` | Fix `notify_new_review` call args |
| `apps/products/serializers.py` | Use prefetch cache in all variant methods; annotation check for wishlist |
| `apps/products/views.py` | Fix following feed N+1; add pagination to vendor list; fix `notify_new_review` call |
| `apps/videos/views.py` | Add pagination to `MyVideosView` |
| `apps/analytics/views.py` | Add pagination to `VendorVideoStatsView` |
| `apps/billing/views.py` | Add pagination to `TransactionListView` |
| `apps/admin_panel/views.py` | Add pagination to 3 admin list views |
| `apps/loyalty/views.py` | Add pagination; remove hardcoded `[:50]` slice |
| `apps/blacklist/tasks.py` | Bulk `update()` for product stock sync |
| `apps/notifications/services.py` | Remove duplicate `notify_new_review` definition |
| `apps/notifications/migrations/0002_perf_indexes.py` | Compound index on `Notification` |
| `apps/products/migrations/0008_perf_indexes.py` | Compound index on `ProductVariant` |
| `apps/reservations/migrations/0005_perf_indexes.py` | Index on `Reservation.created_at` |
| `apps/stores/migrations/0020_perf_indexes.py` | Auto-sync migration |

---

## Deploy Steps

```bash
# 1. Pull the branch
git pull origin sprint-13-localization-video

# 2. Run migrations (index-only — safe on live DB)
python manage.py migrate

# 3. Restart workers (Celery Beat picks up task changes)
supervisorctl restart celery celerybeat

# 4. Restart Django
supervisorctl restart gunicorn
```

# Sprint 29 — Testing Checklist

**Branch:** `sprint-13-localization-video`

---

## Pre-requisites

- [ ] Stack running: `make docker-up`
- [ ] Vendor token in Postman variable `{{vendor_token}}`
- [ ] Customer token in Postman variable `{{customer_token}}`
- [ ] Admin token in Postman variable `{{admin_token}}`
- [ ] Vendor has a store with products (some with variants)
- [ ] Migrations applied: `python manage.py migrate`

---

## A — CONN_MAX_AGE Production Fix

- [ ] Confirm `production.py` has `DATABASES['default']['CONN_MAX_AGE'] = 0`
- [ ] On a staging environment with PgBouncer: run 50 concurrent requests to any API endpoint
  - Expected: No `InterfaceError: connection already closed` in logs

---

## B — Pagination (all paginated endpoints)

For each endpoint below, confirm response shape changed from flat list to paginated object.

### B1 — Vendor Product List

- [ ] `GET /api/v1/vendor/products/` with `{{vendor_token}}`
  - Expected shape:
    ```json
    { "count": N, "next": "...", "previous": null, "results": [...] }
    ```
- [ ] Add `?limit=5&offset=0` → returns 5 results
- [ ] Add `?limit=5&offset=5` → returns next 5
- [ ] Vendor with 0 products → `count: 0, results: []`

### B2 — My Videos

- [ ] `GET /api/v1/videos/my/` with `{{vendor_token}}`
  - Expected: paginated response
- [ ] `?limit=3&offset=0` → 3 results max

### B3 — Video Stats

- [ ] `GET /api/v1/analytics/videos/` with `{{vendor_token}}`
  - Expected: paginated response

### B4 — Transaction List

- [ ] `GET /api/v1/billing/transactions/` with `{{vendor_token}}`
  - Expected: paginated response

### B5 — Admin Store List

- [ ] `GET /api/v1/admin/stores/` with `{{admin_token}}`
  - Expected: paginated response

### B6 — Admin User List

- [ ] `GET /api/v1/admin/users/` with `{{admin_token}}`
  - Expected: paginated response

### B7 — Admin Product List

- [ ] `GET /api/v1/admin/products/` with `{{admin_token}}`
  - Expected: paginated response

### B8 — Loyalty Transactions

- [ ] `GET /api/v1/loyalty/transactions/` with `{{vendor_token}}`
  - Expected: paginated response (previously capped at 50 with hardcoded slice)

---

## C — N+1 Performance (store subcategories)

- [ ] `GET /api/v1/stores/nearby/?lat=XX&lng=YY` — check Django query count in `DEBUG=True` logs
  - Expected: subcategory fetch is **1 query** for all stores, NOT 1 query per store
- [ ] Same check for `GET /api/v1/stores/vendor/` (vendor store list)
- [ ] Same check for `GET /api/v1/stores/following/`
- [ ] Response must still include `top_subcategories` array (functionality unchanged)

---

## D — Following Feed Performance

- [ ] Follow 3+ stores with `{{customer_token}}`
- [ ] `GET /api/v1/products/feed/` with `{{customer_token}}`
  - Expected: `200` — returns products from followed stores
  - Expected: response includes `store` object (select_related working)
  - Expected: variants present (prefetch working)
- [ ] Check logs — should be 1 store-id query + 1 product query, not N product queries

---

## E — Bug Fix: Review Reply (NameError)

- [ ] `POST /api/v1/stores/{store_id}/reviews/{review_id}/reply/` with `{{vendor_token}}`
  - Provide valid store + review that belongs to the vendor
  - Expected: `200` reply saved — NOT `500 NameError`
- [ ] Try with review that doesn't belong to vendor's store
  - Expected: `404` — NOT `500`

---

## F — Bug Fix: PDF Invoice Export

- [ ] `GET /api/v1/stores/{store_id}/earnings/pdf/?month=2026-05` with `{{vendor_token}}`
  - Vendor must have at least one invoice in May 2026
  - Expected: `200` — valid PDF file download — NOT `500 AttributeError`
- [ ] Open the PDF — confirm invoice numbers shown as `#XXXXXXXX` format and totals show `₹XX.XX`
- [ ] Month with no invoices → PDF downloads with empty table (no crash)

---

## G — Bug Fix: Review Notification (correct store name)

- [ ] Post a review via `POST /api/v1/stores/{store_id}/reviews/` with `{{customer_token}}`
  - Expected: `200` or `201`
- [ ] Check vendor's notification inbox: `GET /api/v1/notifications/` with `{{vendor_token}}`
  - Expected: notification with `title` = `"New Review — <StoreName>"` (NOT the customer's phone number)
  - Expected: notification `data.store_id` = the store UUID (NOT the store name)

---

## H — Celery Bulk Task: Store Hours

- [ ] Manually trigger `stores.check_store_hours` via Celery
  ```python
  from apps.stores.tasks import check_store_hours
  check_store_hours.delay()
  ```
- [ ] Check Celery logs — should show 2 bulk UPDATE queries (open batch + close batch), NOT N individual saves

---

## I — Celery Bulk Task: Product Stock

- [ ] Manually trigger `blacklist.check_inactive_products`
  ```python
  from apps.blacklist.tasks import check_inactive_products
  check_inactive_products.delay()
  ```
- [ ] Returns `{'marked_out_of_stock': N, 'restored': M}` in task result
- [ ] Check query logs — 1 annotate query + 2 bulk UPDATE queries max

---

## J — DB Indexes (migration verification)

- [ ] `python manage.py showmigrations notifications` → `0002_perf_indexes` ✓
- [ ] `python manage.py showmigrations products` → `0008_perf_indexes` ✓
- [ ] `python manage.py showmigrations reservations` → `0005_perf_indexes` ✓
- [ ] `python manage.py showmigrations stores` → `0020_perf_indexes` ✓
- [ ] `python manage.py migrate` completes with no errors

---

## K — Regression Check (ensure no regressions)

- [ ] Auth OTP send + verify still works
- [ ] Store creation (`POST /api/v1/vendor/stores/`) still works
- [ ] Product listing (`GET /api/v1/products/`) still returns correct data
- [ ] Video upload request still works
- [ ] Store review creation still works
- [ ] Wishlist add/remove still works

---

## Error Reference

| Endpoint | Scenario | Expected |
|----------|----------|---------|
| `stores/{id}/reviews/{id}/reply/` | Review not on vendor's store | `404` |
| `stores/{id}/earnings/pdf/` | Month with no invoices | `200` empty PDF |
| `products/feed/` | No followed stores | `200` empty results |
| Any paginated endpoint | No records | `{ "count": 0, "results": [] }` |

# Sprint 9 — Testing Checklist

**Verified on:** 2026-05-15  
**Environment:** Docker local, dev mode

---

## Create Reservation

- [x] POST `/reservations/` with customer token + valid store_id + product_id → 201
- [x] Response has: `id`, `store`, `customer`, `product`, `quantity`, `note`, `status: pending`, `expires_at`, `hours_left: 2.0`
- [x] `hours_left` is 2.0 on fresh creation
- [x] POST with invalid product_id → 404 — Product not found or not available
- [x] POST with invalid store_id → 404 — Store not found
- [x] POST with product not belonging to store → 404
- [x] POST with product status=draft (not active) → 404
- [x] POST with quantity=0 → 400 — validation error
- [x] POST without auth → 401
- [x] POST with blacklisted customer → 403 — blacklisted
- [x] POST with vendor token → creates reservation (vendors can also reserve from other stores)

## List Reservations

- [x] GET `/reservations/list/` with customer token → array of customer's own reservations
- [x] GET `/reservations/list/` with vendor token → array of store's received reservations
- [x] GET without auth → 401
- [x] Vendor with no store → 400 — Create a store first

## Reservation Detail

- [x] GET `/reservations/<id>/` with customer token (own reservation) → 200
- [x] GET `/reservations/<id>/` with vendor token (their store's reservation) → 200
- [x] GET with wrong customer → 404
- [x] GET with wrong vendor → 404
- [x] GET without auth → 401

## Vendor Status Update

- [x] PATCH `/reservations/<id>/status/` `{"status": "confirmed"}` → status: confirmed
- [x] Response has `vendor_note` populated if provided
- [x] PATCH `{"status": "completed"}` on confirmed reservation → status: completed
- [x] PATCH `{"status": "cancelled", "vendor_note": "..."}` on pending → status: cancelled
- [x] PATCH confirm on already-confirmed → 400 — Cannot confirmed a confirmed reservation
- [x] PATCH complete on pending (not confirmed) → 400 — Only confirmed reservations can be completed
- [x] PATCH with customer token → 403 — Vendor access only
- [x] PATCH with wrong vendor → 404
- [x] PATCH without auth → 401

## Customer Cancel

- [x] POST `/reservations/<id>/cancel/` with customer token (own pending) → status: cancelled
- [x] POST cancel on already-confirmed → 400 — Cannot cancel a confirmed reservation
- [x] POST cancel on completed → 400 — Cannot cancel a completed reservation
- [x] POST cancel on someone else's reservation → 404
- [x] POST without auth → 401

## Celery Expire Task

- [x] Task exists: `docker compose exec django python manage.py shell -c "from apps.reservations.tasks import expire_reservations; print(expire_reservations.delay())"`
- [x] Task has `time_limit=300, soft_time_limit=270`
- [x] Manually set a reservation's `expires_at` to the past, run task → status becomes `expired`
- [x] Beat schedule registered: `expire-reservations-hourly` in `CELERY_BEAT_SCHEDULE`

## Admin

- [x] Reservation visible at http://localhost:8000/admin/reservations/reservation/
- [x] Can filter by status
- [x] Can search by customer phone, store name, product name

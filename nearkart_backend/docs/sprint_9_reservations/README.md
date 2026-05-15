# Sprint 9 — Reservations

**Status:** Done ✅  
**Verified on:** 2026-05-15

---

## What This Sprint Does

Customers can reserve a product at a store for a 2-hour hold window. The vendor receives the reservation, can confirm or reject it, and marks it completed when the customer picks up. Celery expires unclaimed holds every hour automatically.

---

## Reservation States

```
pending → confirmed → completed
pending → cancelled  (by customer or vendor)
pending → expired    (Celery task after 2h)
confirmed → cancelled (by vendor)
```

---

## Endpoints

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| POST | `/api/v1/reservations/` | Any JWT | Customer creates a reservation |
| GET | `/api/v1/reservations/list/` | Any JWT | Customer sees own / Vendor sees store's |
| GET | `/api/v1/reservations/<id>/` | Any JWT | Detail (customer or store vendor only) |
| PATCH | `/api/v1/reservations/<id>/status/` | Vendor JWT | Confirm / cancel / complete |
| POST | `/api/v1/reservations/<id>/cancel/` | Any JWT | Customer cancels own pending reservation |

---

## Status Transition Rules

| Action | From | To | Who |
|--------|------|----|-----|
| Create | — | `pending` | Customer |
| Confirm | `pending` | `confirmed` | Vendor |
| Cancel | `pending` | `cancelled` | Vendor or Customer |
| Cancel | `confirmed` | `cancelled` | Vendor only |
| Complete | `confirmed` | `completed` | Vendor |
| Expire | `pending` (2h old) | `expired` | Celery task |

---

## Celery Beat Task

`reservations.expire_reservations` — runs at the top of every hour.  
Marks all `pending` reservations with `expires_at < now()` as `expired`.

Registered in `CELERY_BEAT_SCHEDULE` in `config/settings/base.py`.

---

## Blacklist Enforcement

Blacklisted customers cannot create reservations at the store that blocked them.  
Returns `403 — blacklisted`.

---

## Hold Duration

Default: 2 hours. Controlled via `RESERVATION_HOLD_HOURS` in `.env`.

---

## Files Changed

| File | Change |
|------|--------|
| `apps/reservations/models.py` | Reservation model with status choices and indexes |
| `apps/reservations/services.py` | ReservationService — create, confirm, cancel, complete, expire |
| `apps/reservations/serializers.py` | Create, status-update, and response serializers |
| `apps/reservations/views.py` | 5 views |
| `apps/reservations/urls.py` | 5 URL patterns |
| `apps/reservations/tasks.py` | expire_reservations Celery task |
| `apps/reservations/admin.py` | Reservation admin |
| `apps/reservations/migrations/0001_initial.py` | Creates reservations table |
| `config/settings/base.py` | Added expire-reservations-hourly to CELERY_BEAT_SCHEDULE |

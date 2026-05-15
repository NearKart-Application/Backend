# Sprint 6 — Testing Checklist

**Verified on:** 2026-05-15  
**Environment:** Docker local, dev mode

---

## Block / Unblock Toggle

- [x] POST `/stores/<id>/blacklist/<customer_id>/` with vendor token + reason → 200, `is_blocked: true`
- [x] POST same URL again → 200, `is_blocked: false` (unblock)
- [x] POST with no reason body → 200, `is_blocked: true`, reason stored as `""`
- [x] POST with non-existent customer UUID → 404 — Customer not found
- [x] POST with non-existent store UUID → 404 — Store not found
- [x] POST by a vendor who does NOT own the store → 403 — permission_denied
- [x] POST with customer token (not vendor) → 403 — Vendor access only
- [x] POST without auth → 401 — authentication_failed

## List Blocked Customers

- [x] GET `/stores/<id>/blacklist/` with vendor token → array of blocked customers
- [x] Each item has: `id`, `customer_phone`, `customer_name`, `reason`, `created_at`
- [x] Empty array returned when no one is blocked
- [x] Vendor who does NOT own the store → 403 — permission_denied
- [x] GET without auth → 401

## Enforcement — Follow

- [x] Blocked customer calls `POST /stores/<id>/follow/` → 403 — `blacklisted`
- [x] Unblocked customer can follow again

## Enforcement — Review

- [x] Blocked customer calls `POST /stores/<id>/review/` → 403 — `blacklisted`
- [x] Unblocked customer can review again

## Enforcement — Start Conversation

- [x] Blocked customer calls `POST /conversations/start/` with blocked store_id → 403 — `blacklisted`
- [x] Unblocked customer can start conversation again

## Enforcement — WebSocket

- [x] Blocked customer connects to `ws://.../ws/conversations/<id>/?token=...` → closes with code 4003
- [x] Unblocked customer can reconnect normally

## Admin

- [x] Blacklist model visible in Django Admin at http://localhost:8000/admin/
- [x] Can search by store name, customer phone, reason
- [x] Can create/delete blacklist entries directly from admin

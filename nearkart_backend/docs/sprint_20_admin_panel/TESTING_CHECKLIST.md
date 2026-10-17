# Sprint 20 — Backend Testing Checklist

## Pre-Requisites

- [ ] Docker stack running: `docker compose up -d`
- [ ] Migrations applied: `docker exec nearkart-django python manage.py migrate`
- [ ] At least one admin, one master_admin, one customer, one vendor in the database
- [ ] Postman collection loaded (see `POSTMAN_GUIDE.md`)
- [ ] Auth token for master_admin stored in Postman env as `{{admin_token}}`

---

## A — NS Code Prefix

- [ ] Register a new customer → profile_id starts with `NSC-`
- [ ] Register a new vendor → profile_id starts with `NSB-`
- [ ] Admin/master_admin profile_id starts with `NS-`
- [ ] Legacy users (created before this sprint) retain their existing `NS-` codes unchanged
- [ ] `NSC-XX-XX-XXXX` — customer with no location set shows area `XX`
- [ ] `NSB-XX-XX-XXXX` — vendor with no location set shows area `XX`

## B — Option C: First Location Regeneration

- [ ] Create new customer → `NSC-NN-XX-RRRR` (area = XX)
- [ ] Set location for first time with `city = "Hyderabad"` → code regenerates to `NSC-NN-HY-RRRR`
- [ ] Set location a **second time** → code does NOT change (one-time only)
- [ ] If city is blank/empty → code stays as `NSC-NN-XX-RRRR` (no regeneration)
- [ ] Collision check: if generated code already exists → suffix retried, no 500 error

## C — User Suspension

- [ ] `POST /api/v1/admin/users/<id>/suspend/` with `{ "is_suspended": true, "reason": "test" }` → 200
- [ ] Attempt OTP verify for suspended user → HTTP 403
- [ ] 403 body contains `"error": "account_suspended"` and `"message": "<reason>"`
- [ ] `POST /api/v1/admin/users/<id>/suspend/` with `{ "is_suspended": false }` → 200 (unsuspend)
- [ ] Unsuspended user can verify OTP normally → 200

## D — Create User from Admin

- [ ] `POST /api/v1/admin/users/create/` with `{ "phone": "+91XXXXXXXXXX", "full_name": "Test User", "role": "customer" }` → 201
- [ ] New user appears in user list
- [ ] Creating duplicate phone → 400 error (no duplicate accounts)
- [ ] Only admin/master_admin can access — customer token → 403

## E — Search by NS Code

- [ ] `GET /api/v1/admin/users/?search=NSC-AR` → returns users matching that NS code prefix
- [ ] `GET /api/v1/admin/users/?search=NS-AD` → returns admin users
- [ ] Name search still works: `?search=Arjun` → returns by name
- [ ] Combined: partial NS code match works case-insensitively

## F — Store Owner NS Code in Response

- [ ] `GET /api/v1/admin/stores/` → each store object has `owner_profile_id` field
- [ ] `owner_profile_id` matches the store owner's profile_id from users endpoint
- [ ] Field is present even for stores with no owner (returns `null` or empty)

## G — Store Videos

- [ ] `GET /api/v1/admin/stores/<id>/videos/` → returns list of video objects
- [ ] Each video has `id`, `title`, `thumbnail_url`, `status`, `created_at`
- [ ] `DELETE /api/v1/admin/videos/<id>/` → 204 No Content
- [ ] Deleted video no longer appears in store video list
- [ ] Deleting non-existent video → 404

## H — Platform Stats

- [ ] `GET /api/v1/admin/platform/stats/` → response includes `pending_website_requests` field
- [ ] Create a pending website request → `pending_website_requests` count increases
- [ ] Approve/reject that request → count decreases

## I — Activity Log

- [ ] `GET /api/v1/admin/activity-log/` → returns list of log entries
- [ ] Toggle store active → new entry with `action: "toggle_store"`
- [ ] Toggle user active → `action: "toggle_user"`
- [ ] Suspend user → `action: "suspend_user"`
- [ ] Create user → `action: "create_user"`
- [ ] Delete video → `action: "delete_video"`
- [ ] Each entry has: `admin.name`, `action`, `target_type`, `target_label`, `detail`, `created_at`
- [ ] Results ordered by `-created_at` (newest first)
- [ ] City-scoped admin can only see log entries for their city scope

## J — City-Scoped Admin Access

- [ ] Regular admin with `assigned_city = "Hyderabad"` → only sees Hyderabad stores/users
- [ ] Master admin → sees all stores/users across all cities
- [ ] City-scoped admin cannot create another admin → 403

## K — Migration Check

- [ ] `python manage.py showmigrations auth_app` → `0008_user_suspension` shows `[X]`
- [ ] `python manage.py showmigrations admin_panel` → `0002_activity_log` shows `[X]`
- [ ] No migration conflicts: `python manage.py migrate --check` exits 0

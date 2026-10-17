# Sprint 20 — Admin Panel Enhancements + NS Code System

## What was built

Two major areas shipped together:

---

## Part A — NS Code System

### NS Code Prefix by Role

| Role | Prefix | Format | Example |
|------|--------|--------|---------|
| Customer | `NSC-` | `NSC-NN-AA-RRRR` (15 chars) | `NSC-AR-KP-J4X2` |
| Vendor | `NSB-` | `NSB-NN-AA-RRRR` (15 chars) | `NSB-VK-HY-M3R1` |
| Admin / Legacy | `NS-` | `NS-NN-AA-RRRR` (13 chars) | `NS-AD-MB-K8T6` |

`NN` = name tag from full name initials. `AA` = area tag from city. `RRRR` = 4-char random suffix.
`XX` = area placeholder (no location set yet).

### Option C — One-Time NS Code Regeneration on First Location

When a user sets their location **for the first time** and a city name is provided, if their area segment is `XX`, the backend regenerates the code with the real area tag.

- Triggered only once (requires `registered_location` to be `None` before the update)
- New `city` field added to `LocationUpdateSerializer` and `UpdateLocationBody`
- Collision check with `EXCLUDE(pk=user) FILTER(profile_id=new_code)` — retries random suffix on collision
- City sent from mobile via `UpdateLocationBody(lat, lng, name, city)`

**Files changed:**

| File | Change |
|------|--------|
| `core/utils/codes.py` | `make_ns_code(name, area, role)` — returns `NSC-`, `NSB-`, or `NS-` prefix based on role |
| `apps/auth_app/models.py` | `_generate_profile_id(name, area, role)` passes role; `UserManager.create_user` passes role |
| `apps/auth_app/serializers.py` | Added `city` field to `LocationUpdateSerializer` |
| `apps/auth_app/views.py` | `LocationUpdateView`: Option C logic — detect first location, regenerate if area == `XX` |
| `apps/auth_app/migrations/0008_user_suspension.py` | Adds `is_suspended` + `suspension_reason` fields |

---

## Part B — User Suspension

Admins can suspend user accounts. Suspended users cannot log in.

**Flow:**
1. Admin suspends user via `POST /api/v1/admin/users/<id>/suspend/` with `{ "reason": "..." }`
2. `is_suspended = True` set on User
3. At OTP verify, if `user.is_suspended` → return `HTTP 403` with `{ "error": "account_suspended", "message": "..." }`
4. Mobile reads error body and shows suspension dialog instead of navigating

**Fields added to User model:**
- `is_suspended = BooleanField(default=False)`
- `suspension_reason = CharField(max_length=500, blank=True)`

---

## Part C — Admin Panel API Endpoints

### New Endpoints

| Method | URL | Permission | Description |
|--------|-----|-----------|-------------|
| `POST` | `/api/v1/admin/users/create/` | Admin | Create a new user account |
| `POST` | `/api/v1/admin/users/<id>/suspend/` | Admin | Suspend or unsuspend a user |
| `GET` | `/api/v1/admin/stores/<id>/videos/` | Admin | List all videos for a store |
| `DELETE` | `/api/v1/admin/videos/<id>/` | Admin | Delete a video |
| `GET` | `/api/v1/admin/activity-log/` | Admin | Paginated admin activity log |

### Existing Endpoints Enhanced

| Endpoint | Enhancement |
|----------|------------|
| `GET /api/v1/admin/platform/stats/` | Added `pending_website_requests` count |
| `GET /api/v1/admin/users/` | Search now also matches `profile_id__icontains` (NS code search) |
| `GET /api/v1/admin/stores/` | Response now includes `owner_profile_id` |
| `GET /api/v1/admin/users/` | Response now includes `is_suspended`, `suspension_reason` |

---

## Part D — Admin Activity Log

Every key admin action is recorded automatically.

**Model:** `AdminActivityLog` in `apps/admin_panel/models.py`

| Field | Type | Description |
|-------|------|-------------|
| `admin` | FK → User | Who performed the action |
| `action` | CharField(50) | e.g. `suspend_user`, `delete_video`, `toggle_store` |
| `target_type` | CharField(50) | e.g. `user`, `store`, `video` |
| `target_id` | CharField(100) | UUID of the target |
| `target_label` | CharField(200) | Human-readable label |
| `detail` | CharField(500) | Extra context |

**Actions logged automatically:**
- `toggle_store` — admin activates/deactivates store
- `toggle_user` — admin activates/deactivates user account
- `suspend_user` / `unsuspend_user`
- `create_user` — admin creates user from dashboard
- `delete_video` — admin deletes video from store
- `approve_website` / `reject_website`

---

## Backend Files Changed

| File | Change |
|------|--------|
| `core/utils/codes.py` | Role-aware NS code prefix |
| `apps/auth_app/models.py` | NS prefix + suspension fields |
| `apps/auth_app/serializers.py` | `city` in `LocationUpdateSerializer` |
| `apps/auth_app/views.py` | Suspension check at OTP verify + Option C regeneration |
| `apps/auth_app/migrations/0008_user_suspension.py` | New migration |
| `apps/admin_panel/models.py` | `AdminActivityLog` model |
| `apps/admin_panel/migrations/0002_activity_log.py` | New migration |
| `apps/admin_panel/serializers.py` | `owner_profile_id`, `is_suspended`, `suspension_reason` |
| `apps/admin_panel/views.py` | 5 new views + `_log_action()` helper + pending_website_requests stat |
| `apps/admin_panel/urls.py` | 5 new URL patterns |

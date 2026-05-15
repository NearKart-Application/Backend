# Sprint 8 — Postman Guide

## Environment Variables

| Variable | Value | Set by |
|----------|-------|--------|
| `base_url` | `http://localhost:8000/api/v1` | Manual |
| `vendor_token` | (empty) | OTP verify script |
| `admin_token` | (empty) | OTP verify script for staff user |

---

## Create a Staff User (one-time setup)

Run this in your terminal to create the admin user:

```bash
docker compose exec django python manage.py shell -c "
from apps.auth_app.models import User
u, _ = User.objects.get_or_create(phone_number='+919000000001', defaults={'role':'admin','full_name':'Admin'})
u.is_staff = True; u.is_superuser = True; u.save()
print('Done')
"
```

Then use `/auth/otp/send/` + `/auth/otp/verify/` with `+919000000001` to get `admin_token`.

---

## Collection: Sprint 8 — Analytics

### 1. Vendor Dashboard
- **Method:** GET
- **URL:** `{{base_url}}/analytics/vendor/`
- **Auth:** Bearer `{{vendor_token}}`
- **Expected:** Full dashboard object with store, wallet, subscription, current_plan, products, videos

---

### 2. Vendor Video Stats
- **Method:** GET
- **URL:** `{{base_url}}/analytics/vendor/videos/`
- **Auth:** Bearer `{{vendor_token}}`
- **Expected:** Array of videos with view_count, like_count per video

---

### 3. Vendor Product Stats
- **Method:** GET
- **URL:** `{{base_url}}/analytics/vendor/products/`
- **Auth:** Bearer `{{vendor_token}}`
- **Expected:** Array of products with wishlist_count per product

---

## Collection: Sprint 8 — Admin Panel

### 4. Platform Stats
- **Method:** GET
- **URL:** `{{base_url}}/admin-panel/stats/`
- **Auth:** Bearer `{{admin_token}}`
- **Expected:** `{users, stores, videos, products, revenue}`

---

### 5. List All Stores
- **Method:** GET
- **URL:** `{{base_url}}/admin-panel/stores/`
- **Auth:** Bearer `{{admin_token}}`
- **Expected:** `{count, results}` — all stores with owner info

**With filters:**
- `{{base_url}}/admin-panel/stores/?is_verified=false` — unverified stores
- `{{base_url}}/admin-panel/stores/?search=chennai` — search by name

---

### 6. Verify a Store
- **Method:** PATCH
- **URL:** `{{base_url}}/admin-panel/stores/{{store_id}}/`
- **Auth:** Bearer `{{admin_token}}`
- **Body:**
```json
{ "is_verified": true }
```
- **Expected:** Full store object with `is_verified: true`

---

### 7. Deactivate a Store
- **Method:** PATCH
- **URL:** `{{base_url}}/admin-panel/stores/{{store_id}}/`
- **Auth:** Bearer `{{admin_token}}`
- **Body:**
```json
{ "is_active": false }
```
- **Expected:** Full store object with `is_active: false`

---

### 8. List All Users
- **Method:** GET
- **URL:** `{{base_url}}/admin-panel/users/`
- **Auth:** Bearer `{{admin_token}}`
- **Expected:** `{count, results}` — all users with role and store_name

**With filters:**
- `{{base_url}}/admin-panel/users/?role=vendor` — vendors only

---

### 9. Toggle User Active
- **Method:** POST
- **URL:** `{{base_url}}/admin-panel/users/{{customer_id}}/toggle-active/`
- **Auth:** Bearer `{{admin_token}}`
- **Body:** (empty)
- **Expected:** `{"message": "User deactivated successfully.", "user_id": "...", "is_active": false}`

---

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| 403 — permission_denied | Using vendor/customer token | Use staff/admin token |
| 401 — authentication_failed | No Authorization header | Add Bearer token |
| 400 — Create a store first | Vendor has no store | Create store first |
| 404 — Store not found | Wrong store UUID | Check store_id variable |
| 404 — User not found | Wrong user UUID | Check user id |
| 400 — Cannot deactivate own | Toggling your own account | Use a different user |

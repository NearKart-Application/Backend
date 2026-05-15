# Sprint 8 — Analytics + Admin Panel

**Status:** Done ✅  
**Verified on:** 2026-05-15

---

## What This Sprint Does

Two separate modules:

**Analytics** — Vendors get a real-time dashboard showing their store's performance: follower/review counts, subscription status, product breakdown by status, video breakdown by status plus total views and likes.

**Admin Panel** — Staff/superuser-only REST endpoints for platform management: see platform-wide stats, list/search all stores and users, verify/deactivate stores, toggle user active status.

---

## Analytics Endpoints

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| GET | `/api/v1/analytics/vendor/` | Vendor JWT | Full store performance dashboard |
| GET | `/api/v1/analytics/vendor/videos/` | Vendor JWT | Per-video view + like stats |
| GET | `/api/v1/analytics/vendor/products/` | Vendor JWT | Per-product wishlist counts |

### Dashboard Response Shape

```json
{
  "store": { "name", "category", "is_active", "is_verified", "is_open", "follower_count", "review_count", "avg_rating" },
  "wallet": { "balance" },
  "subscription": { "plan", "expires_at", "is_active", "days_left" },
  "current_plan": { "name", "display_name", "video_limit", "product_limit" },
  "products": { "total", "active", "draft", "inactive" },
  "videos": { "total", "ready", "processing", "pending", "total_likes", "total_views" }
}
```

---

## Admin Panel Endpoints

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| GET | `/api/v1/admin-panel/stats/` | Staff JWT | Platform-wide aggregated stats |
| GET | `/api/v1/admin-panel/stores/` | Staff JWT | List all stores (with filters) |
| PATCH | `/api/v1/admin-panel/stores/<store_id>/` | Staff JWT | Verify / activate / open a store |
| GET | `/api/v1/admin-panel/users/` | Staff JWT | List all users (with filters) |
| POST | `/api/v1/admin-panel/users/<user_id>/toggle-active/` | Staff JWT | Enable / disable a user account |

**Staff JWT** = user must have `is_staff=True` (Django `IsAdminUser` permission).

### Store Filters

| Param | Values | Example |
|-------|--------|---------|
| `search` | name or owner phone (partial) | `?search=chennai` |
| `is_active` | `true` / `false` | `?is_active=false` |
| `is_verified` | `true` / `false` | `?is_verified=false` |
| `category` | store category slug | `?category=fashion` |

### User Filters

| Param | Values | Example |
|-------|--------|---------|
| `search` | phone or name (partial) | `?search=9999` |
| `role` | `vendor`, `customer`, `admin` | `?role=vendor` |
| `is_active` | `true` / `false` | `?is_active=true` |

---

## How to Create a Staff User (Dev)

```bash
docker compose exec django python manage.py shell -c "
from apps.auth_app.models import User
u, _ = User.objects.get_or_create(phone_number='+919000000001', defaults={'role':'admin','full_name':'Admin'})
u.is_staff = True; u.is_superuser = True; u.save()
print('Done')
"
```

Then authenticate normally via `/auth/otp/send/` + `/auth/otp/verify/` with that phone number.

---

## No Migrations

This sprint adds no new models. All analytics data is aggregated from existing tables (stores, products, videos, billing_transactions, etc.).

---

## Files Changed

| File | Change |
|------|--------|
| `apps/analytics/views.py` | VendorDashboardView, VendorVideoStatsView, VendorProductStatsView |
| `apps/analytics/serializers.py` | VideoStatSerializer, ProductStatSerializer |
| `apps/analytics/urls.py` | 3 routes |
| `apps/admin_panel/views.py` | PlatformStatsView, AdminStoreListView, AdminStoreUpdateView, AdminUserListView, AdminUserToggleActiveView |
| `apps/admin_panel/serializers.py` | AdminStoreSerializer, AdminStoreUpdateSerializer, AdminUserSerializer |
| `apps/admin_panel/urls.py` | 5 routes |

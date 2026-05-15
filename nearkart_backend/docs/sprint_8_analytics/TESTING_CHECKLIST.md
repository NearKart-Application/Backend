# Sprint 8 — Testing Checklist

**Verified on:** 2026-05-15  
**Environment:** Docker local, dev mode

---

## Analytics — Vendor Dashboard

- [x] GET `/analytics/vendor/` with vendor token → 200, full dashboard object
- [x] Response has: `store`, `wallet`, `subscription`, `current_plan`, `products`, `videos` keys
- [x] `store.follower_count` matches actual follower records
- [x] `store.review_count` and `store.avg_rating` are accurate
- [x] `subscription.days_left` is correct for active plan
- [x] `subscription` is `null` when vendor has no subscription
- [x] `videos.total_views` and `videos.total_likes` aggregate all videos
- [x] `products.active/draft/inactive` counts match DB
- [x] GET without auth → 401
- [x] GET with customer token → 403 — Vendor access only
- [x] GET with no store yet → 400 — Create a store first

## Analytics — Vendor Videos

- [x] GET `/analytics/vendor/videos/` → array of video objects
- [x] Each entry has: `id`, `title`, `status`, `view_count`, `like_count`, `duration_seconds`, `created_at`
- [x] Ordered by most views first
- [x] GET without auth → 401

## Analytics — Vendor Products

- [x] GET `/analytics/vendor/products/` → array of product objects
- [x] Each entry has: `id`, `name`, `status`, `base_price`, `wishlist_count`, `created_at`
- [x] `wishlist_count` matches actual wishlist records for that product
- [x] GET without auth → 401

## Admin Panel — Platform Stats

- [x] GET `/admin-panel/stats/` with staff token → 200
- [x] Response has: `users`, `stores`, `videos`, `products`, `revenue` keys
- [x] `revenue.subscription_revenue` is positive (stored as negative amount in transactions)
- [x] `revenue.total_topups` matches sum of all topup transactions
- [x] GET with vendor/customer token → 403 — permission_denied
- [x] GET without auth → 401

## Admin Panel — Store List

- [x] GET `/admin-panel/stores/` → `{count, results}` with all stores
- [x] Each store has: `owner_phone`, `owner_name`, `product_count`, `video_count`
- [x] `?search=chennai` filters by name (case insensitive)
- [x] `?is_active=false` returns only inactive stores
- [x] `?is_verified=false` returns only unverified stores
- [x] `?category=fashion` returns only fashion stores
- [x] GET with vendor token → 403

## Admin Panel — Store Update

- [x] PATCH `/admin-panel/stores/<id>/` `{"is_verified": false}` → 200, `is_verified` toggled
- [x] PATCH `{"is_verified": true}` → re-verifies store
- [x] PATCH `{"is_active": false}` → deactivates store
- [x] PATCH invalid store UUID → 404
- [x] PATCH with vendor token → 403

## Admin Panel — User List

- [x] GET `/admin-panel/users/` → `{count, results}` with all users
- [x] Vendors have `store_name` populated; customers have `null`
- [x] `?role=vendor` returns only vendors
- [x] `?search=9999` filters by phone partial match
- [x] `?is_active=false` returns only inactive users

## Admin Panel — Toggle User Active

- [x] POST `/admin-panel/users/<id>/toggle-active/` → flips `is_active`
- [x] POST again → flips back
- [x] Response has `message`, `user_id`, `is_active`
- [x] Toggle own account → 400 — Cannot deactivate your own account
- [x] Invalid user UUID → 404
- [x] POST with vendor token → 403

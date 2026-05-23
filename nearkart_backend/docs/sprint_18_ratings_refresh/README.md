# Sprint 18 — Rating Badges Everywhere + Pull-to-Refresh

## What was built

Two complementary improvements: surfacing ratings on every screen a customer sees a store/product, and pull-to-refresh on the Vendor Dashboard.

---

## Option A — Rating Badges Everywhere

### What changed

| Surface | Before | After |
|---------|--------|-------|
| HomeScreen store cards | ★ gold chip (was already there from S17) | No change needed |
| **SearchScreen product cards** | No rating | ★ X.X gold chip when `product.rating > 0` |
| **ProductDetailScreen store row** | Plain muted text, not tappable | BrandRose tappable text → navigates to StoreDetail; ⭐ X.X · N reviews → line if rating > 0 |
| **NotificationsScreen new_review** | 🔔 generic icon, no tap-through | ⭐ icon; tap navigates to StoreReviewsScreen |

### Business rules
- Rating chips only show when `rating > 0` (stores/products with no reviews show no chip)
- Tapping the store name/reviews line on ProductDetail navigates to StoreDetailScreen (full store view)
- `new_review` notification tap resolves store name from SharedPreferences cache (set when store was last viewed); falls back to empty string if not cached

---

## Option B — Pull-to-Refresh

| Screen | Before | After |
|--------|--------|-------|
| HomeScreen | PullToRefreshBox ✅ | No change needed |
| WishlistScreen | PullToRefreshBox ✅ | No change needed |
| ReservationsScreen | PullToRefreshBox ✅ | No change needed |
| NotificationsScreen | PullToRefreshBox ✅ | No change needed |
| **VendorDashboardScreen** | No refresh | PullToRefreshBox — swipe down to reload KPIs without full loading state |

### VendorDashboard refresh behaviour
- First load: shows `DashboardUiState.Loading` spinner (cold load)
- Pull-to-refresh: `isRefreshing = true`, keeps existing content visible, updates in-place — no flash to loading state

---

## Backend change

| File | Change |
|------|--------|
| `apps/products/serializers.py` | `MobileProductDetailSerializer.get_store()` now includes `rating` (avg of reviews) and `review_count` (total review count) for the store |

No migration needed — the fields are computed via `aggregate()` on existing `StoreReview` data.

---

## Mobile changes

| File | Change |
|------|--------|
| `data/models/HomeModels.kt` | Added `rating: Double` and `reviewCount: Int` to `StoreMini` |
| `data/models/ProfileModels.kt` | `AppNotification.emoji`: added `"new_review" -> "⭐"` |
| `ui/screens/search/SearchScreen.kt` | `SearchProductCard`: ★ rating chip; loading state: skeleton grid instead of spinner |
| `ui/screens/product/ProductDetailScreen.kt` | Added `onStoreClick` param; store row is tappable (BrandRose); added ⭐ rating + review count row |
| `ui/screens/vendor/VendorDashboardViewModel.kt` | Added `isRefreshing` StateFlow + `refresh()` + extracted `fetchStats()` |
| `ui/screens/vendor/VendorDashboardScreen.kt` | Wrapped Loaded and NoStore states in `PullToRefreshBox` |
| `MainActivity.kt` | Wired `onStoreClick` on PRODUCT_DETAIL; added `new_review` case to notification tap-through |

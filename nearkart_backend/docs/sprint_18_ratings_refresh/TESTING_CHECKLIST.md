# Sprint 18 — Testing Checklist

## Option A — Rating Badges Everywhere

### SearchScreen — Rating Chip
- [ ] Search for any product that has at least one review (rating > 0)
- [ ] Confirm ★ X.X gold chip appears in the bottom-right of the product card
- [ ] Confirm chip is NOT shown for products with rating = 0 / no reviews
- [ ] Confirm price is still shown in bottom-left alongside the chip

### SearchScreen — Skeleton Loading
- [ ] Trigger a fresh search (clear query, type slowly)
- [ ] Confirm skeleton staggered grid (6 grey boxes, alternating heights) appears while loading
- [ ] Confirm skeleton is replaced by real cards once data arrives
- [ ] Confirm no spinner / `CircularProgressIndicator` is shown during loading

### ProductDetailScreen — Tappable Store Row
- [ ] Open any product detail screen
- [ ] Confirm the store name + distance row is now BrandRose (pink) instead of muted grey
- [ ] Tap the store name row → confirm navigation to StoreDetailScreen for that store
- [ ] Confirm the distance still displays correctly

### ProductDetailScreen — Store Rating Row
- [ ] Open a product from a store that has ≥ 1 review
- [ ] Confirm ⭐ X.X · N reviews → row appears below the store name
- [ ] Tap the rating row → confirm navigation to StoreDetailScreen
- [ ] Open a product from a store with no reviews → confirm rating row is NOT shown
- [ ] Confirm "reviews →" text is BrandRose and invites tap

### NotificationsScreen — new_review Tap-Through
- [ ] Submit a review for a store from a test customer account
- [ ] Check the vendor account notifications — confirm a `new_review` notification appears with ⭐ icon
- [ ] Tap the `new_review` notification → confirm navigation to StoreReviewsScreen for that store
- [ ] Confirm store name is resolved from SharedPreferences cache (visit the store first to populate cache)
- [ ] Test cold path: clear app data → tap `new_review` notification → confirm it still navigates (storeName falls back to empty string)

---

## Option B — Pull-to-Refresh on VendorDashboard

### Cold Load
- [ ] Open VendorDashboard from a fresh launch (no cached data)
- [ ] Confirm `CircularProgressIndicator` spinner shows while loading
- [ ] Confirm KPI cards appear once loaded

### Pull-to-Refresh — Loaded State
- [ ] Open VendorDashboard (fully loaded with store data)
- [ ] Swipe down on the screen
- [ ] Confirm the PullToRefresh indicator appears (spinner at top)
- [ ] Confirm existing KPI values remain visible during refresh (NO flash to Loading spinner)
- [ ] Confirm updated values appear after refresh completes
- [ ] Confirm PullToRefresh indicator disappears after refresh

### Pull-to-Refresh — NoStore State
- [ ] Log in with a vendor account that has no store set up
- [ ] Confirm "You don't have a store yet" banner and empty KPI cards show
- [ ] Swipe down → confirm pull-to-refresh works (indicator appears, data re-fetches)
- [ ] Confirm no flash to Loading state

### Pull-to-Refresh — Already Working Screens (Regression)
- [ ] HomeScreen — swipe down → data refreshes ✅
- [ ] WishlistScreen — swipe down → data refreshes ✅
- [ ] ReservationsScreen — swipe down → data refreshes ✅
- [ ] NotificationsScreen — swipe down → data refreshes ✅

---

## Backend

### ProductDetail Store Response
- [ ] `GET /api/products/{id}/` → response `store` object includes `rating` (float, 1 decimal) and `review_count` (int)
- [ ] For a store with reviews: `rating` > 0, `review_count` > 0
- [ ] For a store with no reviews: `rating` = 0.0, `review_count` = 0
- [ ] No migration needed — verify DB applied without errors

---

## Test Accounts (do not delete or renumber)
- Customer 1: +919000000001
- Customer 2: +919000000002
- Vendor 1: +919999999999
- Vendor 2: +918888888888

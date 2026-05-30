# Sprint 19 — Search Filters & Sort · Store Follow Feed · Vendor Invoices · Map Enhancements

## What was built

Four improvements shipped together:

---

## Option A — Search Filters & Sort

| Surface | Before | After |
|---------|--------|-------|
| SearchScreen search bar | Category chips only | Tune (⚙) icon inside the search bar — highlighted when active |
| Filter bottom sheet | — | Sort (Relevance / Price ↑ / Price ↓ / Rating), Price range slider (₹0–5000), Min rating chips (Any / 3+ / 4+ / 4.5+), "On sale only" toggle |
| Results count | "X results within 2km" | "X results within 5km" + "✕ Clear filters" chip when filters active |

**Backend changes:**
- `ProductSearchView.get()`: new params `min_price`, `max_price`, `min_rating`, `has_offer`, `ordering`
- `ProductService.search()`: applies all filters; `ordering` maps to `price_asc`, `price_desc`, `rating`, or relevance

---

## Option B — Store Follow Feed

| Surface | Before | After |
|---------|--------|-------|
| HomeScreen | One content area (Nearby) | Two tabs: **Nearby** · **Following** |
| Following tab | — | Products from all followed stores, listed in reverse-chronological order |
| Following empty state | — | "No followed stores yet. Tap ♡ on any store…" |

**Backend changes:**
- New endpoint: `GET /api/v1/products/following/` — returns latest products from stores the authenticated user follows (via `StoreFollow`)

**Note:** Follow/Unfollow button already existed on StoreDetailScreen (heart icon, top-right of cover image). No changes needed there.

---

## Option C — Vendor Invoices (Live)

| Surface | Before | After |
|---------|--------|-------|
| VendorInvoiceListScreen | "Invoices coming soon" stub | Real invoice list from API; empty state with + FAB |
| VendorCreateInvoiceScreen | Static UI, no API call | Wired to `POST /stores/mine/invoices/`; line-item builder with add/remove; real total calculation |

**Backend changes:**
- New model: `Invoice` (store, customer_name, customer_phone, items JSONField, notes, total, is_sent)
- Migration: `0005_add_invoice_model`
- New serializer: `InvoiceSerializer`
- New view: `StoreInvoiceListCreateView` at `GET/POST /api/v1/stores/mine/invoices/`

---

## Option D — Map Enhancements

| Surface | Before | After |
|---------|--------|-------|
| MapScreen category chips | Fixed 2km radius | Radius selector chips: **1km · 2km · 5km · 10km** (gold when selected) |
| Map bottom sheet | Open/Closed badge + distance | + ★ X.X gold chip when store has rating > 0 |

**Backend changes:** none — `radius` param was already supported by the nearby stores endpoint.

---

## Mobile files changed

| File | Change |
|------|--------|
| `data/api/StoreApiService.kt` | Added `min_price`, `max_price`, `min_rating` to `searchProducts`; added `getFollowingFeed()` |
| `data/repository/StoreRepository.kt` | Updated `searchProducts()` signature; added `getFollowingFeed()` |
| `data/repository/HomeRepository.kt` | Added `radius` param to `getNearbyStores()` |
| `data/api/VendorApiService.kt` | Added `getInvoices()`, `createInvoice()`, `Invoice`, `InvoiceItem`, `InvoiceListResponse`, `CreateInvoiceRequest` |
| `ui/screens/search/SearchViewModel.kt` | Added `SearchFilters` data class; `applyFilters()`, `clearFilters()`; all filter params forwarded to repo |
| `ui/screens/search/SearchScreen.kt` | Tune icon in search bar; `SearchFilterSheet` bottom sheet; "✕ Clear filters" chip |
| `ui/screens/home/HomeViewModel.kt` | Added `followingProducts`, `isFollowingLoading`, `activeTab` StateFlows; `selectTab()`, `loadFollowing()`, `refreshFollowing()` |
| `ui/screens/home/HomeScreen.kt` | Nearby/Following tab row; Following content area; `FollowingProductCard` |
| `ui/screens/vendor/VendorInvoiceViewModel.kt` | New — `InvoiceUiState`, `CreateInvoiceState`, `load()`, `createInvoice()` |
| `ui/screens/vendor/VendorInvoiceScreen.kt` | Fully wired; list with real data; create screen with live item builder + API save |
| `ui/screens/map/MapViewModel.kt` | Added `radius` StateFlow + `setRadius()` |
| `ui/screens/map/MapScreen.kt` | Radius chip row (1/2/5/10km); rating chip in bottom sheet |
| `MainActivity.kt` | Fixed `VendorCreateInvoiceScreen` wiring (`onSaved` instead of `onPreview`) |

---

## Backend files changed

| File | Change |
|------|--------|
| `apps/products/views.py` | `ProductSearchView`: new filter params; added `FollowingFeedView` |
| `apps/products/services.py` | `ProductService.search()`: `min_price`, `max_price`, `min_rating`, `has_offer`, `ordering` |
| `apps/products/urls.py` | Added `products/following/` route |
| `apps/stores/models.py` | Added `Invoice` model |
| `apps/stores/serializers.py` | Added `InvoiceSerializer` |
| `apps/stores/views.py` | Added `StoreInvoiceListCreateView` |
| `apps/stores/urls.py` | Added `stores/mine/invoices/` route |
| `apps/stores/migrations/0005_add_invoice_model.py` | Migration for Invoice table |

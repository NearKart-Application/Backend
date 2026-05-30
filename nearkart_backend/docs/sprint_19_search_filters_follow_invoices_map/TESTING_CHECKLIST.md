# Sprint 19 — Testing Checklist

## Option A — Search Filters & Sort

### Filter sheet opens / closes
- [ ] Tap the ⚙ (Tune) icon inside the search bar → filter bottom sheet slides up
- [ ] Dismiss by swiping down or tapping outside → sheet closes without applying
- [ ] "Clear all" button in the sheet header → resets all options back to defaults

### Sort
- [ ] Select "Price: Low → High" → tap Apply → results re-ordered cheapest first
- [ ] Select "Price: High → Low" → most expensive products first
- [ ] Select "Top Rated" → highest store-rating products first
- [ ] Select "Relevance" → back to keyword-match order

### Price range
- [ ] Drag min slider to ₹200 → products under ₹200 disappear
- [ ] Drag max slider to ₹1000 → products over ₹1000 disappear
- [ ] Both sliders mid-range → only products within that band shown
- [ ] Max slider at 5000 → label shows "₹5000+" → no upper bound sent to backend

### Min rating
- [ ] Select "3+" → confirm only products from stores rated ≥ 3 returned
- [ ] Select "4+" → stricter; fewer results expected
- [ ] Select "Any" → rating filter removed

### On sale only
- [ ] Toggle "On sale only" on → confirm only products from stores with active offers returned
- [ ] Toggle off → sale filter removed

### Active filter indicator
- [ ] When any filter is active → Tune icon shows white icon on BrandRose background
- [ ] "✕ Clear filters" chip appears in the results count row → tap it → all filters cleared, icon resets

---

## Option B — Store Follow Feed

### Tab switching
- [ ] HomeScreen shows "Nearby" and "Following" tabs below the top bar
- [ ] Tap "Following" → Following tab becomes active (bold + BrandRose underline)
- [ ] Tap "Nearby" → switches back

### Following tab — empty state
- [ ] Log in as a customer who follows no stores → Following tab shows "No followed stores yet" message

### Following tab — with followed stores
- [ ] Follow ≥ 1 store (via ♡ button on StoreDetailScreen)
- [ ] Go to HomeScreen → tap "Following" → products from followed store(s) appear as horizontal list cards
- [ ] Each card shows: product image, name, store name, price, rating chip (if applicable)
- [ ] Tap a product card → navigates to ProductDetailScreen

### Pull-to-refresh
- [ ] On Following tab → swipe down → spinner appears → products reload

### Nearby tab unchanged
- [ ] "Nearby" tab shows existing stores + products content unaffected

---

## Option C — Vendor Invoices

### Invoice list (live)
- [ ] Log in as a vendor → tap Invoices from VendorDashboard
- [ ] Loading spinner appears → invoice list loads (or empty state if no invoices)
- [ ] Empty state: Receipt icon + "No invoices yet" + explanation text
- [ ] Refresh icon in top bar → reloads the list

### Create invoice
- [ ] Tap FAB (+) → navigates to Create Invoice screen
- [ ] Leave Customer Name blank → tap Generate → error shown ("Customer name and at least one item are required")
- [ ] Enter customer name
- [ ] Fill in "Add item" fields (name + price + qty) → tap "Add to invoice" → item appears in list
- [ ] Total updates correctly (sum of price × qty for all items)
- [ ] Delete icon removes a line item (not allowed to delete below 1 item)
- [ ] Tap "Generate Invoice" → loading spinner in button
- [ ] On success → navigates back to invoice list → new invoice appears at top

### Invoice card in list
- [ ] Shows customer name, item count, date, total amount
- [ ] "Sent" label visible for invoices marked is_sent = true

### Regression
- [ ] VendorDashboard → "Invoices" quick action → navigates to list ✓

---

## Option D — Map Enhancements

### Radius selector
- [ ] MapScreen shows radius chips: **1km · 2km · 5km · 10km** below the category chips
- [ ] Default chip "2km" is highlighted gold
- [ ] Tap "5km" → chip highlights gold → map reloads → more stores visible in wider radius
- [ ] Tap "1km" → chip highlights → fewer stores (tight radius)
- [ ] Radius persists while the screen is open (no reset on category change)

### Rating in bottom sheet
- [ ] Tap a map pin for a store with ≥ 1 review → bottom sheet shows ★ X.X gold chip
- [ ] Tap a pin for a store with zero reviews → no rating chip (neither "★ 0.0" nor any placeholder)
- [ ] Open/Closed badge and distance still shown correctly

### Existing functionality unchanged
- [ ] "View Store" button navigates to StoreDetailScreen
- [ ] "Chat" button opens chat thread
- [ ] Category filter chips still filter map pins
- [ ] My Location FAB still re-centres camera

---

## Test Accounts (do not delete or renumber)
- Customer 1: +919000000001
- Customer 2: +919000000002
- Vendor 1: +919999999999 (Dev Test Store)
- Vendor 2: +918888888888

# Sprint 23 — Testing Checklist

---

## Part A — Store Hours

- [ ] Open vendor store setup with an existing store — hour rows pre-fill from API values
- [ ] Tap edit on a day — change time and toggle Closed — tap Save
- [ ] Tap the main Save — verify PUT `/stores/{id}/hours/` called with all 7 days
- [ ] Create a new store — hours submitted alongside create
- [ ] Reload store setup — previously saved hours appear correctly
- [ ] Mark Sunday as Closed — verify `is_closed: true` in payload and "Closed" chip on screen
- [ ] Without internet — hours fallback gracefully (default 10:00–21:00)

---

## Part B — Vendor Discount Codes

### Backend

- [ ] POST `/stores/mine/discount-codes/` with `discount_type=percent, value=20` — code created
- [ ] POST same code again for same store — 400 `unique_store_code` error
- [ ] GET `/stores/mine/discount-codes/` — returns list including new code
- [ ] PATCH `…/<code_id>/` with `is_active: false` — code deactivated
- [ ] DELETE `…/<code_id>/` — 204, code gone from GET list
- [ ] POST `/stores/{id}/apply-discount/` with valid code + order above min — returns `valid: true` with correct `discount_amount`
- [ ] Apply with expired `valid_till` — returns `valid: false, error: expired`
- [ ] Apply with `order_amount` below `min_order_amount` — returns `valid: false, error: min_order_not_met`
- [ ] Apply after `max_uses` reached — returns `valid: false, error: max_uses_reached`
- [ ] Apply inactive code — returns `valid: false, error: inactive`
- [ ] Apply with unknown code — returns `valid: false, error: not_found`
- [ ] Percent discount capped at order amount (value > 100%)
- [ ] Flat discount: `value=100, order=80` → `discount_amount=80, final_amount=0`

### Mobile — Vendor

- [ ] Settings → Discount Codes — screen loads, empty state shows correctly
- [ ] Tap + → create sheet opens with all fields
- [ ] Create "SAVE20" percent 20 — appears in list with correct label
- [ ] Create duplicate code "SAVE20" — error snackbar "A code with that name already exists"
- [ ] Toggle active switch — immediate optimistic update in list
- [ ] Delete code → confirm dialog → deleted, removed from list
- [ ] Long list scrolls without jank

### Mobile — Customer

- [ ] Product detail screen — "Have a discount code?" section visible
- [ ] Tap section header — expands with code and order amount inputs
- [ ] Tap again — collapses, clears state
- [ ] Enter valid code + order amount ≥ min → green "Code applied! Saving ₹X" shows
- [ ] Enter expired/wrong code — red error row shows
- [ ] Discount section not visible when store has no discount codes (apply will return invalid — behaviour correct)

---

## Part C — Product Image Gallery

### Backend

- [ ] GET `/products/{id}/images/` — returns list with `id, url, is_primary, created_at`
- [ ] DELETE `/products/{id}/images/{image_id}/` — 200, file gone, response contains remaining images
- [ ] Delete primary image — next image promoted to `is_primary: true`
- [ ] Delete last image — returns empty list, product `primary_image` set to `""`
- [ ] Non-owner trying to delete — 403
- [ ] Delete already-deleted image — 404

### Mobile

- [ ] Edit product — existing images load immediately below "Current Images" label
- [ ] Primary image shows "Main" badge
- [ ] Tap ✕ on an image — image removed from row, remaining images update in-place
- [ ] Delete primary image — next image gets "Main" badge
- [ ] After deleting all existing images — existing images row disappears, only new picker shown
- [ ] New image picker still works alongside existing images
- [ ] Upload new images after deleting old ones — uploads correctly
- [ ] Images display correct URLs (not localhost port-8000 URLs)

---

## General

- [ ] All API calls use correct authentication headers
- [ ] Errors are user-facing strings, not raw HTTP codes
- [ ] No crashes on slow network / empty states
- [ ] Back navigation works correctly from all new screens

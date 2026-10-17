# Sprint 21 — Testing Checklist

## Pre-conditions
- Docker is running (`docker compose up`)
- You have an admin JWT (role: `admin`)
- You have a vendor JWT (role: `vendor`)
- At least one offer template with `is_default=true` exists (create it in step A)

---

## A — Category Management (Admin)

### Create
- [ ] `POST /api/v1/admin-panel/categories/` with `name`, `slug`, `icon`, `display_order`, `is_active: true`
  - Expect: `201` with full category object including `id`
- [ ] Create duplicate name → expect `400` with validation error
- [ ] Create with `is_active: false` → confirm it is hidden from public endpoint
- [ ] Non-admin token → expect `403`

### List (Admin)
- [ ] `GET /api/v1/admin-panel/categories/` → returns both active and inactive categories
- [ ] Results ordered by `display_order` then `name`

### Update
- [ ] `PATCH /api/v1/admin-panel/categories/<id>/` → change `name`, `icon`, `display_order`
  - Expect: `200` with updated fields
- [ ] Set `is_active: false` → category disappears from public list
- [ ] Set `is_active: true` → category reappears in public list
- [ ] Non-existent `id` → expect `404`

### Delete
- [ ] `DELETE /api/v1/admin-panel/categories/<id>/` → expect `204`
- [ ] Re-fetch deleted id → expect `404`
- [ ] Non-admin token → expect `403`

### Public Endpoint
- [ ] `GET /api/v1/products/categories/` → returns only active categories
- [ ] Inactive category created above is NOT in this list
- [ ] Unauthenticated → expect `401`

---

## B — Offer Template Management (Admin)

### Create
- [ ] `POST /api/v1/admin-panel/offer-templates/` with all fields: `name`, `description_template`, `default_discount_pct`, `badge_text`, `emoji`, `is_active: true`, `is_default: false`
  - Expect: `201` with full template object
- [ ] Create another template with `is_default: true`
  - Expect: previous default has `is_default` flipped to `false`
- [ ] Non-admin token → expect `403`

### Single-Default Invariant
- [ ] Create 3 templates, set each to `is_default: true` one by one
- [ ] After each, verify only 1 template has `is_default: true` in the admin list
- [ ] At no point should 2 templates simultaneously have `is_default: true`

### List (Admin)
- [ ] `GET /api/v1/admin-panel/offer-templates/` → returns all templates including inactive
- [ ] Results ordered by `display_order` then `name`

### Update
- [ ] `PATCH /api/v1/admin-panel/offer-templates/<id>/` → update `name`, `badge_text`, `default_discount_pct`
  - Expect: `200`
- [ ] Set `is_active: false` → template disappears from public endpoint
- [ ] Set `is_default: true` on a non-default → existing default flipped to false
- [ ] Non-existent `id` → expect `404`

### Delete
- [ ] `DELETE /api/v1/admin-panel/offer-templates/<id>/` → expect `204`
- [ ] Non-admin token → expect `403`

### Public Endpoint
- [ ] `GET /api/v1/stores/offer-templates/` with vendor token → returns only active templates
- [ ] Inactive template is NOT in this list
- [ ] Unauthenticated → expect `401`
- [ ] Customer token → check expected behaviour (401 or filtered list per implementation)

---

## C — Vendor Offers Screen (Mobile)

- [ ] Open VendorOffersScreen → template chip row loads from API (no hardcoded data)
- [ ] Template with `is_default: true` is auto-selected on first open
- [ ] Selecting a chip pre-fills: name, description, discount %
- [ ] Tapping "Custom" chip clears all fields
- [ ] If API returns empty list → screen still renders (no crash)
- [ ] Inactive templates do NOT appear in the chip row

---

## D — Admin Mobile Screens

### Categories Screen
- [ ] Admin home shows "Categories" action card → navigates to `AdminCategoriesScreen`
- [ ] List loads all categories including inactive (shows "Hidden" badge)
- [ ] Create: tap FAB → bottom sheet opens → fill fields → save → row appears
- [ ] Edit: tap edit icon → sheet pre-fills existing data → save → row updates
- [ ] Hide/Show: tap toggle → "Hidden" badge appears/disappears in list
- [ ] Delete: tap delete → confirmation dialog → confirm → row removed
- [ ] Snackbar shown after each successful action

### Offer Templates Screen
- [ ] Admin home shows "Offer Templates" action card → navigates to `AdminOfferTemplatesScreen`
- [ ] List loads all templates
- [ ] DEFAULT chip visible on the default template
- [ ] Create: fill all fields including is_default toggle → save → appears in list
- [ ] Setting is_default on a new template → previous DEFAULT chip moves
- [ ] Edit: pre-fills correctly, updates on save
- [ ] Delete: confirmation → row removed
- [ ] Snackbar shown after each action

---

## E — Edge Cases

- [ ] Create category with `display_order: 0` and another with `display_order: 1` → public list returns them in correct order
- [ ] Slug collision → `400` returned
- [ ] Deleting the default offer template → no crash; public list returns remaining active templates
- [ ] Empty categories list → `GET /api/v1/products/categories/` returns `[]` not `404`
- [ ] Empty offer templates list → `GET /api/v1/stores/offer-templates/` returns `[]` not `404`

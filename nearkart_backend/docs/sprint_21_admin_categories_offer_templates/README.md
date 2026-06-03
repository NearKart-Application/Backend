# Sprint 21 — Admin Category Management + Admin Offer Templates

## What was built

Two admin-managed data systems that connect across the full stack (admin panel → vendor side → customer-facing APIs).

---

## Part A — Category Management

Admins can now create and manage the master category list used across the app (e.g., Groceries, Electronics, Fashion).

### Fields

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Auto-generated primary key |
| `name` | CharField(100) | Unique |
| `slug` | SlugField(100) | Unique, URL-safe |
| `icon` | CharField(10) | Emoji or icon code |
| `display_order` | PositiveIntegerField | Controls list order |
| `is_active` | BooleanField | Hidden from public when false |
| `created_by` | FK → User | Admin who created it |
| `created_at` / `updated_at` | DateTimeField | Auto timestamps |

### Admin Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/api/v1/admin-panel/categories/` | List all categories (active + inactive) |
| `POST` | `/api/v1/admin-panel/categories/` | Create a new category |
| `PATCH` | `/api/v1/admin-panel/categories/<id>/` | Edit name / icon / order / active status |
| `DELETE` | `/api/v1/admin-panel/categories/<id>/` | Delete a category |

### Public Endpoint

| Method | URL | Permission | Description |
|--------|-----|-----------|-------------|
| `GET` | `/api/v1/products/categories/` | Any authenticated | Active categories only (vendors + customers) |

### Database

| Table | Key Indexes |
|-------|------------|
| `admin_categories` | `display_order`, `is_active` |

---

## Part B — Offer Template Management

Admins manage a library of reusable offer templates (e.g., Summer Sale, Festive Offer, Weekend Deal). Vendors pick from these when creating offers.

### Fields

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Auto-generated primary key |
| `name` | CharField(200) | Display name (e.g., "Summer Sale") |
| `description_template` | TextField | Pre-filled description text |
| `default_discount_pct` | PositiveSmallIntegerField | Suggested discount % (optional) |
| `badge_text` | CharField(20) | Short badge label (e.g., "HOT") |
| `emoji` | CharField(10) | Visual emoji for the chip |
| `image_url` | URLField | Optional banner image |
| `is_active` | BooleanField | Hidden from vendors when false |
| `is_default` | BooleanField | One default per system — auto-selected for vendors |
| `display_order` | PositiveIntegerField | Chip order in vendor UI |
| `created_by` | FK → User | Admin who created it |

### Single-Default Invariant

Only one template can have `is_default=True` at a time. Setting a new default automatically unsets any existing default (enforced in both the backend `save()` and the mobile ViewModel).

### Admin Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/api/v1/admin-panel/offer-templates/` | List all templates (active + inactive) |
| `POST` | `/api/v1/admin-panel/offer-templates/` | Create a new template |
| `PATCH` | `/api/v1/admin-panel/offer-templates/<id>/` | Edit any field including is_default |
| `DELETE` | `/api/v1/admin-panel/offer-templates/<id>/` | Delete a template |

### Public Endpoint

| Method | URL | Permission | Description |
|--------|-----|-----------|-------------|
| `GET` | `/api/v1/stores/offer-templates/` | Vendor (authenticated) | Active templates only |

### Database

| Table | Key Indexes |
|-------|------------|
| `admin_offer_templates` | `display_order`, `is_active`, `is_default` |

---

## Part C — Vendor Integration

The `VendorOffersScreen` now loads templates from the API instead of hardcoded data.

- Templates displayed as horizontal chip row
- The template with `is_default=true` is auto-selected when the screen opens
- Selecting a chip pre-fills: name, description, discount %, badge text
- "Custom" chip clears all pre-fills — vendor builds an offer from scratch
- Inactive templates are never shown (filtered server-side)

---

## Mobile Screens Added

### Admin: Categories Screen (`AdminCategoriesScreen`)
- List view: emoji + name + "Hidden" badge for inactive
- Each row: **Edit** / **Hide/Show** / **Delete** actions
- ModalBottomSheet: emoji field, name field, display order, is_active toggle
- Delete confirmation dialog + snackbar feedback

### Admin: Offer Templates Screen (`AdminOfferTemplatesScreen`)
- List view: emoji + name + discount badge + **DEFAULT** chip + "Hidden" badge
- Each row: **Edit** / **Set Default** / **Hide/Show** / **Delete** actions
- ModalBottomSheet: all fields including is_default toggle
- Setting default locally unsets previous default in UI state

### Admin Home
- Two new action cards: **Categories** and **Offer Templates**

---

## Backend Files Changed

| File | Change |
|------|--------|
| `apps/admin_panel/models.py` | Added `Category` + `OfferTemplate` models |
| `apps/admin_panel/serializers.py` | Added serializers for both models |
| `apps/admin_panel/views.py` | Added 6 new views (CRUD + 2 public) |
| `apps/admin_panel/urls.py` | Added 8 new URL patterns |
| `apps/admin_panel/migrations/0003_category_offertemplate.py` | New migration |
| `apps/products/urls.py` | Delegated `categories/` public endpoint |
| `apps/stores/urls.py` | Delegated `offer-templates/` public endpoint |

## Mobile Files Changed

| File | Change |
|------|--------|
| `data/api/AdminApiService.kt` | 4 new data classes + 10 new Retrofit methods |
| `ui/screens/admin/AdminCategoriesScreen.kt` | New admin screen |
| `ui/screens/admin/AdminCategoriesViewModel.kt` | New ViewModel |
| `ui/screens/admin/AdminOfferTemplatesScreen.kt` | New admin screen |
| `ui/screens/admin/AdminOfferTemplatesViewModel.kt` | New ViewModel |
| `ui/screens/admin/AdminHomeScreen.kt` | 2 new action cards |
| `ui/navigation/NavGraph.kt` | 2 new route constants |
| `MainActivity.kt` | Wired 2 new composable routes |
| `ui/screens/vendor/VendorOffersViewModel.kt` | Loads templates from API |
| `ui/screens/vendor/VendorOffersScreen.kt` | API-driven template chips + default auto-selection |

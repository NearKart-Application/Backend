# Sprint 3 — Store & Product Module

**Goal:** Vendors create stores and products. Customers discover nearby stores and products.
**Status:** Done ✅
**Actual time:** ~20 hours
**Depends on:** Sprint 2 (Auth) complete

---

## What Was Built

### Files Created / Modified

| File | Purpose |
|------|---------|
| `apps/stores/models.py` | Store, StoreHours, StoreFollow, StoreReview models |
| `apps/stores/serializers.py` | StoreSerializer, StoreListSerializer, StoreReviewSerializer |
| `apps/stores/services.py` | StoreService (create/update/follow/review), QRService |
| `apps/stores/views.py` | 7 API endpoint views |
| `apps/stores/urls.py` | URL routing for stores |
| `apps/stores/admin.py` | StoreAdmin with verify action, StoreReviewAdmin, StoreFollowAdmin |
| `apps/stores/migrations/0001_initial.py` | Creates tables + indexes |
| `apps/stores/migrations/0002_store_location_geography.py` | Adds geography=True to PointField |
| `apps/products/models.py` | Product, ProductVariant, ProductImage, Wishlist models |
| `apps/products/serializers.py` | ProductSerializer, ProductListSerializer, ProductVariantSerializer |
| `apps/products/services.py` | ProductService (create/update/search/wishlist) |
| `apps/products/views.py` | 6 API endpoint views |
| `apps/products/urls.py` | URL routing for products |
| `apps/products/admin.py` | ProductAdmin with inline variants/images, WishlistAdmin |
| `apps/products/migrations/0001_initial.py` | Creates tables + indexes |
| `core/utils/geo.py` | Added get_nearby_products() |
| `core/utils/cache.py` | Added nearby_products_key() |

---

## Database Models

### Store
```
id                UUID (primary key)
owner             OneToOneField → User (one store per vendor)
name              String — GIN trigram index for search
category          Enum: fashion/jewellery/footwear/decor/furniture/gifts/beauty/food/electronics/other
phone             String (optional)
address           Text
locality          Auto-filled by reverse_geocode() on create/location change
location          PointField(geography=True) — PostGIS geographic coordinates
logo_url          URL (optional)
banner_url        URL (optional)
qr_code_url       URL — set by QRService on first GET /qr-code/
is_active         Boolean (default True)
is_verified       Boolean (default False) — must be True to appear in nearby results
is_open           Boolean (default False) — vendor toggles
performance_score Float — auto-calculated average of all review ratings
wallet_balance    Decimal — for future promotions
```

### StoreHours
```
store       ForeignKey → Store
day         Integer: 0=Monday … 6=Sunday (unique per store)
open_time   Time
close_time  Time
is_closed   Boolean
```

### StoreFollow / StoreReview
```
user + store   unique_together
rating         Integer 1–5 (StoreReview only)
comment        Text (StoreReview only)
```

### Product
```
id              UUID (primary key)
store           ForeignKey → Store
name            String — GIN trigram index for search
description     Text (optional)
category        String (free text, not enum)
status          Enum: draft/active/inactive/out_of_stock
is_visible      Boolean (default True)
base_price      Decimal
last_updated_at DateTime (auto_now)
```

### ProductVariant
```
product         ForeignKey → Product
name            String (e.g. Small, Red, XL)
sku             String — globally unique across all products
price           Decimal
stock_quantity  Integer (nearby query filters qty > 0)
```

### ProductImage / Wishlist
```
ProductImage: product, image_url, s3_key, is_primary, order
Wishlist:     user + product (unique_together)
```

---

## API Endpoints

Base URL: `http://localhost:8000/api/v1/`

### Store Endpoints

| Method | URL | Auth | Purpose |
|--------|-----|------|---------|
| GET | `stores/nearby/` | None | Get stores within radius (lat, lng, radius, category) |
| GET | `stores/<uuid>/` | None | Full store detail with hours and reviews |
| POST | `stores/` | Vendor JWT | Create store (one per vendor) |
| PUT | `stores/<uuid>/update/` | Owner JWT | Update store fields (partial) |
| POST | `stores/<uuid>/follow/` | JWT | Follow / unfollow toggle |
| POST | `stores/<uuid>/review/` | JWT | Add or update review (rating 1–5) |
| GET | `stores/<uuid>/qr-code/` | Owner JWT | Get or generate QR code |

### Product Endpoints

| Method | URL | Auth | Purpose |
|--------|-----|------|---------|
| GET | `products/nearby/` | None | Get products within radius |
| GET | `products/search/` | None | Trigram search by name |
| GET | `products/<uuid>/` | None | Full product with variants, images, is_wishlisted |
| POST | `products/` | Vendor JWT | Create product with variants |
| PUT | `products/<uuid>/update/` | Owner JWT | Update product (partial) |
| DELETE | `products/<uuid>/update/` | Owner JWT | Hard delete product |
| POST | `products/<uuid>/wishlist/` | JWT | Add / remove wishlist toggle |

---

## Key Technical Decisions

**geography=True on Store.location**
Django's DWithin filter with D(km=...) requires a geographic field. Plain geometry raises a ValueError.

**is_verified=False default**
New stores are invisible in nearby queries until an admin verifies them. Prevents fake stores appearing.

**Trigram search threshold 0.2**
TrigramSimilarity > 0.2 catches partial matches while filtering noise. Results sorted by similarity score.

**update_or_create for reviews**
One review per user per store. Calling the review endpoint again updates the existing review and recalculates performance_score.

---

## Important Notes

- New stores have `is_verified=False`. For testing: set `is_verified=True` in Django admin or psql.
- Products in `draft` status do NOT appear in nearby/search results. Set `status=active`.
- Nearby products only returns products with at least one variant with `stock_quantity > 0`.
- QR code generation requires AWS S3. In dev it fails silently — `qr_code_url` stays empty.
- `locality` field is auto-set via Google Maps API on store create. Falls back to "Unknown area" if API fails.

---

## Dev Testing Note

OTP is always `123456` when `DEV_FIXED_OTP=123456` is set in `.env`.
Real Twilio SMS and AWS S3 are deferred to Sprint 12.

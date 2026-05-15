# Sprint 3 — Store & Product Module: Code Reference

Files created or modified in this sprint.

---

## apps/stores/models.py

### `StoreCategory` (TextChoices)
Enum for store types: `fashion`, `jewellery`, `footwear`, `decor`, `furniture`, `gifts`, `beauty`, `food`, `electronics`, `other`.
Used as `choices` on `Store.category`.

### `Store(BaseModel)`
Core store entity. One store per vendor (OneToOneField to User).

| Field | Type | Notes |
|-------|------|-------|
| `owner` | OneToOneField(User) | Each vendor can have exactly one store |
| `name` | CharField(200) | GIN trigram index for fast text search |
| `description` | TextField | Optional |
| `category` | CharField | Choices from `StoreCategory` |
| `phone` | CharField(15) | Optional store contact |
| `address` | TextField | Human-readable address |
| `locality` | CharField(200) | Auto-filled via reverse geocode |
| `location` | PointField(srid=4326, geography=True) | PostGIS geographic point — `geography=True` required for meter-based DWithin queries |
| `logo_url` | URLField | Optional CDN URL |
| `banner_url` | URLField | Optional CDN URL |
| `qr_code_url` | URLField | Auto-set by QRService on first request |
| `is_active` | BooleanField(default=True) | Soft delete flag |
| `is_verified` | BooleanField(default=False) | Set to True by admin after vetting; nearby queries filter on this |
| `is_open` | BooleanField(default=False) | Vendor toggles when store opens/closes |
| `performance_score` | FloatField(default=0.0) | Auto-calculated as average of all review ratings |
| `wallet_balance` | DecimalField | For future ad spend / promotions |

**Meta:**
- `db_table = 'stores'`
- Composite index on `(is_active, is_verified)` — used by every nearby query
- GIN index on `name` with `gin_trgm_ops` — needed for trigram similarity search
- Ordering: `-created_at`

---

### `StoreHours(Model)`
Operating hours per day for a store.

| Field | Type | Notes |
|-------|------|-------|
| `store` | ForeignKey(Store) | Parent store |
| `day` | PositiveSmallIntegerField | 0=Monday … 6=Sunday |
| `open_time` | TimeField | Opening time |
| `close_time` | TimeField | Closing time |
| `is_closed` | BooleanField(default=False) | True if closed on that day |

**Meta:** `unique_together = [('store', 'day')]` — one entry per store per day.

---

### `StoreFollow(BaseModel)`
Tracks which users follow which stores.

| Field | Type | Notes |
|-------|------|-------|
| `user` | ForeignKey(User) | Following user |
| `store` | ForeignKey(Store) | Followed store |

**Meta:** `unique_together = [('user', 'store')]` — one follow record per user-store pair.

---

### `StoreReview(BaseModel)`
User reviews for stores (rating 1–5).

| Field | Type | Notes |
|-------|------|-------|
| `user` | ForeignKey(User) | Reviewer |
| `store` | ForeignKey(Store) | Store being reviewed |
| `rating` | PositiveSmallIntegerField | 1–5 (validated in serializer) |
| `comment` | TextField | Optional written review |

**Meta:** `unique_together = [('user', 'store')]` — one review per user per store (upsert pattern).

---

## apps/stores/serializers.py

### `StoreHoursSerializer`
Read-only serializer for store operating hours. Exposes `day_name` via `get_day_display`.

### `StoreSerializer`
Full store serializer used for create, update, and detail endpoints.

**Write-only fields:** `latitude`, `longitude` — accepted on input, converted to a `PointField` in the service layer.

**Read-only computed fields:**
- `lat`, `lng` — extracted from `store.location.y / .x`
- `owner_phone` — from `store.owner.phone_number`
- `follower_count` — count of `store.followers`
- `distance_km` — available only when ORM annotates `distance` (nearby queries)
- `hours` — nested `StoreHoursSerializer`

**Read-only model fields:** `id`, `is_verified`, `performance_score`, `qr_code_url`, `locality`, `created_at`

### `StoreListSerializer`
Compact version for nearby/list endpoints. Only includes: `id`, `name`, `category`, `locality`, `logo_url`, `is_open`, `is_verified`, `performance_score`, `lat`, `lng`, `distance_km`.

### `StoreReviewSerializer`
Used for both reading and writing reviews. `validate_rating` enforces 1–5 range. `user_phone` is read-only.

---

## apps/stores/services.py

### `StoreService`

**`create(user, validated_data) → Store`**
- Pops `latitude` and `longitude` from validated data
- Creates a PostGIS `Point(lng, lat, srid=4326)` (note: longitude is X, latitude is Y)
- Calls `reverse_geocode(lat, lng)` to auto-fill `locality`
- Creates and returns the store

**`update(store, validated_data) → Store`**
- If `latitude`/`longitude` present: updates `store.location`, re-geocodes locality, invalidates nearby cache
- Sets all other fields with `setattr`
- Deletes store detail cache key
- Returns saved store

**`get_nearby(lat, lng, radius_km, category) → QuerySet`**
- Delegates to `core.utils.geo.get_nearby_stores()`

**`toggle_follow(user, store) → bool`**
- `get_or_create` on `StoreFollow`
- If already exists: deletes and returns `False` (unfollowed)
- If new: returns `True` (followed)

**`add_review(user, store, rating, comment) → StoreReview`**
- `update_or_create` on `StoreReview` — upsert pattern (user can only have one review per store)
- Recalculates `store.performance_score` as average of all ratings
- Saves only `performance_score` field for efficiency

### `QRService`

**`generate_and_upload(store) → str`**
- Generates a QR code image using the `qrcode` library pointing to `https://nearkart.in/stores/<id>`
- Uploads PNG to S3 at key `qrcodes/<store_id>/qr.png`
- Saves CDN URL to `store.qr_code_url`
- Wrapped in try/except — fails gracefully in dev (returns empty string)

---

## apps/stores/views.py

### `NearbyStoresView` — GET /stores/nearby/
- `AllowAny` permission
- Parses `lat`, `lng`, `radius`, `category` query params
- Delegates to `StoreService.get_nearby()`
- Returns `StoreListSerializer` (compact)

### `StoreDetailView` — GET /stores/<store_id>/
- `AllowAny` permission
- Redis cache lookup first (`CacheService.store_detail_key`)
- On miss: fetches with `prefetch_related('hours', 'reviews')`
- Caches result for `TTL_STORE_DETAIL` seconds

### `StoreCreateView` — POST /stores/
- `IsAuthenticated + IsVendor` permissions
- Guards against creating a second store (`hasattr(user, 'store')`)
- Validates with `StoreSerializer`, delegates to `StoreService.create()`

### `StoreUpdateView` — PUT /stores/<store_id>/update/
- `IsAuthenticated + IsStoreOwner` permissions
- `partial=True` on serializer — only sent fields are updated

### `StoreFollowView` — POST /stores/<store_id>/follow/
- `IsAuthenticated` permission
- Toggle follow via `StoreService.toggle_follow()`
- Returns `{ followed: bool, message: str }`

### `StoreReviewView` — POST /stores/<store_id>/review/
- `IsAuthenticated` permission
- Validates rating (1–5) via `StoreReviewSerializer`
- Delegates to `StoreService.add_review()`

### `StoreQRCodeView` — GET /stores/<store_id>/qr-code/
- `IsAuthenticated + IsStoreOwner` permissions
- Returns existing `qr_code_url` or generates new one via `QRService.generate_and_upload()`

---

## apps/stores/admin.py

### `StoreAdmin`
- List display: name, owner, category, locality, verification/active/open flags, performance score
- List filters: category, is_verified, is_active, is_open
- Search by name, owner phone, locality
- Inline: `StoreHoursInline` — manage hours from store detail page
- Actions: `verify_stores` / `unverify_stores` — bulk update `is_verified`

### `StoreReviewAdmin`
- List display: store name, user, rating, date
- Filter by rating

### `StoreFollowAdmin`
- List display: user, store, date

---

## apps/products/models.py

### `ProductStatus` (TextChoices)
`draft`, `active`, `inactive`, `out_of_stock`

### `Product(BaseModel)`

| Field | Type | Notes |
|-------|------|-------|
| `store` | ForeignKey(Store) | Parent store |
| `name` | CharField(200) | GIN trigram index for search |
| `description` | TextField | Optional |
| `category` | CharField(50) | Free text (not enum — stores can create their own subcategories) |
| `status` | CharField | Choices from `ProductStatus`, default `draft` |
| `is_visible` | BooleanField(db_index=True) | Hide without deleting |
| `base_price` | DecimalField | Base price — may be overridden per variant |
| `last_updated_at` | DateTimeField(auto_now=True) | Auto-updated on every save |

**Meta:** Composite index on `(status, is_visible)` + GIN index on `name`.

### `ProductVariant(BaseModel)`
Size / color / style variants for a product.

| Field | Type | Notes |
|-------|------|-------|
| `product` | ForeignKey(Product) | Parent product |
| `name` | CharField(100) | e.g. "Small", "Red", "XL" |
| `sku` | CharField(100, unique=True) | Stock-keeping unit — globally unique |
| `price` | DecimalField | Variant-specific price |
| `stock_quantity` | PositiveIntegerField(db_index=True) | Available stock |

### `ProductImage(BaseModel)`
Images attached to a product.

| Field | Type | Notes |
|-------|------|-------|
| `product` | ForeignKey(Product) | Parent product |
| `image_url` | URLField | CDN URL |
| `s3_key` | CharField(500) | S3 object key for deletion |
| `is_primary` | BooleanField | Primary image shown in list views |
| `order` | PositiveSmallIntegerField | Display order |

### `Wishlist(BaseModel)`
User's saved products.

| Field | Type | Notes |
|-------|------|-------|
| `user` | ForeignKey(User) | Wishlisting user |
| `product` | ForeignKey(Product) | Wishlisted product |

**Meta:** `unique_together = [('user', 'product')]`

---

## apps/products/serializers.py

### `ProductVariantSerializer`
Fields: `id`, `name`, `sku`, `price`, `stock_quantity`

### `ProductImageSerializer`
Fields: `id`, `image_url`, `is_primary`, `order`

### `ProductSerializer`
Full product serializer for create/update/detail.

**Computed fields:**
- `store_name`, `store_id` — read-only from FK
- `distance_km` — from ORM `distance` annotation (nearby queries only)
- `is_wishlisted` — checks `obj.wishlisted_by.filter(user=request.user)` using request context

**Nested write:** `variants` — accepted on create, creates `ProductVariant` objects. Variants are ignored on update (manage separately).

### `ProductListSerializer`
Compact version for list/nearby/search endpoints.

**Computed fields:**
- `primary_image` — first image with `is_primary=True`, falls back to first image
- `min_price` — cheapest variant price, falls back to `base_price`
- `distance_km` — from ORM annotation

---

## apps/products/services.py

### `ProductService`

**`create(store, validated_data) → Product`**
- Pops `variants` list from validated data
- Creates `Product`, then creates each `ProductVariant`

**`update(product, validated_data) → Product`**
- Sets attributes, saves product
- Invalidates nearby product cache for the store's location

**`get_nearby(lat, lng, radius_km, category) → QuerySet`**
- Delegates to `core.utils.geo.get_nearby_products()`

**`search(query, lat, lng, radius_km) → QuerySet`**
- Uses `TrigramSimilarity('name', query)` — requires `pg_trgm` extension
- Filters: `status=active`, `is_visible=True`, store active and verified
- Similarity threshold: `> 0.2` (20% match minimum)
- If lat/lng provided: additionally filters by store location within radius
- Returns top 30 results sorted by similarity

**`toggle_wishlist(user, product) → bool`**
- `get_or_create` on `Wishlist`
- Toggle: delete if exists (returns `False`), keep if new (returns `True`)

---

## apps/products/views.py

### `NearbyProductsView` — GET /products/nearby/
- `AllowAny`
- Same query param pattern as nearby stores

### `ProductSearchView` — GET /products/search/
- `AllowAny`
- Requires `q` param; `lat`/`lng`/`radius` optional
- Delegates to `ProductService.search()`

### `ProductDetailView` — GET /products/<product_id>/
- `AllowAny`
- Only returns products with `status=active` and `is_visible=True`
- Prefetches `variants` and `images`
- `is_wishlisted` reflects authenticated user's wishlist state

### `ProductCreateView` — POST /products/
- `IsAuthenticated + IsVendor`
- Guards: vendor must have a store first
- Delegates to `ProductService.create(request.user.store, ...)`

### `ProductUpdateView` — PUT/DELETE /products/<product_id>/update/
- `IsAuthenticated + IsStoreOwner`
- PUT: partial update via `ProductService.update()`
- DELETE: hard delete, returns `204 No Content`

### `ProductWishlistView` — POST /products/<product_id>/wishlist/
- `IsAuthenticated`
- Toggle via `ProductService.toggle_wishlist()`

---

## apps/products/admin.py

### `ProductAdmin`
- Inline: `ProductVariantInline`, `ProductImageInline` — manage from product page
- List display: name, store, category, status, visibility, price, created date
- Filters: status, is_visible, category
- Search: product name, store name

### `WishlistAdmin`
- List display: user, product, date
- Search: user phone, product name

---

## core/utils/geo.py (updated)

### `get_nearby_products(lat, lng, radius_km, category) → QuerySet`
Added alongside existing `get_nearby_stores`. Pattern:
```python
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D

user_point = Point(lng, lat, srid=4326)
qs = Product.objects.filter(
    status='active',
    is_visible=True,
    store__is_active=True,
    store__is_verified=True,
    store__location__dwithin=(user_point, D(km=radius_km)),
).annotate(distance=Distance('store__location', user_point)).order_by('distance')
```

---

## core/utils/cache.py (updated)

### `nearby_products_key(lat, lng, radius_km, category) → str`
Cache key generator for nearby products query results. Follows same pattern as `nearby_stores_key`.

---

## apps/stores/migrations/

### `0001_initial.py`
Creates tables: `stores`, `store_hours`, `store_follows`, `store_reviews`.
Adds indexes: `store_active_verified_idx`, `store_category_idx`, `store_name_gin_idx`.

### `0002_store_location_geography.py`
Alters `Store.location` to add `geography=True`.
Required because `D(km=...)` in `DWithin` queries needs geographic coordinates (not raw geometric).

---

## apps/products/migrations/

### `0001_initial.py`
Creates tables: `products`, `product_variants`, `product_images`, `wishlists`.
Adds indexes: `product_status_visible_idx`, `product_name_gin_idx`.

---

## Key Design Decisions

**`geography=True` on `Store.location`**
Django's `DWithin` filter with `D(km=...)` raises `ValueError` on plain geometry fields. The `geography=True` flag stores coordinates in a geographic reference system enabling meter/km distance calculations directly.

**`is_verified=False` default**
New stores are not visible in nearby queries until an admin marks them verified. This prevents unverified/fake stores from appearing in customer searches.

**Trigram similarity threshold 0.2**
A threshold of 0.2 (20%) catches partial matches like "kur" → "kurta" while filtering noise. Results are ordered by similarity score so the best matches appear first.

**OneToOneField for Store→User**
Enforces one store per vendor at the database level. Views also add a Python-level guard (`hasattr(user, 'store')`) for a clearer error message.

**`update_or_create` for reviews**
Users can update their review by re-posting. The unique constraint `(user, store)` combined with `update_or_create` implements this at the service layer without extra endpoints.

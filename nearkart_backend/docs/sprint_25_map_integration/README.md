# Sprint 25 — Store Offers in Nearby API · Sale Price PATCH · Broadcast Seed · Cache Invalidation

**Branch:** `MAP-Integration`
**Date:** June 2026
**Status:** Complete

---

## Overview

| # | Change | Area |
|---|--------|------|
| 1 | `active_offer_labels` in nearby stores response | stores serializer |
| 2 | Offer expiry filter in geo utils | geo utils |
| 3 | Nearby stores cache busted on offer create/delete | stores views |
| 4 | `sale_price` PATCH → updates first variant price | products views |
| 5 | `seed_city_offers` management command | management commands |
| 6 | `seed_city_broadcast_posts` management command | management commands |
| 7 | Extended `invalidate_store_caches()` coverage | cache utils |

---

## Change 1 — `active_offer_labels` in Nearby Stores Response

### Problem
Store cards on the mobile app had no way to show offer teasers — the `get_nearby_stores()` response didn't include any offer data.

### Solution
`StoreListSerializer` now computes `active_offer_labels` as a `SerializerMethodField`. It reads from the already-prefetched `StoreOffer` queryset (zero extra DB hits) and returns up to 5 active, non-expired offer labels.

### Files
**`apps/stores/serializers.py`**
```python
active_offer_labels = serializers.SerializerMethodField()

def get_active_offer_labels(self, obj) -> list[str]:
    offers = getattr(obj, 'active_offers', None)
    if not offers:
        return []
    return [o.label for o in offers[:5]]
```

**`core/utils/geo.py`** — prefetch queryset updated to filter expired offers:
```python
from datetime import date
from django.db.models import Q

Prefetch(
    'offers',
    queryset=StoreOffer.objects.filter(
        is_active=True
    ).filter(
        Q(valid_till__isnull=True) | Q(valid_till__gte=date.today())
    ).order_by('-created_at'),
    to_attr='active_offers',
)
```

### Response shape
```json
{
  "id": "...",
  "name": "Sneha's Fashion House",
  "active_offer_labels": ["Flat ₹200 off on orders above ₹1500", "Buy 2 Get 1 Free on kurtis"]
}
```

---

## Change 2 — Cache Invalidation on Offer Create/Delete

### Problem
When a vendor created or deleted an offer, the nearby stores cache (`nearby_stores:{h3_cell}:{radius}:{category}`) was not busted. Customers would see stale offer labels until TTL expired (5 minutes).

### Solution
`StoreOfferView.post()` and `StoreOfferDeleteView.delete()` both call `CacheService.invalidate_store_caches(lat, lng)` after writing to the DB.

**`apps/stores/views.py`**
```python
# After creating / deactivating an offer:
if store.location:
    CacheService.invalidate_store_caches(
        store.location.y,  # lat
        store.location.x,  # lng
    )
```

**`core/utils/cache.py`** — `invalidate_store_caches()` now covers all meaningful radii and categories:
```python
RADII = [1, 2, 3, 5, 10]
CATEGORIES = [
    None, "fashion", "jewellery", "footwear",
    "decor", "furniture", "gifts", "beauty",
    "food", "electronics",
]
```

---

## Change 3 — Sale Price PATCH on Product Update

### How `is_on_sale` works
There is no `sale_price` column. The mobile app shows a sale badge when `variant.price < product.base_price`. Setting a "sale price" means lowering the first variant's price.

### Endpoint
`PUT /api/v1/products/{id}/update/`

Now accepts an optional `sale_price` field:
- If `sale_price < base_price` → first variant's price is set to `sale_price`
- If `sale_price >= base_price` or invalid → ignored (no change to variant)
- If not provided → variant price unchanged

**`apps/products/views.py` — `ProductUpdateView.put()`**
```python
sale_price_raw = request.data.get('sale_price')
if sale_price_raw is not None:
    from decimal import Decimal, InvalidOperation
    try:
        sale_price = Decimal(str(sale_price_raw))
        variant = product.variants.order_by('created_at').first()
        if variant:
            variant.price = sale_price if sale_price < product.base_price else product.base_price
            variant.save(update_fields=['price'])
    except (InvalidOperation, ValueError):
        pass
```

---

## Change 4 — Seed Management Commands

### `seed_city_offers`

Seeds 1–5 category-appropriate offers per store (only for stores with Indian phone numbers starting `+917`, i.e. seeded stores). Safe to re-run — skips stores that already have offers.

```bash
docker compose exec django python manage.py seed_city_offers
# Result: ~197,297 offers created across 65,550 stores
```

**Offer templates** — keyed by category (fashion, jewellery, footwear, decor, furniture, gifts, beauty, food, electronics). `valid_till` is 60–180 days from today; 30% of offers have no expiry.

### `seed_city_broadcast_posts`

Seeds 1–3 posts per `BroadcastChannel` for seeded stores. Safe to re-run — skips channels that already have posts.

```bash
docker compose exec django python manage.py seed_city_broadcast_posts
# Result: ~131,267 posts created
```

---

## Docker Update Workflow

| Type of change | Command |
|---------------|---------|
| Python-only (views, serializers, utils) | `docker compose restart django` |
| New pip package | `docker compose build django && docker compose up -d` |
| New migration | `docker compose exec django python manage.py migrate` |
| Management command | `docker compose exec django python manage.py <command>` |

---

## Files Changed

| File | Change |
|------|--------|
| `apps/stores/serializers.py` | Added `active_offer_labels` SerializerMethodField |
| `core/utils/geo.py` | Offer prefetch now filters expired offers |
| `apps/stores/views.py` | Cache bust on offer create/delete |
| `apps/products/views.py` | `sale_price` PATCH → first variant price |
| `core/utils/cache.py` | Extended `invalidate_store_caches()` radii + categories |
| `apps/stores/management/commands/seed_city_offers.py` | **NEW** — category offers seed |
| `apps/stores/management/commands/seed_city_broadcast_posts.py` | **NEW** — broadcast posts seed |

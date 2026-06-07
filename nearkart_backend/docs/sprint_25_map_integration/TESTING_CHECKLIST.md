# Sprint 25 — Backend Testing Checklist

---

## Setup

- `docker compose up -d` — all services running
- Seeds run: `seed_city_offers` and `seed_city_broadcast_posts`
- Redis running (cache layer active)
- Vendor test account: Sneha Reddy (`+919000000004` / OTP `400004`)

---

## Part A — `active_offer_labels` in Nearby Stores

- [ ] `GET /stores/nearby/?lat=...&lng=...&radius=3` returns `active_offer_labels` field on every store object
- [ ] Stores with active offers → labels populated (non-empty list)
- [ ] Stores with no offers → `active_offer_labels: []` (empty list, not null)
- [ ] Maximum 5 labels returned per store (even if store has more)
- [ ] Expired offers (`valid_till` < today) are excluded from labels
- [ ] Offers with `valid_till: null` (no expiry) are included

---

## Part B — Cache Invalidation on Offer Changes

- [ ] Call `/stores/nearby/` → note current offer labels, confirm response is cached (same response on second call)
- [ ] Create a new offer via `POST /stores/mine/offers/` (vendor auth)
- [ ] Call `/stores/nearby/` again immediately → new offer label appears (cache was busted)
- [ ] Delete the offer via `DELETE /stores/mine/offers/{id}/`
- [ ] Call `/stores/nearby/` again immediately → deleted offer label is gone

---

## Part C — Sale Price on Product Update

- [ ] `PUT /products/{id}/update/` with `sale_price < base_price` → first variant's price updated to sale price
- [ ] `GET /products/{id}/` after update → `is_on_sale: true`, variant shows sale price
- [ ] `PUT` with `sale_price >= base_price` → variant price unchanged (ignored)
- [ ] `PUT` with `sale_price: "abc"` (invalid) → no 500 error, variant unchanged
- [ ] `PUT` without `sale_price` key → variant price unchanged
- [ ] `PUT` with `sale_price` equal to base_price → treated as no sale, variant = base_price

---

## Part D — Seed Commands

- [ ] `python manage.py seed_city_offers` runs without errors
- [ ] Offer count in DB increases (check `StoreOffer.objects.count()`)
- [ ] Re-running command → no duplicate offers created (idempotent for stores that already have offers)
- [ ] `python manage.py seed_city_broadcast_posts` runs without errors
- [ ] Post count in DB increases
- [ ] Re-running → no duplicate posts (idempotent)

---

## Part E — Broadcast Channel Endpoints

- [ ] `GET /stores/{id}/channels/` returns list of channels with `subscriber_count` and `post_count`
- [ ] `GET /stores/{id}/channels/{channel_id}/posts/` returns posts with `title`, `body`, `created_at`
- [ ] Empty channel → posts endpoint returns `[]`
- [ ] Store with no channels → channels endpoint returns `[]`

---

## Part F — Regression

- [ ] `GET /stores/nearby/` — all existing fields still present (name, category, distance, is_open, etc.)
- [ ] `POST /stores/mine/offers/` — offer creation still works (201 response)
- [ ] `GET /products/vendor/` — product list unaffected
- [ ] `PUT /products/{id}/update/` without `sale_price` — other fields update normally
- [ ] Cache TTL still working: second identical nearby call within 5 minutes hits cache (fast response)
- [ ] Django admin → StoreOffer entries visible and editable

---

## Django Shell Verification

```python
# docker compose exec django python manage.py shell

from apps.stores.models import StoreOffer, Store
from datetime import date

# Count offers
print(StoreOffer.objects.count())

# Count non-expired active offers
from django.db.models import Q
print(StoreOffer.objects.filter(
    is_active=True
).filter(
    Q(valid_till__isnull=True) | Q(valid_till__gte=date.today())
).count())

# Check a store's offers
store = Store.objects.filter(phone__startswith='+917').first()
print(list(store.offers.values_list('label', flat=True)))

# Check broadcast posts
from apps.broadcast.models import BroadcastPost
print(BroadcastPost.objects.count())
```

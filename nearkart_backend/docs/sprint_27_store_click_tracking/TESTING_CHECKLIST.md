# Sprint 27 — Backend Testing Checklist: Store Click Tracking

---

## Setup

- `docker compose up -d` — all services running including Redis
- Vendor test account: **Sneha Reddy** (`+919000000004` / OTP `400004`)
- Customer test account: **Arjun Kumar** (`+919000000001` / OTP `100001`)
- Note the vendor's store ID from `GET /stores/mine/`

---

## Part A — Stats Endpoint Returns Real Data

- [ ] `GET /stores/mine/stats/` returns all three new fields: `store_views`, `inquiries_pending`, `products_need_action`
- [ ] None of the three fields are missing from the response
- [ ] Response still includes all existing fields: `store_name`, `store_address`, `active_reservations`, `total_products`, `follower_count`
- [ ] No 500 error on the stats endpoint

---

## Part B — Store Views (HyperLogLog)

- [ ] Customer (`Arjun Kumar`) calls `GET /stores/{vendor_store_id}/` — returns 200
- [ ] `GET /stores/mine/stats/` as vendor — `store_views` is ≥ 1
- [ ] Same customer calls store detail 3 more times — `store_views` count stays the same (unique per day, not raw hits)
- [ ] Different customer (`Priya Sharma`) calls store detail — `store_views` increases by 1
- [ ] Unauthenticated `GET /stores/{id}/` (no token) — `store_views` does NOT increase
- [ ] Vendor calling their own store detail — counted (vendor is authenticated; optional to filter but acceptable)

---

## Part C — Inquiries Pending

- [ ] Customer sends a chat message to vendor's store
- [ ] `GET /stores/mine/stats/` → `inquiries_pending` ≥ 1
- [ ] Vendor reads/marks the conversation as read
- [ ] `GET /stores/mine/stats/` → `inquiries_pending` decreases accordingly
- [ ] No unread conversations → `inquiries_pending` = 0

---

## Part D — Products Need Action

- [ ] Set all variants of an active product to `stock_quantity = 0`
- [ ] `GET /stores/mine/stats/` → `products_need_action` ≥ 1
- [ ] Restock one variant (set `stock_quantity` > 0)
- [ ] `GET /stores/mine/stats/` → `products_need_action` decreases
- [ ] Inactive/deactivated products do NOT count in `products_need_action`
- [ ] Product with at least one variant in stock does NOT appear in count

---

## Part E — Regression

- [ ] `GET /stores/mine/stats/` for a vendor with no store → returns empty/zero response (no 500)
- [ ] `GET /stores/{id}/` still works and returns store detail normally
- [ ] Cache still works on store detail (second call within TTL returns cached response)
- [ ] HyperLogLog tracking still fires on cache-hit path (visit counted even when response is cached)
- [ ] No mobile changes required — vendor dashboard tiles update automatically

---

## Django Shell Verification

```python
# docker compose exec django python manage.py shell

from core.utils.cache import CacheService
from apps.stores.models import Store

store = Store.objects.filter(phone__startswith='+919000000004').first()

# Check today's unique visitors
print('Today views:', CacheService.get_unique_visitors(str(store.id)))

# Check last 7 days
visitors_7d = CacheService.get_unique_visitors_range(str(store.id), days=7)
print('Last 7 days:', visitors_7d)
print('Total 7-day views:', sum(visitors_7d.values()))

# Check inquiries
from apps.chat.models import Conversation
print('Inquiries pending:', Conversation.objects.filter(store=store, unread_count_vendor__gt=0).count())

# Check products need action
from django.db.models import Sum
print('Products need action:', store.products.filter(status='active').annotate(
    total_stock=Sum('variants__stock_quantity')
).filter(total_stock=0).count())
```

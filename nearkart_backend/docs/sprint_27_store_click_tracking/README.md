# Sprint 27 — Store Click Tracking: Vendor Dashboard Live Stats

**Branch:** `MAP-Integration`
**Date:** June 2026
**Status:** Complete

---

## Overview

The vendor dashboard KPI tiles for **Store Views**, **Inquiries**, and **Products Need Action** previously always showed `0`. This sprint wires all three to real data — no model changes, no migration, no mobile changes.

| Tile | Source |
|------|--------|
| Store Views | HyperLogLog unique visitor count (Redis) — 30-day rolling sum |
| Inquiries | Conversations with unread vendor messages (`unread_count_vendor > 0`) |
| Products Need Action | Active products where all variants have `stock_quantity = 0` |

---

## How Store Views Work (Algorithm 5 — HyperLogLog)

The tracking pipeline was already fully built in a prior sprint. Every `GET /stores/{id}/` call by an authenticated user fires:

```python
CacheService.record_store_visit(str(store_id), str(request.user.id))
```

This calls `PFADD nearkart:hll:store:{store_id}:{YYYY-MM-DD} {user_id}` in Redis — a HyperLogLog operation that counts unique visitors with ~1% error in O(1) time using only 12 KB per key. Keys are retained for 30 days.

The stats endpoint now sums these daily counts over the last 30 days:

```python
store_views = sum(CacheService.get_unique_visitors_range(str(store.id), days=30).values())
```

**Properties:**
- Same user viewing the store multiple times in a day counts as **1** (unique visits, not raw hits)
- Cache hits also count — `record_store_visit` is called on both cache-hit and cache-miss paths
- Unauthenticated requests are not counted (no user ID to track)
- Privacy-safe — user IDs are hashed into the HyperLogLog, never stored individually

---

## How Inquiries Work

`Conversation.unread_count_vendor` is incremented each time a customer sends a message and decremented when the vendor reads it. The stat is:

```python
inquiries_pending = Conversation.objects.filter(
    store=store, unread_count_vendor__gt=0
).count()
```

This is the number of customer chat threads the vendor hasn't responded to yet — a direct proxy for pending inquiries.

---

## How Products Need Action Works

```python
from django.db.models import Sum

products_need_action = store.products.filter(status='active').annotate(
    total_stock=Sum('variants__stock_quantity')
).filter(total_stock=0).count()
```

An active product "needs action" when every variant is sold out. This prompts the vendor to restock or deactivate the listing.

---

## File Changed

| File | Change |
|------|--------|
| `apps/stores/views.py` — `VendorStatsView.get()` | Added `store_views`, `inquiries_pending`, `products_need_action` to response |

---

## No Mobile Changes

The `VendorStatsResponse` data class and `VendorDashboardScreen` KPI tiles were already wired up — they just received `0` from the API. Now they receive real values with no mobile code changes.

---

## Why No Model Changes

`store_views` is derived from Redis (HyperLogLog) — no DB column needed.
`inquiries_pending` uses the existing `unread_count_vendor` field on `Conversation`.
`products_need_action` is a live DB aggregation — no stored field needed.

# Sprint 17 — Postman Guide

> No new endpoints in Sprint 17. All API calls use endpoints from Sprint 16.
> Use the Sprint 16 Postman Guide for review-related endpoints.

Base URL: `http://localhost:8000/api/v1/`

---

## Endpoints used by StoreDetailScreen (all pre-existing)

### Store detail with live rating

```
GET /stores/{store_id}/
```

Returns `rating` (avg, computed from reviews) and `review_count`. These update automatically after new reviews are submitted.

### Preview reviews (first 3 shown in StoreDetailScreen)

```
GET /stores/{store_id}/reviews/
```

Returns `results` array ordered by most recent. Each review includes `vendor_reply` if the vendor has replied.

---

## Verification flow

1. POST a review for store X (see Sprint 16 POSTMAN_GUIDE.md, Step 1)
2. GET `/stores/{store_id}/` → confirm `rating` and `review_count` reflect the new review
3. POST vendor reply to that review (see Sprint 16 Step 3)
4. GET `/stores/{store_id}/reviews/` → confirm `vendor_reply` is populated on the review
5. On mobile: open StoreDetailScreen → review preview shows vendor reply in green block

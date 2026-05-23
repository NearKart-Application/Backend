# Sprint 18 — Postman Guide

## No New Endpoints

Sprint 18 adds no new API endpoints. The only backend change is an enhancement to the existing Product Detail endpoint — the `store` object in the response now includes `rating` and `review_count`.

---

## Updated Response: Product Detail

### `GET /api/products/{id}/`

**Auth:** Bearer token (customer)

**Sample response (store section):**
```json
{
  "id": "prod-uuid",
  "name": "Basmati Rice 5kg",
  "price": "299.00",
  "store": {
    "id": "store-uuid",
    "name": "Fresh Grains Market",
    "avatar": "https://...",
    "rating": 4.3,
    "review_count": 17
  },
  ...
}
```

**Store with no reviews:**
```json
{
  "store": {
    "id": "store-uuid",
    "name": "New Corner Shop",
    "avatar": null,
    "rating": 0.0,
    "review_count": 0
  }
}
```

---

## Existing Endpoints Used by Sprint 18 Features

These endpoints were built in earlier sprints and are unchanged:

| Feature | Endpoint | Sprint |
|---------|----------|--------|
| Store Detail navigation | `GET /api/stores/{id}/` | S14 |
| Store Reviews navigation | `GET /api/stores/{id}/reviews/` | S16 |
| Vendor notifications | `GET /api/notifications/` | S13 |

---

## How to Verify the Backend Change

1. Ensure a store has at least one review (use S16 submit review endpoint if needed)
2. `GET /api/products/{id}/` for a product belonging to that store
3. Check `store.rating` is a rounded float (e.g., `4.3`) and `store.review_count` is the total count
4. Repeat for a product whose store has zero reviews — confirm `rating: 0.0`, `review_count: 0`

---

## Environment Variables

| Variable | Value |
|----------|-------|
| `{{base_url}}` | `http://127.0.0.1:8000` (local) |
| `{{token}}` | Bearer token from login response |
| `{{product_id}}` | UUID of a product to test |
| `{{store_id}}` | UUID of the product's store |

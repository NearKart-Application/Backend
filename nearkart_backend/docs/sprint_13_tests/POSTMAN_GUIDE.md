# Sprint 13 — Algorithms Postman Guide

## Collection Setup

Add a new folder inside your existing Postman collection: **"13 — Performance Algorithms"**

Variables needed (should already be set from earlier sprints):

| Variable | Value | Set by |
|----------|-------|--------|
| `base_url` | `http://localhost:8000/api/v1` | Manual |
| `customer_token` | (JWT) | OTP verify script |
| `vendor_token` | (JWT) | OTP verify script |
| `store_id` | (int) | From nearby stores response |

---

## 1 — Weighted Nearby Stores (Algorithm 2)

### Get Nearby Stores

```
GET {{base_url}}/stores/nearby/?lat=17.4948&lng=78.3996
Authorization: Bearer {{customer_token}}
```

Expected response:
```json
[
  {
    "id": 1,
    "name": "Sneha's Fashion House",
    "distance": "0.45 km",
    "is_open": true,
    "avg_rating": 4.2,
    "has_active_offer": true,
    "lat": 17.4951,
    "lng": 78.4001
  },
  ...
]
```

**What to check:** Open stores should appear before closed ones at similar distance. Stores with active offers rank higher than stores without.

### Get Nearby Stores — Filtered by Category

```
GET {{base_url}}/stores/nearby/?lat=17.4948&lng=78.3996&category=electronics
Authorization: Bearer {{customer_token}}
```

Expected: only stores in the `electronics` category.

---

## 2 — BM25 Hybrid Product Search (Algorithm 7)

### Exact match

```
GET {{base_url}}/products/search/?q=shirt&lat=17.4948&lng=78.3996
Authorization: Bearer {{customer_token}}
```

Expected response:
```json
[
  {
    "id": 5,
    "name": "Cotton Shirt",
    "price": "599.00",
    "store_name": "Sneha's Fashion House",
    "distance": "0.45 km"
  },
  ...
]
```

### Typo tolerance (trigram)

```
GET {{base_url}}/products/search/?q=shrt&lat=17.4948&lng=78.3996
Authorization: Bearer {{customer_token}}
```

Expected: "Cotton Shirt" still appears (trigram similarity catches the typo).

### Partial match

```
GET {{base_url}}/products/search/?q=elec&lat=17.4948&lng=78.3996
Authorization: Bearer {{customer_token}}
```

Expected: "Electronics", "Electric Kettle" etc. returned.

### No results

```
GET {{base_url}}/products/search/?q=zznonexistent&lat=17.4948&lng=78.3996
Authorization: Bearer {{customer_token}}
```

Expected: `200` with `[]`

### With category filter

```
GET {{base_url}}/products/search/?q=phone&lat=17.4948&lng=78.3996&category=electronics
Authorization: Bearer {{customer_token}}
```

---

## 3 — Sliding Window Rate Limiter (Algorithm 6)

### Send OTP — normal

```
POST {{base_url}}/auth/send-otp/
Content-Type: application/json

{
  "phone_number": "+919000000099"
}
```

Expected: `200 {"message": "OTP sent"}`

Repeat this request 5 times with the **same phone number**.

### Trigger rate limit (6th request)

Same request again:

```
POST {{base_url}}/auth/send-otp/
Content-Type: application/json

{
  "phone_number": "+919000000099"
}
```

Expected response `429`:
```json
{
  "error": "rate_limited",
  "message": "Too many OTP requests. Try again in 1 hour."
}
```

**To reset (for re-testing):**
```bash
docker compose exec redis redis-cli DEL "rl:otp:+919000000099"
```

---

## 4 — Store Detail: HyperLogLog Visitors (Algorithm 5)

### View store detail

```
GET {{base_url}}/stores/{{store_id}}/
Authorization: Bearer {{customer_token}}
```

Expected: full store detail including products, videos, reviews.

**After calling this**, check the Redis visitor counter:
```bash
docker compose exec redis redis-cli PFCOUNT "visitors:store:{{store_id}}:$(date +%Y-%m-%d)"
```

Should be ≥ 1. Calling with the same token again should NOT increase the count (HyperLogLog deduplicates by user_id).

### Verify caching

Call the same endpoint twice in quick succession. The second call should return from cache (check Django logs — no DB query on the second call).

```
GET {{base_url}}/stores/{{store_id}}/
Authorization: Bearer {{customer_token}}
```

---

## 5 — Cache Inspection (optional, via Redis CLI)

Run these from your terminal to inspect algorithm state:

```bash
# All nearby-store cache keys (H3 geohash-based)
docker compose exec redis redis-cli KEYS "nearby:stores:*"

# All store detail cache keys
docker compose exec redis redis-cli KEYS "store:detail:*"

# OTP rate limiter keys
docker compose exec redis redis-cli KEYS "rl:otp:*"

# HyperLogLog visitor keys
docker compose exec redis redis-cli KEYS "visitors:store:*"

# Check TTL on a specific key
docker compose exec redis redis-cli TTL "store:detail:1"

# Flush all caches (for testing cold-start behaviour)
docker compose exec redis redis-cli FLUSHDB
```

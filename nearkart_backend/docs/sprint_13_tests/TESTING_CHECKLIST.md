# Sprint 13 — Testing Checklist

**Branch:** `sprint-13-tests`

---

## Pre-requisites

- [ ] Stack running: `docker compose up -d`
- [ ] All containers healthy (especially celery + celery-beat — they crashed before the requirements fix)
- [ ] Customer token in Postman variable `{{customer_token}}`
- [ ] Vendor token in Postman variable `{{vendor_token}}`
- [ ] Location lat/lng set: Kukatpally area (17.4948, 78.3996) or nearby

---

## A — Nearby Stores: Weighted Ranking

- [ ] `GET /api/v1/stores/nearby/?lat=17.4948&lng=78.3996`
  - Expected: stores ordered by relevance score, not pure distance
  - Open stores should appear above closed stores of similar distance
  - Stores with higher ratings should rank above lower-rated stores at similar distance
- [ ] `GET /api/v1/stores/nearby/?lat=17.4948&lng=78.3996` (same call, within 30 s)
  - Expected: identical response in < 5 ms (L1 in-process cache hit — check Django logs)
- [ ] `GET /api/v1/stores/nearby/?lat=17.4948&lng=78.3996` (after 30 s)
  - Expected: Redis cache hit (L2), still fast but slightly slower than L1
- [ ] Add `?category=electronics` — only electronics stores returned
- [ ] Location well outside Hyderabad → empty list (no stores in range)

---

## B — Product Search: BM25 Hybrid

- [ ] `GET /api/v1/products/search/?q=shirt&lat=17.4948&lng=78.3996`
  - Expected: products with "shirt" in name ranked highest
- [ ] `GET /api/v1/products/search/?q=shrt` (typo)
  - Expected: results still returned via trigram similarity (not empty)
- [ ] `GET /api/v1/products/search/?q=elec` (partial match)
  - Expected: "electronics", "electric" etc. returned via trigram
- [ ] `GET /api/v1/products/search/?q=` (blank query)
  - Expected: `400` or empty list — no server error
- [ ] `GET /api/v1/products/search/?q=zzzznonexistent`
  - Expected: empty list `[]`

---

## C — OTP Rate Limiter (Sliding Window)

- [ ] `POST /api/v1/auth/send-otp/` with `{"phone_number": "+919000000099"}` × 5 times
  - Expected: first 5 → `200` (OTP sent)
- [ ] 6th call to same number within the hour
  - Expected: `429` with `{"error": "rate_limited", ...}`
- [ ] Different phone number → still works (rate limiter is per-number)
- [ ] Wait for the window to reset (1 hour) or flush Redis key manually:
  ```bash
  docker compose exec redis redis-cli DEL "rl:otp:+919000000099"
  ```
  Then: next call → `200` again

---

## D — Store Detail: HyperLogLog Unique Visitors

- [ ] `GET /api/v1/stores/{store_id}/` with `{{customer_token}}`
  - Expected: `200` with store detail
  - Check Redis: `PFCOUNT visitors:store:{store_id}:{today}` should increment
    ```bash
    docker compose exec redis redis-cli PFCOUNT "visitors:store:1:$(date +%Y-%m-%d)"
    ```
- [ ] Same request with same token → PFCOUNT unchanged (same user not counted twice per day)
- [ ] Same request with a different customer token → PFCOUNT increments
- [ ] Unauthenticated request (`GET` without token) → PFCOUNT unchanged (anonymous visits not tracked)

---

## E — Store Detail: Caching Bug Fixed

- [ ] `GET /api/v1/stores/{store_id}/` (first time — cold cache)
  - Expected: `200`, response time < 300 ms
  - Check Django logs: "cache miss" then DB query
- [ ] Same call immediately after
  - Expected: `200`, response from cache (faster), no DB query in logs
- [ ] Check Redis for the cache key:
  ```bash
  docker compose exec redis redis-cli KEYS "store:detail:*"
  ```
  Should show a key for the store. If empty → caching not working.

---

## F — Circuit Breaker (Mobile only — verify via logs)

The circuit breaker is a mobile-side OkHttp interceptor. To verify:
- [ ] Kill the backend: `docker compose stop django`
- [ ] Make 5 API calls from the mobile app
- [ ] On the 6th call → app should show "Service temporarily unavailable" immediately (no network timeout wait)
- [ ] Restart backend: `docker compose start django`
- [ ] After 30 s the circuit goes to HALF_OPEN — next call goes through and resets

---

## G — pytest Test Suite

- [ ] Activate venv: `source nearkart_venv/bin/activate`
- [ ] `cd nearkart_backend`
- [ ] `pytest --cov=apps --cov-report=term-missing -x`
  - Expected: all tests pass, coverage report printed
- [ ] `pytest apps/auth_app/tests/ -v` — auth tests only
- [ ] `pytest -k "search"` — search tests only
- [ ] `pytest --co -q` — list all collected tests without running

---

## H — Docker Stability Check (requirements fix)

- [ ] `docker compose ps` — all 7 containers show `Up` (not `Restarting`)
  - `nearkart_backend-celery-1`: Up
  - `nearkart_backend-celery-beat-1`: Up
  - Previously both crash-looped due to missing h3/cachetools
- [ ] `docker compose logs celery --tail=20` — no ImportError for h3 or cachetools
- [ ] `docker compose exec celery python -c "import h3; import cachetools; print('OK')"` → `OK`

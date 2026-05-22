# Sprint 13 — Performance Algorithms + Test Infrastructure

**Status:** Done ✅
**Verified on:** 2026-05-21

---

## What This Sprint Does

Adds 10 modern performance and resilience algorithms across the backend and mobile app, plus a full pytest test infrastructure that runs without Docker.

---

## Backend Algorithms (7)

### Algorithm 1 — H3 Hexagonal Geohash Cache Keys
**File:** `core/utils/cache.py`

Replaces lat/lng rounding with Uber's H3 hexagonal grid (resolution 9 ≈ 170 m cells) for cache keys.

- `h3_key(lat, lng, prefix)` — builds a stable cache key from an H3 cell
- Identical location queries within the same cell always hit the same cache entry
- Version-agnostic: uses `latlng_to_cell` (h3 v4) or `geo_to_h3` (h3 v3) automatically

### Algorithm 2 — Weighted Relevance Ranking
**File:** `core/utils/geo.py`

Replaces pure distance sorting with a multi-factor score computed in the DB:

```
score = 400 / (distance + 10)          # 40% — distance  (closer = higher)
      + 0.25 × avg_rating              # 25% — rating
      + open_bonus (2.0 if open now)   # 20% — open status
      + offer_bonus (1.5 if active)    # 10% — has offer
      + popular_bonus (0.5 if >100 f)  # 5%  — follower count
```

Open stores with good ratings rank above slightly closer closed/low-rated stores.

### Algorithm 3 — Two-Level Cache (L1 in-process + L2 Redis)
**File:** `core/utils/cache.py`

- **L1:** `cachetools.TTLCache(maxsize=500, ttl=30)` — 0 ms, thread-safe with `threading.Lock()`
- **L2:** Redis — shared across all workers, configurable TTL
- Read path: L1 hit → return immediately; L1 miss → Redis; Redis miss → compute
- Write path: sets both L1 and Redis simultaneously

### Algorithm 4 — XFetch Probabilistic Cache Refresh
**File:** `core/utils/cache.py` → `get_or_compute()`

Prevents cache stampedes on popular keys. The formula:

```python
-beta * log(random()) < remaining_ttl / original_ttl
```

As TTL approaches zero, the probability of early refresh increases. The first request to "win" refreshes; all others return the cached value while the refresh runs. `beta=1.0` is the default; higher values = more aggressive early refresh.

### Algorithm 5 — HyperLogLog Unique Visitors
**File:** `core/utils/cache.py`

Uses Redis `PFADD` / `PFCOUNT` to count unique store visitors per day — 12 KB of memory regardless of visitor count (vs. storing every user ID).

- `record_store_visit(store_id, user_id)` — called in `StoreDetailView.get()` for authenticated requests
- `get_unique_visitors(store_id, date)` — count for a single day
- `get_unique_visitors_range(store_id, days)` — union of multiple HLL registers for a date range

### Algorithm 6 — Sliding Window Rate Limiter
**File:** `core/utils/cache.py` → `is_rate_limited()`

Redis ZSET-based rate limiter; eliminates the burst vulnerability of fixed-window counters.

```
pipeline:
  ZREMRANGEBYSCORE key 0 (now - window_ms)   # evict old entries
  ZADD key now now                            # record this request
  ZCARD key                                   # count in window
  EXPIRE key window_secs
```

Applied to OTP send: 5 requests per phone number per hour. Fails open (allows request) if Redis is unavailable.

### Algorithm 7 — BM25 + Trigram Hybrid Search
**File:** `apps/products/services.py`

Combines PostgreSQL full-text search (BM25 approximation) with trigram similarity:

```
hybrid_score = 0.6 × bm25_rank + 0.4 × trigram_score
```

- `SearchVector` on `name` (weight A) + `description` (weight B) with `config='simple'` for multi-language support
- `cover_density=True` gives higher rank when search terms appear close together
- Trigram handles typos and partial matches that BM25 misses
- Pre-filter: `bm25_rank > 0.01 OR trigram_score > 0.2` before scoring

---

## Other Backend Fixes

### StoreDetailView caching bug fixed
The store detail view was reading from cache but never writing on a miss. First fetch always hit the DB. Fixed: sets `CacheService` entry after DB fetch.

### requirements/base.txt — h3 and cachetools added
`cache.py` imports `h3` and `cachetools` at module load. They were present in the root `requirements.txt` but missing from `requirements/base.txt` (the file used by Docker). This caused celery and celery-beat to crash-loop on container startup.

---

## Mobile Algorithms (3)

### Algorithm 8 — Circuit Breaker (OkHttp interceptor)
**File:** `ApiCircuitBreaker.kt`, `di/AppModule.kt`

Three states: CLOSED → OPEN (after 5 failures) → HALF_OPEN (after 30 s timeout). Wired as an OkHttp interceptor so every API call in every repository is covered automatically. `CircuitOpenException extends IOException` keeps Retrofit error handling unchanged.

### Algorithm 9 — Exponential Backoff + Jitter (WebSocket reconnect)
**File:** `ui/screens/chat/ChatViewModel.kt`

```
delay = min(1s × 2^attempt, 30s) + random(0..1s)
```

Jitter prevents thundering herd when a server restart triggers simultaneous reconnects from all connected clients. `retryJob` is cancelled before each new attempt so only one reconnect timer runs at a time.

### Algorithm 10 — Flow Debounce Auto-Search
**File:** `ui/screens/search/SearchViewModel.kt`

```kotlin
_query.debounce(300).combine(_selectedCategory).collectLatest { ... }
```

300 ms pause required before a search fires. `collectLatest` cancels the in-flight coroutine the moment a new character arrives — only the final query hits the network.

---

## Test Infrastructure

**File:** `docs/sprint_13_tests/TEST_RUNNER_GUIDE.md`

- Full pytest suite using SpatiaLite in-memory DB — no Docker required
- `pytest-django`, `pytest-cov`, `factory-boy`, `pytest-asyncio`
- Run: `pytest --cov=apps --cov-report=term-missing -x`
- Coverage report printed inline; CI-ready

---

## Files Changed

| File | Change |
|------|--------|
| `core/utils/cache.py` | Full rewrite — L1/L2 cache, XFetch, HyperLogLog, sliding window rate limiter |
| `core/utils/geo.py` | Full rewrite — H3 keys, weighted ranking, Exists() fix, XFetch integration |
| `apps/products/services.py` | BM25 + trigram hybrid search |
| `apps/auth_app/views.py` | Replaced non-functional throttle_scope with sliding window rate limiter |
| `apps/stores/views.py` | HyperLogLog visit tracking + store detail caching bug fixed |
| `requirements/base.txt` | Added `h3>=3.7` and `cachetools>=5.3` |

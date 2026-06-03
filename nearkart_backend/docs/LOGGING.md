# NearKart — Logging Reference

Complete guide to every log channel: where the files live, what events go in them,
how to query them, and how to add new events.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Backend Log Files](#2-backend-log-files)
3. [Mobile Logs — Logcat Tags](#3-mobile-logs--logcat-tags)
4. [Mobile Logs — Crashlytics Custom Keys](#4-mobile-logs--crashlytics-custom-keys)
5. [Event Shipping — Mobile → Backend](#5-event-shipping--mobile--backend)
6. [Log Rotation Settings](#6-log-rotation-settings)
7. [Investigation Playbooks](#7-investigation-playbooks)
8. [How to Add a New Log Event](#8-how-to-add-a-new-log-event)

---

## 1. Architecture Overview

```
MOBILE APP                          BACKEND SERVER
──────────────────────────          ─────────────────────────────────────────
NkLog (Logcat tags)                 logs/
  NK_AUTH  → auth events              ├── app.log           ← all events (JSON)
  NK_SECURITY → security events       ├── auth.log          ← login / logout
  NK_API  → every HTTP call           ├── stores.log        ← store events
  NK_PERF → slow calls (>2s)          ├── products.log      ← product events
  NK_NAV  → screen views              ├── customers.log     ← customer events
  NK_USER → wishlist/search/reserve   ├── reservations.log  ← reservation events
  NK_PREFETCH → background worker     ├── videos.log        ← video events
                                      ├── billing.log       ← wallet / payments
NkEventShipper                        ├── requests.log      ← every HTTP request
  login_failed ──POST──────────────→  ├── security.log      ← threats + anomalies
  login_blocked                       ├── performance.log   ← slow requests (>2s)
  otp_rate_limited                    ├── client_events.log ← mobile-shipped events
                                      └── error.log         ← ERROR+ all sources
Firebase Crashlytics
  crash reports + custom keys
  (device_model, os_version,
   app_version, install_id,
   network_type)
```

---

## 2. Backend Log Files

### File Location

```
Production:  /home/ubuntu/nearkart/logs/
Development: <project_root>/../logs/   (one level above nearkart_backend/)
```

All files use **RotatingFileHandler**: rotates at 10 MB, keeps 7 backups (~70 MB max per channel).

---

### 2.1 `app.log` — Global JSON stream

**What:** Every event from every channel in a single file. JSON format, one event per line.
**Level:** DEBUG and above.
**Use for:** Searching across multiple domains at once with `jq`.

**Format:**
```json
{"ts":"2026-06-03T10:22:01Z","level":"INFO","logger":"nearkart.auth","entity":"auth","action":"login_success","user_id":"u123","role":"customer","duration_ms":341}
```

**Useful jq queries:**
```bash
# All events for a specific user
cat app.log | jq 'select(.user_id=="abc123")'

# All errors in the last hour
cat app.log | jq 'select(.level=="ERROR")'

# All login failures
cat app.log | jq 'select(.action=="login_failed")'

# Slow requests only
cat app.log | jq 'select(.action=="slow_request")'

# All events for a specific store
cat app.log | jq 'select(.store_id=="s456")'
```

---

### 2.2 `auth.log` — Authentication events

**What:** Login, logout, OTP, token refresh.
**Level:** DEBUG and above.
**Format:** Human-readable key=value.

**Events logged:**

| action | When | Fields |
|---|---|---|
| `login_success` | OTP verified, tokens issued | `user_id`, `role`, `duration_ms` |
| `login_failed` | OTP wrong or expired | `user_id` (if known), `reason` |
| `login_blocked` | Account suspended or locked | `user_id`, `reason` |
| `otp_sent` | OTP requested | `user_id` (if exists) |
| `logout` | User logs out | `user_id`, `role` |
| `token_refresh` | Silent JWT refresh | `user_id` |

**Sample line:**
```
[2026-06-03 10:22:01] INFO     entity=auth  action=login_success  user_id=abc123  role=customer  duration_ms=341
```

**Code reference:** `apps/auth_app/views.py` → `OTPVerifyView`, `LogoutView`

---

### 2.3 `stores.log` — Store events

**What:** Store views, follows, product interactions within stores.
**Level:** DEBUG and above.

**Events logged:**

| action | When | Fields |
|---|---|---|
| `store_viewed` | Customer opens store detail | `store_id`, `user_id` |
| `store_followed` | Customer follows a store | `store_id`, `user_id` |
| `store_created` | Vendor creates store | `store_id`, `user_id` |
| `store_updated` | Vendor edits store info | `store_id`, `user_id` |

**Code reference:** `apps/stores/views.py`

---

### 2.4 `products.log` — Product events

**What:** Product creation, wishlist, views.
**Level:** DEBUG and above.

**Events logged:**

| action | When | Fields |
|---|---|---|
| `product_created` | Vendor adds a product | `product_id`, `store_id`, `user_id` |
| `product_updated` | Vendor edits a product | `product_id`, `store_id`, `user_id` |
| `product_wishlisted` | Customer adds to wishlist | `product_id`, `user_id` |
| `product_unwishlisted` | Customer removes from wishlist | `product_id`, `user_id` |

**Code reference:** `apps/products/views.py`

---

### 2.5 `customers.log` — Customer events

**What:** Profile updates, location changes, search.
**Level:** DEBUG and above.

**Events logged:**

| action | When | Fields |
|---|---|---|
| `profile_updated` | Customer edits profile | `user_id`, `fields_changed` |
| `location_updated` | Customer sets location | `user_id`, `lat`, `lng`, `location_name` |
| `search` | Customer searches products | `user_id`, `query`, `result_count` |

---

### 2.6 `reservations.log` — Reservation events

**What:** Every reservation lifecycle event.
**Level:** DEBUG and above.

**Events logged:**

| action | When | Fields |
|---|---|---|
| `reservation_created` | Customer reserves a product | `reservation_id`, `product_id`, `store_id`, `customer_id`, `quantity`, `hours` |
| `reservation_cancelled` | Customer or vendor cancels | `reservation_id`, `cancelled_by` |
| `reservation_expired` | Timer runs out | `reservation_id`, `product_id` |
| `reservation_fulfilled` | Vendor marks as picked up | `reservation_id`, `store_id` |

**Code reference:** `apps/reservations/views.py`

---

### 2.7 `videos.log` — Video events

**What:** Video uploads, plays, likes, saves.
**Level:** DEBUG and above.

**Events logged:**

| action | When | Fields |
|---|---|---|
| `video_uploaded` | Vendor uploads video | `video_id`, `store_id`, `user_id` |
| `video_played` | Customer plays video | `video_id`, `user_id` |
| `video_liked` | Customer likes video | `video_id`, `user_id` |
| `video_saved` | Customer saves video | `video_id`, `user_id` |

---

### 2.8 `billing.log` — Wallet and payment events

**What:** All money movements — top-ups, deductions, subscription payments.
**Level:** DEBUG and above.

**Events logged:**

| action | When | Fields |
|---|---|---|
| `wallet_topup` | Vendor adds funds | `store_id`, `user_id`, `amount`, `payment_method` |
| `wallet_deduction` | Monthly subscription charge | `store_id`, `amount`, `plan`, `balance_after` |
| `subscription_activated` | Store goes live | `store_id`, `plan`, `amount` |
| `subscription_expired` | Payment failed or lapsed | `store_id`, `plan` |

---

### 2.9 `requests.log` — HTTP request log

**What:** Every HTTP request to the API (health checks and static files excluded).
**Level:** DEBUG and above (INFO for 2xx, WARNING for 4xx, ERROR for 5xx).

**Format:**
```
[2026-06-03 10:22:01] INFO     entity=requests  action=http_request  method=GET  path=/api/v1/stores/  status=200  duration_ms=87  user_id=abc123  role=customer
```

**Fields:** `method`, `path`, `status`, `duration_ms`, `user_id`, `role`

**Code reference:** `core/middleware.py` → `RequestLoggingMiddleware`

---

### 2.10 `security.log` — Security threats and anomalies

**What:** Failed auth, blocked accounts, 401/403/429 responses, brute-force signals, and cross-posted from `client_events.log`.
**Level:** WARNING and above only.

**Events logged:**

| action | Source | When | Fields |
|---|---|---|---|
| `login_failed` | `auth_app/views.py` | Wrong OTP submitted | `user_id`, `reason` |
| `login_blocked` | `auth_app/views.py` | Account suspended/locked | `user_id`, `reason` |
| `otp_rate_limited` | `auth_app/views.py` | Too many OTP requests | `user_id` |
| `unauthorized_access` | `middleware.py` | 401 response | `method`, `path`, `ip`, `user_id` |
| `forbidden_access` | `middleware.py` | 403 response | `method`, `path`, `ip`, `user_id` |
| `rate_limit_exceeded` | `middleware.py` | 429 response | `method`, `path`, `ip`, `user_id` |
| `login_failed` | `client_events.log` | Mobile-reported, with device context | `install_id`, `device_model`, `os_version`, `network_type`, `reason` |
| `login_blocked` | `client_events.log` | Mobile-reported, with device context | same as above |

**How to detect brute force:**
```bash
# Count login_failed per install_id in the last hour
cat security.log | grep "login_failed" | grep "2026-06-03 10:" | \
  grep -oP "install_id=\S+" | sort | uniq -c | sort -rn | head -20
```

---

### 2.11 `performance.log` — Slow requests

**What:** Any API request or DB query exceeding 2000 ms. WARNING level only.
**Level:** WARNING and above.

**Events logged:**

| action | When | Fields |
|---|---|---|
| `slow_request` | HTTP response took > 2000 ms | `method`, `path`, `status`, `duration_ms`, `threshold_ms` |

**Sample line:**
```
[2026-06-03 10:22:01] WARNING  entity=performance  action=slow_request  method=GET  path=/api/v1/stores/  status=200  duration_ms=3421  threshold_ms=2000
```

**Code reference:** `core/middleware.py` → `RequestLoggingMiddleware`

**Threshold constant:** `core/logging.py` → `SLOW_REQUEST_MS = 2_000`

---

### 2.12 `client_events.log` — Mobile-shipped security events

**What:** Security events submitted by the mobile app via `POST /api/v1/auth/client-logs/`.
Includes full device and network context that the backend cannot observe.
**Level:** WARNING and above.

**Events logged (mobile-reported only):**

| action | When | Device fields added |
|---|---|---|
| `login_failed` | OTP wrong, from mobile | `device_model`, `os_version`, `app_version`, `install_id`, `network_type` |
| `login_blocked` | Account suspended/locked, from mobile | same |
| `otp_rate_limited` | 429 on OTP send, from mobile | same |

**Sample line:**
```
[2026-06-03 10:22:01] WARNING  entity=client_events  action=login_failed  install_id=a3f9c2b1  device_model=Samsung Galaxy A53  os_version=Android 13 (API 33)  app_version=1.2.0 (45)  network_type=2G  reason=otp_invalid  ip=103.x.x.x
```

> **Note:** Events in `client_events.log` are also written to `security.log` automatically (the logger routes to both handlers). So `security.log` is the single place to look for all security signals.

**Code reference:** `apps/auth_app/views.py` → `ClientLogsView`

---

### 2.13 `error.log` — All errors

**What:** ERROR-level events from every channel. Catchall for anything that broke.
**Level:** ERROR and above.
**Format:** JSON (same as `app.log`).

**Use for:** "What went wrong in the last 24 hours" summary scan.

```bash
# All errors today
cat error.log | jq 'select(.ts | startswith("2026-06-03"))'

# All 5xx errors
cat error.log | jq 'select(.status >= 500)'
```

---

## 3. Mobile Logs — Logcat Tags

Filter in Android Studio: **Logcat → Tag filter → paste the tag name**

| Tag | Channel | What it covers |
|---|---|---|
| `NK_AUTH` | Auth | `login_success`, `login_failed`, `login_blocked`, `logout`, `token_refreshed` |
| `NK_SECURITY` | Security | `circuit_breaker_open/closed`, `unauthorized_access`, `login_failed/blocked` |
| `NK_API` | API | Every HTTP call: `request_ok`, `request_error`. Slow calls also written to `NK_PERF`. |
| `NK_PERF` | Performance | Any API call > 2000 ms: `slow_request` |
| `NK_NAV` | Navigation | `screen_view` — fires on every screen open |
| `NK_USER` | Business events | `wishlist_add/remove`, `search`, `product_view`, `store_view`, `reservation_created`, `video_played` |
| `NK_PREFETCH` | Background worker | `prefetch_complete`, `prefetch_partial`, `prefetch_failed` |

**Where these are defined:** `app/src/main/java/com/nearspot/app/core/NkLog.kt`

**Sample Logcat line:**
```
2026-06-03 10:22:01  D  NK_API: request_ok  path=/api/v1/stores/  status=200  ms=87
2026-06-03 10:22:03  W  NK_PERF: slow_request  path=/api/v1/products/  status=200  duration_ms=2341  threshold_ms=2000
2026-06-03 10:22:05  I  NK_AUTH: login_success  role=customer  duration_ms=421
2026-06-03 10:22:06  D  NK_NAV: screen_view  screen=product_detail
2026-06-03 10:22:07  I  NK_USER: reservation_created  reservation_id=r789
```

**Call sites per tag:**

| Tag | Called in |
|---|---|
| `NK_AUTH` | `AuthViewModel`, `AuthRepository`, `AppModule` (token refresh) |
| `NK_SECURITY` | `AuthViewModel` (login failures), `ApiCircuitBreaker` |
| `NK_API` | `AppModule` OkHttp interceptor (every request) |
| `NK_PERF` | Auto-escalated from `NK_API` when `duration_ms >= 2000` |
| `NK_NAV` | `StoreDetailViewModel.init`, `ProductDetailViewModel.init`, `ReservationsViewModel.init`, `SearchViewModel.init` (via `screenView()`) |
| `NK_USER` | `ProductDetailViewModel`, `WishlistViewModel`, `SearchViewModel`, `VideoViewModel` |
| `NK_PREFETCH` | `HomeRefreshWorker` |

---

## 4. Mobile Logs — Crashlytics Custom Keys

Set once at app start (`NkDeviceContext.init()`), automatically attached to every crash report.
Updated in real time when network type changes.

| Key | Example value | When updated |
|---|---|---|
| `device_model` | `Samsung Galaxy A53` | App start only |
| `os_version` | `Android 13 (API 33)` | App start only |
| `app_version` | `1.2.0 (45)` | App start only |
| `install_id` | `a3f9c2b1-...` (UUID) | App start only (persisted in SharedPreferences) |
| `network_type` | `WiFi` / `4G/5G` / `3G` / `2G` / `none` | On every connectivity change |

**Where defined:** `app/src/main/java/com/nearspot/app/core/NkDeviceContext.kt`

**How to see them:** Firebase Console → Crashlytics → select any crash → scroll to "Keys" tab

> `install_id` is a randomly generated UUID stored in SharedPreferences. It persists across app restarts but resets on reinstall. It is never tied to a phone number, IMEI, or personal identity.

---

## 5. Event Shipping — Mobile → Backend

Security events from the mobile app are sent to the backend in real time.

**Endpoint:** `POST /api/v1/auth/client-logs/`
**Auth required:** No (events are often sent before a token exists)
**Max events per request:** 50
**Allowed actions:** `login_failed`, `login_blocked`, `otp_rate_limited`

**Payload format:**
```json
{
  "events": [
    {
      "action":       "login_failed",
      "device_model": "Samsung Galaxy A53",
      "os_version":   "Android 13 (API 33)",
      "app_version":  "1.2.0 (45)",
      "install_id":   "a3f9c2b1-1234-5678-abcd-ef0123456789",
      "network_type": "4G/5G",
      "extra": {
        "reason": "otp_invalid"
      }
    }
  ]
}
```

**Where the event lands:**
- Written to `client_events.log` with full device context
- Also cross-written to `security.log` (so it appears alongside backend-detected threats)

**Mobile components:**
- `core/NkDeviceContext.kt` — provides device fields
- `core/NkEventShipper.kt` — fire-and-forget POST, called from `AuthViewModel`
- `data/api/ClientLogApiService.kt` — Retrofit interface
- `data/models/LogModels.kt` — `ClientLogEvent`, `ClientLogPayload`

---

## 6. Log Rotation Settings

All backend log files use the same rotation policy (defined in `config/settings/base.py`):

| Setting | Value |
|---|---|
| Rotate when file reaches | 10 MB |
| Backups kept | 7 (`.1` through `.7`) |
| Max disk per channel | ~70 MB |
| Total max across all 13 files | ~910 MB |

Rotated files are named: `auth.log.1`, `auth.log.2`, ... `auth.log.7`

To check current log sizes:
```bash
ls -lh /home/ubuntu/nearkart/logs/
```

---

## 7. Investigation Playbooks

### Scenario A — "User says they can't log in"

```bash
# 1. Check auth.log for their user_id or phone
grep "login_failed\|login_blocked" logs/auth.log | grep "u123"

# 2. Check if their account is blocked in security.log
grep "u123" logs/security.log

# 3. Check if they hit the OTP rate limit
grep "otp_rate_limited" logs/security.log | grep "u123"
```

---

### Scenario B — "Someone is brute-forcing OTPs"

```bash
# Count login_failed events by install_id (mobile brute force)
grep "login_failed" logs/client_events.log | \
  grep -oP "install_id=\S+" | sort | uniq -c | sort -rn | head -20

# Count login_failed events by IP (web/API brute force)
grep "login_failed\|unauthorized_access" logs/security.log | \
  grep -oP "ip=\S+" | sort | uniq -c | sort -rn | head -20
```

---

### Scenario C — "API is slow — which endpoints?"

```bash
# All slow requests today, sorted by duration
cat logs/performance.log | grep "2026-06-03" | \
  grep -oP "path=\S+|duration_ms=\d+" | \
  paste - - | sort -t= -k4 -rn | head -20

# Or with jq on app.log
cat logs/app.log | jq 'select(.action=="slow_request") | {path, duration_ms}' | \
  jq -s 'sort_by(-.duration_ms) | .[:20]'
```

---

### Scenario D — "Crash reported on Crashlytics — need context"

1. Open Firebase Console → Crashlytics → find the crash
2. Click "Keys" tab — you will see:
   - `device_model`: which phone model caused it
   - `os_version`: which Android version
   - `app_version`: which build
   - `network_type`: WiFi or 4G at time of crash
3. Cross-reference with `requests.log` using the timestamp to find what API calls preceded the crash

---

### Scenario E — "Background prefetch is failing silently"

Android Studio Logcat, filter: `NK_PREFETCH`

```
NK_PREFETCH  prefetch_failed  (exception message)
NK_PREFETCH  prefetch_partial  reason=banners_unavailable
NK_PREFETCH  prefetch_complete  stores=12  products=48  images_preloaded=28
```

---

### Scenario F — "Reservation was created but not found on backend"

```bash
# Find the reservation in reservations.log
grep "reservation_id=r789" logs/reservations.log

# Check if the API call reached the server at all
grep "reservations" logs/requests.log | grep "POST" | grep "r789"

# Check for any errors at that time
grep "2026-06-03 10:22" logs/error.log
```

---

## 8. How to Add a New Log Event

### Backend

```python
from core.logging import log_event

# In any view or service:
log_event(
    'reservations',              # channel name — must exist in _ENTITY_LOGGERS
    action      = 'my_action',   # required — snake_case verb
    level       = 'info',        # debug | info | warning | error
    reservation_id = 'r123',     # any additional context fields
    user_id        = 'u456',
)
```

**Available channels:** `auth`, `stores`, `products`, `customers`, `reservations`, `videos`, `billing`, `requests`, `security`, `performance`, `client_events`

To add a new channel:
1. Add logger in `core/logging.py` → `_ENTITY_LOGGERS`
2. Add handler in `config/settings/base.py` → `LOGGING['handlers']`
3. Add logger config in `config/settings/base.py` → `LOGGING['loggers']`

---

### Mobile

```kotlin
// In any ViewModel — use the closest matching NkLog method:
NkLog.screenView("my_screen")
NkLog.storeView(storeId)
NkLog.productView(productId, storeId)
NkLog.search(query, resultCount)
NkLog.wishlistToggle(productId, added = true)
NkLog.reservationCreated(reservationId)
NkLog.videoPlayed(videoId)
NkLog.apiSuccess(path, statusCode, durationMs)
NkLog.apiError(path, statusCode, durationMs, exception)

// For anything not covered — use the generic error helper:
NkLog.error("MY_TAG", "something unexpected happened", throwable)
```

To add a new category:
1. Add a new `private const val MY_TAG = "NK_MYTAG"` in `NkLog.kt`
2. Add a new function: `fun myEvent(...) = timber(MY_TAG).i("event_name  field=%s", value)`
3. Add the tag to the table in section 3 of this document

---

## Quick Reference Card

| I want to find... | Look here |
|---|---|
| A specific user's login history | `auth.log` → grep `user_id=` |
| Who got blocked today | `security.log` → grep `login_blocked` |
| Which phone model crashes most | Firebase Crashlytics → Issues → device_model key |
| Which API endpoints are slow | `performance.log` or `app.log` with jq |
| A specific reservation | `reservations.log` → grep `reservation_id=` |
| All errors from last hour | `error.log` → grep timestamp |
| Mobile brute force attempts | `client_events.log` → grep `login_failed`, count by `install_id` |
| Every request from a user | `requests.log` → grep `user_id=` |
| Background worker health | Android Logcat `NK_PREFETCH` tag |
| Network issues at login | Android Logcat `NK_API` + `NK_PERF` tags |

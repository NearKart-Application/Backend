# Sprint 1 — Code Reference

Every file created in Sprint 1 (Django Foundation).
For each file: all classes, functions, variables, and why they were written.

---

## 1. core/models.py

**Purpose:** Defines `BaseModel` — the parent class that every single NearKart model inherits from.

---

### Class: `BaseModel`

```python
class BaseModel(models.Model):
    class Meta:
        abstract = True
```

**Why:** Instead of repeating `id`, `created_at`, `updated_at` in every model (User, Store, Product, Video etc.), we define them once here. All models inherit from `BaseModel` and automatically get these fields.

**`abstract = True`** — tells Django this is not a real table. It only exists to be inherited. No `core_basemodel` table is created in the database.

**Fields:**

| Field | Type | Why |
|-------|------|-----|
| `id` | UUIDField (primary key) | UUID instead of auto-increment integer. Safer — IDs cannot be guessed or enumerated by attackers. `uuid.uuid4` generates a random UUID automatically |
| `created_at` | DateTimeField (`auto_now_add=True`) | Set once when the record is first created. Never changes. Used for sorting and analytics |
| `updated_at` | DateTimeField (`auto_now=True`) | Updated every time the record is saved. Used to detect stale cache |

**`editable=False` on `id`:** Prevents the Django admin from showing the UUID field as editable — it should never be manually changed.

**`ordering = ['-created_at']`:** Default ordering for all models — newest first. Can be overridden per-model.

**`__repr__`:** Returns `<ClassName uuid>` in Python shell and logs. Makes debugging easier.

---

## 2. core/exceptions.py

**Purpose:** Makes every API error return the same JSON format regardless of what went wrong.

Without this, DRF returns inconsistent formats:
- Validation error: `{"phone_number": ["This field is required."]}`
- Auth error: `{"detail": "Authentication credentials were not provided."}`
- Not found: `{"detail": "Not found."}`

With `custom_exception_handler`, every error looks like:
```json
{
    "error": "validation_error",
    "message": "Enter a valid Indian mobile number",
    "code": "INVALID_PHONE",
    "details": {}
}
```

---

### Function: `custom_exception_handler(exc, context)`

**Why:** Registered in `REST_FRAMEWORK['EXCEPTION_HANDLER']` in settings. DRF calls this function for every exception that occurs in any view.

**Flow:**
1. Calls DRF's default `exception_handler(exc, context)` first — it handles the standard HTTP conversion
2. If a response exists (not a 500 crash), reformats `response.data` into our standard shape
3. Returns the reformatted response

**`error_map` dict:** Maps HTTP status codes to human-readable error type strings:
- `400` → `"validation_error"`
- `401` → `"authentication_failed"`
- `403` → `"permission_denied"`
- `404` → `"not_found"`
- `429` → `"throttled"`

---

### Function: `_extract_message(data)`

**Why:** DRF stores error messages in many different shapes depending on what raised the error. This function handles all cases and returns a single string:
- `{"detail": "Not found."}` → returns `"Not found."`
- `{"phone_number": ["Invalid format"]}` → returns `"Invalid format"` (first field error)
- `["Some error"]` → returns `"Some error"`

---

### Function: `_extract_code(data)`

**Why:** Returns the error code in uppercase for mobile app to handle programmatically.
Mobile app can check `if (error.code === 'NOT_AUTHENTICATED')` and redirect to login.

---

### Function: `_extract_details(data)`

**Why:** Preserves all the field-level validation errors in the `details` key so the frontend can show errors next to specific form fields.

---

## 3. core/middleware.py

**Purpose:** Authenticates WebSocket connections using JWT token passed as a URL query parameter.

---

### Class: `JWTAuthMiddleware`

**Why:** Django REST Framework's JWT authentication only works for HTTP requests. WebSocket connections don't have an `Authorization` header — the token must be passed in the URL query string like: `ws://localhost:8001/ws/chat/123/?token=eyJhbGc...`

This middleware reads the token, validates it, and sets `scope['user']` so WebSocket consumers can access `self.scope['user']` just like HTTP views use `request.user`.

**Inherits from `BaseMiddleware`** (Django Channels) — required to wrap Channels applications.

**Function `__call__(scope, receive, send)`:**
- Extracts `?token=...` from the WebSocket URL query string
- Calls `_get_user(token_key)` to validate and fetch the user
- Sets `scope['user']` — available to all downstream WebSocket consumers

**Function `_get_user(token_key)`:**
- `@database_sync_to_async` — database queries are synchronous (Django ORM), but Channels runs in async. This decorator runs the DB query in a thread pool so it doesn't block the event loop
- Validates the JWT `AccessToken`
- Fetches `User` by `token['user_id']`
- Returns `None` if token is invalid/expired — unauthenticated WebSocket connection

---

### Function: `JWTAuthMiddlewareStack(inner)`

**Why:** A convenience wrapper so `asgi.py` can write `JWTAuthMiddlewareStack(URLRouter(...))` instead of `JWTAuthMiddleware(URLRouter(...))`. Matches Django Channels' `AuthMiddlewareStack` naming convention.

---

## 4. core/pagination.py

**Purpose:** Two pagination styles for different use cases across the API.

---

### Class: `StandardCursorPagination`

**Why:** Used for real-time feeds — video feed, message list, notification list.

Cursor pagination uses an opaque cursor (encoded timestamp) instead of page numbers. This means:
- Page 1, 2, 3 → instead: `?cursor=cD0yMDI0...`
- If new records are added while user scrolls, they won't see duplicates or skip items
- Safe for infinite scroll on mobile

**Variables:**
- `page_size = 20` — 20 items per page by default
- `page_size_query_param = 'page_size'` — client can override with `?page_size=10`
- `max_page_size = 50` — hard cap, prevents abuse
- `ordering = '-created_at'` — newest first
- `cursor_query_param = 'cursor'` — URL param name for the cursor value

---

### Class: `StandardOffsetPagination`

**Why:** Used for manageable lists — store list, invoice list, analytics tables.

Offset pagination uses `?page=2` style. Simpler than cursor but can show duplicates if records are inserted between pages. Acceptable for lists that don't change in real-time.

**Variables:**
- `page_size = 20` — 20 items per page
- `max_page_size = 100` — admin panels may need more
- `page_query_param = 'page'` — URL param: `?page=3`

---

## 5. core/permissions.py

**Purpose:** Role-based access control classes used as `permission_classes` on views.

---

### Class: `IsCustomer`

**Why:** Restricts endpoint to customers only. Example: browsing video feed, placing reservations.

**Logic:** Checks `request.user.is_authenticated AND request.user.role == 'customer'`

---

### Class: `IsVendor`

**Why:** Restricts endpoint to vendors only. Example: creating stores, uploading videos, viewing own analytics.

---

### Class: `IsAdmin`

**Why:** Restricts endpoint to NearKart admins. Example: admin panel, approving vendors, viewing all analytics.

---

### Class: `IsVendorOrAdmin`

**Why:** Some actions are allowed for both vendors and admins. Example: approving/rejecting products.

---

### Class: `IsStoreOwner`

**Why:** Object-level permission. Checks that the vendor owns the specific store/product/video they're trying to modify.

Without this, any vendor could edit another vendor's store by guessing the UUID.

**Logic:**
- If `obj` has an `owner` field: checks `obj.owner == request.user`
- If `obj` has a `store` field: checks `obj.store.owner == request.user`
- Used on: Store, Product, Video, Invoice endpoints

---

## 6. core/urls/health.py

**Purpose:** Single health check endpoint that verifies PostgreSQL and Redis are reachable.

---

### Function: `health_check(request)`

**Why:** Used by Docker's healthcheck, load balancers, and monitoring tools to verify the service is alive and all dependencies are working.

**What it checks:**

| Check | How | Why |
|-------|-----|-----|
| Database | `connection.ensure_connection()` | Verifies PostgreSQL is up and Django can connect |
| Redis | `cache.set('health_check', '1', 5)` then `cache.get(...)` | Verifies Redis is up and read/write works |

**Returns 200** if both are `ok`.
**Returns 503** if either is down — so load balancers can route traffic away from this instance.

---

## 7. core/utils/cache.py

**Purpose:** Central place for all Redis cache key patterns and TTL constants.

---

### Class: `CacheService`

**Why:** Instead of writing `cache.get(f'stores:nearby:{lat}:{lng}')` scattered across views, all cache keys are defined here. If a key format needs to change, only one file needs updating.

**TTL Constants (time-to-live in seconds):**

| Variable | Value | Why |
|----------|-------|-----|
| `TTL_NEARBY_STORES` | 300 (5 min) | Store locations don't change every second. Cache reduces PostGIS queries |
| `TTL_VIDEO_FEED` | 120 (2 min) | Feed refreshes frequently — new videos posted often |
| `TTL_PRODUCT_SEARCH` | 60 (1 min) | Search results can change quickly |
| `TTL_STORE_DETAIL` | 600 (10 min) | Store details rarely change |

**Key Builder Functions:**

| Function | Key Format | Why |
|----------|-----------|-----|
| `nearby_stores_key(lat, lng, radius, category)` | MD5 hash | Lat/lng rounded to 3 decimals (~100m grid). All users within 100m share the same cache entry |
| `video_feed_key(locality)` | MD5 hash of locality | All users in the same area share the same video feed cache |
| `product_search_key(query, lat, lng)` | MD5 hash | Same search in same area returns cached results |
| `store_detail_key(store_id)` | `store:detail:{id}` | Simple key per store |

**Why MD5 for keys:** Cache keys have character limits and cannot contain spaces or special chars. MD5 gives a fixed-length safe key from any input.

**Invalidation Functions:**

| Function | When to call |
|----------|-------------|
| `invalidate_video_feed(locality)` | After vendor posts new video |
| `invalidate_store_caches(lat, lng)` | After store location or details change |

---

## 8. core/utils/geo.py

**Purpose:** PostGIS and Google Maps utility functions for location-based features.

---

### Function: `build_point(lat, lng)`

**Why:** PostGIS `Point()` takes `(longitude, latitude)` order — opposite of what humans expect. This wrapper makes it impossible to mix up the order elsewhere in the codebase.

---

### Function: `get_nearby_stores(lat, lng, radius_km, category, limit)`

**Why:** The core hyperlocal query — finds stores within X km of the user.

**How it works:**
1. Checks Redis cache first. If cached, returns immediately (no DB query)
2. Builds a PostGIS `Point` for the user's location
3. Uses `location__dwithin=(user_point, D(km=radius_km))` — PostGIS `ST_DWithin` which uses the GIST spatial index (extremely fast)
4. Annotates each store with `Distance('location', user_point)` for sorting
5. Orders by distance ascending — nearest store first
6. Caches result for `TTL_NEARBY_STORES` seconds

**Variables:**
- `radius_km = 2` — default 2km radius
- `limit = 50` — max 50 stores returned

---

### Function: `reverse_geocode(lat, lng)`

**Why:** Converts GPS coordinates to a human-readable area name like `"Kukatpally, Hyderabad"`.
Used to display "Showing stores near Kukatpally" in the app.

Uses Google Maps Geocoding API. Falls back to `"Unknown area"` if API fails or key is missing.

---

## 9. core/utils/s3.py

**Purpose:** AWS S3 utility functions for media file management (videos, images).

---

### Function: `get_s3_client()`

**Why:** Creates a boto3 S3 client with credentials from settings. Centralised so all S3 functions use the same client configuration.

---

### Function: `generate_presigned_upload_url(store_id, video_id, content_type)`

**Why:** Instead of uploading video through Django (which would slow down the server and use bandwidth), the mobile app uploads directly to S3.

Flow:
1. App calls this function → gets a presigned URL
2. App uploads video directly to S3 using that URL
3. Django never touches the video bytes

S3 key format: `videos/{store_id}/{video_id}/original.mp4`

`ExpiresIn` = `AWS_PRESIGNED_URL_EXPIRY` (900 seconds = 15 minutes from `.env`)

---

### Function: `generate_presigned_image_url(store_id, product_id, filename, content_type)`

**Why:** Same direct-upload pattern for product images.

S3 key format: `images/{store_id}/{product_id}/{filename}`

---

### Function: `delete_video_files(store_id, video_id)`

**Why:** When a video is deleted, all associated S3 files must be cleaned up to avoid storage costs.

Lists all objects with `prefix = videos/{store_id}/{video_id}/` and batch deletes them. This covers: original.mp4, HLS segments (.ts files), playlist.m3u8, thumbnail.jpg.

---

### Function: `get_cdn_url(s3_key)`

**Why:** Returns the public URL for a file. Uses CDN domain if configured (faster delivery), falls back to direct S3 URL.

---

## 10. core/utils/validators.py

**Purpose:** Reusable validation functions used in serializers across multiple apps.

---

### Function: `validate_indian_phone(value)`

**Why:** Centralized phone validation so the same regex is used everywhere — auth serializer, store creation, etc. Raises Django `ValidationError` with a specific error code `INVALID_PHONE` that the frontend can check.

**Regex:** `^\+91[6-9]\d{9}$`
- `+91` — India country code
- `[6-9]` — valid first digit for Indian mobile numbers
- `\d{9}` — 9 more digits

---

### Function: `validate_otp(value)`

**Why:** Validates that OTP is exactly 6 digits. `^\d{6}$`

---

### Function: `validate_video_content_type(value)`

**Why:** Only allows MP4, MOV, AVI. Prevents uploading PDFs or executables as "videos".

Allowed: `video/mp4`, `video/quicktime`, `video/x-msvideo`

---

### Function: `validate_image_content_type(value)`

**Why:** Only allows JPEG, PNG, WebP for product images.

---

### Function: `validate_video_size(size_mb, is_story)`

**Why:** Enforces size limits from `.env` settings:
- Regular video: `VIDEO_MAX_SIZE_MB` (100MB)
- Story: `STORY_MAX_SIZE_MB` (50MB)

Reading from settings (not hardcoded) so limits can be changed without code deployment.

---

### Function: `validate_radius(value)`

**Why:** Search radius must be one of `[1, 2, 3, 5]` km. Prevents arbitrary values like `radius=500` that would query the entire country and kill the DB.

---

## 11. config/asgi.py

**Purpose:** Entry point for the ASGI server (gunicorn + uvicorn workers). Handles both HTTP and WebSocket in a single process.

---

**`ProtocolTypeRouter`:** Routes incoming connections based on protocol type:
- `http` → standard Django ASGI app (handles all REST API requests)
- `websocket` → Django Channels with JWT auth middleware (handles chat and group WebSockets)

**`AllowedHostsOriginValidator`:** Rejects WebSocket connections from origins not in `ALLOWED_HOSTS`. Prevents cross-site WebSocket hijacking.

**`JWTAuthMiddlewareStack`:** Validates JWT token in WebSocket URL before the connection reaches any consumer.

**`URLRouter`:** Routes WebSocket connections to specific consumers based on URL pattern. Combines `chat_urlpatterns` and `group_urlpatterns`.

---

## 12. config/settings/base.py — Key Settings

---

### `INSTALLED_APPS` — Three groups

| Group | Apps | Why |
|-------|------|-----|
| `DJANGO_APPS` | admin, auth, gis, etc. | Django built-ins |
| `THIRD_PARTY_APPS` | drf, simplejwt, channels, etc. | Installed packages |
| `LOCAL_APPS` | core, auth_app, stores, etc. | Our code |

`django.contrib.gis` — enables PostGIS support for PointField, distance queries, spatial indexes.

---

### `DATABASES` setting

```python
'ENGINE': 'django.contrib.gis.db.backends.postgis'
```

**Why `postgis` not `postgresql`:** The PostGIS engine adds spatial query support (`ST_DWithin`, `ST_Distance`, GeoJSON serialization). Without it, `PointField` and location queries don't work.

`CONN_MAX_AGE = 60` — reuses DB connections for 60 seconds instead of creating a new connection per request. Reduces connection overhead.

---

### `CACHES` setting — Redis

`KEY_PREFIX = 'nearkart'` — all cache keys are prefixed with `nearkart:`. Prevents collision if multiple apps share the same Redis.

Three separate Redis databases:
- `db=0` — Celery broker (task queue)
- `db=1` — Django cache
- `db=2` — Channels layer (WebSocket messages)

---

### `SIMPLE_JWT` setting

| Variable | Value | Why |
|----------|-------|-----|
| `ACCESS_TOKEN_LIFETIME` | 1 hour | Short-lived for security |
| `REFRESH_TOKEN_LIFETIME` | 30 days | Long-lived for convenience |
| `ROTATE_REFRESH_TOKENS` | False | Do not issue a new refresh token on each use |
| `BLACKLIST_AFTER_ROTATION` | True | When rotation is on, blacklist old token |
| `AUTH_HEADER_TYPES` | `('Bearer',)` | Tokens passed as `Authorization: Bearer <token>` |
| `USER_ID_FIELD` | `'id'` | Our UUID field name |
| `USER_ID_CLAIM` | `'user_id'` | Key name inside the JWT payload |

---

### `REST_FRAMEWORK` setting

| Key | Value | Why |
|-----|-------|-----|
| `DEFAULT_AUTHENTICATION_CLASSES` | `JWTAuthentication` | All API requests require JWT by default |
| `DEFAULT_PERMISSION_CLASSES` | `IsAuthenticated` | All endpoints require login unless overridden with `AllowAny` |
| `DEFAULT_RENDERER_CLASSES` | `JSONRenderer` only | No HTML browsable API in production |
| `EXCEPTION_HANDLER` | `custom_exception_handler` | Consistent error format |
| `DEFAULT_SCHEMA_CLASS` | `drf_spectacular.openapi.AutoSchema` | Auto-generates OpenAPI schema for Swagger UI |

---

### `AUTH_USER_MODEL = 'auth_app.User'`

**Why:** Tells Django to use our custom `User` model instead of Django's default. Must be set before the first migration. Cannot be changed after migrations exist.

---

## 13. Dockerfile

**Purpose:** Multi-stage Docker build for the Django application.

**Three stages:**

| Stage | Name | Purpose |
|-------|------|---------|
| Stage 1 | `builder` | Installs system dependencies and Python packages into `/venv` |
| Stage 2 | `development` | Extends builder, installs dev packages, runs as non-root user |
| Stage 3 | `production` | Clean image with only runtime dependencies, no build tools |

**Why `/venv` not `/app/venv`:**
`docker-compose.yml` mounts `.:/app` which overwrites everything in `/app`. If venv was at `/app/venv`, it would be wiped by the volume mount. Placing it at `/venv` (outside `/app`) keeps it intact.

**Non-root user `appuser`:**
Running as root inside Docker is a security risk. If the container is compromised, attacker has root access to the host. `appuser` limits the blast radius.

---

## 14. docker-compose.yml — Services

| Service | Port | Purpose |
|---------|------|---------|
| `django` | 8000 | Gunicorn + Uvicorn workers, serves REST API |
| `daphne` | 8001 | ASGI WebSocket server for real-time chat |
| `celery` | — | Background task worker (SMS, video processing) |
| `celery-beat` | — | Scheduled tasks (blacklist cleanup, expiry checks) |
| `postgres` | 5432 | PostgreSQL + PostGIS database |
| `redis` | 6379 | Cache + Celery broker + Channels layer |
| `nginx` | 80 | Reverse proxy — routes /api/ to django, /ws/ to daphne, /static/ to filesystem |

**Why gunicorn uses `config.asgi:application` with `uvicorn.workers.UvicornWorker`:**
Django Channels requires ASGI, not WSGI. Using WSGI would break WebSocket support. Uvicorn workers run inside gunicorn for process management + ASGI support.

---

## Summary — All Files in Sprint 1

| File | Purpose |
|------|---------|
| `core/models.py` | BaseModel with UUID + timestamps for all models |
| `core/exceptions.py` | Consistent JSON error format for all API errors |
| `core/middleware.py` | JWT auth for WebSocket connections |
| `core/pagination.py` | Cursor pagination (feeds) + offset pagination (lists) |
| `core/permissions.py` | Role-based permission classes (IsCustomer, IsVendor, IsAdmin, IsStoreOwner) |
| `core/urls/health.py` | Health check endpoint — verifies DB + Redis |
| `core/utils/cache.py` | Redis cache key builders, TTL constants, invalidation helpers |
| `core/utils/geo.py` | PostGIS nearby store queries, Google Maps reverse geocoding |
| `core/utils/s3.py` | AWS S3 presigned URLs for direct video/image upload |
| `core/utils/validators.py` | Phone, OTP, video/image type and size validators |
| `config/asgi.py` | ASGI entry point — routes HTTP to Django, WebSocket to Channels |
| `config/settings/base.py` | All shared settings: DB, Redis, JWT, DRF, Celery, Spectacular |
| `config/settings/development.py` | Dev overrides: DEBUG=True, CORS allow all, console email, fixed OTP |
| `Dockerfile` | Multi-stage build: builder → development → production |
| `docker-compose.yml` | 7 services: django, daphne, celery, celery-beat, postgres, redis, nginx |
| `nginx/nginx.conf` | Reverse proxy with rate limiting on OTP and upload endpoints |

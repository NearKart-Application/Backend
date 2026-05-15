# Sprint 2 — Code Reference

Every file created or updated in Sprint 2.
For each file: what classes/functions exist, what variables they use, and why they were written.

---

## 1. apps/auth_app/models.py

**Purpose:** Defines the database tables for users, OTP tokens, and device tokens.

---

### Class: `UserRole`

```python
class UserRole(models.TextChoices):
    CUSTOMER = 'customer', 'Customer'
    VENDOR   = 'vendor',   'Vendor'
    ADMIN    = 'admin',    'Admin'
```

**Why:** Django's `TextChoices` creates a safe enum for the `role` field.
Prevents storing invalid values like `"moderator"` or `"superadmin"` in the DB.

**Variables:**
- `CUSTOMER` — default role for anyone who signs up
- `VENDOR` — shop owners who create stores and upload videos
- `ADMIN` — internal NearKart staff

---

### Class: `UserManager`

```python
class UserManager(BaseUserManager):
```

**Why:** Django requires a custom manager when `USERNAME_FIELD` is not `username`.
Since we use `phone_number` as the login field, this manager tells Django how to create users.

**Functions:**

| Function | What it does |
|----------|-------------|
| `create_user(phone_number, role, **extra_fields)` | Creates a regular user. Sets unusable password (no password login — only OTP) |
| `create_superuser(phone_number, **extra_fields)` | Creates admin user with `is_staff=True` and `is_superuser=True` for Django admin access |

---

### Class: `User`

```python
class User(AbstractBaseUser, PermissionsMixin, BaseModel):
```

**Why:** Custom user model replacing Django's default User.
We replaced `username/password` login with `phone_number/OTP` login.

**Inherits from:**
- `AbstractBaseUser` — gives `password`, `last_login`, `is_active` fields and auth methods
- `PermissionsMixin` — gives `is_superuser`, `groups`, `user_permissions` for Django admin
- `BaseModel` — gives `id` (UUID), `created_at`, `updated_at` (defined in `core/models.py`)

**Fields:**

| Field | Type | Why |
|-------|------|-----|
| `phone_number` | CharField, unique | Primary login identifier. `+91XXXXXXXXXX` format |
| `role` | CharField (choices) | Controls what the user can do: customer/vendor/admin |
| `full_name` | CharField, blank | Optional display name. Empty on first signup |
| `email` | EmailField, blank | Optional. For billing receipts / SendGrid emails |
| `is_active` | BooleanField | False = soft-deleted user. Cannot login |
| `is_staff` | BooleanField | True = can access Django admin panel |
| `registered_location` | PointField (PostGIS) | GPS coordinates. Used to show nearby stores in feed |

**Key settings:**
- `USERNAME_FIELD = 'phone_number'` — tells Django to use phone as login field
- `REQUIRED_FIELDS = []` — no fields are required at `createsuperuser` prompt (only phone)
- `db_table = 'auth_users'` — exact table name in PostgreSQL

---

### Class: `OTPToken`

```python
class OTPToken(BaseModel):
```

**Why:** Stores the OTP for each login attempt. We never store the raw OTP — only its SHA256 hash.
This way even if the DB is breached, attacker cannot read the OTP.

**Class-level constants:**

| Variable | Value | Why |
|----------|-------|-----|
| `MAX_ATTEMPTS` | 5 | After 5 wrong guesses, token is locked. Prevents brute-force attacks |
| `OTP_EXPIRY_MINUTES` | 5 | OTP expires in 5 minutes. Standard security practice |

**Fields:**

| Field | Type | Why |
|-------|------|-----|
| `user` | ForeignKey → User | Links this OTP to a specific user |
| `otp_hash` | CharField(64) | SHA256 hash of the 6-digit OTP. 64 chars = length of SHA256 hex string |
| `expires_at` | DateTimeField | When this OTP stops being valid |
| `is_used` | BooleanField | True after successful verify. Prevents OTP reuse |
| `attempts` | PositiveSmallIntegerField | Count of wrong guesses. Locked when >= MAX_ATTEMPTS |

**Functions:**

| Function | What it does |
|----------|-------------|
| `make_hash(otp)` | Returns `SHA256(otp)` as hex string. Used to hash before storing and before comparing |
| `create_for_user(user, otp)` | Marks all old unused OTPs as used, then creates a new one. Ensures only 1 active OTP per user |
| `is_expired` (property) | Returns True if current time is past `expires_at` |
| `is_locked` (property) | Returns True if `attempts >= MAX_ATTEMPTS` |
| `verify(otp)` | Increments attempts. Compares `SHA256(otp)` with stored hash. Marks `is_used=True` on success |

---

### Class: `DeviceToken`

```python
class DeviceToken(BaseModel):
```

**Why:** Stores Firebase Cloud Messaging (FCM) push tokens for each device.
Used in Sprint 8 (Notifications) to send push alerts to the user's phone/tablet.

**Fields:**

| Field | Type | Why |
|-------|------|-----|
| `user` | ForeignKey → User | Which user owns this device |
| `fcm_token` | CharField(512) | Firebase push token. Long string provided by the mobile app |
| `device_type` | CharField (android/ios) | To send platform-specific notification payloads |
| `is_active` | BooleanField | False = user uninstalled app or logged out on that device |

---

## 2. apps/auth_app/services.py

**Purpose:** Business logic layer. Views call services — services handle all the rules.
Keeps views thin and logic testable independently.

---

### Class: `OTPService`

**Why:** Groups all OTP-related logic (generate, send, verify) in one place.
If we change from Twilio to another SMS provider, only this file needs updating.

**Functions:**

| Function | What it does |
|----------|-------------|
| `generate_otp()` | Returns 6-digit OTP. In dev uses `settings.DEV_FIXED_OTP` (123456). In production generates `random.randint(100000, 999999)` |
| `generate_and_send(phone_number)` | Creates user if new, generates OTP, stores hash in DB, queues Celery SMS task |
| `verify(phone_number, otp)` | Looks up user and latest unused OTP. Checks not expired/locked. Calls `token.verify(otp)`. Returns User on success or raises `ValueError` |

**Why `ValueError` instead of HTTP exception?**
Services don't know about HTTP. Views catch `ValueError` and convert it to a 400 response.
This makes services reusable in Celery tasks, management commands, or tests.

---

### Class: `JWTService`

**Why:** Groups JWT token creation and location update in one place.

**Functions:**

| Function | What it does |
|----------|-------------|
| `issue_tokens(user)` | Creates SimpleJWT RefreshToken, embeds `role` and `phone` as custom claims, returns `{access, refresh}` dict |
| `update_location(user, latitude, longitude)` | Creates PostGIS `Point(longitude, latitude)` and saves to `registered_location`. Note: PostGIS takes `(lng, lat)` order, not `(lat, lng)` |

**Custom JWT claims:**
```python
refresh['role']  = user.role          # 'customer' / 'vendor' / 'admin'
refresh['phone'] = user.phone_number  # '+919876543210'
```
These are embedded in the token so the mobile app can read role/phone without an extra API call.

---

## 3. apps/auth_app/serializers.py

**Purpose:** Validates and cleans incoming request data before it reaches the service layer.
Also formats outgoing response data.

---

### Class: `OTPSendSerializer`

**Why:** Validates the phone number format before generating an OTP.
Rejects numbers like `9876543210` (no +91) or `+1234567890` (non-Indian).

**Fields:**
- `phone_number` — CharField, max_length=15

**Validation method `validate_phone_number(value)`:**
- Strips all spaces from input
- Regex: `^\+91[6-9]\d{9}$`
  - `\+91` — must start with +91 (India code)
  - `[6-9]` — 6/7/8/9 are valid first digits for Indian mobile numbers
  - `\d{9}` — followed by exactly 9 more digits
  - Total = 13 characters: `+91` + 10 digits

---

### Class: `OTPVerifySerializer`

**Why:** Validates both phone number and OTP format before verification.

**Fields:**
- `phone_number` — CharField
- `otp` — CharField, min_length=6, max_length=6

**Validation method `validate_otp(value)`:**
- Checks `value.isdigit()` — OTP must be all numbers, no letters or symbols

---

### Class: `UserSerializer`

**Why:** Controls exactly which User fields are returned in API responses.
Sensitive fields like `password`, `otp_tokens`, `is_superuser` are excluded.

**Fields returned:** `id`, `phone_number`, `role`, `full_name`, `email`, `created_at`

**Read-only fields:** `id`, `phone_number`, `role`, `created_at`
These cannot be changed via PATCH /me/ — only `full_name` and `email` are editable.

---

### Class: `LocationUpdateSerializer`

**Why:** Validates GPS coordinates before saving to PostGIS.

**Fields:**
- `latitude` — FloatField, min_value=-90, max_value=90
- `longitude` — FloatField, min_value=-180, max_value=180

---

## 4. apps/auth_app/views.py

**Purpose:** HTTP layer. Receives requests, calls serializers to validate, calls services for logic, returns responses.

---

### Class: `OTPSendView`

- Method: `POST`
- URL: `/api/v1/auth/otp/send/`
- Auth: None (`AllowAny`)
- Throttle: `otp_send` scope (rate limited)
- Calls: `OTPService.generate_and_send(phone_number)`

---

### Class: `OTPVerifyView`

- Method: `POST`
- URL: `/api/v1/auth/otp/verify/`
- Auth: None (`AllowAny`)
- Throttle: `otp_verify` scope
- Calls: `OTPService.verify()` then `JWTService.issue_tokens()`
- Returns: user data + access + refresh tokens

---

### Class: `TokenRefreshView`

- Method: `POST`
- URL: `/api/v1/auth/token/refresh/`
- Auth: None (`AllowAny`)
- Calls: SimpleJWT `RefreshToken(refresh_token)` directly
- Returns: new `access` token

---

### Class: `MeView`

- Methods: `GET`, `PATCH`
- URL: `/api/v1/auth/me/`
- Auth: Required (`IsAuthenticated`)
- GET: returns `UserSerializer(request.user).data`
- PATCH: partial update of `full_name` and `email` only

---

### Class: `LocationUpdateView`

- Method: `PUT`
- URL: `/api/v1/auth/me/location/`
- Auth: Required (`IsAuthenticated`)
- Calls: `JWTService.update_location(user, lat, lng)`

---

### Class: `LogoutView`

- Method: `POST`
- URL: `/api/v1/auth/logout/`
- Auth: Required (`IsAuthenticated`)
- Calls: `RefreshToken(refresh_token).blacklist()`
- Why blacklist: once blacklisted, that refresh token can never generate a new access token

---

## 5. apps/auth_app/tasks.py

**Purpose:** Celery async task to send OTP SMS in the background.

---

### Function: `send_otp_sms`

```python
@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_otp_sms(self, phone_number, otp):
```

**Why async / Celery:**
Twilio API can take 1-3 seconds. If we called it synchronously in the view, the user waits 3 seconds for the `/otp/send/` response. With Celery, the view responds instantly and SMS is sent in the background.

**Parameters:**
- `bind=True` — gives `self` access so we can call `self.retry()`
- `max_retries=3` — if SMS fails, retry up to 3 times automatically
- `default_retry_delay=30` — wait 30 seconds between retries

**Imports `SMSService` inside the function** (not at top) to avoid circular import issues at startup.

---

## 6. apps/auth_app/admin.py

**Purpose:** Registers models in Django Admin so NearKart staff can view/manage users and OTPs.

---

### Class: `UserAdmin`

**Why:** Custom admin view for `User` model. Inherits from `BaseUserAdmin` to keep Django's auth admin features (like change password button).

**Configured:**
- `list_display` — columns shown in the user list: phone, role, name, active status, date
- `list_filter` — filter sidebar by role and active status
- `search_fields` — search by phone number or name
- `fieldsets` — groups fields into sections on the edit page
- `add_fieldsets` — minimal fields shown when creating a new user

---

### Class: `OTPTokenAdmin`

**Why:** Lets staff see all OTP attempts, check if used, see how many wrong attempts.
`readonly_fields = ['otp_hash']` — shows the hash but prevents editing it.

---

### Class: `DeviceTokenAdmin`

**Why:** Lets staff see which devices are registered for push notifications.

---

## 7. apps/notifications/services.py

**Purpose:** Sends SMS via Twilio. Kept separate from auth_app so other apps (billing, reservations) can also send SMS without duplicating code.

---

### Class: `SMSService`

**Function `send_otp(phone_number, otp)`:**
- Imports Twilio client lazily (inside function) so the app starts even if Twilio is not installed
- Creates Twilio message with fixed template: `"Your NearKart OTP is {otp}. Valid for 5 minutes."`
- Returns `True` on success, `False` on any exception (never raises)
- Logs success and failure so we can monitor in production

**Why return bool instead of raise:**
The Celery task `send_otp_sms` uses the return value to decide whether to retry.
Raising inside the service would require the task to catch exceptions — instead, it checks the bool.

---

## 8. config/settings/base.py — Changes Made

**Added `rest_framework_simplejwt.token_blacklist` to `THIRD_PARTY_APPS`:**
- Required for `RefreshToken.blacklist()` to work in the logout endpoint
- Creates `token_blacklist_outstandingtoken` and `token_blacklist_blacklistedtoken` tables in DB

**Updated `SPECTACULAR_SETTINGS`:**
- Added `APPEND_COMPONENTS` with `jwtAuth` security scheme — shows Authorize button in Swagger UI
- Added `SECURITY: [{'jwtAuth': []}]` — marks all endpoints as requiring JWT by default
- Added `displayRequestDuration` and `filter` to `SWAGGER_UI_SETTINGS` for better UX

---

## 9. config/settings/development.py — Changes Made

**Added `SENTRY_DSN = ''`:**
- The `.env` file had a placeholder Sentry DSN
- `base.py` reads it and calls `sentry_sdk.init()` if non-empty
- Sentry's WSGI middleware conflicted with our ASGI server (gunicorn + uvicorn workers)
- Setting it to empty in dev prevents Sentry from initializing

**Removed debug_toolbar:**
- `django-debug-toolbar` is designed for Django's `runserver` (development server)
- We run `gunicorn` which doesn't serve static files by default
- Toolbar was causing 404 errors for `/static/debug_toolbar/` and injecting broken HTML into responses

---

## 10. .env — Changes Made

**`SENTRY_DSN` cleared to empty:**
```
SENTRY_DSN=
```
Was: `SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0`

The placeholder DSN was real enough to trigger `sentry_sdk.init()` but invalid, causing
`TypeError: sentry_patched_wsgi_handler() missing 1 required positional argument: 'start_response'`
on every single HTTP request.

---

## Summary — All Files in Sprint 2

| File | Status | Purpose |
|------|--------|---------|
| `apps/auth_app/models.py` | Created | User, OTPToken, DeviceToken DB models |
| `apps/auth_app/services.py` | Created | OTPService, JWTService business logic |
| `apps/auth_app/serializers.py` | Created | Request/response validation |
| `apps/auth_app/views.py` | Created | 6 API endpoint handlers |
| `apps/auth_app/urls.py` | Created | URL routing |
| `apps/auth_app/tasks.py` | Created | Celery async SMS task |
| `apps/auth_app/admin.py` | Created | Django admin panels |
| `apps/auth_app/migrations/0001_initial.py` | Generated | DB migration for User/OTP/Device tables |
| `apps/notifications/services.py` | Created | Twilio SMS service |
| `config/settings/base.py` | Updated | Added token_blacklist app, Swagger JWT auth |
| `config/settings/development.py` | Updated | Disabled Sentry, removed debug_toolbar |
| `.env` | Updated | Cleared placeholder SENTRY_DSN |

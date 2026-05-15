# Sprint 2 — Postman Testing Guide

Step-by-step guide to test all Auth API endpoints in Postman.

---

## Prerequisites

- Docker running: `docker compose up -d`
- Health check passes: `http://localhost:8000/api/v1/health/`
- `.env` has `DEV_FIXED_OTP=123456` (OTP is always 123456 in dev — no Twilio needed)

---

## Step 1 — One-Time Postman Setup

### Create Environment

1. Open Postman
2. Click **Environments** (left sidebar) → **+**
3. Name it: `NearKart Local`
4. Add these variables:

| Variable | Initial Value | Current Value |
|----------|--------------|---------------|
| `base_url` | `http://localhost:8000/api/v1` | `http://localhost:8000/api/v1` |
| `access_token` | *(leave empty)* | *(leave empty)* |
| `refresh_token` | *(leave empty)* | *(leave empty)* |

5. Click **Save**
6. Select `NearKart Local` from the **environment dropdown** (top-right corner of Postman)

### Create Collection

1. Click **Collections** → **+** → **Blank Collection**
2. Name it: `NearKart Auth`

---

## Step 2 — Test Flow (Run in This Order)

### REQUEST 1 — Send OTP

**Purpose:** Trigger OTP for a phone number. Creates the user if first time.

```
Method : POST
URL    : {{base_url}}/auth/otp/send/
```

**Headers tab:**
```
Content-Type : application/json
```

**Body tab → raw → JSON:**
```json
{
    "phone_number": "+919876543210"
}
```

**Expected Response — 200 OK:**
```json
{
    "message": "OTP sent successfully"
}
```

> In dev, no SMS is sent. OTP is always `123456` (set by `DEV_FIXED_OTP` in `.env`).

---

### REQUEST 2 — Verify OTP (Login)

**Purpose:** Submit the OTP → get JWT access + refresh tokens.

```
Method : POST
URL    : {{base_url}}/auth/otp/verify/
```

**Body tab → raw → JSON:**
```json
{
    "phone_number": "+919876543210",
    "otp": "123456"
}
```

**Tests tab (paste this to auto-save tokens):**
```javascript
const r = pm.response.json();
if (r.access) {
    pm.environment.set("access_token", r.access);
    pm.environment.set("refresh_token", r.refresh);
    console.log("Tokens saved to environment");
}
```

**Expected Response — 200 OK:**
```json
{
    "message": "Login successful",
    "user": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "phone_number": "+919876543210",
        "role": "customer",
        "full_name": "",
        "email": "",
        "created_at": "2024-01-01T00:00:00Z"
    },
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

> After this runs, `{{access_token}}` and `{{refresh_token}}` are auto-filled in the environment.

---

### REQUEST 3 — Get My Profile

**Purpose:** Fetch the logged-in user's profile using the access token.

```
Method : GET
URL    : {{base_url}}/auth/me/
```

**Authorization tab:**
```
Type  : Bearer Token
Token : {{access_token}}
```

*(No body needed)*

**Expected Response — 200 OK:**
```json
{
    "id": "550e8400-...",
    "phone_number": "+919876543210",
    "role": "customer",
    "full_name": "",
    "email": "",
    "created_at": "2024-01-01T00:00:00Z"
}
```

---

### REQUEST 4 — Update Profile

**Purpose:** Update the user's name and email.

```
Method : PATCH
URL    : {{base_url}}/auth/me/
```

**Authorization tab:**
```
Type  : Bearer Token
Token : {{access_token}}
```

**Body tab → raw → JSON:**
```json
{
    "full_name": "Rahul Kumar",
    "email": "rahul@example.com"
}
```

**Expected Response — 200 OK:**
```json
{
    "id": "550e8400-...",
    "phone_number": "+919876543210",
    "role": "customer",
    "full_name": "Rahul Kumar",
    "email": "rahul@example.com",
    "created_at": "2024-01-01T00:00:00Z"
}
```

---

### REQUEST 5 — Update Location

**Purpose:** Set the user's GPS coordinates (used for hyperlocal feed).

```
Method : PUT
URL    : {{base_url}}/auth/me/location/
```

**Authorization tab:**
```
Type  : Bearer Token
Token : {{access_token}}
```

**Body tab → raw → JSON:**
```json
{
    "latitude": 13.0827,
    "longitude": 80.2707
}
```

*(These are Chennai, Tamil Nadu coordinates)*

**Expected Response — 200 OK:**
```json
{
    "message": "Location updated"
}
```

---

### REQUEST 6 — Refresh Token

**Purpose:** Get a new access token when the old one expires (1 hour lifetime).

```
Method : POST
URL    : {{base_url}}/auth/token/refresh/
```

**Body tab → raw → JSON:**
```json
{
    "refresh": "{{refresh_token}}"
}
```

**Tests tab (update saved access token):**
```javascript
const r = pm.response.json();
if (r.access) {
    pm.environment.set("access_token", r.access);
    console.log("Access token refreshed");
}
```

**Expected Response — 200 OK:**
```json
{
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

### REQUEST 7 — Logout

**Purpose:** Blacklist the refresh token so it can never be reused.

```
Method : POST
URL    : {{base_url}}/auth/logout/
```

**Authorization tab:**
```
Type  : Bearer Token
Token : {{access_token}}
```

**Body tab → raw → JSON:**
```json
{
    "refresh": "{{refresh_token}}"
}
```

**Expected Response — 200 OK:**
```json
{
    "message": "Logged out successfully"
}
```

---

## Step 3 — Error Case Tests

These test that the API rejects bad input correctly.

### ERROR 1 — Wrong phone format

```
POST {{base_url}}/auth/otp/send/
Body: { "phone_number": "9876543210" }
```
Expected: **400** — missing `+91` prefix

---

### ERROR 2 — Non-Indian number

```
POST {{base_url}}/auth/otp/send/
Body: { "phone_number": "+1234567890" }
```
Expected: **400** — must start with `+91`

---

### ERROR 3 — Wrong OTP

```
POST {{base_url}}/auth/otp/verify/
Body: { "phone_number": "+919876543210", "otp": "000000" }
```
Expected: **400**
```json
{
    "error": "otp_invalid",
    "message": "Invalid OTP. 4 attempt(s) remaining."
}
```

---

### ERROR 4 — No auth token

```
GET {{base_url}}/auth/me/
(No Authorization header)
```
Expected: **401 Unauthorized**

---

### ERROR 5 — Fake token

```
GET {{base_url}}/auth/me/
Authorization: Bearer faketoken123
```
Expected: **401 Unauthorized**

---

### ERROR 6 — Use refresh token after logout

After Request 7 (logout), try Request 6 (refresh) again.

Expected: **401** — token is blacklisted

---

### ERROR 7 — Invalid location coordinates

```
PUT {{base_url}}/auth/me/location/
Body: { "latitude": 200, "longitude": 80.2707 }
```
Expected: **400** — latitude must be between -90 and 90

---

## Step 4 — Admin Panel Verification

1. Open: `http://localhost:8000/admin/`
2. Log in (create superuser first if needed):
   ```bash
   docker compose run --rm django /venv/bin/python manage.py createsuperuser
   ```
3. Check:
   - **Auth app > Users** — your test phone number appears
   - **Auth app > Otp tokens** — shows `is_used = True` after successful verify
   - User's `registered_location` is set after location update test

---

## Quick Reference — All Endpoints

| # | Method | URL | Auth | Purpose |
|---|--------|-----|------|---------|
| 1 | POST | `/auth/otp/send/` | No | Send OTP |
| 2 | POST | `/auth/otp/verify/` | No | Verify OTP → get tokens |
| 3 | GET | `/auth/me/` | Bearer | Get profile |
| 4 | PATCH | `/auth/me/` | Bearer | Update name/email |
| 5 | PUT | `/auth/me/location/` | Bearer | Update GPS location |
| 6 | POST | `/auth/token/refresh/` | No | Refresh access token |
| 7 | POST | `/auth/logout/` | Bearer | Logout + blacklist |

Base URL: `http://localhost:8000/api/v1`

Swagger UI (auto-generated docs): `http://localhost:8000/api/docs/`

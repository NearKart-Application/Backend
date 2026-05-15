# Sprint 2 — API Test Flow

Step-by-step order to test all Auth endpoints.
Base URL: `http://localhost:8000/api/v1`

---

## Prerequisites

- Docker running: `docker compose up -d`
- Health check OK: `http://localhost:8000/api/v1/health/`
- OTP in dev is always: `123456` (set by `DEV_FIXED_OTP` in `.env`)

---

## Flow 1 — Happy Path (Full Login to Logout)

Run these in order. Each step depends on the previous one.

---

### STEP 1 — Send OTP

```
Method  : POST
URL     : /api/v1/auth/otp/send/
Auth    : None
```

Request Body:
```json
{
    "phone_number": "+919876543210"
}
```

Expected Response — 200 OK:
```json
{
    "message": "OTP sent successfully"
}
```

What happens internally:
- User is created in DB if first time
- OTP is generated (always 123456 in dev)
- OTP hash (SHA256) is saved in `auth_otp_tokens` table
- Celery task queues SMS (Twilio not needed in dev)

---

### STEP 2 — Verify OTP → Get Tokens

```
Method  : POST
URL     : /api/v1/auth/otp/verify/
Auth    : None
```

Request Body:
```json
{
    "phone_number": "+919876543210",
    "otp": "123456"
}
```

Expected Response — 200 OK:
```json
{
    "message": "Login successful",
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
        "id": "6d8890be-c503-4b0b-994f-b4e6aaef557b",
        "phone_number": "+919876543210",
        "role": "customer",
        "full_name": "",
        "email": "",
        "created_at": "2024-01-01T00:00:00Z"
    }
}
```

**Save the `access` and `refresh` tokens — you need them for the next steps.**

---

### STEP 3 — Get My Profile

```
Method  : GET
URL     : /api/v1/auth/me/
Auth    : Bearer <access token from Step 2>
```

No request body needed.

Expected Response — 200 OK:
```json
{
    "id": "6d8890be-...",
    "phone_number": "+919876543210",
    "role": "customer",
    "full_name": "",
    "email": "",
    "created_at": "2024-01-01T00:00:00Z"
}
```

---

### STEP 4 — Update Profile

```
Method  : PATCH
URL     : /api/v1/auth/me/
Auth    : Bearer <access token>
```

Request Body:
```json
{
    "full_name": "Rahul Kumar",
    "email": "rahul@example.com"
}
```

Expected Response — 200 OK:
```json
{
    "id": "6d8890be-...",
    "phone_number": "+919876543210",
    "role": "customer",
    "full_name": "Rahul Kumar",
    "email": "rahul@example.com",
    "created_at": "2024-01-01T00:00:00Z"
}
```

Note: `phone_number` and `role` cannot be changed via this endpoint.

---

### STEP 5 — Update Location

```
Method  : PUT
URL     : /api/v1/auth/me/location/
Auth    : Bearer <access token>
```

Request Body (Chennai coordinates):
```json
{
    "latitude": 13.0827,
    "longitude": 80.2707
}
```

Expected Response — 200 OK:
```json
{
    "message": "Location updated"
}
```

Note: This saves a PostGIS Point to the `registered_location` column.
Used later by the hyperlocal feed to show nearby stores.

---

### STEP 6 — Refresh Token

```
Method  : POST
URL     : /api/v1/auth/token/refresh/
Auth    : None
```

Request Body:
```json
{
    "refresh": "<your refresh token from Step 2>"
}
```

Expected Response — 200 OK:
```json
{
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

Use this when the access token expires (after 1 hour).

---

### STEP 7 — Logout

```
Method  : POST
URL     : /api/v1/auth/logout/
Auth    : Bearer <access token>
```

Request Body:
```json
{
    "refresh": "<your refresh token>"
}
```

Expected Response — 200 OK:
```json
{
    "message": "Logged out successfully"
}
```

After this the refresh token is permanently blacklisted.

---

### STEP 8 — Try Refresh After Logout (should fail)

```
Method  : POST
URL     : /api/v1/auth/token/refresh/
Auth    : None
```

Request Body (same refresh token as Step 7):
```json
{
    "refresh": "<same refresh token>"
}
```

Expected Response — 401 Unauthorized:
```json
{
    "detail": "Token is blacklisted"
}
```

---

## Flow 2 — Validation / Error Cases

### Wrong phone format — 400

```json
POST /api/v1/auth/otp/send/
{ "phone_number": "9876543210" }
```
Response: `400` — missing `+91` prefix

---

### Non-Indian number — 400

```json
POST /api/v1/auth/otp/send/
{ "phone_number": "+1234567890" }
```
Response: `400` — must be `+91XXXXXXXXXX`

---

### Wrong OTP — 400

```json
POST /api/v1/auth/otp/verify/
{ "phone_number": "+919876543210", "otp": "000000" }
```
Response:
```json
{ "error": "otp_invalid", "message": "Invalid OTP. 4 attempt(s) remaining." }
```

---

### No token on protected endpoint — 401

```
GET /api/v1/auth/me/
(no Authorization header)
```
Response: `401 Unauthorized`

---

### Fake token — 401

```
GET /api/v1/auth/me/
Authorization: Bearer faketoken123
```
Response: `401 Unauthorized`

---

### Invalid location coordinates — 400

```json
PUT /api/v1/auth/me/location/
{ "latitude": 200, "longitude": 80.2707 }
```
Response: `400` — latitude must be -90 to 90

---

## Postman Setup

1. Create Environment: `NearKart Local`
2. Add variable: `base_url` = `http://localhost:8000/api/v1`
3. Add variable: `access_token` = *(empty)*
4. Add variable: `refresh_token` = *(empty)*
5. In Step 2 Tests tab, add:
```javascript
const r = pm.response.json();
pm.environment.set("access_token", r.access);
pm.environment.set("refresh_token", r.refresh);
```

## Swagger UI Setup

1. Open: `http://localhost:8000/api/docs/`
2. Run Step 1 and Step 2 using Try it out
3. Copy `access` token from Step 2 response
4. Click **Authorize** (top right) → enter: `Bearer <token>`
5. All protected endpoints now work with Try it out

# Sprint 2 — Auth Module

**Goal:** OTP login end-to-end. JWT tokens issued. User roles working.
**Status:** Done
**Time estimate:** ~14 hours

---

## What Was Built

### Files Created

| File | Purpose |
|------|---------|
| `apps/auth_app/models.py` | User, OTPToken, DeviceToken models |
| `apps/auth_app/services.py` | OTPService (generate/verify), JWTService (issue tokens) |
| `apps/auth_app/serializers.py` | Request/response validation |
| `apps/auth_app/views.py` | 6 API endpoints |
| `apps/auth_app/urls.py` | URL routing for auth |
| `apps/auth_app/tasks.py` | Celery task to send SMS in background |
| `apps/auth_app/admin.py` | Django admin for User/OTP/Device |
| `apps/notifications/services.py` | SMSService via Twilio |
| `core/middleware.py` | JWT auth for WebSocket connections |

---

## Database Models

### User
```
id              UUID (primary key)
phone_number    String, unique (+91XXXXXXXXXX format)
role            Enum: customer / vendor / admin
full_name       String (optional)
email           String (optional)
registered_location  PointField (lat/lng, set on first login)
is_active       Boolean
created_at      DateTime
updated_at      DateTime
```

### OTPToken
```
user            ForeignKey → User
otp_hash        SHA256 hash of the 6-digit OTP
expires_at      5 minutes after creation
is_used         Boolean (true after successful verify)
attempts        Counter (locked after 5 wrong attempts)
```

### DeviceToken
```
user            ForeignKey → User
fcm_token       Firebase push token
device_type     android / ios
is_active       Boolean
```

---

## API Endpoints

Base URL: `http://localhost:8000/api/v1/auth/`

| Method | Endpoint | Auth Required | Purpose |
|--------|----------|--------------|---------|
| POST | `otp/send/` | No | Send OTP to phone number |
| POST | `otp/verify/` | No | Verify OTP → get tokens |
| POST | `token/refresh/` | No | Get new access token |
| GET | `me/` | Yes (Bearer) | Get current user profile |
| PATCH | `me/` | Yes (Bearer) | Update name/email |
| PUT | `me/location/` | Yes (Bearer) | Update user location |
| POST | `logout/` | Yes (Bearer) | Logout + blacklist token |

---

## How OTP Login Works (Flow)

```
User enters phone number
        │
        ▼
POST /otp/send/
        │
        ├── Creates User if not exists
        ├── Generates random 6-digit OTP
        ├── Stores SHA256(OTP) in OTPToken table
        └── Queues Celery task → sends SMS via Twilio
                │
                ▼
        User receives SMS with OTP
                │
                ▼
        POST /otp/verify/
                │
                ├── Looks up latest OTPToken for phone
                ├── Compares SHA256(input) with stored hash
                ├── Checks: not expired (5min), not used, attempts < 5
                └── On success → issues JWT access + refresh tokens
                                │
                                ▼
                        User is logged in
```

---

## JWT Token Details

```
Access Token:
  - Expires in: 1 hour
  - Contains: user_id, role, phone_number
  - Use in: Authorization: Bearer <token>

Refresh Token:
  - Expires in: 30 days
  - Use to get new access token via /token/refresh/
  - Blacklisted on logout
```

---

## Development Note — DEV_FIXED_OTP

In your `.env` file:
```
DEV_FIXED_OTP=123456
```

This means during development, the OTP is always `123456`.
You do NOT need a real Twilio account to test locally.

Remove or empty this in production.

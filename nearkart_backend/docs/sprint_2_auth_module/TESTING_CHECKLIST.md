# Sprint 2 — Testing Checklist

Complete all tests below before marking Sprint 2 as done.
Mark each test with [x] when it passes.

---

## Requirements Before Testing

- [ ] Docker is running (`docker compose up --build`)
- [ ] `.env` file has `DEV_FIXED_OTP=123456`
- [ ] Postman is open
- [ ] Swagger UI loads at http://localhost:8000/api/docs/

---

## METHOD A — Fast Tests (No Docker, Seconds)

Run from terminal with venv activated:

```bash
source venv/bin/activate
pytest apps/auth_app/tests/ -v
```

Expected: all tests pass, no errors.

---

## METHOD B — Manual API Tests in Postman

### Setup (do once)

1. Open Postman
2. Create Environment named `NearKart Local`
3. Add variable: `base_url` = `http://localhost:8000/api/v1`
4. Add variable: `access_token` = (leave empty)
5. Add variable: `refresh_token` = (leave empty)
6. Select `NearKart Local` from environment dropdown (top right)

---

### TEST 1 — Send OTP ✅

```
Method : POST
URL    : {{base_url}}/auth/otp/send/
Body   : raw → JSON
```

```json
{
  "phone_number": "+919876543210"
}
```

**Expected Result:**

- Status: `200 OK`
- Body:

```json
{
  "message": "OTP sent successfully"
}
```

- [ ] Status is 200
- [ ] Message says "OTP sent successfully"

---

### TEST 2 — Send OTP with wrong phone format ❌

```
Method : POST
URL    : {{base_url}}/auth/otp/send/
Body   : raw → JSON
```

```json
{
  "phone_number": "9876543210"
}
```

**Expected Result:**

- Status: `400 Bad Request`
- Body contains validation error about phone format

- [ ] Status is 400
- [ ] Error message mentions phone number format

---

### TEST 3 — Send OTP with missing +91 ❌

```json
{
  "phone_number": "+1234567890"
}
```

**Expected Result:**

- Status: `400 Bad Request`

- [ ] Status is 400

---

### TEST 4 — Verify OTP (correct) ✅

```
Method : POST
URL    : {{base_url}}/auth/otp/verify/
Body   : raw → JSON
```

```json
{
  "phone_number": "+919876543210",
  "otp": "123456"
}
```

Add this to **Tests tab** in Postman to auto-save tokens:

```javascript
const r = pm.response.json();
pm.environment.set("access_token", r.access);
pm.environment.set("refresh_token", r.refresh);
```

**Expected Result:**

- Status: `200 OK`
- Body:

```json
{
  "message": "Login successful",
  "user": {
    "id": "...",
    "phone_number": "+919876543210",
    "role": "customer",
    "full_name": "",
    "email": "",
    "created_at": "..."
  },
  "access": "eyJ...",
  "refresh": "eyJ..."
}
```

- [ ] Status is 200
- [ ] `access` token present
- [ ] `refresh` token present
- [ ] `user.phone_number` matches what you sent
- [ ] `user.role` is "customer"
- [ ] Tokens saved in Postman environment

---

### TEST 5 — Verify OTP (wrong OTP) ❌

```
Method : POST
URL    : {{base_url}}/auth/otp/verify/
Body   : raw → JSON
```

```json
{
  "phone_number": "+919876543210",
  "otp": "000000"
}
```

**Expected Result:**

- Status: `400 Bad Request`
- Body:

```json
{
  "error": "otp_invalid",
  "message": "Invalid OTP. 4 attempt(s) remaining."
}
```

- [ ] Status is 400
- [ ] Error message shows remaining attempts

---

### TEST 6 — Get Current User (with token) ✅

```
Method        : GET
URL           : {{base_url}}/auth/me/
Authorization : Bearer Token → Token: {{access_token}}
```

**Expected Result:**

- Status: `200 OK`
- Body: user profile with phone_number, role etc.

- [ ] Status is 200
- [ ] Returns correct user data

---

### TEST 7 — Get Current User (without token) ❌

```
Method : GET
URL    : {{base_url}}/auth/me/
(No Authorization header)
```

**Expected Result:**

- Status: `401 Unauthorized`

```json
{
  "error": "authentication_failed",
  "message": "Authentication credentials were not provided.",
  "code": "NOT_AUTHENTICATED",
  "details": {}
}
```

- [ ] Status is 401
- [ ] Error format matches exactly

---

### TEST 8 — Get Current User (expired/fake token) ❌

```
Method        : GET
URL           : {{base_url}}/auth/me/
Authorization : Bearer Token → Token: faketoken123
```

**Expected Result:**

- Status: `401 Unauthorized`

- [ ] Status is 401

---

### TEST 9 — Update Profile ✅

```
Method        : PATCH
URL           : {{base_url}}/auth/me/
Authorization : Bearer Token → {{access_token}}
Body          : raw → JSON
```

```json
{
  "full_name": "Test User",
  "email": "test@example.com"
}
```

**Expected Result:**

- Status: `200 OK`
- Body: user object with updated full_name and email

- [ ] Status is 200
- [ ] `full_name` updated to "Test User"
- [ ] `email` updated

---

### TEST 10 — Update Location ✅

```
Method        : PUT
URL           : {{base_url}}/auth/me/location/
Authorization : Bearer Token → {{access_token}}
Body          : raw → JSON
```

```json
{
  "latitude": 13.0827,
  "longitude": 80.2707
}
```

_(These are Chennai coordinates)_

**Expected Result:**

- Status: `200 OK`

```json
{
  "message": "Location updated"
}
```

- [ ] Status is 200
- [ ] Message says "Location updated"

---

### TEST 11 — Update Location with invalid coordinates ❌

```json
{
  "latitude": 200,
  "longitude": 80.2707
}
```

**Expected Result:**

- Status: `400 Bad Request`
- Validation error about latitude range

- [ ] Status is 400

---

### TEST 12 — Refresh Token ✅

```
Method : POST
URL    : {{base_url}}/auth/token/refresh/
Body   : raw → JSON
```

```json
{
  "refresh": "{{refresh_token}}"
}
```

**Expected Result:**

- Status: `200 OK`

```json
{
  "access": "eyJ..."
}
```

- [ ] Status is 200
- [ ] New `access` token returned

---

### TEST 13 — Logout ✅

```
Method        : POST
URL           : {{base_url}}/auth/logout/
Authorization : Bearer Token → {{access_token}}
Body          : raw → JSON
```

```json
{
  "refresh": "{{refresh_token}}"
}
```

**Expected Result:**

- Status: `200 OK`

```json
{
  "message": "Logged out successfully"
}
```

- [ ] Status is 200

---

### TEST 14 — Use token after logout ❌

After logging out, try to use the old refresh token again:

```
Method : POST
URL    : {{base_url}}/auth/token/refresh/
Body:
```

```json
{
  "refresh": "{{refresh_token}}"
}
```

**Expected Result:**

- Status: `401 Unauthorized`
- Token is blacklisted

- [ ] Status is 401

---

## METHOD C — Django Admin Tests

1. Open http://localhost:8000/admin/
2. Login with superuser credentials

### Admin Checklist

- [ ] Can see **Users** list with the phone number you tested
- [ ] Can see **Otp tokens** showing is_used = True (after successful verify)
- [ ] User `registered_location` updated after TEST 10
- [ ] Can create a new user manually from admin
- [ ] Can change user role from customer to vendor

---

## All Tests Summary

| #   | Test                    | Type       | Expected     |
| --- | ----------------------- | ---------- | ------------ |
| 1   | Send OTP valid phone    | Happy path | 200          |
| 2   | Send OTP no +91         | Validation | 400          |
| 3   | Send OTP wrong country  | Validation | 400          |
| 4   | Verify OTP correct      | Happy path | 200 + tokens |
| 5   | Verify OTP wrong        | Error      | 400          |
| 6   | Get /me/ with token     | Happy path | 200          |
| 7   | Get /me/ no token       | Auth error | 401          |
| 8   | Get /me/ fake token     | Auth error | 401          |
| 9   | Update profile          | Happy path | 200          |
| 10  | Update location valid   | Happy path | 200          |
| 11  | Update location invalid | Validation | 400          |
| 12  | Refresh token           | Happy path | 200          |
| 13  | Logout                  | Happy path | 200          |
| 14  | Use token after logout  | Auth error | 401          |

**Total: 14 tests — 8 happy path, 6 error cases**

---

## Sprint 2 Sign-off

- [ ] All 14 Postman tests pass
- [ ] Django Admin shows correct data
- [ ] `make test` (pytest) passes without Docker
- [ ] No errors in Docker logs (`docker compose logs django`)

**Mark Sprint 2 complete when all boxes above are checked.**

Test Flow (run in order)

┌──────┬────────┬──────────────────────────────────┬────────────────────────────────────────────────────┐
│ Step │ Method │ URL │ Body │
├──────┼────────┼──────────────────────────────────┼────────────────────────────────────────────────────┤
│ 1 │ POST │ {{base_url}}/auth/otp/send/ │ {"phone_number": "+919876543210"} │
├──────┼────────┼──────────────────────────────────┼────────────────────────────────────────────────────┤
│ 2 │ POST │ {{base_url}}/auth/otp/verify/ │ {"phone_number": "+919876543210", "otp": "123456"} │
├──────┼────────┼──────────────────────────────────┼────────────────────────────────────────────────────┤
│ 3 │ GET │ {{base_url}}/auth/me/ │ — (Bearer {{access_token}}) │
├──────┼────────┼──────────────────────────────────┼────────────────────────────────────────────────────┤
│ 4 │ PATCH │ {{base_url}}/auth/me/ │ {"full_name": "Test User"} │
├──────┼────────┼──────────────────────────────────┼────────────────────────────────────────────────────┤
│ 5 │ PUT │ {{base_url}}/auth/me/location/ │ {"latitude": 13.0827, "longitude": 80.2707} │
├──────┼────────┼──────────────────────────────────┼────────────────────────────────────────────────────┤
│ 6 │ POST │ {{base_url}}/auth/token/refresh/ │ {"refresh": "{{refresh_token}}"} │
├──────┼────────┼──────────────────────────────────┼────────────────────────────────────────────────────┤
│ 7 │ POST │ {{base_url}}/auth/logout/ │ {"refresh": "{{refresh_token}}"} │
└──────┴────────┴──────────────────────────────────┴────────────────────────────────────────────────────┘

# Request OTP

curl -X POST http://localhost:8000/api/v1/auth/otp/request/ \
 -H "Content-Type: application/json" \
 -d '{"phone_number": "+919876543210"}'

# Verify OTP (use DEV_FIXED_OTP=123456)

curl -X POST http://localhost:8000/api/v1/auth/otp/verify/ \
 -H "Content-Type: application/json" \
 -d '{"phone_number": "+919876543210", "otp": "123456"}'

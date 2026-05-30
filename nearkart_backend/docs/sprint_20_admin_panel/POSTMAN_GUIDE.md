# Sprint 20 — Postman Guide

## Environment Variables

| Variable | Value |
|----------|-------|
| `base_url` | `http://localhost:8000/api/v1` |
| `admin_token` | _(paste Bearer token from admin login)_ |
| `master_admin_token` | _(paste Bearer token from master_admin login)_ |
| `test_user_id` | _(UUID of a test customer)_ |
| `test_store_id` | _(UUID of a test store)_ |
| `test_video_id` | _(UUID of a video in that store)_ |

Add header to all admin requests:
```
Authorization: Bearer {{admin_token}}
```

---

## 1. Get Admin Token

**POST** `{{base_url}}/auth/otp/request/`
```json
{ "phone": "+919000000011" }
```

**POST** `{{base_url}}/auth/otp/verify/`
```json
{ "phone": "+919000000011", "otp": "111011" }
```
→ Copy `access` token → save as `admin_token`

---

## 2. Platform Stats

**GET** `{{base_url}}/admin/platform/stats/`

Expected response includes:
```json
{
  "users": { "total": 12, "vendors": 4 },
  "stores": { "total": 4 },
  "products": { "active": 24 },
  "pending_website_requests": 2
}
```

---

## 3. List Stores (with owner NS code)

**GET** `{{base_url}}/admin/stores/`

Each store object includes:
```json
{
  "id": "...",
  "name": "Sneha's Fashion House",
  "owner_profile_id": "NSB-SN-HY-J4X2",
  "is_active": true,
  "product_count": 8,
  "video_count": 3
}
```

---

## 4. Get Store Videos

**GET** `{{base_url}}/admin/stores/{{test_store_id}}/videos/`

```json
{
  "videos": [
    {
      "id": "...",
      "title": "Summer collection",
      "thumbnail_url": "https://...",
      "status": "active",
      "created_at": "2026-05-28T10:00:00Z"
    }
  ]
}
```

---

## 5. Delete a Video

**DELETE** `{{base_url}}/admin/videos/{{test_video_id}}/`

→ 204 No Content
→ Check activity log — should show `delete_video` entry

---

## 6. List Users (with suspension info)

**GET** `{{base_url}}/admin/users/`

Each user includes:
```json
{
  "id": "...",
  "full_name": "Arjun Kumar",
  "profile_id": "NSC-AR-KP-J4X2",
  "role": "customer",
  "is_active": true,
  "is_suspended": false,
  "suspension_reason": ""
}
```

---

## 7. Search Users by NS Code

**GET** `{{base_url}}/admin/users/?search=NSC-AR`

→ Returns users whose profile_id contains `NSC-AR`

---

## 8. Suspend a User

**POST** `{{base_url}}/admin/users/{{test_user_id}}/suspend/`
```json
{
  "is_suspended": true,
  "reason": "Suspicious activity detected during QA testing"
}
```

→ 200:
```json
{ "success": true, "is_suspended": true }
```

---

## 9. Verify Suspension at OTP (403 Test)

**POST** `{{base_url}}/auth/otp/verify/`
```json
{ "phone": "+91XXXXXXXXXX", "otp": "XXXXXX" }
```

→ Expected 403:
```json
{
  "error": "account_suspended",
  "message": "Suspicious activity detected during QA testing"
}
```

---

## 10. Unsuspend a User

**POST** `{{base_url}}/admin/users/{{test_user_id}}/suspend/`
```json
{ "is_suspended": false }
```

→ 200:
```json
{ "success": true, "is_suspended": false }
```

---

## 11. Create a User from Admin

**POST** `{{base_url}}/admin/users/create/`
```json
{
  "phone": "+919876543210",
  "full_name": "New Test User",
  "role": "customer"
}
```

→ 201:
```json
{
  "id": "...",
  "phone": "+919876543210",
  "full_name": "New Test User",
  "profile_id": "NSC-NT-XX-K3P1",
  "role": "customer"
}
```

---

## 12. Activity Log

**GET** `{{base_url}}/admin/activity-log/`

```json
{
  "results": [
    {
      "id": "...",
      "admin": { "id": "...", "name": "Admin User" },
      "action": "delete_video",
      "target_type": "video",
      "target_label": "Summer collection",
      "detail": "store: Sneha's Fashion House",
      "created_at": "2026-05-30T09:15:00Z"
    }
  ]
}
```

---

## 13. NS Code Regeneration via Location Update

**PUT** `{{base_url}}/auth/location/`

Headers: `Authorization: Bearer {{customer_token}}`
```json
{
  "lat": 17.385,
  "lng": 78.4867,
  "name": "Kukatpally, Hyderabad",
  "city": "Hyderabad"
}
```

→ If first location set AND profile_id area was `XX` → profile_id updates to `NSC-NN-HY-RRRR`
→ Second call with same city → profile_id unchanged

---

## Common Errors

| Status | Meaning |
|--------|---------|
| 403 (on admin endpoint) | Token is not admin/master_admin role |
| 403 (on OTP verify) | User is suspended — read `message` field |
| 404 | Video or user UUID not found |
| 400 | Validation error (e.g., duplicate phone on create) |

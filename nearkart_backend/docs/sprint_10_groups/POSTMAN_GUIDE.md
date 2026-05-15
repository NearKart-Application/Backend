# Sprint 10 — Postman Guide

## Environment Variables

| Variable | Value | Set by |
|----------|-------|--------|
| `base_url` | `http://localhost:8000/api/v1` | Manual |
| `customer_token` | (empty) | OTP verify script |
| `vendor_token` | (empty) | OTP verify script |
| `friend_token` | (empty) | OTP verify for a 2nd user |
| `group_id` | (empty) | Create Group script below |
| `sp_id` | (empty) | Share Product script below |

## Auto-Save Scripts

**Create Group — Tests tab:**
```js
const r = pm.response.json();
if (r.id) {
    pm.environment.set("group_id", r.id);
    console.log("group_id saved:", r.id);
}
```

**Share Product — Tests tab:**
```js
const r = pm.response.json();
if (r.id) {
    pm.environment.set("sp_id", r.id);
    console.log("sp_id saved:", r.id);
}
```

---

## Collection: Sprint 10 — Groups

### 1. Create Customer Group

- **Method:** POST
- **URL:** `{{base_url}}/groups/`
- **Auth:** Bearer `{{customer_token}}`
- **Body:**
```json
{
  "name": "Weekend Shopping",
  "group_type": "customer"
}
```
- **Expected:** 201 — group object with `member_count: 1`

---

### 2. Create Vendor Group

- **Method:** POST
- **URL:** `{{base_url}}/groups/`
- **Auth:** Bearer `{{vendor_token}}`
- **Body:**
```json
{
  "name": "VIP Followers Deal",
  "group_type": "vendor"
}
```
- **Expected:** 201 — group object with `store_name` populated

---

### 3. List My Groups

- **Method:** GET
- **URL:** `{{base_url}}/groups/`
- **Auth:** Bearer `{{customer_token}}`
- **Expected:** Array of groups

---

### 4. Group Detail

- **Method:** GET
- **URL:** `{{base_url}}/groups/{{group_id}}/`
- **Auth:** Bearer `{{customer_token}}`
- **Expected:** Group object with `members` array

---

### 5. Add Member

- **Method:** POST
- **URL:** `{{base_url}}/groups/{{group_id}}/members/add/`
- **Auth:** Bearer `{{customer_token}}`
- **Body:**
```json
{
  "phone_number": "+919876543210"
}
```
- **Expected:** 201 — member added message

---

### 6. Share Product

- **Method:** POST
- **URL:** `{{base_url}}/groups/{{group_id}}/products/`
- **Auth:** Bearer `{{customer_token}}`
- **Body:**
```json
{
  "product_id": "{{product_id}}",
  "note": "This looks perfect for the wedding!"
}
```
- **Expected:** 201 — shared product object with `is_finalized: false`

---

### 7. List Shared Products

- **Method:** GET
- **URL:** `{{base_url}}/groups/{{group_id}}/products/`
- **Auth:** Bearer `{{customer_token}}`
- **Expected:** Array of shared products

---

### 8. Finalize Product

- **Method:** POST
- **URL:** `{{base_url}}/groups/{{group_id}}/products/{{sp_id}}/finalize/`
- **Auth:** Bearer `{{customer_token}}`
- **Body:** (empty)
- **Expected:** 200 — `is_finalized: true`, `finalized_by_name` populated

---

### 9. Leave Group (as friend)

- **Method:** POST
- **URL:** `{{base_url}}/groups/{{group_id}}/leave/`
- **Auth:** Bearer `{{friend_token}}`
- **Expected:** 200 — You have left the group

---

### 10. Delete Group

- **Method:** DELETE
- **URL:** `{{base_url}}/groups/{{group_id}}/`
- **Auth:** Bearer `{{customer_token}}`
- **Expected:** 200 — Group deleted

---

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| 400 — Only vendors can create vendor groups | customer trying to create vendor group | Use vendor_token |
| 400 — Create a store first | vendor has no store | Create store in Sprint 3 first |
| 403 — User does not follow this store | Adding non-follower to vendor group | User must follow the store first |
| 403 — Only group admin can add members | Non-admin trying to add | Use admin/creator token |
| 400 — User is already a member | Duplicate add | Check current members |
| 400 — Group creator cannot leave | Creator trying to leave | Delete the group instead |
| 400 — Product is already finalized | Finalizing twice | Check is_finalized field |
| 404 — No active user found | Wrong phone number | Verify phone is a NearKart user |

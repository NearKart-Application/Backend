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
| `friend_profile_id` | (empty) | Copy from friend's GET /auth/me/ |

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

### 0. Get My Profile ID

- **Method:** GET
- **URL:** `{{base_url}}/auth/me/`
- **Auth:** Bearer `{{friend_token}}`
- **Expected:** 200 — user object includes `profile_id` (e.g. `NK-A3X9K2`)
- **Action:** Copy the `profile_id` value → save as `friend_profile_id` env variable

---

### 1. Search User by Profile ID

- **Method:** GET
- **URL:** `{{base_url}}/auth/users/search/?profile_id={{friend_profile_id}}`
- **Auth:** Bearer `{{customer_token}}`
- **Expected:** 200 — `{ "id": "...", "profile_id": "NK-A3X9K2", "full_name": "..." }` (no phone)

---

### 2. Create Customer Group

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
- **Expected:** 201 — group object with `member_count: 1`, `created_by_profile_id`

---

### 3. Create Vendor Group

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

### 4. List My Groups

- **Method:** GET
- **URL:** `{{base_url}}/groups/`
- **Auth:** Bearer `{{customer_token}}`
- **Expected:** Array of groups

---

### 5. Group Detail

- **Method:** GET
- **URL:** `{{base_url}}/groups/{{group_id}}/`
- **Auth:** Bearer `{{customer_token}}`
- **Expected:** Group object with `members` array — each member shows `profile_id` + `full_name` (no phone)

---

### 6. Add Member (Customer Group — by Profile ID)

- **Method:** POST
- **URL:** `{{base_url}}/groups/{{group_id}}/members/add/`
- **Auth:** Bearer `{{customer_token}}`
- **Body:**
```json
{
  "profile_id": "{{friend_profile_id}}"
}
```
- **Expected:** 201 — member added

---

### 7. Eligible Members (Vendor Group only)

- **Method:** GET
- **URL:** `{{base_url}}/groups/{{group_id}}/eligible-members/`
- **Auth:** Bearer `{{vendor_token}}`
- **Expected:** Array of followers not yet in the group — each has `user_id`, `profile_id`, `full_name`

---

### 8. Add Member (Vendor Group — by User ID)

- **Method:** POST
- **URL:** `{{base_url}}/groups/{{group_id}}/members/add/`
- **Auth:** Bearer `{{vendor_token}}`
- **Body:**
```json
{
  "user_id": "{{user_id_from_eligible_members}}"
}
```
- **Expected:** 201 — member added

---

### 9. Make Admin

- **Method:** POST
- **URL:** `{{base_url}}/groups/{{group_id}}/members/{{friend_user_id}}/make-admin/`
- **Auth:** Bearer `{{customer_token}}`
- **Expected:** 200 — user is now an admin

---

### 10. Remove Admin

- **Method:** POST
- **URL:** `{{base_url}}/groups/{{group_id}}/members/{{friend_user_id}}/remove-admin/`
- **Auth:** Bearer `{{customer_token}}`
- **Expected:** 200 — user is no longer an admin

---

### 11. Share Product

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
- **Expected:** 201 — shared product with `is_finalized: false`, `shared_by_profile_id`

---

### 12. Share Product — External Link (should fail)

- **Method:** POST
- **URL:** `{{base_url}}/groups/{{group_id}}/products/`
- **Auth:** Bearer `{{customer_token}}`
- **Body:**
```json
{
  "product_id": "{{product_id}}",
  "note": "Check this out: http://youtube.com/xyz"
}
```
- **Expected:** 400 — External links are not allowed

---

### 13. List Shared Products

- **Method:** GET
- **URL:** `{{base_url}}/groups/{{group_id}}/products/`
- **Auth:** Bearer `{{customer_token}}`
- **Expected:** Array of shared products — finalized first

---

### 14. Finalize Product

- **Method:** POST
- **URL:** `{{base_url}}/groups/{{group_id}}/products/{{sp_id}}/finalize/`
- **Auth:** Bearer `{{customer_token}}`
- **Body:** (empty)
- **Expected:** 200 — `is_finalized: true`, `finalized_by_name` populated

---

### 15. Leave Group (as friend)

- **Method:** POST
- **URL:** `{{base_url}}/groups/{{group_id}}/leave/`
- **Auth:** Bearer `{{friend_token}}`
- **Expected:** 200 — You have left the group

---

### 16. Delete Group

- **Method:** DELETE
- **URL:** `{{base_url}}/groups/{{group_id}}/`
- **Auth:** Bearer `{{customer_token}}`
- **Expected:** 200 — Group deleted

---

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| 400 — Only vendors can create vendor groups | Customer trying to create vendor group | Use vendor_token |
| 400 — Create a store first | Vendor has no store | Create store in Sprint 3 first |
| 400 — Provide either profile_id or user_id | Empty add-member body | Add profile_id or user_id |
| 403 — User does not follow this store | Adding non-follower to vendor group | User must follow the store first |
| 403 — Only group admin can add members | Non-admin trying to add | Use admin/creator token |
| 400 — User is already a member | Duplicate add | Check current members list |
| 400 — Group creator cannot leave | Creator trying to leave | Delete the group instead |
| 400 — Cannot remove the group creator | Trying to remove creator | Cannot remove the creator |
| 400 — Product is already finalized | Finalizing twice | Check is_finalized field |
| 400 — External links are not allowed | Note contains external URL | Remove URL or use nearkart:// link |
| 404 — No user found with this Profile ID | Wrong profile_id | Check profile_id from /auth/me/ |

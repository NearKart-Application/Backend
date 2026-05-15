# Sprint 4 — Postman Guide

## Environment Variables (add to NearKart Local environment)

| Variable | Value | Set by |
|----------|-------|--------|
| `base_url` | `http://localhost:8000/api/v1` | Manual |
| `vendor_token` | (empty) | OTP verify script |
| `customer_token` | (empty) | OTP verify script |
| `video_id` | (empty) | Create video script |

---

## Collection: Sprint 4 — Videos

### 1. Request Upload URL
- **Method:** POST
- **URL:** `{{base_url}}/videos/request-upload/`
- **Auth:** Bearer `{{vendor_token}}`
- **Body (JSON):**
```json
{
  "title": "Summer Kurta Collection",
  "description": "Handwoven cotton kurtas for the season"
}
```
- **Tests tab (auto-save video_id):**
```javascript
const r = pm.response.json();
if (r.video_id) {
    pm.environment.set("video_id", r.video_id);
    pm.environment.set("upload_url", r.upload_url);
    console.log("video_id saved:", r.video_id);
}
```

---

### 2. Confirm Upload (triggers transcoding)
- **Method:** POST
- **URL:** `{{base_url}}/videos/{{video_id}}/confirm-upload/`
- **Auth:** Bearer `{{vendor_token}}`
- **Body (JSON):**
```json
{
  "duration_seconds": 45
}
```
- **Expected:** `{"status": "processing", ...}`
- **Note:** In dev mode, wait 2–3 seconds then check video detail — it will be `ready`.

---

### 3. Video Feed (Public)
- **Method:** GET
- **URL:** `{{base_url}}/videos/feed/`
- **Auth:** None
- **Params:**
  - `lat` = `13.0418`
  - `lng` = `80.2341`
  - `radius` = `10`
- **Expected:** Array of ready videos with `distance_km`

---

### 4. Video Detail (Public)
- **Method:** GET
- **URL:** `{{base_url}}/videos/{{video_id}}/`
- **Auth:** None (or add Bearer token to see `is_liked`)
- **Note:** `view_count` increments on every call

---

### 5. Like / Unlike Video (Toggle)
- **Method:** POST
- **URL:** `{{base_url}}/videos/{{video_id}}/like/`
- **Auth:** Bearer `{{customer_token}}`
- **Body:** None
- **Expected (1st call):** `{"liked": true, "message": "Liked."}`
- **Expected (2nd call):** `{"liked": false, "message": "Unliked."}`

---

### 6. Delete Video (Vendor Only)
- **Method:** DELETE
- **URL:** `{{base_url}}/videos/{{video_id}}/delete/`
- **Auth:** Bearer `{{vendor_token}}`
- **Body:** None
- **Expected:** `204 No Content`

---

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| 400 — Create a store first | Vendor has no store | Complete Sprint 3 store creation |
| 400 — Video is already in "ready" state | Called confirm-upload twice | Check status with GET /videos/<id>/ first |
| 400 — lat and lng are required | Missing feed params | Add ?lat=13.0&lng=80.2 to URL |
| 403 — Vendor access only | Customer token used on upload | Use vendor token |
| 404 — Video not found | Video is processing/failed/expired | Wait for transcoding or check status |

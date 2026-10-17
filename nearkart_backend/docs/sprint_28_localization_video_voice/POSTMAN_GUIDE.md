# Sprint 28 — Postman Guide

## Collection Setup

Add a new folder inside your existing Postman collection: **"28 — Localization · Product Demo Video · Voice OTP"**

Variables needed (should already be set from earlier sprints):

| Variable | Value |
|----------|-------|
| `base_url` | `http://localhost:8000/api/v1` |
| `vendor_token` | JWT from OTP verify |
| `product_id` | UUID of a product owned by the vendor |
| `video_id` | (set by upload request script below) |

---

## 1 — Product Demo Video

### Upload a Demo Video

```
POST {{base_url}}/videos/upload/request/
Authorization: Bearer {{vendor_token}}
Content-Type: application/json

{
  "title": "Summer Saree Demo",
  "description": "See how this saree drapes",
  "video_type": "product_demo",
  "product_id": "{{product_id}}"
}
```

Expected response:
```json
{
  "id": "uuid",
  "title": "Summer Saree Demo",
  "video_type": "product_demo",
  "product_id": "uuid-of-product",
  "upload_url": "https://...",
  "status": "pending"
}
```

Add to **Tests** tab to save video_id:
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
const d = pm.response.json();
pm.collectionVariables.set("video_id", d.id);
pm.test("video_type saved", () => pm.expect(d.video_type).to.eql("product_demo"));
```

---

### Upload a Store Promo Video (no product)

```
POST {{base_url}}/videos/upload/request/
Authorization: Bearer {{vendor_token}}
Content-Type: application/json

{
  "title": "Summer Sale Promo",
  "description": "Check out our summer deals",
  "video_type": "store_promo"
}
```

Expected: `200` — `video_type = "store_promo"`, `product_id = null`

---

### Mark Video as Ready (Django Admin / shell)

After uploading the MP4 to S3, mark the video ready for testing:

```python
# Django shell
from apps.videos.models import Video
v = Video.objects.get(id='<video_id>')
v.status = 'ready'
v.is_visible = True
v.save(update_fields=['status', 'is_visible'])
```

---

### Fetch Product Demo Video

```
GET {{base_url}}/products/{{product_id}}/demo-video/
```

No auth required.

Expected:
```json
{
  "id": "uuid",
  "title": "Summer Saree Demo",
  "video_type": "product_demo",
  "product_id": "uuid-of-product",
  "play_url": "https://...",
  "thumb_url": "https://...",
  "status": "ready"
}
```

**Error cases:**

| Scenario | Body | Expected |
|----------|------|---------|
| No demo video for product | — | `404 {"detail": "No demo video found for this product."}` |
| Product UUID doesn't exist | — | `404` |
| Video is_visible=False | — | `404` |
| Video status=processing | — | `404` |

---

## 2 — Voice OTP

### Request OTP via SMS (unchanged)

```
POST {{base_url}}/auth/otp/send/
Content-Type: application/json

{
  "phone_number": "+919999999999",
  "is_signup": false
}
```

Expected: `200 {"message": "OTP sent successfully"}`

---

### Request OTP via Voice Call

```
POST {{base_url}}/auth/otp/send/
Content-Type: application/json

{
  "phone_number": "+919999999999",
  "is_signup": false,
  "delivery_method": "voice"
}
```

Expected: `200 {"message": "OTP sent successfully"}`

- **Dev mode:** No real Twilio call is made; OTP is `123456`
- **Production:** Twilio places a voice call reading the OTP aloud via TwiML (`voice: alice, language: en-IN`)

---

### Verify OTP (same for both delivery methods)

```
POST {{base_url}}/auth/otp/verify/
Content-Type: application/json

{
  "phone_number": "+919999999999",
  "otp": "123456"
}
```

Expected: `200` with `access` + `refresh` tokens.

---

### Invalid delivery_method

```
POST {{base_url}}/auth/otp/send/
Content-Type: application/json

{
  "phone_number": "+919999999999",
  "delivery_method": "telegram"
}
```

Expected: `400` — validation error listing valid choices `["sms", "voice"]`

---

## 3 — Migration Verification

Confirm migration applied cleanly:

```bash
python manage.py showmigrations videos
```

Expected output includes:
```
[X] 0004_video_video_type_video_product
```

---

## Quick Reference — New Endpoints

| Method | Endpoint | Auth | Notes |
|--------|----------|------|-------|
| GET | `/products/{id}/demo-video/` | None | Latest ready+visible demo video for product |
| POST | `/videos/upload/request/` | Vendor JWT | Now accepts `video_type` + `product_id` |
| POST | `/auth/otp/send/` | None | Now accepts `delivery_method: "sms" \| "voice"` |

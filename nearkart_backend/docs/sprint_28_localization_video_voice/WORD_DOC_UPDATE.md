# Word Doc Update — Sprint 28

Add the following section to `NearKart_Master_API_Testing_Guide.docx` after the Sprint 27 section.

---

## Sprint 28 — Product Demo Video · Voice OTP
**Branch:** sprint-13-localization-video | **Date:** 2026-06-17

---

### New Endpoint: Product Demo Video

**GET** `/api/v1/products/{product_id}/demo-video/`

- **Auth:** None (AllowAny)
- **Returns:** Latest ready + visible demo video for the product
- **Error:** `404` when no demo video exists

**Response fields:**
```
id, title, description, video_type, product_id,
play_url, thumb_url, status, created_at
```

---

### Updated Endpoint: Video Upload Request

**POST** `/api/v1/videos/upload/request/`

**New request fields:**

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `video_type` | string | No | `"store_promo"` | `"store_promo"` or `"product_demo"` |
| `product_id` | UUID | No | null | Must belong to vendor's own store |

---

### Updated Endpoint: OTP Send

**POST** `/api/v1/auth/otp/send/`

**New request field:**

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `delivery_method` | string | No | `"sms"` | `"sms"` or `"voice"` |

When `delivery_method = "voice"`:
- Twilio places a voice call to the phone number
- OTP is read aloud using TwiML (voice: alice, language: en-IN)
- In dev mode: call is skipped; OTP = 123456 as always

---

### Postman Tests to Add

1. **Get product demo video** — `GET /products/{id}/demo-video/` → expect `200` with `video_type = "product_demo"`
2. **Upload demo video** — `POST /videos/upload/request/` with `video_type: "product_demo"` + `product_id`
3. **Voice OTP** — `POST /auth/otp/send/` with `delivery_method: "voice"` → verify with `123456`
4. **Invalid delivery_method** — `delivery_method: "telegram"` → expect `400`

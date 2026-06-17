# Sprint 28 — Testing Checklist

**Branch:** `sprint-13-localization-video`

---

## Pre-requisites

- [ ] Stack running: `make docker-up`
- [ ] Vendor token in Postman variable `{{vendor_token}}`
- [ ] Vendor has a store and at least one active product
- [ ] Migration applied: `python manage.py migrate`

---

## A — Product Demo Video — Upload

- [ ] `POST /api/v1/videos/upload/request/` with `video_type: "store_promo"` (no product_id)
  - Expected: `200` — `video_type` = `"store_promo"`, `product_id` = null in response
- [ ] Same with `video_type: "product_demo"` and a valid `product_id` from vendor's store
  - Expected: `200` — `video_type` = `"product_demo"`, `product_id` = UUID in response
- [ ] `product_demo` type with `product_id` belonging to a **different** vendor's store
  - Expected: `404`
- [ ] `product_demo` type with no `product_id`
  - Expected: Upload proceeds; `product_id` = null (product_id is optional even for demo type)
- [ ] `store_promo` type with a `product_id` included
  - Expected: `200` — `product_id` stored as provided (no validation blocks it)
- [ ] Old uploads without `video_type` field (omit entirely)
  - Expected: `200` — defaults to `"store_promo"` (backward compatible)

---

## B — Product Demo Video — Fetch

- [ ] `GET /api/v1/products/{product_id}/demo-video/` — product with no demo video
  - Expected: `404` `{"detail": "No demo video found for this product."}`
- [ ] Upload a `product_demo` video for a product; set `status = ready` and `is_visible = True` in Django Admin
- [ ] `GET /api/v1/products/{product_id}/demo-video/`
  - Expected: `200` — full `VideoSerializer` response including `play_url`, `thumb_url`, `video_type = "product_demo"`
- [ ] Upload a second demo video for the same product (both ready + visible)
  - Expected: `GET` returns the **most recent** one (`order_by('-created_at').first()`)
- [ ] Set `is_visible = False` on the demo video → `GET` returns `404`
- [ ] Set `status = processing` on the demo video → `GET` returns `404`
- [ ] No auth required — test without `Authorization` header → `200` (AllowAny)
- [ ] Non-existent product UUID → `404`

---

## C — Voice OTP — Send

- [ ] `POST /api/v1/auth/otp/send/` with `delivery_method: "sms"` (explicit)
  - Expected: `200 {"message": "OTP sent successfully"}`
  - Delivery: SMS Celery task queued
- [ ] Same with `delivery_method: "voice"`
  - Expected: `200 {"message": "OTP sent successfully"}`
  - Delivery: Voice Celery task queued (in dev: skipped, 123456 still works)
- [ ] Omit `delivery_method` entirely
  - Expected: `200` — defaults to `"sms"` (backward compatible)
- [ ] `delivery_method: "carrier_pigeon"` (invalid value)
  - Expected: `400` — validation error
- [ ] Rate limit still applies to voice requests (5 per hour per phone)
  - Expected: 6th request within an hour → `429 rate_limited`
- [ ] Log check: `otp_sent` event in `auth.log` includes `delivery_method` field

---

## D — Voice OTP — Dev Mode

- [ ] In `DEBUG=True` (default dev stack): `delivery_method: "voice"` returns `200`
- [ ] OTP is still `123456` — verify with `POST /api/v1/auth/otp/verify/` using `123456`
  - Expected: Login success (voice delivery skipped in DEBUG, code still valid)

---

## E — Celery Tasks

- [ ] With DEBUG=False and no DEV_FIXED_OTP set:
  - `delivery_method: "sms"` → `send_otp_sms` task appears in Celery worker logs
  - `delivery_method: "voice"` → `send_otp_voice` task appears in Celery worker logs
- [ ] Task retry: simulate Twilio failure (bad credentials) → task retries up to 3 times with 30 s delay

---

## F — Migration

- [ ] `python manage.py migrate` completes with no errors
- [ ] `python manage.py showmigrations videos` shows `0004_video_video_type_video_product` applied
- [ ] Existing Video rows have `video_type = "store_promo"` (default backfill)
- [ ] Existing Video rows have `product = null`
- [ ] Django Admin → Videos → a video detail page shows `video_type` and `product` fields

---

## G — Happy Path (end to end)

- [ ] Vendor uploads a demo video for a specific product (via Postman)
- [ ] Mark video ready + visible in Django Admin
- [ ] Customer calls `GET /products/{id}/demo-video/` → gets back the video
- [ ] Customer requests voice OTP → `200`, Celery task queued
- [ ] Customer verifies with `123456` (dev) → login succeeds

---

## Error Reference

| Endpoint | Scenario | Expected |
|----------|---------|---------|
| `upload/request/` | Product belongs to different vendor | `404` |
| `products/{id}/demo-video/` | No ready+visible demo video | `404` |
| `products/{id}/demo-video/` | Invalid UUID | `404` |
| `auth/otp/send/` | `delivery_method` invalid value | `400` |
| `auth/otp/send/` | Rate limited (6th request/hour) | `429` |

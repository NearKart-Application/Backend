# Sprint 28 — Localization · Product Demo Video · Voice OTP

**Branch:** `sprint-13-localization-video`
**Status:** Done ✅
**Date:** 2026-06-17

---

## Features

| ID | Feature | Scope |
|----|---------|-------|
| NF-50 | Product Demo Video | New `video_type` field + product FK on `Video` model; new endpoint to fetch a product's demo video |
| NF-10 | Voice OTP | Twilio voice call delivery; `delivery_method` field on OTP send endpoint |
| NF-07 | Telugu Localization | Client-side only — no backend changes |

---

## NF-50 — Product Demo Video

### Model Changes

**`apps/videos/models.py`**

New class constants:
```python
TYPE_STORE_PROMO  = 'store_promo'
TYPE_PRODUCT_DEMO = 'product_demo'
```

New fields on `Video`:
```python
video_type = CharField(max_length=20, choices=TYPE_CHOICES, default='store_promo', db_index=True)
product    = ForeignKey('products.Product', on_delete=SET_NULL, null=True, blank=True,
                        related_name='demo_videos')
```

### Serializer Changes

**`apps/videos/serializers.py`**

`VideoSerializer` — two new read-only fields:
```
video_type  (str)  — "store_promo" | "product_demo"
product_id  (UUID) — null for store_promo videos
```

`VideoUploadRequestSerializer` — two new upload fields:
```
video_type  (ChoiceField) — default "store_promo"
product_id  (UUIDField)   — required only when video_type = "product_demo"
```

Vendor must own the product to link it; otherwise 404.

### New Endpoint

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/api/v1/products/{id}/demo-video/` | None (AllowAny) | Returns the latest ready+visible demo video for a product |

Response: single `VideoSerializer` object.

Returns `404` when no demo video exists.

### Video Upload — Updated Fields

| Method | Endpoint | Change |
|--------|----------|--------|
| POST | `/api/v1/videos/upload/request/` | Add `video_type` + `product_id` to request body |

**Upload request example (demo video):**
```json
{
  "title": "Saree Draping Guide",
  "description": "See how this saree drapes on a real model",
  "video_type": "product_demo",
  "product_id": "uuid-of-product"
}
```

---

## NF-10 — Voice OTP

### Serializer Changes

**`apps/auth_app/serializers.py`**

New field on `OTPSendSerializer`:
```python
delivery_method = ChoiceField(choices=['sms', 'voice'], default='sms', required=False)
```

### Service Changes

**`apps/notifications/services.py`**

New method on `SMSService`:
```python
SMSService.send_voice_otp(phone_number, otp) → bool
```

Uses Twilio `calls.create()` with TwiML `VoiceResponse`. OTP digits are spaced for clarity.
Voice: `alice`, Language: `en-IN`.

**`apps/auth_app/services.py`**

`OTPService.generate_and_send()` now accepts `delivery_method: str = 'sms'`.
Routes to `send_otp_sms` or `send_otp_voice` Celery task accordingly.

**`apps/auth_app/tasks.py`**

New Celery task:
```python
@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_otp_voice(self, phone_number, otp)
```

### View Changes

**`apps/auth_app/views.py`**

`OTPSendView.post()` now reads `delivery_method` from the serializer and passes it to `OTPService.generate_and_send()`.

Event log includes `delivery_method` in the `otp_sent` log entry.

### OTP Send Request — Updated

```json
{
  "phone_number": "+919999999999",
  "delivery_method": "voice"
}
```

Omitting `delivery_method` defaults to `"sms"` — fully backward compatible.

---

## Migration

```
apps/videos/migrations/0004_video_video_type_video_product.py
```

Depends on:
- `videos.0003_videoproducttag`
- `products.0007_product_previous_price`

Run: `python manage.py migrate`

---

## Files Changed

| File | Change |
|------|--------|
| `apps/videos/models.py` | Added `video_type` and `product` FK |
| `apps/videos/migrations/0004_*` | Migration for new video fields |
| `apps/videos/serializers.py` | Exposed `video_type`, `product_id`; added upload fields |
| `apps/videos/services.py` | `request_upload()` accepts `video_type` + `product` |
| `apps/videos/views.py` | `VideoUploadRequestView` validates product ownership |
| `apps/products/views.py` | New `ProductDemoVideoView` |
| `apps/products/urls.py` | Added `products/<id>/demo-video/` route |
| `apps/auth_app/serializers.py` | Added `delivery_method` to `OTPSendSerializer` |
| `apps/auth_app/services.py` | `generate_and_send()` routes by delivery method |
| `apps/auth_app/tasks.py` | Added `send_otp_voice` Celery task |
| `apps/auth_app/views.py` | `OTPSendView` passes `delivery_method` through |
| `apps/notifications/services.py` | Added `SMSService.send_voice_otp()` |

# Sprint 12 — Razorpay Payments + Video Download Postman Guide

## Collection Setup

Add a new folder inside your existing Postman collection: **"12 — Razorpay Payments + Video Download"**

Variables needed (should already be set from earlier sprints):

| Variable | Value | Set by |
|----------|-------|--------|
| `base_url` | `http://localhost:8000/api/v1` | Manual |
| `vendor_token` | (JWT) | OTP verify script |
| `razorpay_order_id` | (empty) | Set by initiate script below |

---

## Payment Flow (3 Steps)

### Step 1 — List Plans (find the price)

```
GET {{base_url}}/billing/plans/
```

No auth required.

Expected response:
```json
[
  {"name": "free",    "display_name": "Free Plan",    "price": "0.00",   ...},
  {"name": "basic",   "display_name": "Basic Plan",   "price": "499.00", ...},
  {"name": "premium", "display_name": "Premium Plan", "price": "999.00", ...}
]
```

---

### Step 2 — Initiate Payment (create Razorpay order)

```
POST {{base_url}}/billing/payment/initiate/
Authorization: Bearer {{vendor_token}}
Content-Type: application/json

{
  "plan_name": "basic"
}
```

Expected response:
```json
{
  "order_id":        "order_DEV_store_abc12345",
  "amount":          49900,
  "currency":        "INR",
  "plan_name":       "basic",
  "receipt":         "store_abc12345_basic_1716000000",
  "razorpay_key_id": "rzp_test_PLACEHOLDER"
}
```

> **Dev mode:** `order_id` starts with `order_DEV_` — no real Razorpay call is made.
> **Production:** `order_id` starts with `order_` — open Razorpay checkout SDK with this ID and `razorpay_key_id`.

Add this to the **Tests** tab to auto-save the order ID:
```javascript
pm.test("Status is 200", () => pm.response.to.have.status(200));
const data = pm.response.json();
pm.collectionVariables.set("razorpay_order_id", data.order_id);
pm.test("Order ID saved", () => pm.expect(data.order_id).to.include("order_"));
```

---

### Step 3 — Verify Payment (activate subscription)

```
POST {{base_url}}/billing/payment/verify/
Authorization: Bearer {{vendor_token}}
Content-Type: application/json

{
  "razorpay_order_id":   "{{razorpay_order_id}}",
  "razorpay_payment_id": "pay_DEV_test12345",
  "razorpay_signature":  "mock_signature_dev",
  "plan_name":           "basic"
}
```

Expected response (full subscription object):
```json
{
  "id":         "uuid",
  "plan":       {"name": "basic", "display_name": "Basic Plan", "price": "499.00", ...},
  "started_at": "2026-05-15T10:00:00Z",
  "expires_at": "2026-06-14T10:00:00Z",
  "is_active":  true,
  "days_left":  29
}
```

> **Dev mode:** Signature check is bypassed — any value for `razorpay_signature` works.
> **Production:** The app sends the real `razorpay_payment_id` and `razorpay_signature` returned by the Razorpay checkout SDK.

---

## Confirm Wallet Was Topped Up

After verify succeeds, check:

```
GET {{base_url}}/billing/wallet/
Authorization: Bearer {{vendor_token}}
```

Expected: `wallet_balance` includes the plan price credited, then deducted by subscription.

```
GET {{base_url}}/billing/transactions/
Authorization: Bearer {{vendor_token}}
```

Expected: Two transactions — a `topup` (positive, reference = `pay_DEV_test12345`) and a `subscription` (negative).

---

## Webhook Endpoint (Razorpay Dashboard Setup)

Register this URL in Razorpay Dashboard → Settings → Webhooks:

```
POST https://api.nearkart.in/api/v1/billing/payment/webhook/
```

Events to subscribe: `payment.captured`

This endpoint is idempotent — if `verify` already processed the payment, the webhook skips it.

**Test webhook locally (dev mode — any signature accepted):**

```
POST {{base_url}}/billing/payment/webhook/
Content-Type: application/json
X-Razorpay-Signature: mock_sig

{
  "event": "payment.captured",
  "payload": {
    "payment": {
      "entity": {
        "id": "pay_DEV_webhook001",
        "order_id": "order_DEV_store_abc",
        "notes": {
          "store_id": "{{store_id}}",
          "plan": "basic"
        }
      }
    }
  }
}
```

Expected: `200 {"status": "ok"}`

Expected (if payment already processed): `200 {"status": "already_processed"}`

---

## Error Cases

| Scenario | Expected |
|----------|---------|
| `initiate` with `plan_name: "free"` | `400` — free plan needs no payment |
| `initiate` with unknown plan | `404` — plan not found |
| `verify` missing `razorpay_signature` | `400` — all fields required |
| `verify` — production only — wrong signature | `400` — payment_failed |
| `webhook` — production only — wrong signature | `400` — invalid_signature |
| `initiate` without store | `404` — you do not have a store |
| `initiate` with customer token | `403` — vendor only |

---

## Common Errors

| Error code | Meaning | Fix |
|------------|---------|-----|
| `payment_failed` | HMAC signature mismatch | Check you're sending the exact values from Razorpay callback |
| `subscription_failed` | Wallet top-up OK but subscribe errored | Check logs — plan may have changed |
| `invalid_signature` (webhook) | Webhook secret mismatch | Set correct `RAZORPAY_WEBHOOK_SECRET` in `.env` |
| `already_processed` (webhook) | Payment already handled by verify | Not an error — idempotency guard working correctly |
| `conflict` (download) | No raw file for this video | Video was never fully uploaded or raw key missing |

---

## Video Download (After Expiry Notification)

### Step 1 — Get Download URL

When vendor receives a `video_expiring_soon` push notification, the app reads `data.video_id` and calls:

```
GET {{base_url}}/videos/{{video_id}}/download/
Authorization: Bearer {{vendor_token}}
```

Expected response:
```json
{
  "video_id":    "uuid",
  "title":       "Summer Sale Promo",
  "download_url": "https://mock-s3.dev/videos/raw/.../original.mp4?download=true&dev=true",
  "expires_in":  3600
}
```

> **Dev mode:** URL contains `mock-s3.dev` — no real S3 call.
> **Production:** URL is a real presigned S3 GET URL valid for 1 hour. Open in browser or use `curl -L <download_url> -o video.mp4` to save locally.

Add this to the **Tests** tab:
```javascript
pm.test("Status is 200", () => pm.response.to.have.status(200));
const data = pm.response.json();
pm.test("Download URL present", () => pm.expect(data.download_url).to.be.a('string').and.not.empty);
pm.test("Expires in 1 hour", () => pm.expect(data.expires_in).to.equal(3600));
```

---

### Step 2 — Simulate Expiry Notification (manual test)

To test the full flow without waiting 28 days, update the video in Django Admin or shell:

```python
# Django shell
from apps.videos.models import Video
from django.utils import timezone
from datetime import timedelta

v = Video.objects.get(id='<your-video-id>')
v.expires_at = timezone.now() + timedelta(hours=25)
v.save(update_fields=['expires_at'])

# Trigger the notification task
from apps.videos.tasks import notify_expiring_videos
notify_expiring_videos()
# Returns: 1 (one notification sent)
```

Then check the vendor's notification inbox:

```
GET {{base_url}}/notifications/
Authorization: Bearer {{vendor_token}}
```

Look for `notification_type: "video_expiring_soon"` with `data.action: "download_prompt"`.

---

### Step 3 — Simulate Auto-Delete

```python
# Django shell — set video as past expiry
v.expires_at = timezone.now() - timedelta(hours=1)
v.save(update_fields=['expires_at'])

from apps.videos.tasks import delete_expired_videos
delete_expired_videos()
# Returns: 1 (one video expired)
```

Confirm the video is gone from feed:

```
GET {{base_url}}/videos/feed/?lat=12.97&lng=77.59
```

The expired video must NOT appear.

# NearKart — Going to Production Guide

> **Purpose:** Every single thing that uses dummy / placeholder data in development
> and must be replaced with real values before going live.
> Follow this top to bottom. Miss nothing.

---

## How Dev Mode Works (Understand This First)

The backend has 6 built-in dev-mode bypasses. Each one activates automatically
based on the value in `.env` — **no code changes needed**. Just set the right value
and the bypass switches off.

| Service | What triggers DEV mode | What triggers PRODUCTION mode |
|---------|------------------------|-------------------------------|
| OTP / SMS | `DEV_FIXED_OTP=123456` set in `.env` | `DEV_FIXED_OTP=` (empty) in `.env` |
| Twilio SMS | OTP is fixed — Twilio never called | `DEV_FIXED_OTP` is empty → Twilio sends real SMS |
| Firebase FCM | `FIREBASE_CREDENTIALS_JSON` file missing or invalid | Valid `firebase-credentials.json` file → real pushes sent |
| AWS S3 / HLS | `AWS_ACCESS_KEY_ID` contains `EXAMPLE` | Real AWS key → real S3 uploads + FFmpeg transcoding |
| Razorpay | `RAZORPAY_KEY_ID` contains `PLACEHOLDER` | `rzp_live_*` key → real payment charged |
| Video Download | Same as AWS S3 above | Same as AWS S3 — real presigned GET URL returned |

---

## Section 1 — Django Core

| Variable | Dev value | Production value | Where to get it |
|----------|-----------|-----------------|-----------------|
| `SECRET_KEY` | `your-50-char-secret-key...` | Random 50-char string | `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DEBUG` | `True` | **`False`** | Hardcoded |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | `api.nearspot.in,api-staging.nearspot.in` | Your domain name |
| `DJANGO_SETTINGS_MODULE` | `config.settings.development` | `config.settings.production` | Hardcoded |
| `DEV_FIXED_OTP` | `123456` | **empty string** (remove the value entirely) | Just clear it |

> ⚠️ **Critical:** `DEV_FIXED_OTP=` (empty) is what switches OTP from fixed `123456`
> to real random OTP sent via Twilio. Do not leave `123456` in production.

---

## Section 2 — Database (PostgreSQL + PostGIS)

| Variable | Dev value | Production value |
|----------|-----------|-----------------|
| `DB_NAME` | `nearkart` | `nearkart_prod` |
| `DB_USER` | `nearkart` | `nearkart_prod` |
| `DB_PASSWORD` | `nearkart_dev_password_change_in_prod` | Strong random password (20+ chars) |
| `DB_HOST` | `postgres` (Docker service name) | RDS endpoint: `nearkart-prod.xxxx.ap-south-1.rds.amazonaws.com` |
| `DB_PORT` | `5432` | `5432` |

**AWS RDS setup steps:**
1. Go to AWS Console → RDS → Create Database
2. Engine: PostgreSQL 15 + enable PostGIS extension after creation
3. Instance: `db.t3.medium` minimum for production
4. Enable Multi-AZ for high availability
5. After creation, connect and run: `CREATE EXTENSION postgis;`

---

## Section 3 — Redis

| Variable | Dev value | Production value |
|----------|-----------|-----------------|
| `REDIS_URL` | `redis://redis:6379/0` | `redis://:PASSWORD@nearkart-prod.xxxx.cache.amazonaws.com:6379/0` |
| `REDIS_CACHE_URL` | `redis://redis:6379/1` | `redis://:PASSWORD@nearkart-prod.xxxx.cache.amazonaws.com:6379/1` |
| `REDIS_CHANNEL_URL` | `redis://redis:6379/2` | `redis://:PASSWORD@nearkart-prod.xxxx.cache.amazonaws.com:6379/2` |
| `REDIS_PASSWORD` | *(empty)* | Strong random password |
| `CELERY_BROKER_URL` | `redis://redis:6379/0` | Same as `REDIS_URL` above |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/0` | Same as `REDIS_URL` above |

**AWS ElastiCache setup:** Create a Redis 7 cluster with AUTH enabled. Copy the endpoint.

---

## Section 4 — AWS (S3 + CDN)

**What changes:** Setting real AWS credentials disables the dev bypass.
All video uploads, HLS transcoding, thumbnails, and presigned download URLs
will use real S3 instead of mock URLs.

| Variable | Dev value | Production value |
|----------|-----------|-----------------|
| `AWS_ACCESS_KEY_ID` | `AKIAIOSFODNN7EXAMPLE` | Real IAM key — e.g. `AKIAXXXXXXXXXXXXXXXX` |
| `AWS_SECRET_ACCESS_KEY` | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` | Real IAM secret |
| `AWS_REGION` | `ap-south-1` | `ap-south-1` (keep unless you change region) |
| `AWS_S3_BUCKET` | `nearkart-media-dev` | `nearkart-media-prod` |
| `AWS_S3_STATIC_BUCKET` | `nearkart-static-dev` | `nearkart-static-prod` |
| `AWS_CDN_DOMAIN` | `nearkart-media-dev.s3.ap-south-1.amazonaws.com` | Your CloudFront domain: `dXXXXXX.cloudfront.net` |
| `AWS_PRESIGNED_URL_EXPIRY` | `900` (15 min) | `900` (keep or adjust) |

**AWS setup steps:**
1. Create IAM user `nearkart-backend-prod` with programmatic access
2. Attach policy with permissions: `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject`, `s3:ListBucket`
3. Create S3 bucket `nearkart-media-prod` in `ap-south-1` — **Block all public access**
4. Create S3 bucket `nearkart-static-prod` in `ap-south-1` — public read for static files
5. Create CloudFront distribution pointing to `nearkart-media-prod` for CDN URLs
6. Copy CloudFront domain (e.g. `dXXXX.cloudfront.net`) to `AWS_CDN_DOMAIN`

---

## Section 5 — Twilio (SMS OTP)

**What changes:** Once `DEV_FIXED_OTP` is empty, every OTP is a real random 6-digit code
sent via Twilio SMS. Vendors and customers receive the OTP on their phone.

| Variable | Dev value | Production value |
|----------|-----------|-----------------|
| `TWILIO_ACCOUNT_SID` | `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` | Real SID from Twilio Console |
| `TWILIO_AUTH_TOKEN` | `your_twilio_auth_token_here` | Real auth token from Twilio Console |
| `TWILIO_FROM_NUMBER` | `+1234567890` | Your purchased Twilio India number: `+91XXXXXXXXXX` |

**Twilio setup steps:**
1. Go to [console.twilio.com](https://console.twilio.com)
2. Copy `Account SID` and `Auth Token` from dashboard home
3. Buy an Indian phone number: Phone Numbers → Manage → Buy a Number → India
4. For India SMS, complete DLT registration (required by TRAI):
   - Register entity on DLT portal (Airtel/BSNL/Vodafone)
   - Get your Template ID for OTP messages
   - Add DLT Template ID to your Twilio message body or use Twilio's DLT feature

---

## Section 6 — Firebase (FCM Push Notifications)

**What changes:** When a valid `firebase-credentials.json` file exists, FCM sends real
push notifications to vendor/customer devices instead of just logging them.

| Variable | Dev value | Production value |
|----------|-----------|-----------------|
| `FIREBASE_CREDENTIALS_JSON` | `/app/firebase-credentials.json` (file missing = dev mode) | `/app/firebase-credentials.json` (real file present = production mode) |

**Firebase setup steps:**
1. Go to [console.firebase.google.com](https://console.firebase.google.com)
2. Create project: `nearkart-production`
3. Go to Project Settings → Service Accounts
4. Click **Generate new private key** → downloads `firebase-credentials.json`
5. In production (ECS): store file content as AWS Secrets Manager secret,
   mount it at `/app/firebase-credentials.json` in ECS task definition
6. OR: base64-encode the file, store as env var, decode at startup in `entrypoint.sh`

> ⚠️ **Never commit `firebase-credentials.json` to Git.**
> This file gives full admin access to your Firebase project.

---

## Section 7 — Razorpay (Payments)

**What changes:** Setting `rzp_live_*` keys disables the dev bypass.
All payments, HMAC signature verification, and webhooks become real.
Real money moves.

| Variable | Dev value | Production value |
|----------|-----------|-----------------|
| `RAZORPAY_KEY_ID` | `rzp_test_PLACEHOLDER` | `rzp_live_XXXXXXXXXXXXXXXXXX` |
| `RAZORPAY_KEY_SECRET` | `PLACEHOLDER_SECRET` | Real live secret from Razorpay Dashboard |
| `RAZORPAY_WEBHOOK_SECRET` | `PLACEHOLDER_WEBHOOK_SECRET` | Webhook secret from Razorpay Dashboard |

**Razorpay setup steps:**
1. Go to [dashboard.razorpay.com](https://dashboard.razorpay.com) → Settings → API Keys
2. Generate live keys — copy `Key ID` and `Key Secret`
3. Go to Settings → Webhooks → Add New Webhook:
   - URL: `https://api.nearspot.in/api/v1/billing/payment/webhook/`
   - Events: tick `payment.captured`
   - Copy the **Webhook Secret** shown
4. Complete KYC / business verification in Razorpay to activate live mode
5. Update `.env.production` with all 3 values

> ⚠️ **Test in Razorpay test mode first** (`rzp_test_*` keys) with real bank/card
> before switching to live. Use Razorpay's test card numbers to simulate payments.

---

## Section 8 — Sentry (Error Monitoring)

| Variable | Dev value | Production value |
|----------|-----------|-----------------|
| `SENTRY_DSN` | `https://examplePublicKey@o0.ingest.sentry.io/0` | Real DSN from Sentry project |
| `SENTRY_ENVIRONMENT` | `development` | `production` (or `staging` for staging) |

**Sentry setup steps:**
1. Go to [sentry.io](https://sentry.io) → Create Project → Django
2. Copy the DSN shown after project creation
3. Create two environments: `staging` and `production`
4. Set alert rules for `production` environment (notify on new issues)

---

## Section 9 — SendGrid (Email)

Currently used for transactional emails (receipts, etc.).

| Variable | Dev value | Production value |
|----------|-----------|-----------------|
| `SENDGRID_API_KEY` | `SG.your_sendgrid_api_key_here` | Real API key from SendGrid |
| `DEFAULT_FROM_EMAIL` | `hello@nearspot.in` | `hello@nearspot.in` (verify this domain in SendGrid) |
| `DEFAULT_FROM_NAME` | `Nearspot` | `Nearspot` |

**SendGrid setup steps:**
1. Go to [app.sendgrid.com](https://app.sendgrid.com) → Settings → API Keys → Create
2. Verify your sending domain `nearspot.in` under Sender Authentication
3. Copy API key to `SENDGRID_API_KEY`

---

## Section 10 — Google Maps (Geo / Location)

Used for reverse geocoding store addresses.

| Variable | Dev value | Production value |
|----------|-----------|-----------------|
| `GOOGLE_MAPS_API_KEY` | `AIzaSyYour_Google_Maps_API_Key_Here` | Real key from Google Cloud Console |

**Google Maps setup steps:**
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Enable APIs: **Maps JavaScript API**, **Geocoding API**, **Places API**
3. Create credentials → API Key → restrict to your server IP or domain
4. Copy to `GOOGLE_MAPS_API_KEY`

---

## Section 11 — CORS

| Variable | Dev value | Production value |
|----------|-----------|-----------------|
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost:19006` | `https://app.nearspot.in,https://vendor.nearspot.in` |

Add every domain your mobile/web apps will call the API from.

---

## Section 12 — One-Time Production Setup (After First Deploy)

Run these **once** after the first ECS deployment:

```bash
# 1. SSH into ECS task or use ECS Exec
aws ecs execute-command \
  --cluster nearkart-production \
  --task <TASK_ID> \
  --container nearkart-backend \
  --command "/bin/bash" \
  --interactive

# 2. Create Django superuser (for Admin panel)
python manage.py createsuperuser

# 3. Seed subscription plans (free / basic / premium)
python manage.py loaddata fixtures/plans.json

# 4. Static files (entrypoint.sh does this automatically on every deploy)
python manage.py collectstatic --noinput
```

---

## Section 13 — Business Logic Constants (Review Before Go-Live)

These have defaults set in `.env.example`. Review and adjust for your launch:

| Variable | Default | Meaning | Change? |
|----------|---------|---------|---------|
| `VIDEO_EXPIRY_DAYS` | `30` | Videos auto-delete after 30 days | Adjust if needed |
| `VIDEO_MAX_DURATION_SECONDS` | `60` | Max video length 60 sec | Keep |
| `VIDEO_MAX_SIZE_MB` | `100` | Max upload size 100 MB | Adjust based on S3 costs |
| `STORY_EXPIRY_HOURS` | `24` | Stories expire in 24 hours | Keep |
| `RESERVATION_HOLD_HOURS` | `2` | Reservation holds for 2 hours | Keep |
| `BLACKLIST_INACTIVE_DAYS` | `30` | Store blacklisted after 30 days inactivity | Keep |
| `BLACKLIST_WARNING_DAY` | `20` | First warning at day 20 | Keep |
| `BLACKLIST_FINAL_WARNING_DAY` | `27` | Final warning at day 27 | Keep |
| `OTP_SEND_RATE_LIMIT` | `5` | Max 5 OTP requests per user | Keep |
| `JWT_ACCESS_TOKEN_LIFETIME_HOURS` | `1` | Token expires in 1 hour | Keep |
| `JWT_REFRESH_TOKEN_LIFETIME_DAYS` | `30` | Refresh token valid 30 days | Keep |
| `GUNICORN_WORKERS` | `4` | Number of app server workers | Set to `2 × CPU cores + 1` |

---

## Section 14 — Final Pre-Launch Verification

After setting all variables and deploying, verify each service works end-to-end:

```bash
# 1. Health check
curl https://api.nearspot.in/api/v1/health/
# Expected: {"status": "ok", "database": "ok", "redis": "ok"}

# 2. OTP — real SMS should arrive on your phone
curl -X POST https://api.nearspot.in/api/v1/auth/otp/send/ \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+91XXXXXXXXXX"}'
# Expected: SMS delivered within 10 seconds

# 3. Video upload — should create real S3 presigned URL (not mock-s3.dev)
# POST /videos/request-upload/ → check upload_url starts with https://nearspot-media-prod.s3...

# 4. Razorpay — initiate a basic plan payment
# POST /billing/payment/initiate/ → order_id should start with "order_" (not "order_DEV_")

# 5. Push notification — register a device token and trigger a notification
# order_id NOT starting with order_DEV_ = Razorpay live mode active

# 6. Swagger must be BLOCKED on production
curl https://api.nearspot.in/api/docs/
# Expected: 403 Forbidden (Nginx blocks it)

# 7. Swagger accessible on staging
curl https://api-staging.nearspot.in/api/docs/
# Expected: 200 OK with Swagger UI
```

---

## Quick Summary — Minimum Changes to Go Live

If you want the absolute minimum required, these 5 things are non-negotiable:

1. `SECRET_KEY` — must be a real random string (security)
2. `DEV_FIXED_OTP=` — must be empty (otherwise anyone can log in with `123456`)
3. `DB_PASSWORD` — must be a strong password (security)
4. `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` — real keys (videos won't work without)
5. `RAZORPAY_KEY_ID` — must be `rzp_live_*` to charge real money

Everything else can be set progressively as you onboard each feature.

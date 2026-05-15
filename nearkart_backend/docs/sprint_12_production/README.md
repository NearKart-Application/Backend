# Sprint 12 — Staging + Production

**Status:** Done ✅
**Verified on:** 2026-05-15

---

## What This Sprint Does

Completes the production-readiness of the NearKart Backend:
- Full production Django settings (security, S3, structured logging)
- Staging environment (separate from production)
- Production Docker Compose (no code mounts, resource limits, Redis auth)
- Production Nginx config (HTTP-only; SSL terminated at AWS ALB)
- Auto-migrate entrypoint (zero-downtime ECS deploys)
- CI/CD pipeline fixes (Python 3.13, sprint branches, staging→prod deploy gate)
- `.env.example` with all required variables documented
- **Razorpay payment flow** — initiate order → verify HMAC → fund wallet → activate subscription + webhook backup

---

## Deployment Architecture

```
Internet
    ↓  HTTPS (port 443)
AWS Application Load Balancer  ←── SSL terminated here (AWS ACM certificate)
    ↓  HTTP (port 80) + X-Forwarded-Proto: https
    ↓
Nginx (port 80)  →  rate limiting, static files, WS upgrade
    ↓
Gunicorn + Uvicorn workers (port 8000)  ←── ASGI: handles HTTP + WebSocket
    ↓
Django (ASGI app)
    ↓
PostgreSQL + PostGIS  |  Redis  |  AWS S3  |  Firebase FCM
```

---

## Environments

| Environment | Branch | Settings | Deploy |
|-------------|--------|----------|--------|
| Local dev | any | `config.settings.development` | `make docker-up` |
| CI/CD tests | PRs | `config.settings.testing` | automatic (GitHub Actions) |
| Staging | `main` | `config.settings.staging` | auto after CI passes |
| Production | `main` | `config.settings.production` | manual approval required |

---

## Files Changed / Created

| File | Change |
|------|--------|
| `config/settings/production.py` | Completed — ALLOWED_HOSTS, S3 STORAGES, CloudWatch logging, SECURE_PROXY_SSL_HEADER |
| `config/settings/staging.py` | New — inherits production, staging-specific Sentry env + Swagger allowed |
| `scripts/entrypoint.sh` | New — auto-migrate + collectstatic before gunicorn starts |
| `Dockerfile` | Updated — production stage uses entrypoint.sh, sets DJANGO_SETTINGS_MODULE |
| `docker-compose.prod.yml` | New — production compose: production build target, no code mounts, resource limits |
| `nginx/nginx.prod.conf` | New — production nginx: ALB proxy headers, Swagger blocked, attack path blocking |
| `.env.example` | Updated — REDIS_PASSWORD, AWS_S3_STATIC_BUCKET, GUNICORN_WORKERS, Razorpay keys |
| `.github/workflows/ci_cd.yml` | Fixed — Python 3.13, sprint-* branches, staging→prod deploy gate, AWS creds |
| `Makefile` | Updated — prod-up, prod-down, prod-logs, check-env commands |
| `apps/billing/razorpay_service.py` | New — RazorpayService with dev-mode bypass; create_order, verify signatures |
| `apps/billing/views.py` | Added PaymentInitiateView, PaymentVerifyView, PaymentWebhookView |
| `apps/billing/urls.py` | Added /payment/initiate/, /payment/verify/, /payment/webhook/ routes |
| `config/settings/base.py` | Added RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, RAZORPAY_WEBHOOK_SECRET |
| `requirements/base.txt` | Added razorpay>=1.4 |

---

## Razorpay Payment API

Three new endpoints added under `/api/v1/billing/payment/`:

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/payment/initiate/` | JWT + Vendor | Create Razorpay order for a plan → get `order_id` for checkout SDK |
| POST | `/payment/verify/` | JWT + Vendor | Verify HMAC signature → credit wallet → activate subscription |
| POST | `/payment/webhook/` | None (signature) | Razorpay webhook backup for `payment.captured` events |

### Mobile App Integration Flow

```
1. Vendor taps "Subscribe Basic"
2. App → POST /billing/payment/initiate/ { plan_name: "basic" }
   ← { order_id, amount: 49900, currency: "INR", razorpay_key_id }
3. App opens Razorpay checkout SDK with order_id + key_id
4. User completes payment in SDK
   ← SDK returns { razorpay_payment_id, razorpay_signature }
5. App → POST /billing/payment/verify/ { order_id, payment_id, signature, plan_name }
   ← Subscription object with is_active: true
```

### Dev Mode

Set `RAZORPAY_KEY_ID=rzp_test_PLACEHOLDER` in `.env` (default).
- `initiate` returns a mock `order_DEV_*` order ID
- `verify` skips signature check — any values accepted
- `webhook` skips signature check
- No real money moves

### Going Live

1. Get keys from [dashboard.razorpay.com/app/keys](https://dashboard.razorpay.com/app/keys)
2. Update `.env`:
   ```
   RAZORPAY_KEY_ID=rzp_live_XXXXXXXXXX
   RAZORPAY_KEY_SECRET=your_live_secret
   RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
   ```
3. Register webhook URL in Razorpay Dashboard → Settings → Webhooks:
   `https://api.nearkart.in/api/v1/billing/payment/webhook/`
   Events: `payment.captured`

---

## How to Deploy to Production

### Prerequisites (one-time setup)

1. **AWS ECS clusters**: `nearkart-staging` and `nearkart-production`
2. **AWS ECR repository**: `nearkart-backend`
3. **GitHub Secrets** (Settings → Secrets and variables → Actions):
   - `AWS_ACCOUNT_ID`
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
4. **GitHub Environments** (Settings → Environments):
   - `staging` — no approval required
   - `production` — required reviewers (you)

### Deploy flow

```
git push origin main
    ↓
GitHub Actions runs:
  1. Lint (flake8, black, isort)
  2. Tests (pytest with PostGIS + Redis)
  3. Docker build → push to ECR
  4. Auto-deploy to ECS staging
  5. ⏸ Wait for manual approval in GitHub Actions
  6. Deploy to ECS production
```

### Manual deploy (emergency)

```bash
# Build and push image
docker build --target production -t <ECR_URI>/nearkart-backend:latest .
docker push <ECR_URI>/nearkart-backend:latest

# Force new ECS deployment
aws ecs update-service \
  --cluster nearkart-production \
  --service nearkart-backend-production \
  --force-new-deployment \
  --region ap-south-1
```

---

## Local Production Simulation

To test the production build locally:

```bash
# 1. Create .env.production with real values
cp .env.example .env.production
# Edit .env.production ...

# 2. Check all required env vars are set
make check-env

# 3. Start production stack
make prod-up

# 4. Check logs
make prod-logs

# 5. Stop
make prod-down
```

---

## Key Production Settings

| Setting | Value | Why |
|---------|-------|-----|
| `DEBUG` | `False` | Never expose stack traces |
| `SECURE_PROXY_SSL_HEADER` | `HTTP_X_FORWARDED_PROTO, https` | Trust ALB HTTPS header |
| `SECURE_SSL_REDIRECT` | `False` | ALB handles redirect; avoid double-redirect |
| `SECURE_HSTS_SECONDS` | `31536000` (1 year) | Browser caches HTTPS-only for 1 year |
| `STORAGES.staticfiles` | S3Boto3Storage | Static files served from S3/CDN |
| `CONN_HEALTH_CHECKS` | `True` | DB reconnects if connection drops |
| Logging | JSON to stdout | CloudWatch picks it up automatically |

---

## Swagger Docs

| Environment | Swagger available? |
|-------------|-------------------|
| Development | ✅ `http://localhost:8000/api/docs/` |
| Staging | ✅ `https://api-staging.nearkart.in/api/docs/` |
| Production | ❌ Blocked at Nginx (returns 403) |

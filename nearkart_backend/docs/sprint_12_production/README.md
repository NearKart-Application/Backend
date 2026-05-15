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
| `.env.example` | Updated — added REDIS_PASSWORD, AWS_S3_STATIC_BUCKET, GUNICORN_WORKERS |
| `.github/workflows/ci_cd.yml` | Fixed — Python 3.13, sprint-* branches, staging→prod deploy gate, AWS creds |
| `Makefile` | Updated — prod-up, prod-down, prod-logs, check-env commands |

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

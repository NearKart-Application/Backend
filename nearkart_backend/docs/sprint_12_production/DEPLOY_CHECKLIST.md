# Sprint 12 — Production Deploy Checklist

Run this checklist before every production deployment.

---

## Pre-Deploy

- [ ] All tests pass: `pytest --cov=apps --cov-fail-under=75`
- [ ] No uncommitted migrations: `python manage.py migrate --check`
- [ ] `.env.production` has all required vars: `make check-env`
- [ ] Sentry DSN is set in `.env.production`
- [ ] Firebase credentials JSON is set
- [ ] AWS S3 buckets exist: `nearkart-media-prod` and `nearkart-static-prod`
- [ ] ECS task definition has latest image tag

## AWS GitHub Secrets Set

- [ ] `AWS_ACCOUNT_ID`
- [ ] `AWS_ACCESS_KEY_ID`
- [ ] `AWS_SECRET_ACCESS_KEY`

## GitHub Environments Configured

- [ ] `staging` environment exists (no approval)
- [ ] `production` environment exists (required reviewer: you)

---

## Deploy Steps

- [ ] Merge sprint branch PR → `main`
- [ ] Watch GitHub Actions: lint → test → build → staging
- [ ] Test on staging: `https://api-staging.nearkart.in/api/v1/health/`
- [ ] Approve production deployment in GitHub Actions UI
- [ ] Watch ECS rolling deploy complete (ECS console)
- [ ] Test on production: `https://api.nearkart.in/api/v1/health/`
- [ ] Check Sentry for new errors (first 15 minutes)

---

## Post-Deploy Verification

```bash
# Health check
curl https://api.nearkart.in/api/v1/health/

# Expected:
# {"status": "ok", "database": "ok", "redis": "ok", ...}
```

- [ ] Health check returns `200 OK`
- [ ] Send OTP works (Twilio SMS)
- [ ] Login with OTP works (JWT returned)
- [ ] Nearby stores returns data (PostGIS working)
- [ ] WebSocket connects (use Postman WS tab)
- [ ] Swagger blocked on prod (curl https://api.nearkart.in/api/docs/ → 403)
- [ ] Swagger accessible on staging (https://api-staging.nearkart.in/api/docs/)

---

## Rollback (if needed)

```bash
# Get previous task definition revision
aws ecs describe-services \
  --cluster nearkart-production \
  --services nearkart-backend-production \
  --region ap-south-1

# Roll back to previous task definition
aws ecs update-service \
  --cluster nearkart-production \
  --service nearkart-backend-production \
  --task-definition nearkart-backend-production:<PREVIOUS_REVISION> \
  --region ap-south-1
```

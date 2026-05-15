# Sprint 12 — Testing Checklist

**Branch:** `sprint-12-production`

---

## Pre-requisites

- [ ] Stack running: `make docker-up`
- [ ] Vendor token in Postman variable `{{vendor_token}}`
- [ ] Vendor has a store (`POST /api/v1/stores/`)
- [ ] Plans seeded in DB (`python manage.py loaddata fixtures/plans.json` or via Django Admin)

---

## A — Production Settings

- [ ] `DEBUG=False` in `.env` → stack still starts cleanly
- [ ] `SECRET_KEY` is not the Django default — 50+ char random string
- [ ] `make check-env` exits 0 (all required vars present)

---

## B — Razorpay — Initiate Payment

- [ ] `POST /api/v1/billing/payment/initiate/` — `plan_name: "basic"`
  - Expected: `200` with `order_id`, `amount: 49900`, `currency: "INR"`, `razorpay_key_id`
  - Dev: `order_id` starts with `order_DEV_`
- [ ] Same request for `plan_name: "premium"`
  - Expected: `amount: 99900`
- [ ] `plan_name: "free"` → `400` — free plan needs no payment
- [ ] Unknown plan name → `404`
- [ ] Missing `plan_name` field → `404` (plan "" not found)
- [ ] Customer token → `403`
- [ ] No token → `401`
- [ ] Vendor without store → `404`

---

## C — Razorpay — Verify Payment

- [ ] `POST /api/v1/billing/payment/verify/` with all 4 fields
  - Expected: `200` — subscription object, `is_active: true`
- [ ] Subscription shows correct plan, `days_left ≈ 29`
- [ ] Wallet shows topup transaction with `reference_id = pay_DEV_test12345`
- [ ] Transaction history shows 2 entries: `topup` (+499) then `subscription` (−499)
- [ ] Call verify again with same `razorpay_payment_id`
  - Expected: subscription renewed (same subscription row updated), second topup created — this is intentional (Razorpay deduplication happens at their end)
- [ ] Missing `razorpay_order_id` → `400` — all fields required
- [ ] Missing `plan_name` → `400` — all fields required
- [ ] Empty body → `400`
- [ ] Customer token → `403`

---

## D — Razorpay — Webhook

- [ ] `POST /api/v1/billing/payment/webhook/` with `event: "payment.captured"`
  - Body contains correct `store_id` in notes
  - Expected: `200 {"status": "ok"}`
  - Wallet topped up, subscription activated
- [ ] Call same webhook again with same `payment_id` (duplicate)
  - Expected: `200 {"status": "already_processed"}` (idempotency guard)
  - No duplicate transaction created
- [ ] Unknown event (e.g. `"payment.failed"`) → `200 {"status": "ok"}` (ignored gracefully)
- [ ] Invalid JSON body → `400`
- [ ] (Production only) Wrong `X-Razorpay-Signature` → `400 invalid_signature`
- [ ] Webhook endpoint requires NO JWT (`authentication_classes = []` confirmed)

---

## E — Full Happy Path (end to end)

- [ ] `GET /billing/plans/` — see all 3 plans and prices
- [ ] `GET /billing/wallet/` — balance = 0.00
- [ ] `POST /billing/payment/initiate/` with `plan_name: "basic"` → save `order_id`
- [ ] `POST /billing/payment/verify/` → subscription activated
- [ ] `GET /billing/subscription/` → `is_active: true`, plan = basic
- [ ] `GET /billing/wallet/` → balance reflects net (topup − subscription = 0 for same plan)
- [ ] `GET /billing/transactions/` → 2 records (topup + subscription)
- [ ] Vendor inbox (`GET /notifications/`) → `wallet_topup` notification created
- [ ] `POST /billing/payment/initiate/` with `plan_name: "premium"` → upgrade
- [ ] `POST /billing/payment/verify/` → subscription upgraded, new expiry set

---

## F — Production Stack (local simulation)

- [ ] `cp .env.example .env.production` and fill values
- [ ] `make prod-up` — stack starts with production settings
- [ ] `curl http://localhost/api/v1/health/` → `200 {"status": "ok"}`
- [ ] `curl http://localhost/api/docs/` → `403` (Swagger blocked in prod nginx)
- [ ] `make prod-logs` — logs are JSON structured (CloudWatch format)
- [ ] `make prod-down` — stops cleanly

---

## G — CI/CD (GitHub Actions)

- [ ] Push to `sprint-12-production` branch → Actions runs lint + test jobs
- [ ] `main` branch push → lint → test → build → deploy-staging auto-triggers
- [ ] Production deploy requires manual approval in GitHub Actions UI
- [ ] Merge PR → all checks pass in Actions

---

## H — Django Admin Checks

- [ ] Admin → Billing → Transactions — shows topup and subscription records
- [ ] Admin → Billing → Subscriptions — shows active subscription with correct plan and expiry
- [ ] Admin → Billing → Plans — all 3 plans (free/basic/premium) present and active

---

## Error Reference

| Endpoint | Error | Expected status |
|----------|-------|----------------|
| `initiate` — free plan | `validation_error` | `400` |
| `initiate` — unknown plan | `not_found` | `404` |
| `verify` — missing fields | `validation_error` | `400` |
| `verify` — wrong signature (prod) | `payment_failed` | `400` |
| `webhook` — wrong signature (prod) | `invalid_signature` | `400` |
| `webhook` — duplicate payment | `already_processed` | `200` |
| Any billing endpoint — no store | `not_found` | `404` |
| Any billing endpoint — customer token | Forbidden | `403` |

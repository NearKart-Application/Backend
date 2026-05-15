# Sprint 7 — Billing + Wallet

**Status:** Done ✅  
**Verified on:** 2026-05-15

---

## What This Sprint Does

Vendors have a wallet on their store. They top up the wallet and use that balance to subscribe to a plan.
The plan controls how many videos and products they can have active.

---

## Plans

| Plan | Price | Videos | Products |
|------|-------|--------|----------|
| Free | ₹0 | 3 | 10 |
| Basic | ₹499/month | 20 | 50 |
| Premium | ₹999/month | Unlimited | Unlimited |

Seed plans once after migration:
```
docker compose exec django python manage.py seed_plans
```

---

## Endpoints

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| GET | `/api/v1/billing/plans/` | Public | List all plans |
| GET | `/api/v1/billing/wallet/` | Vendor JWT | Current wallet balance |
| POST | `/api/v1/billing/topup/` | Vendor JWT | Add money to wallet |
| POST | `/api/v1/billing/subscribe/` | Vendor JWT | Buy a plan |
| GET | `/api/v1/billing/subscription/` | Vendor JWT | Current subscription status |
| GET | `/api/v1/billing/transactions/` | Vendor JWT | Wallet transaction history |

---

## Plan Enforcement

Checked at upload/create time — not at read time.

| Action | Enforcement |
|--------|-------------|
| `POST /videos/request-upload/` | `403 plan_limit_reached` if at video limit |
| `POST /products/` | `403 plan_limit_reached` if at product limit |

A vendor with no subscription (or expired) is treated as Free plan (3 videos, 10 products).

---

## Celery Beat Task

`billing.expire_subscriptions` — runs daily at midnight IST.
Marks all subscriptions past `expires_at` as `is_active=False`.

The schedule is registered in `CELERY_BEAT_SCHEDULE` in `config/settings/base.py`.

---

## Dev Mode Notes

- Top-up is instant — no Razorpay integration yet
- `reference_id` is auto-generated as `DEV-TOPUP-<timestamp>`
- Subscription `reference_id` is `SUB-BASIC-<timestamp>` etc.

---

## Files Changed

| File | Change |
|------|--------|
| `apps/billing/models.py` | Plan, Subscription, Transaction models |
| `apps/billing/services.py` | BillingService — topup, subscribe, limits, expire |
| `apps/billing/serializers.py` | PlanSerializer, SubscriptionSerializer, TransactionSerializer |
| `apps/billing/views.py` | 6 views |
| `apps/billing/urls.py` | 6 URL patterns |
| `apps/billing/tasks.py` | `expire_subscriptions` Celery task |
| `apps/billing/admin.py` | Plan, Subscription, Transaction admin |
| `apps/billing/management/commands/seed_plans.py` | Seeds 3 default plans |
| `apps/billing/migrations/0001_initial.py` | Creates 3 billing tables |
| `apps/videos/views.py` | Video limit check in VideoUploadRequestView |
| `apps/products/views.py` | Product limit check in ProductCreateView |
| `config/settings/base.py` | CELERY_BEAT_SCHEDULE added |

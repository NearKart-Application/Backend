# Sprint 7 — Testing Checklist

**Verified on:** 2026-05-15  
**Environment:** Docker local, dev mode

---

## Plans (Public)

- [x] GET `/billing/plans/` — returns 3 plans: Free, Basic, Premium
- [x] Each plan has: `name`, `display_name`, `price`, `duration_days`, `video_limit`, `product_limit`, `video_limit_display`, `product_limit_display`, `description`
- [x] Premium shows `video_limit_display: "Unlimited"` and `product_limit_display: "Unlimited"`
- [x] No auth required — public endpoint

## Wallet

- [x] GET `/billing/wallet/` with vendor token → `{store_name, wallet_balance}`
- [x] Initial balance is `0.00`
- [x] GET without auth → 401
- [x] GET with customer token → 403 — Vendor access only
- [x] GET without a store → 404

## Top-up

- [x] POST `/billing/topup/` `{"amount": "1000.00"}` → 200, balance increases
- [x] Response has: `message`, `amount_added`, `wallet_balance`, `transaction_id`
- [x] POST with `amount: 0` → 400 — amount must be a positive number
- [x] POST with `amount: -100` → 400 — validation error
- [x] POST with `amount: "abc"` → 400 — validation error
- [x] POST without auth → 401

## Subscribe

- [x] POST `/billing/subscribe/` `{"plan_name": "basic"}` after ₹1000 topup → 200, subscription created
- [x] Response has full SubscriptionSerializer: plan details, started_at, expires_at, is_active, days_left
- [x] `days_left` is 29 or 30 (30-day plan)
- [x] Wallet balance reduced by ₹499 after subscribing Basic
- [x] POST `{"plan_name": "premium"}` with insufficient balance → 400 — insufficient_balance
- [x] POST `{"plan_name": "free"}` → 200, no wallet deduction
- [x] POST `{"plan_name": "invalid"}` → 404 — Plan not found
- [x] Subscribe again (renew) → updates existing subscription in-place

## Subscription Status

- [x] GET `/billing/subscription/` → full subscription + plan details
- [x] No subscription yet → 404 — No subscription found
- [x] GET without auth → 401

## Transaction History

- [x] GET `/billing/transactions/` → array, ordered newest first
- [x] Top-up shows: `type: "topup"`, positive `amount`, `balance_after`
- [x] Subscription shows: `type: "subscription"`, negative `amount`, `balance_after`
- [x] Free plan subscription creates NO transaction (no money movement)
- [x] GET without auth → 401

## Plan Enforcement — Video Limit

- [x] On Free plan (3 video limit): upload 3 videos successfully
- [x] 4th video upload → 403 — plan_limit_reached with message about limit
- [x] After upgrading to Basic → can upload again (limit is 20)

## Plan Enforcement — Product Limit

- [x] On Free plan (10 product limit): create 10 products successfully
- [x] 11th product → 403 — plan_limit_reached
- [x] After upgrading → can create again

## Celery Task

- [x] `expire_subscriptions` task exists and runs: `docker compose exec django python manage.py shell -c "from apps.billing.tasks import expire_subscriptions; print(expire_subscriptions.delay())"`
- [x] Subscription with past `expires_at` gets `is_active=False` after task runs

## Admin

- [x] Plan, Subscription, Transaction visible at http://localhost:8000/admin/
- [x] Can search subscriptions by store name / phone
- [x] Can toggle Plan.is_active in list view

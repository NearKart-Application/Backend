# Sprint 7 — Postman Guide

## Environment Variables

| Variable | Value | Set by |
|----------|-------|--------|
| `base_url` | `http://localhost:8000/api/v1` | Manual |
| `vendor_token` | (empty) | OTP verify script |
| `store_id` | (empty) | Sprint 3 |

---

## Collection: Sprint 7 — Billing

### 1. List Plans (Public)
- **Method:** GET
- **URL:** `{{base_url}}/billing/plans/`
- **Auth:** None
- **Expected:** Array of 3 plans — Free, Basic, Premium

---

### 2. Wallet Balance
- **Method:** GET
- **URL:** `{{base_url}}/billing/wallet/`
- **Auth:** Bearer `{{vendor_token}}`
- **Expected:** `{"store_name": "...", "wallet_balance": "0.00"}`

---

### 3. Top Up Wallet
- **Method:** POST
- **URL:** `{{base_url}}/billing/topup/`
- **Auth:** Bearer `{{vendor_token}}`
- **Body:**
```json
{ "amount": "1000.00" }
```
- **Expected:** `{"message": "₹1000.00 added to wallet.", "wallet_balance": "1000.00", ...}`

---

### 4. Subscribe to Basic Plan
- **Method:** POST
- **URL:** `{{base_url}}/billing/subscribe/`
- **Auth:** Bearer `{{vendor_token}}`
- **Body:**
```json
{ "plan_name": "basic" }
```
- **Expected:** Full subscription object with `is_active: true`, `days_left: 29`

---

### 5. Subscription Status
- **Method:** GET
- **URL:** `{{base_url}}/billing/subscription/`
- **Auth:** Bearer `{{vendor_token}}`
- **Expected:** Current plan, expiry date, days_left

---

### 6. Transaction History
- **Method:** GET
- **URL:** `{{base_url}}/billing/transactions/`
- **Auth:** Bearer `{{vendor_token}}`
- **Expected:** Array — most recent first. Top-up shows positive amount, subscription shows negative.

---

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| 400 — amount must be positive | `amount: 0` or negative | Use amount > 0 |
| 400 — insufficient_balance | Not enough in wallet | Top up first |
| 404 — Plan not found | Wrong plan_name | Use: free, basic, premium |
| 403 — plan_limit_reached | Video/product over plan limit | Upgrade plan or delete items |
| 404 — No subscription found | Never subscribed | POST /billing/subscribe/ first |
| 403 — Vendor access only | Using customer token | Use vendor token |

# NearKart Backend — Testing Guide

## Quick Start

```bash
cd nearkart_backend

# 1. Install dependencies (first time only)
make install

# 2. Run all tests
make test

# 3. Run tests + generate full HTML report
make test-report
```

---

## Commands

| Command | What it does |
|---------|-------------|
| `make test` | Run all 310 tests, print pass/fail in terminal |
| `make test-cov` | Run tests + show coverage % per file in terminal |
| `make test-report` | Run tests + generate HTML report + JUnit XML + coverage HTML |
| `pytest tests/test_auth.py -v` | Run one specific test file |
| `pytest tests/test_auth.py::test_otp_send_voice_delivery -v` | Run one specific test |
| `pytest -k "voice"` | Run all tests whose name contains "voice" |
| `pytest -x` | Stop after first failure |

---

## Where Are the Reports?

After running `make test-report`, three outputs are saved to `test-results/`:

```
test-results/
├── report.html          ← Open in browser — full test report with pass/fail table
├── junit.xml            ← Machine-readable XML (for CI tools like Jenkins / GitHub Actions)
└── coverage/
    └── index.html       ← Open in browser — which lines of code are covered
```

> `test-results/` is in `.gitignore` — reports stay local, not pushed to GitHub.

---

## How to Read the HTML Report (`report.html`)

Open `test-results/report.html` in any browser.

| Section | What to look for |
|---------|-----------------|
| **Summary bar** | Green = passed, Red = failed, Yellow = error |
| **Test table** | Each row = one test. Click row to expand traceback |
| **Duration** | Slow tests (> 1 s) may indicate a DB or API bottleneck |
| **Environment** | Shows Django settings, Python version, pytest version |

**Status meanings:**

| Status | Meaning |
|--------|---------|
| `PASSED` | Test ran and assertion succeeded |
| `FAILED` | Assertion failed — check the traceback |
| `ERROR` | Test crashed before reaching the assertion (setup error) |
| `XFAIL` | Expected failure — known issue |
| `SKIPPED` | Test was skipped (marker condition not met) |

---

## How to Read Coverage (`coverage/index.html`)

Open `test-results/coverage/index.html` in any browser.

- **Green lines** — covered by at least one test
- **Red lines** — NOT covered — no test exercises this code path
- **Coverage %** — aim for > 80% on critical apps (auth, products, stores)

Click any file to see line-by-line coverage.

---

## Test File Map

| Test File | Sprints | What it covers |
|-----------|---------|----------------|
| `test_auth.py` | S2, S28 | OTP send/verify, JWT, logout, profile, voice OTP |
| `test_videos.py` | S4, S28 | Upload, confirm, feed, like, delete, download, demo video |
| `test_products.py` | S3, S26, S28 | Product CRUD, generate-code, demo video fetch |
| `test_stores.py` | S3, S23 | Store CRUD, nearby, follow, hours |
| `test_reviews.py` | S16 | Create review, list, vendor reply, eligibility |
| `test_reservations.py` | S9 | Reserve, confirm, cancel |
| `test_loyalty.py` | S15 | Balance, history, apply referral, redeem |
| `test_discount_codes.py` | S23, S25 | Discount codes CRUD, apply, broadcast channels |
| `test_billing.py` | S7 | Plans, wallet, topup, subscribe |
| `test_notifications.py` | S11, S14 | Push notifications, device tokens |
| `test_chat.py` | S5 | Conversations, messages |
| `test_groups.py` | S10 | Group CRUD, members |
| `test_blacklist.py` | S6 | Block/unblock |
| `test_admin_panel.py` | S8, S20, S21 | Users, stores, create/suspend, categories, banners, coupons |
| `test_analytics.py` | S8 | Vendor dashboard |
| `test_celery_tasks.py` | S13 | Background tasks |
| `test_sprint19.py` | S19 | Search filters, follow feed, invoices |
| `test_health.py` | S1 | Health check endpoint |

**Total: 310 tests**

---

## Running a Specific Sprint's Tests

```bash
# Sprint 28 only (voice OTP + product demo video)
pytest tests/test_auth.py -k "voice" -v
pytest tests/test_videos.py -k "demo" -v
pytest tests/test_products.py -k "demo or generate" -v

# Sprint 16 (reviews)
pytest tests/test_reviews.py -v

# Sprint 15 (loyalty)
pytest tests/test_loyalty.py -v

# All admin tests (Sprints 20-21)
pytest tests/test_admin_panel.py -v
```

---

## CI / GitHub Actions

To run tests automatically on every push, add this workflow:

**`.github/workflows/tests.yml`**
```yaml
name: Backend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgis/postgis:15-3.3
        env:
          POSTGRES_DB: nearkart_test
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        ports: ["5432:5432"]
      redis:
        image: redis:7
        ports: ["6379:6379"]

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - name: Install dependencies
        run: cd nearkart_backend && pip install -r requirements/development.txt
      - name: Run tests
        run: cd nearkart_backend && make test-report
      - name: Upload HTML report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-report
          path: nearkart_backend/test-results/
```

After this is set up, every push to GitHub will run all 310 tests automatically. The HTML report is uploaded as a downloadable artifact on GitHub Actions.

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `django.db.utils.OperationalError` | DB not running | Run `make docker-up` or check PostgreSQL |
| `ModuleNotFoundError: apps.loyalty` | Missing migration | Run `make migrate` |
| `AssertionError: 404 != 200` | Wrong URL in test | Check `urls.py` for correct path |
| `fixture 'store' not found` | Missing fixture import | Check `conftest.py` |
| `pytest-html not found` | Missing package | Run `make install` |

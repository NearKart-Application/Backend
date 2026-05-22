# NearKart Backend — Test Runner Guide

How to install, run, and filter the full test suite.  
No Docker required — all tests use an in-memory SpatiaLite database.

---

## 1. Prerequisites

```bash
# Activate your virtual environment first
source nearkart_venv/bin/activate          # macOS / Linux
nearkart_venv\Scripts\activate             # Windows

# Install all dev dependencies (includes pytest, coverage tools)
pip install -r requirements/development.txt
```

**Key packages installed:**

| Package | Purpose |
|---|---|
| `pytest` | Test runner |
| `pytest-django` | Django integration (DB, settings) |
| `pytest-cov` | Code coverage reports |
| `pytest-asyncio` | Async test support |
| `factory-boy` | Test data factories |

---

## 2. Run All Tests

```bash
# Simplest — run everything
pytest

# Or via Make shortcut
make test
```

This automatically uses `config.settings.testing` (defined in `pytest.ini`) which:
- Uses an in-memory SpatiaLite database (no real DB needed)
- Mocks AWS, OTP, Firebase, Razorpay (dev-mode bypasses)
- Runs Celery tasks synchronously (no Redis needed)

---

## 3. Run a Single Test File

```bash
pytest tests/test_auth.py
pytest tests/test_billing.py
pytest tests/test_videos.py
```

---

## 4. Run a Single Test Function

```bash
# Pattern:  pytest tests/<file>.py::<test_function_name>
pytest tests/test_auth.py::test_send_otp_success
pytest tests/test_billing.py::test_wallet_topup
pytest tests/test_videos.py::test_video_download_presigned_url
```

---

## 5. Run Tests by Keyword (name match)

```bash
# Runs any test whose name contains the keyword
pytest -k "otp"              # all OTP-related tests
pytest -k "subscription"     # all subscription tests
pytest -k "video"            # all video tests
pytest -k "admin"            # all admin panel tests
pytest -k "expire"           # all expiry/task tests
pytest -k "auth or billing"  # combine with or / and / not
```

---

## 6. All Test Files & What They Cover

| File | Module | Tests |
|---|---|---|
| `tests/test_health.py` | Health Check | 1 — `/health/` endpoint |
| `tests/test_auth.py` | Auth | 18 — OTP send/verify, login, refresh, logout, profile, device token |
| `tests/test_stores.py` | Stores | 16 — create, update, nearby search, follow/unfollow, hours |
| `tests/test_products.py` | Products | 11 — CRUD, permissions, vendor-only actions |
| `tests/test_videos.py` | Videos | 22 — upload, confirm, feed, like, delete, download presigned URL |
| `tests/test_billing.py` | Billing | 22 — plans, wallet, topup, subscribe, Razorpay initiate/verify/webhook |
| `tests/test_notifications.py` | Notifications | 13 — inbox, unread count, mark read, device token, service layer |
| `tests/test_reservations.py` | Reservations | 11 — create, list, confirm, cancel, expire task |
| `tests/test_blacklist.py` | Blacklist | 6 — status check, enforcement, admin override, service layer |
| `tests/test_chat.py` | Chat | 10 — create conversation, list, message history, permissions |
| `tests/test_groups.py` | Groups | 12 — create, list, delete, add/remove members, join, share, finalize |
| `tests/test_analytics.py` | Analytics | 4 — vendor dashboard, auth/role enforcement |
| `tests/test_admin_panel.py` | Admin Panel | 8 — list users, toggle active, list stores, verify store |
| `tests/test_celery_tasks.py` | Celery Tasks | 10 — expire subscriptions, expire reservations, notify/delete expiring videos |

**Total: 145+ tests across 14 files**

---

## 7. Run Tests for a Specific Module (keyword group)

```bash
# Auth module
pytest tests/test_auth.py -v

# All Celery background task tests
pytest tests/test_celery_tasks.py -v

# Everything related to stores + products
pytest tests/test_stores.py tests/test_products.py -v

# All permission/access control tests
pytest -k "forbidden or unauthorized or requires_auth or non_admin"
```

---

## 8. Coverage Report

```bash
# Print coverage in terminal
pytest --cov=apps --cov-report=term-missing

# Or via Make shortcut
make test-cov

# Generate HTML report (opens in browser)
pytest --cov=apps --cov-report=html
open htmlcov/index.html      # macOS
start htmlcov/index.html     # Windows
```

Coverage target is **75%** (CI gate). Focus areas if below target:
- `apps/billing/` — payment flows
- `apps/videos/` — upload/processing pipeline
- `apps/notifications/` — service + FCM layer

---

## 9. Verbose Output & Debugging

```bash
# Show each test name as it runs
pytest -v

# Show full traceback on failure (default is --tb=short)
pytest --tb=long

# Stop at first failure
pytest -x

# Stop after N failures
pytest --maxfail=3

# Show print() output during tests
pytest -s

# Combine: verbose + stop on first fail + show prints
pytest -v -x -s tests/test_billing.py
```

---

## 10. Markers (Test Categories)

Tests are tagged with markers defined in `pytest.ini`:

| Marker | Meaning | Run command |
|---|---|---|
| `unit` | No external services | `pytest -m unit` |
| `integration` | Requires Docker | `pytest -m integration` |
| `geo` | Requires PostGIS | `pytest -m geo` |
| `slow` | Long-running tests | `pytest -m slow` |

Most tests in `tests/` have no marker — they run without Docker.

---

## 11. Quick Reference

```bash
# ── Most Common Commands ───────────────────────────────────────

# Run everything
pytest

# Run one file
pytest tests/test_auth.py

# Run one test
pytest tests/test_auth.py::test_send_otp_success

# Run by keyword
pytest -k "video"

# Run with coverage
pytest --cov=apps --cov-report=term-missing

# Run verbosely, stop on first failure
pytest -v -x

# Run all, skip slow
pytest -m "not slow"
```

---

## 12. CI / GitHub Actions

Tests run automatically on every push via `.github/workflows/ci.yml`.

The CI pipeline:
1. Sets up Python + SpatiaLite
2. Installs `requirements/development.txt`
3. Runs `pytest --cov=apps --cov-report=xml`
4. Fails if coverage drops below **75%**

To replicate CI locally:
```bash
pytest --cov=apps --cov-report=term-missing --cov-fail-under=75
```

---

## 13. Test Settings (How Dev Bypasses Work)

All tests run against `config/settings/testing.py`. The following services are auto-mocked:

| Service | How it's bypassed | What you get in tests |
|---|---|---|
| OTP (Twilio) | `DEV_FIXED_OTP=123456` in testing settings | Always returns OTP `123456` |
| AWS S3 | `AWS_ACCESS_KEY_ID` contains `EXAMPLE` | Returns mock URLs like `https://mock-s3.dev/...` |
| Firebase FCM | App not initialized | Logs to console, no real push sent |
| Razorpay | `RAZORPAY_KEY_ID` contains `PLACEHOLDER` | Returns mock order IDs |
| Celery | `CELERY_TASK_ALWAYS_EAGER=True` | Tasks run synchronously inline |
| Database | SpatiaLite in-memory | No real DB needed, wiped after each test |

---

*Branch: `sprint-13-tests` | Last updated: Sprint 13*

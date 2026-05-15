# NearKart Backend — How to Run & Test

> Complete guide to start the server locally and test the Auth API.
> Follow every step in order. Do not skip steps.

---

## Two Ways to Run

| Method | When to use |
|--------|-------------|
| **Option A — Local (venv)** | Quick code editing, running single files, IDE auto-complete |
| **Option B — Docker** | Full stack (Postgres + Redis + Celery). Required for real API testing |

> Use **both together**: venv for writing code + IDE support, Docker for running the full stack.

---

## PART 1 — Python Virtual Environment (venv) Setup

> Do this FIRST before anything else. A virtual environment keeps project packages
> isolated from your Mac's system Python.

### Step 1 — Check your Python version

```bash
python3 --version
```

Expected: `Python 3.11.x` or higher. If lower, install Python 3.11 from python.org.

---

### Step 2 — Go to the project folder

```bash
cd /Users/hazeevali/Documents/NearKart/Backend/nearkart_backend
```

---

### Step 3 — Create the virtual environment

```bash
python3 -m venv venv
```

This creates a `venv/` folder inside your project. It contains an isolated Python install.

```
nearkart_backend/
├── venv/               ← created now (never commit this to Git)
│   ├── bin/
│   │   ├── python      ← isolated Python
│   │   └── pip         ← isolated pip
│   └── lib/
│       └── python3.11/
│           └── site-packages/  ← all packages install here
├── apps/
├── config/
└── ...
```

---

### Step 4 — Activate the virtual environment

```bash
source venv/bin/activate
```

Your terminal prompt will change to show `(venv)` at the start:

```
# BEFORE activation:
hazeevali@Mac nearkart_backend %

# AFTER activation:
(venv) hazeevali@Mac nearkart_backend %
```

> **Every time you open a new terminal**, you must run `source venv/bin/activate` again.
> The venv only stays active for that terminal session.

---

### Step 5 — Upgrade pip inside venv

```bash
pip install --upgrade pip
```

Always upgrade pip first. Never use `pip3` — just `pip` inside the venv.

---

### Step 6 — Install project dependencies

```bash
pip install -r requirements/development.txt
```

This installs everything: Django, DRF, Celery, Twilio, Pytest, Black, etc.

Watch for any errors. Common fix if you see `ERROR: Failed building wheel`:

```bash
# On Mac, install Xcode tools first:
xcode-select --install
# Then retry:
pip install -r requirements/development.txt
```

Verify installation:

```bash
pip list
```

You should see packages like `Django`, `celery`, `pytest`, etc.

---

### Step 7 — Verify Django is installed

```bash
python -m django --version
```

Expected: `4.2.13`

---

### Step 8 — Deactivate when done

```bash
deactivate
```

Prompt goes back to normal. Run `source venv/bin/activate` again next time.

---

### venv Quick Reference

```bash
# Create (once only)
python3 -m venv venv

# Activate (every new terminal session)
source venv/bin/activate

# Install packages
pip install -r requirements/development.txt

# Install a single new package
pip install package-name

# See installed packages
pip list

# Deactivate
deactivate
```

---

## PART 2 — Environment Variables (.env file)

> The `.env` file holds secrets (DB password, API keys). Never commit it to Git.

### Step 1 — Create your .env file

Make sure venv is active, then:

```bash
cp .env.example .env
```

### Step 2 — Generate a SECRET_KEY

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy the output. It looks like:
```
django-insecure-abc123xyz-very-long-random-string-here
```

### Step 3 — Edit your .env file

```bash
code .env
```

Update these values (minimum required to run):

```bash
# Replace with your generated key
SECRET_KEY=django-insecure-abc123xyz-your-generated-key-here

# Keep as-is for local development
DB_PASSWORD=nearkart_dev_password_change_in_prod
DEBUG=True

# This lets you test OTP without real Twilio account
# OTP will always be 123456 in development
DEV_FIXED_OTP=123456
```

Leave all other values (AWS, Twilio, Firebase) as the example placeholders for now.
They are only needed when testing those specific features.

---

## PART 3 — Running with Docker (Full Stack)

> Docker runs Postgres, Redis, Celery alongside Django.
> You need Docker Desktop open (whale icon in Mac menu bar).

### Step 1 — Make sure Docker Desktop is running

```bash
docker info
```

If you see `ERROR: Cannot connect to the Docker daemon` → open Docker Desktop from Applications.

### Step 2 — Build and start all services

```bash
# Make sure you are in the project folder
cd /Users/hazeevali/Documents/NearKart/Backend/nearkart_backend

# First time (builds Docker image, takes 3-5 min)
docker compose up --build

# After first time (just start, takes ~10 sec)
docker compose up
```

What's running after this:

```
Service         Port    Purpose
─────────────────────────────────────────
nginx           :80     Main entry (routes to django/daphne)
django          :8000   REST API
daphne          :8001   WebSocket server
postgres        :5432   Database (PostGIS)
redis           :6379   Cache + Celery broker
celery          -       Background tasks (SMS, video processing)
celery-beat     -       Scheduled tasks (cron jobs)
```

### Step 3 — Verify it's working

Open a **new terminal tab** (keep docker compose running in the first tab):

```bash
curl http://localhost:8000/api/v1/health/
```

Expected:
```json
{"status": "ok"}
```

Open Swagger UI in browser:
```
http://localhost:8000/api/docs/
```

> You will see the full NearKart API documentation with all endpoints listed.

---

### How venv + Docker work together

```
Your Mac
│
├── venv/          ← Local Python env for IDE, linting, running scripts
│   └── (Django, pytest, black, etc.)
│
└── Docker         ← Runs the full stack with database and services
    ├── Django container (has its own venv inside at /app/venv)
    ├── Postgres container
    ├── Redis container
    └── Celery container
```

You write code with your Mac venv (VS Code sees the packages, auto-complete works).
Docker runs the actual server with the same packages inside its own venv.

---

## PART 4 — Testing the Auth API in Postman

### Setup Postman Environment (do once)

1. Open Postman → Click **Environments** (left sidebar)
2. Click **+** → Name it `NearKart Local`
3. Add these variables:

| Variable | Initial Value |
|----------|--------------|
| `base_url` | `http://localhost:8000/api/v1` |
| `access_token` | (leave empty) |
| `refresh_token` | (leave empty) |

4. Select `NearKart Local` from the environment dropdown (top right of Postman)

---

### Test 1 — Send OTP

```
Method : POST
URL    : {{base_url}}/auth/otp/send/
Body   : raw → JSON
```

```json
{
    "phone_number": "+919876543210"
}
```

Expected `200 OK`:
```json
{
    "message": "OTP sent successfully"
}
```

> OTP is always `123456` in dev (set by `DEV_FIXED_OTP` in your `.env`).

---

### Test 2 — Verify OTP → Get Tokens

```
Method : POST
URL    : {{base_url}}/auth/otp/verify/
Body   : raw → JSON
```

```json
{
    "phone_number": "+919876543210",
    "otp": "123456"
}
```

Expected `200 OK`:
```json
{
    "message": "Login successful",
    "user": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "phone_number": "+919876543210",
        "role": "customer",
        "full_name": "",
        "email": "",
        "created_at": "2025-05-14T10:00:00Z"
    },
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Auto-save tokens** — paste this in the Postman **Tests** tab of this request:

```javascript
const r = pm.response.json();
pm.environment.set("access_token", r.access);
pm.environment.set("refresh_token", r.refresh);
```

Now `{{access_token}}` is auto-filled for all future requests.

---

### Test 3 — Get Current User (Protected)

```
Method        : GET
URL           : {{base_url}}/auth/me/
Authorization : Bearer Token → Token: {{access_token}}
```

Expected `200 OK` — your user profile.

**Test without token** (remove Authorization) → Expected `401 Unauthorized`:
```json
{
    "error": "authentication_failed",
    "message": "Authentication credentials were not provided.",
    "code": "NOT_AUTHENTICATED",
    "details": {}
}
```

---

### Test 4 — Update Location

```
Method        : PUT
URL           : {{base_url}}/auth/me/location/
Authorization : Bearer Token → {{access_token}}
Body          : raw → JSON
```

```json
{
    "latitude": 13.0827,
    "longitude": 80.2707
}
```

Expected `200 OK`:
```json
{
    "message": "Location updated"
}
```

---

### Test 5 — Logout

```
Method        : POST
URL           : {{base_url}}/auth/logout/
Authorization : Bearer Token → {{access_token}}
Body          : raw → JSON
```

```json
{
    "refresh": "{{refresh_token}}"
}
```

Expected `200 OK`:
```json
{
    "message": "Logged out successfully"
}
```

---

### Test 6 — Error Cases

**Wrong OTP:**
```json
POST /auth/otp/verify/
{ "phone_number": "+919876543210", "otp": "000000" }
```
→ `400` with `"Invalid OTP. 4 attempt(s) remaining."`

**Bad phone format (missing +91):**
```json
POST /auth/otp/send/
{ "phone_number": "9876543210" }
```
→ `400` validation error

---

## PART 5 — Django Admin Panel

```bash
# Create superuser (run once)
docker compose exec django python manage.py createsuperuser
```

Enter phone: `+919999999999` → follow prompts.

Open: `http://localhost:8000/admin/`

You can see and manage: **Users**, **OTP Tokens**, **Device Tokens**.

---

## PART 6 — Useful Commands

```bash
# ── venv ────────────────────────────────────────────────────
source venv/bin/activate          # activate venv
deactivate                        # deactivate venv
pip install -r requirements/development.txt  # install all deps
pip freeze > requirements/base.txt           # save new packages

# ── Docker ──────────────────────────────────────────────────
docker compose up --build         # first time build + start
docker compose up                 # start (after first build)
docker compose up -d              # start in background
docker compose down               # stop all services
docker compose down -v            # stop + delete database data

# ── Django (inside Docker) ──────────────────────────────────
docker compose exec django python manage.py migrate
docker compose exec django python manage.py createsuperuser
docker compose exec django python manage.py shell

# ── Tests ────────────────────────────────────────────────────
docker compose exec django pytest -v
docker compose exec django pytest apps/auth_app/tests/ -v
docker compose exec django pytest --cov=apps -v

# ── Logs ─────────────────────────────────────────────────────
docker compose logs -f django     # Django logs
docker compose logs -f celery     # Celery/SMS task logs
docker compose logs -f postgres   # Database logs
```

---

## PART 7 — Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `Cannot connect to Docker daemon` | Docker Desktop not open | Open Docker Desktop |
| `Port 5432 already in use` | Local Postgres running | `brew services stop postgresql` |
| `Port 6379 already in use` | Local Redis running | `brew services stop redis` |
| `ModuleNotFoundError` | venv not activated | `source venv/bin/activate` |
| `pip: command not found` | venv not activated | `source venv/bin/activate` |
| `SECRET_KEY not set` | `.env` missing or wrong | `cp .env.example .env` + add SECRET_KEY |
| `relation does not exist` | Migrations not run | `docker compose exec django python manage.py migrate` |
| `401 on /me/` | Token expired | Re-run `/otp/verify/` to get new tokens |
| `OTP expired` | Waited 5+ minutes | Re-run `/otp/send/` |

---

*Last updated: Sprint 2 — Auth Module*

# Nearspot — How to Run the Application

Complete guide to running the Nearspot backend and mobile app locally for development and testing.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Project Structure](#2-project-structure)
3. [Running the Backend](#3-running-the-backend)
4. [Running the Mobile App](#4-running-the-mobile-app)
5. [Connecting Mobile App to Backend](#5-connecting-mobile-app-to-backend)
6. [Admin Panel](#6-admin-panel)
7. [Useful Commands](#7-useful-commands)
8. [Ports Reference](#8-ports-reference)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Prerequisites

Make sure the following are installed on your Mac before starting.

### Required Tools

| Tool | Purpose | Install |
|---|---|---|
| Docker Desktop | Runs backend services | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop) |
| Android Studio | Builds & runs the mobile app | [developer.android.com/studio](https://developer.android.com/studio) |
| Homebrew | macOS package manager | `brew.sh` |

### Check everything is installed

```bash
docker --version          # Docker version 24+
docker-compose --version  # Docker Compose version 2+
```

---

## 2. Project Structure

```
NearSpot/
├── Backend/
│   ├── nearkart_backend/     ← Django backend (this repo)
│   │   ├── apps/             ← All Django apps
│   │   ├── config/           ← Settings, URLs, Celery
│   │   ├── docker-compose.yml
│   │   ├── Dockerfile
│   │   └── .env              ← Local environment variables
│   └── nearkart_venv/        ← Python virtual environment (for tests only)
│
└── Mobile-App/               ← Android app (Kotlin + Jetpack Compose)
    ├── app/                  ← Shared library module
    ├── app-customer/         ← Customer APK
    ├── app-vendor/           ← Vendor APK
    └── local.properties      ← Local dev URLs and API keys
```

---

## 3. Running the Backend

### Step 1 — Open Docker Desktop

Open **Docker Desktop** from your Applications folder.
Wait until the whale icon in the menu bar stops animating (Docker is ready).

### Step 2 — Go to backend directory

```bash
cd /Users/hazeevali/Documents/NearSpot/Backend/nearkart_backend
```

### Step 3 — Start all services

```bash
docker-compose up -d
```

This starts all 9 services automatically:

| Service | Description |
|---|---|
| `postgres` | PostgreSQL 15 + PostGIS database |
| `pgbouncer` | Database connection pooler |
| `redis` | Cache, queues, WebSocket channels |
| `django` | Django REST API (Daphne ASGI) |
| `daphne` | WebSocket server |
| `celery` | Background task worker |
| `celery-transcoding` | Video processing worker |
| `celery-beat` | Scheduled task runner |
| `nginx` | Reverse proxy + static files |

### Step 4 — Verify everything is running

```bash
docker-compose ps
```

All services should show `Up` or `healthy`.

### Step 5 — Check the server is working

Open in browser:
```
http://localhost/api/v1/health/
```

Expected response:
```json
{"status": "ok", "db": "ok", "redis": "ok", "version": "1.0.0", "environment": "development"}
```

### Step 6 — View live logs (optional)

```bash
docker-compose logs -f django
```

Press `Ctrl + C` to stop watching logs.

---

## 4. Running the Mobile App

### Step 1 — Open the project in Android Studio

1. Open **Android Studio**
2. Click **Open**
3. Navigate to `/Users/hazeevali/Documents/NearSpot/Mobile-App`
4. Click **OK**
5. Wait for Gradle sync to finish

### Step 2 — Select the correct run configuration

At the top toolbar in Android Studio, select either:
- **`app-customer`** → Customer-facing app
- **`app-vendor`** → Vendor-facing app

### Step 3 — Connect a device or start emulator

**Physical Device:**
1. Enable **Developer Options** on your Android phone
2. Enable **USB Debugging**
3. Connect via USB cable
4. Accept the debugging prompt on your phone

**Emulator:**
1. In Android Studio → **Device Manager** → **Create Device**
2. Select a Pixel device → API 33 or higher → Finish
3. Click the play button to start the emulator

### Step 4 — Run the app

Click the **Run** button (green play ▶) or press `Shift + F10`.

Android Studio will build and install the APK on your device/emulator.

---

## 5. Connecting Mobile App to Backend

The mobile app connects to the backend based on settings in `local.properties`.

### File location

```
/Users/hazeevali/Documents/NearSpot/Mobile-App/local.properties
```

### Current configuration

```properties
# Your Mac's WiFi IP — phone must be on same WiFi network
dev.base.url.local=http://192.168.29.39:8000/api/v1/
dev.ws.url.local=ws://192.168.29.39:8000/ws/

# Public URL via ngrok (works on any network)
dev.base.url.public=https://expansion-unripe-uncommon.ngrok-free.dev/api/v1/
dev.ws.url.public=wss://expansion-unripe-uncommon.ngrok-free.dev/ws/
```

### How URL selection works

The app automatically picks the right URL:
1. **Emulator** → always uses `10.0.2.2:8000` (emulator's localhost)
2. **Physical device (same WiFi)** → uses `LOCAL` URL (`192.168.x.x`)
3. **Physical device (different network)** → uses `PUBLIC` ngrok URL

### If the WiFi IP changes

Find your current Mac IP:
```bash
ipconfig getifaddr en0
```

Update `local.properties` with the new IP:
```properties
dev.base.url.local=http://<YOUR_NEW_IP>:8000/api/v1/
dev.ws.url.local=ws://<YOUR_NEW_IP>:8000/ws/
```

Then in Android Studio: **File → Sync Project with Gradle Files**, then re-run the app.

### Requirements for physical device testing

- Phone and Mac must be on the **same WiFi network**
- Backend Docker containers must be running
- No VPN active on the phone

---

## 6. Admin Panel

### URL

```
http://localhost/admin/
```

> Use port **80** (via Nginx), NOT port 8000. Port 80 serves static files (CSS/JS) correctly.

### Login Credentials

| Account | Username | Password |
|---|---|---|
| Superuser | `+910000000001` | `Admin@123` |
| Master Admin | `+919121030352` | `Admin@123` |

### What you can do in Admin

- **Users** — View, create, suspend users
- **Stores** — Manage stores, verify vendors
- **Products** — Review and manage products
- **Inventory** — Stock movement logs, suppliers, purchase orders
- **Billing** — Plans and subscriptions
- **Notifications** — Push notification history
- **Banners** — Promo banners
- **Categories** — Product categories

### API Documentation

```
http://localhost/api/docs/
```

Interactive API explorer (Swagger UI) — test all endpoints directly in the browser.

---

## 7. Useful Commands

### Backend

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart only Django (after code changes)
docker-compose restart django

# View Django live logs
docker-compose logs -f django

# View all service logs
docker-compose logs -f

# Run Django management commands
docker exec nearkart_backend-django-1 /venv/bin/python manage.py shell
docker exec nearkart_backend-django-1 /venv/bin/python manage.py makemigrations
docker exec nearkart_backend-django-1 /venv/bin/python manage.py migrate

# Reset admin password
docker exec nearkart_backend-django-1 /venv/bin/python manage.py shell -c "
from apps.auth_app.models import User
u = User.objects.get(phone_number='+910000000001')
u.set_password('Admin@123')
u.save()
"

# Check all containers status
docker-compose ps

# Rebuild after code or requirements change
docker-compose build django
docker-compose up -d
```

### Run Tests

```bash
cd /Users/hazeevali/Documents/NearSpot/Backend/nearkart_backend
/Users/hazeevali/Documents/NearSpot/Backend/nearkart_venv/bin/python3 -m pytest tests/ -v
```

### Mobile — Build APK from terminal

```bash
cd /Users/hazeevali/Documents/NearSpot/Mobile-App

# Debug APK (for testing)
./gradlew assembleDebug

# APK output location:
# app-customer/build/outputs/apk/debug/app-customer-debug.apk
# app-vendor/build/outputs/apk/debug/app-vendor-debug.apk
```

---

## 8. Ports Reference

| Port | Service | Access URL |
|---|---|---|
| `80` | Nginx (main entry point) | `http://localhost` |
| `8000` | Django direct (no static files) | `http://localhost:8000` |
| `8001` | Daphne WebSocket direct | `ws://localhost:8001` |
| `5432` | PostgreSQL | pgAdmin / TablePlus |
| `6432` | PgBouncer (connection pooler) | Internal only |
| `6379` | Redis | Internal only |

> **Always use port 80** for browser access (Admin, API Docs, API calls).
> Port 8000 is direct Django — no CSS/JS static files are served there.

---

## 9. Troubleshooting

### Docker not starting

**Problem:** `Cannot connect to the Docker daemon`
**Fix:** Open Docker Desktop from Applications and wait for it to fully start.

---

### Port already in use

**Problem:** `Error starting userland proxy: listen tcp 0.0.0.0:8000: bind: address already in use`
**Fix:**
```bash
# Find what's using port 8000
lsof -i :8000
# Kill the process
kill -9 <PID>
# Then restart
docker-compose up -d
```

---

### Mobile app can't connect to backend

**Problem:** App shows connection error or blank screens
**Checklist:**
1. Is Docker running? → `docker-compose ps` → all services should show `Up`
2. Is your phone on the **same WiFi** as your Mac?
3. Is there a VPN active on your phone? → Turn it off
4. Has your Mac IP changed? → `ipconfig getifaddr en0` → update `local.properties`
5. Test in phone browser: `http://<YOUR_MAC_IP>:8000/api/v1/health/` → should show `{"status":"ok"}`

---

### Admin page has no CSS (looks broken)

**Problem:** Django admin page loads without styling
**Fix:** Use `http://localhost/admin/` (port 80 via Nginx), NOT `http://localhost:8000/admin/`

---

### Database connection error

**Problem:** `could not connect to server` or `pgbouncer` errors
**Fix:**
```bash
# Restart just the database services
docker-compose restart postgres pgbouncer
# Wait 10 seconds, then restart Django
docker-compose restart django
```

---

### Migrations not applied

**Problem:** `Table does not exist` errors in logs
**Fix:**
```bash
docker exec nearkart_backend-django-1 /venv/bin/python manage.py migrate
```

---

### OTP not working in dev

All test accounts use the fixed OTP: **`123456`**

Test phone numbers available:
- `9000000001` — Customer
- `9000000002` — Customer
- `9000000003` — Vendor
- `9000000004` — Vendor

---

*Last updated: June 2026*

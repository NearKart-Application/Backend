# Sprint 1 — Django Foundation

**Goal:** Django running in Docker with PostgreSQL + PostGIS + Redis. Admin accessible.
**Status:** Done
**Time estimate:** ~12 hours

---

## What Was Built

### Folder Structure

```
nearkart_backend/
├── config/
│   ├── settings/
│   │   ├── base.py          ← All shared settings (DB, JWT, Celery, AWS etc.)
│   │   ├── development.py   ← Local dev overrides
│   │   ├── production.py    ← Production overrides
│   │   └── testing.py       ← Testing settings (SQLite, no Docker needed)
│   ├── asgi.py              ← WebSocket entry point
│   ├── celery.py            ← Celery configuration
│   ├── urls.py              ← All API routes wired here
│   └── wsgi.py              ← HTTP entry point
│
├── core/
│   ├── models.py            ← BaseModel (UUID + timestamps for all models)
│   ├── exceptions.py        ← Consistent error response format
│   ├── permissions.py       ← IsCustomer, IsVendor, IsAdmin
│   ├── pagination.py        ← StandardOffsetPagination, CursorPagination
│   ├── middleware.py        ← JWT auth for WebSocket connections
│   └── utils/
│       ├── cache.py         ← Redis cache helpers
│       ├── geo.py           ← PostGIS geo query helpers
│       └── s3.py            ← AWS S3 file upload helpers
│
├── apps/                    ← All 13 Django apps live here
├── docker-compose.yml       ← All 7 services defined
├── Dockerfile               ← Multi-stage build with venv
├── nginx/nginx.conf         ← Rate limiting + proxy config
├── requirements/
│   ├── base.txt             ← Core packages
│   ├── development.txt      ← + testing/linting tools
│   └── production.txt       ← + gunicorn/uvicorn
└── .env.example             ← All environment variables documented
```

### Services Running in Docker

| Service | Port | Image |
|---------|------|-------|
| Django (REST API) | 8000 | python:3.13-slim (custom) |
| Daphne (WebSocket) | 8001 | python:3.13-slim (custom) |
| Celery Worker | — | python:3.13-slim (custom) |
| Celery Beat | — | python:3.13-slim (custom) |
| PostgreSQL + PostGIS | 5432 | postgis/postgis:15-3.3 |
| Redis | 6379 | redis:7-alpine |
| Nginx | 80 | nginx:alpine |

### Key Settings Configured

- **Database:** PostgreSQL with PostGIS extension (for location queries)
- **Cache:** Redis (db=1)
- **Celery broker:** Redis (db=0)
- **WebSocket channels:** Redis (db=2)
- **JWT:** Access token 1hr, Refresh token 30 days
- **Timezone:** Asia/Kolkata
- **Custom error format:** All errors return `{error, message, code, details}`

---

## How to Verify Sprint 1 is Working

### Option A — Docker (full stack)

```bash
docker compose up --build
```

Then check:

```bash
# Health check
curl http://localhost:8000/api/v1/health/
# Expected: {"status": "ok"}
```

Open in browser:
- `http://localhost:8000/api/docs/` → Swagger UI
- `http://localhost:8000/admin/` → Django Admin

### Option B — Local (no Docker)

```bash
source venv/bin/activate
python manage.py check
# Expected: System check identified no issues (0 silenced).
```

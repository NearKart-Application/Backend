# Sprint 1 — API Test Flow

Sprint 1 has only one testable endpoint — the Health Check.
All other Sprint 1 work is infrastructure (settings, Docker, core utilities) with no user-facing APIs.

---

## Prerequisites

- Docker running: `docker compose up -d`
- All containers show `Up` status: `docker compose ps`

---

## STEP 1 — Health Check

```
Method  : GET
URL     : http://localhost:8000/api/v1/health/
Auth    : None
```

No request body needed.

Expected Response — 200 OK:
```json
{
    "status": "ok",
    "db": "ok",
    "redis": "ok",
    "version": "1.0.0",
    "environment": "development"
}
```

What it checks:
- `db: ok` — Django can connect to PostgreSQL
- `redis: ok` — Django can read/write to Redis cache
- If either is down: returns `503` with `"status": "degraded"`

---

## STEP 2 — Swagger UI

Open in browser:
```
http://localhost:8000/api/docs/
```

Expected: Swagger UI loads with all API endpoints listed under their tags.

---

## STEP 3 — Django Admin

Open in browser:
```
http://localhost:8000/admin/
```

Create a superuser first if needed:
```bash
docker compose run --rm django /venv/bin/python manage.py createsuperuser
```

When prompted, enter a phone number in `+91XXXXXXXXXX` format.

Expected: Admin panel loads and shows all registered models.

---

## STEP 4 — Docker Container Health

Run in terminal:
```bash
docker compose ps
```

All 7 containers must show `Up`:

| Container | Port | Status |
|-----------|------|--------|
| django | 8000 | Up |
| daphne | 8001 | Up |
| celery | — | Up |
| celery-beat | — | Up |
| postgres | 5432 | Up (healthy) |
| redis | 6379 | Up (healthy) |
| nginx | 80 | Up |

---

## STEP 5 — Verify Through Nginx (port 80)

```bash
curl http://localhost:80/api/v1/health/
```

Expected: same `{"status": "ok"}` response — confirms Nginx is correctly proxying to Django.

---

## STEP 6 — Check Migrations Applied

```bash
docker compose run --rm django /venv/bin/python manage.py showmigrations
```

Expected: All migrations show `[X]` (applied). No `[ ]` (unapplied) lines.

---

## Error Cases

### Health check returns `db: error`
- PostgreSQL is not running or Django cannot connect
- Check: `docker compose logs postgres`

### Health check returns `redis: error`
- Redis is not running or Django cannot connect
- Check: `docker compose logs redis`

### Health check returns `503`
- One or both services are down
- Fix: `docker compose restart postgres redis`

### Swagger UI does not load
- Django is not running
- Check: `docker compose logs django`

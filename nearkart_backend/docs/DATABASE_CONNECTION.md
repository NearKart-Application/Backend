# Nearspot — Database Connection Guide

## Overview

The Nearspot backend uses **PostgreSQL 15 + PostGIS** for the main application database,
managed through **PgBouncer** (connection pooler) inside Docker.

There are three separate databases across two PostgreSQL instances:

| Database | PostgreSQL Instance | Purpose |
|---|---|---|
| `nearkart` | Docker (port 5432) | Live app data (dev/staging/prod) |
| `template_nearspot` | Local Homebrew (port 5432) | Template for test DB creation |
| `nearspot_test` | Local Homebrew (port 5432) | Auto-created/destroyed by pytest |

---

## 1. Application Database (Docker)

This is the main database used by the running Django app.

### Prerequisites
- Docker Desktop must be running

### Start the database
```bash
cd /Users/hazeevali/Documents/NearSpot/Backend/nearkart_backend
docker-compose up -d postgres pgbouncer
```

### Connection details

| Field | Value |
|---|---|
| Host | `localhost` |
| Port | `5432` (direct) / `6432` (via PgBouncer) |
| Database | `nearkart` |
| Username | `nearkart` |
| Password | `nearkart_dev_password_change_in_prod` |

> The Django app connects via PgBouncer on port **6432**. For GUI tools and direct inspection, use port **5432** (direct Postgres).

### Connect via psql (CLI)
```bash
# Direct connection (inside Docker container)
docker exec -it nearkart_backend-postgres-1 psql -U nearkart -d nearkart

# From your Mac terminal (Docker must be running)
psql -h localhost -p 5432 -U nearkart -d nearkart
```

### Useful psql commands
```sql
\dt                          -- list all tables
\d table_name                -- describe a table's columns
\di                          -- list all indexes

SELECT * FROM stores LIMIT 5;
SELECT * FROM products LIMIT 10;
SELECT * FROM auth_users LIMIT 5;
SELECT * FROM product_variants LIMIT 10;
SELECT * FROM inv_stock_movement_logs LIMIT 10;
```

### Connect via pgAdmin (GUI)

1. Open pgAdmin
2. Right-click **Servers** → **Register** → **Server**
3. Fill in:
   - **Name (label):** `NearSpot Local`
   - **Host:** `localhost`
   - **Port:** `5432`
   - **Database:** `nearkart`
   - **Username:** `nearkart`
   - **Password:** `nearkart_dev_password_change_in_prod`

### Connect via TablePlus / DBeaver

Use the same connection details as pgAdmin above.

---

## 2. Test Database (Local Homebrew PostgreSQL)

Used only by `pytest`. Django creates and destroys it automatically on each test run.

### Prerequisites
- No Docker needed
- Local PostgreSQL (Homebrew) must be running

### Start local PostgreSQL
```bash
brew services start postgresql@14
```

### Run tests
```bash
cd /Users/hazeevali/Documents/NearSpot/Backend/nearkart_backend
/Users/hazeevali/Documents/NearSpot/Backend/nearkart_venv/bin/python3 -m pytest tests/ -v
```

### Connection details (test DB)

| Field | Value |
|---|---|
| Host | `localhost` |
| Port | `5432` |
| Database | `nearspot_test` *(auto-created by pytest)* |
| Username | `hazeevali` |
| Password | *(none — local trust auth)* |

### Template database
`template_nearspot` is a permanent local database that pre-installs required PostgreSQL
extensions (`postgis`, `pg_trgm`, `btree_gin`) into every test database. **Do not delete it.**

To recreate it if lost:
```bash
psql -U hazeevali postgres -c "CREATE DATABASE template_nearspot TEMPLATE template0 ENCODING 'UTF8';"
psql -U hazeevali template_nearspot -c "CREATE EXTENSION postgis; CREATE EXTENSION pg_trgm; CREATE EXTENSION btree_gin;"
psql -U hazeevali postgres -c "UPDATE pg_database SET datistemplate = TRUE WHERE datname = 'template_nearspot';"
```

---

## 3. Docker Architecture

```
Android App / API Client
        │
        ▼
   Django (port 8000)
        │
        ▼
  PgBouncer (port 6432)   ← connection pooler, limits DB connections
        │
        ▼
  PostgreSQL (port 5432)  ← postgis/postgis:15-3.3 Docker image
        │
        ▼
   "nearkart" database    ← all app data lives here
```

### Stop all containers
```bash
docker-compose down
```

### Stop and wipe all data (destructive)
```bash
docker-compose down -v   # WARNING: deletes the postgres_data volume
```

---

## 4. Settings Files

| Settings file | Database used |
|---|---|
| `config/settings/base.py` | Reads from `.env` → Docker `nearkart` |
| `config/settings/testing.py` | Local Homebrew `nearspot_test` (PostGIS) |
| `config/settings/staging.py` | Remote staging server |
| `config/settings/production.py` | Remote production server |

The active `.env` file is at:
```
/Users/hazeevali/Documents/NearSpot/Backend/nearkart_backend/.env
```

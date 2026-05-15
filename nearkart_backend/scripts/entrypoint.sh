#!/bin/bash
# NearKart — Production Entrypoint
# Runs before the app server starts inside the ECS container.
# Handles: migrations, static files collection, then starts gunicorn.

set -e

echo "[entrypoint] Starting NearKart Backend..."

# ── WAIT FOR DB ───────────────────────────────────────────────
echo "[entrypoint] Waiting for database..."
until python manage.py migrate --check 2>/dev/null; do
    echo "[entrypoint] Database not ready yet — retrying in 2s..."
    sleep 2
done

# ── RUN MIGRATIONS ────────────────────────────────────────────
echo "[entrypoint] Running database migrations..."
python manage.py migrate --noinput

# ── COLLECT STATIC FILES ──────────────────────────────────────
echo "[entrypoint] Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "[entrypoint] Setup complete. Starting app server..."

# ── START APP SERVER ──────────────────────────────────────────
# Gunicorn with Uvicorn workers handles both HTTP and WebSocket (ASGI)
exec gunicorn config.asgi:application \
    --bind 0.0.0.0:8000 \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers "${GUNICORN_WORKERS:-4}" \
    --timeout 120 \
    --graceful-timeout 30 \
    --keepalive 5 \
    --access-logfile - \
    --error-logfile - \
    --log-level "${GUNICORN_LOG_LEVEL:-info}"

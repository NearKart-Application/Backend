# ── Stage 1: Builder ─────────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /app

# System dependencies for PostGIS, FFmpeg, and Python packages
RUN apt-get update && apt-get install -y \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    gdal-bin \
    ffmpeg \
    gcc \
    g++ \
    python3-dev \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create venv at /venv (NOT inside /app — volume mount would overwrite it)
RUN python -m venv /venv

# Use the venv for all installs
ENV PATH="/venv/bin:$PATH"
ENV VIRTUAL_ENV="/venv"

COPY requirements/base.txt requirements/base.txt
COPY requirements/production.txt requirements/production.txt

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements/production.txt

# ── Stage 2: Development ─────────────────────────────────────
FROM builder AS development

COPY requirements/development.txt requirements/development.txt
RUN pip install --no-cache-dir -r requirements/development.txt

WORKDIR /app

# Non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app /venv
USER appuser

ENV PATH="/venv/bin:$PATH"
ENV VIRTUAL_ENV="/venv"

EXPOSE 8000 8001

# ── Stage 3: Production ──────────────────────────────────────
FROM python:3.13-slim AS production

WORKDIR /app

# Runtime system dependencies only
RUN apt-get update && apt-get install -y \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    gdal-bin \
    ffmpeg \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy venv from builder
COPY --from=builder /venv /venv

# Copy app code
COPY . .

# Non-root user
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app /venv
USER appuser

ENV PATH="/venv/bin:$PATH"
ENV VIRTUAL_ENV="/venv"

EXPOSE 8000 8001

CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]

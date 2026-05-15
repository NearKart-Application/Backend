# NearKart Backend — Developer Commands
# Usage: make <command>

.PHONY: help install test test-auth run shell migrate docker-up docker-down lint format

help:
	@echo ""
	@echo "  NearKart Backend Commands"
	@echo "  ─────────────────────────────────────────────────"
	@echo "  make install      Install all dependencies in venv"
	@echo "  make test         Run all tests (no Docker needed)"
	@echo "  make test-auth    Run only auth tests"
	@echo "  make run          Start Django dev server (no Docker)"
	@echo "  make shell        Open Django shell"
	@echo "  make migrate      Run database migrations"
	@echo "  make docker-up    Start full stack with Docker"
	@echo "  make docker-down  Stop Docker services"
	@echo "  make lint         Check code style"
	@echo "  make format       Auto-format code with black"
	@echo ""

# ── LOCAL (no Docker) ─────────────────────────────────────────

install:
	pip install --upgrade pip
	pip install -r requirements/development.txt

test:
	pytest

test-auth:
	pytest apps/auth_app/tests/ -v

test-cov:
	pytest --cov=apps --cov-report=term-missing

run:
	DJANGO_SETTINGS_MODULE=config.settings.development \
	python manage.py runserver 0.0.0.0:8000

shell:
	DJANGO_SETTINGS_MODULE=config.settings.development \
	python manage.py shell

migrate:
	DJANGO_SETTINGS_MODULE=config.settings.development \
	python manage.py migrate

# ── DOCKER (full stack) ───────────────────────────────────────

docker-up:
	docker compose up --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f django

# ── CODE QUALITY ──────────────────────────────────────────────

lint:
	flake8 apps/ core/ config/

format:
	black apps/ core/ config/
	isort apps/ core/ config/

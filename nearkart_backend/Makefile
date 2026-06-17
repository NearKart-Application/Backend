# NearKart Backend — Developer Commands
# Usage: make <command>

.PHONY: help install test test-auth test-cov test-report run shell migrate docker-up docker-down lint format \
        prod-up prod-down prod-logs check-env

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
	@echo "  make docker-up    Start full stack with Docker (dev)"
	@echo "  make docker-down  Stop Docker services (dev)"
	@echo "  make prod-up      Start production stack"
	@echo "  make prod-down    Stop production stack"
	@echo "  make prod-logs    Tail production Django logs"
	@echo "  make check-env    Validate .env.production has required vars"
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

test-report:
	@mkdir -p test-results
	pytest \
	  --html=test-results/report.html \
	  --self-contained-html \
	  --junitxml=test-results/junit.xml \
	  --cov=apps \
	  --cov-report=html:test-results/coverage \
	  --cov-report=term-missing \
	  -v
	@echo ""
	@echo "  Reports saved to test-results/"
	@echo "  HTML report  : test-results/report.html"
	@echo "  JUnit XML    : test-results/junit.xml"
	@echo "  Coverage HTML: test-results/coverage/index.html"

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

# ── PRODUCTION DOCKER ─────────────────────────────────────────

prod-up:
	docker compose -f docker-compose.prod.yml up -d --build

prod-down:
	docker compose -f docker-compose.prod.yml down

prod-logs:
	docker compose -f docker-compose.prod.yml logs -f django

check-env:
	@echo "Checking .env.production for required variables..."
	@for var in SECRET_KEY DB_PASSWORD REDIS_PASSWORD AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY \
	            TWILIO_ACCOUNT_SID TWILIO_AUTH_TOKEN FIREBASE_CREDENTIALS_JSON SENDGRID_API_KEY \
	            SENTRY_DSN; do \
	    grep -q "^$$var=" .env.production 2>/dev/null || echo "  MISSING: $$var"; \
	done
	@echo "Done."

# ── CODE QUALITY ──────────────────────────────────────────────

lint:
	flake8 apps/ core/ config/

format:
	black apps/ core/ config/
	isort apps/ core/ config/

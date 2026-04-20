.PHONY: up down build migrate seed test test-api install-api dev-api dev-web

# ---------- Docker Compose ----------
up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

# ---------- Database ----------
migrate:
	docker compose exec api alembic upgrade head

seed:
	docker compose exec api python -m app.services.seed

# ---------- Local dev (no Docker) ----------
install-api:
	pip install -r api/requirements.txt

dev-api:
	cd api && uvicorn app.main:app --reload --port 8000

dev-worker:
	cd api && python -m app.workers.runner

install-web:
	cd web && npm install --legacy-peer-deps

dev-web:
	cd web && npm run dev

# ---------- Tests ----------
test-api:
	cd api && python -m pytest tests/ -v

test-ml:
	cd api && python -m pytest tests/test_ml.py -v

# ---------- Full local stack ----------
dev: install-api install-web
	@echo "Run 'make dev-api' in one terminal and 'make dev-web' in another"

# ---------- Backtest worker (manual trigger) ----------
run-backtests:
	cd api && python -c "from app.workers.backtest_worker import check_all_backtests; check_all_backtests()"

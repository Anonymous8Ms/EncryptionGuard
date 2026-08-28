.PHONY: install generate train evaluate dev test lint clean

# ── Install ──────────────────────────────────
install:
	pip install -r backend/requirements.txt
	cd frontend && npm install

# ── Data Generation ──────────────────────────
generate:
	PYTHONPATH=backend python -m data.generator

# ── ML Training ──────────────────────────────
train:
	PYTHONPATH=backend python -m ml.train

# ── ML Evaluation ────────────────────────────
evaluate:
	PYTHONPATH=backend python -m ml.evaluate

# ── Development Servers ──────────────────────
dev:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
	cd backend && celery -A app.workers.celery_app worker --loglevel=info

# ── Tests ────────────────────────────────────
test:
	cd backend && pytest tests/ -v --cov=app --cov-report=term-missing

# ── Lint ─────────────────────────────────────
lint:
	cd backend && ruff check . && ruff format --check .
	cd frontend && npm run lint

# ── Clean ────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/htmlcov backend/.coverage
	rm -rf frontend/node_modules frontend/dist

# EncryptionGuard 

Explainable AI for detecting coordinated refund abuse on Razorpay.

## Quick Start

```bash
git clone https://github.com/Anonymous8Ms/EncryptionGuard.git
cd EncryptionGuard

# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials

# Generate synthetic data
python -m data.generator

# Train ML model
python -m ml.train --data-dir data --output-dir ml/artifacts --n-trials 20

# Evaluate
python -m ml.evaluate --model-path ml/artifacts/model.pkl --data-dir data --output-dir ml/artifacts

# Run backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Live Demo

- **Frontend**: https://encryptionguard-three.vercel.app
- **Backend API**: https://encryptionguard.onrender.com
- **API Docs**: https://encryptionguard.onrender.com/docs

## Evaluation Results

| Metric | Value |
|--------|-------|
| PR-AUC | 0.7222 |
| Test Samples | 72 |
| Abuse Rate | 72.22% |
| Model | XGBoost + Optuna (20 trials) |

Cross-seed report (seeds 42, 123, 999):
- PR-AUC: 0.7222 ± 0.0000

See `backend/ml/artifacts/MODEL_CARD.md` for full model card.

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│  FastAPI     │────▶│  SQLite/     │
│  React+Vite  │     │  Backend     │     │  Supabase    │
└──────────────┘     └──────┬───────┘     └──────────────┘
                            │
                   ┌────────┼────────┐
                   ▼        ▼        ▼
             ┌──────────┐ ┌──────┐ ┌──────────┐
             │  Neo4j   │ │Redis │ │ XGBoost  │
             │  Aura    │ │Cloud │ │ ML Model │
             └──────────┘ └──────┘ └──────────┘
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root status |
| GET | `/health` | Health check |
| POST | `/api/webhooks/razorpay` | Razorpay webhook receiver |
| GET | `/api/cases/` | List cases with filters |
| GET | `/api/cases/{id}` | Case detail with evidence |
| POST | `/api/feedback/` | Submit analyst feedback |

## Tech Stack

| Concern | Choice |
|---------|--------|
| API | Python + FastAPI |
| Database | SQLite (dev) / Supabase PostgreSQL (prod) |
| Graph store | Neo4j Aura |
| Velocity cache | Redis Cloud |
| Frontend | React + TypeScript + Vite + Tailwind CSS |
| Graph visualization | Cytoscape.js |
| ML model | XGBoost with Optuna tuning |
| Explainability | SHAP TreeExplainer |
| Analyst assistant | Xiaomi MiMo API |

## Project Structure

```
EncryptionGuard/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── api/                 # Route handlers
│   │   ├── models/              # SQLAlchemy models
│   │   ├── services/            # Scoring, LLM, webhook
│   │   └── workers/             # Celery tasks
│   ├── features/                # Feature engineering
│   │   ├── schema.py            # FeatureVector model
│   │   ├── velocity.py          # Redis velocity features
│   │   └── graph.py             # Neo4j graph features
│   ├── ml/
│   │   ├── train.py             # XGBoost + Optuna training
│   │   ├── evaluate.py          # Model evaluation
│   │   ├── model_card.py        # Model card generator
│   │   └── artifacts/           # Trained models
│   ├── data/
│   │   ├── generator.py         # Synthetic data generator
│   │   └── scenarios.py         # Scenario definitions
│   ├── tests/                   # Test suite (18 tests)
│   └── migrations/              # SQL schema
├── frontend/
│   ├── src/
│   │   ├── components/          # AlertQueue, GraphView, FeedbackButtons
│   │   ├── pages/               # Dashboard, CaseDetail, Analytics
│   │   └── services/            # API client
│   └── package.json
└── notebooks/                   # Jupyter analysis
```

## ML Pipeline

1. **Data generation** — 8 scenario families: Normal, Legitimate Refund, Shared Network, Single Abuse, Coordinated Ring, Coordinated Ring Large, Near-Miss Shared Infra, High Loss Ring
2. **Feature engineering** — 27 features: velocity (Redis), graph (Neo4j), transaction
3. **Training** — XGBoost with Bayesian optimization (Optuna, 20 trials), class-weighted loss
4. **Evaluation** — PR-AUC, precision, recall, confusion matrix, PR curve
5. **Explainability** — SHAP TreeExplainer for feature contributions

## Testing

```bash
cd backend && pytest tests/ -v
```

All 18 tests pass:
- Webhook signature verification (3 tests)
- Webhook processing (3 tests)
- Feature vector validation (3 tests)
- Policy checker (6 tests)
- Data split (3 tests)

## What Broke

1. **SQLite on Render wipes on every deploy** — Render's free tier uses ephemeral filesystem. We implemented SQLite fallback that auto-seeds on startup.

2. **ModuleNotFoundError: backend.app** — Import paths used `backend.` prefix which failed on Render. Fixed by using relative imports.

3. **Route mismatch** — Frontend called `/cases/` but backend expected `/api/cases/`. Fixed by standardizing on `/api/` prefix and setting `VITE_API_URL` on Vercel.


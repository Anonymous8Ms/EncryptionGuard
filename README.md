# EncryptionGuard v5 (Cloud-Light)

Explainable AI for detecting coordinated refund abuse on Razorpay.

## Overview

EncryptionGuard identifies suspicious accounts, devices, IPs, and payment tokens that collectively exhibit refund-abuse behavior. The system estimates merchant exposure, explains evidence using SHAP and graph analysis, and recommends bounded responses (allow, monitor, step_up_verification, manual_review, hold_for_review).

### Key Features

- **Coordinated ring detection** — Neo4j graph analysis with Louvain community detection and PageRank centrality
- **ML risk scoring** — XGBoost with Optuna tuning, SHAP TreeExplainer for feature-level explanations
- **Real-time webhook processing** — FastAPI receiver with HMAC-SHA256 validation and idempotent processing
- **Analyst dashboard** — React + TypeScript + Cytoscape.js interactive graph visualization
- **LLM assistant** — Xiaomi MiMo API for evidence summarization with deterministic policy checker
- **Cloud-first** — Supabase (PostgreSQL), Neo4j Aura, Redis Cloud — no local Docker required

## Quick Start

```bash
# 1. Install dependencies
make install

# 2. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env with your credentials

# 3. Generate synthetic data
make generate

# 4. Train the ML model
make train

# 5. Evaluate model
make evaluate

# 6. Run development servers
make dev
# Backend API → http://localhost:8000
# Frontend   → http://localhost:3000

# 7. Run tests
make test
```

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│  FastAPI     │────▶│  Supabase    │
│  React+Vite  │     │  Backend     │     │ (PostgreSQL) │
└──────────────┘     └──────┬───────┘     └──────────────┘
                            │
                   ┌────────┼────────┐
                   ▼        ▼        ▼
             ┌──────────┐ ┌──────┐ ┌──────────┐
             │  Neo4j   │ │Redis │ │ Celery   │
             │  Aura    │ │Cloud │ │ Workers  │
             └──────────┘ └──────┘ └──────────┘
                            │
                   ┌────────┼────────┐
                   ▼                 ▼
             ┌──────────┐     ┌──────────┐
             │ XGBoost  │     │ MiMo API │
             │ ML Model │     │ (LLM)    │
             └──────────┘     └──────────┘
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/api/webhooks/razorpay` | Razorpay webhook receiver |
| GET | `/api/cases` | List cases with filters |
| GET | `/api/cases/{id}` | Case detail with evidence |
| POST | `/api/feedback` | Submit analyst feedback |

## Tech Stack

| Concern | Choice |
|---------|--------|
| API | Python + FastAPI |
| Database | Supabase (PostgreSQL) |
| Graph store | Neo4j Aura |
| Velocity cache | Redis Cloud |
| Background queue | Celery with Redis broker |
| Frontend | React + TypeScript + Vite + Tailwind CSS |
| Graph visualization | Cytoscape.js |
| ML model | XGBoost with Optuna tuning |
| Explainability | SHAP TreeExplainer |
| Analyst assistant | Xiaomi MiMo API |

## Project Structure

```
Encryption Guard/
├── Makefile                    # Build commands
├── notebooks/                  # Jupyter analysis
│   ├── 01_eda.ipynb           # Exploratory data analysis
│   ├── 02_feature_correlation.ipynb
│   ├── 03_pr_curves.ipynb     # Precision-recall curves
│   └── 04_shap_plots.ipynb    # SHAP visualizations
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI application
│   │   ├── config.py          # Settings from .env
│   │   ├── api/               # Route handlers
│   │   ├── models/            # SQLAlchemy models
│   │   ├── services/          # Business logic
│   │   └── workers/           # Celery tasks
│   ├── features/              # Shared feature library
│   │   ├── velocity.py        # Redis velocity features
│   │   ├── graph.py           # Neo4j graph features
│   │   └── schema.py          # FeatureVector model
│   ├── ml/
│   │   ├── train.py           # XGBoost training + Optuna
│   │   ├── evaluate.py        # Model evaluation
│   │   └── model_card.py      # Model card generator
│   ├── data/
│   │   └── generator.py       # Scenario generator
│   ├── tests/                 # Test suite
│   ├── migrations/            # SQL schema
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/        # AlertQueue, GraphView, FeedbackButtons
│   │   ├── pages/             # Dashboard, CaseDetail
│   │   └── services/          # API client
│   └── package.json
└── docs/
    └── compose/               # Design specs & plans
```

## ML Pipeline

1. **Data generation** — Synthetic scenario generator with 5 types: Normal, Legitimate Refund, Shared Network, Single Abuse, Coordinated Ring
2. **Feature engineering** — Shared `features/` module used by both online scoring and offline training (prevents training-serving skew)
3. **Training** — XGBoost with Bayesian optimization (Optuna, 100 trials), class-weighted loss
4. **Evaluation** — PR-AUC, precision, recall, ring-level metrics, calibration, cost-sensitive thresholds
5. **Explainability** — SHAP TreeExplainer for feature contributions, graph evidence for relationship analysis

## Graph Model

- **Nodes**: Account, Device, IPAddress, PaymentToken, Order, Payment, Refund
- **Edges**: USES, ORIGINATED_FROM, SHIPS_TO, PAID_WITH, PLACED, HAS_PAYMENT, HAS_REFUND
- **TTL**: 90-day edge expiration with query-time filtering and weekly hard delete
- **Algorithms**: Connected components, Louvain community detection, PageRank centrality

## Testing

```bash
make test
```

Tests cover:
- Webhook signature verification and idempotency
- Feature vector serialization and type enforcement
- Split leakage prevention (ring IDs, scenario IDs)
- Policy checker (prohibited content, irreversible actions, citation validation)

## License

Proprietary — Xiaomi Internal Use Only

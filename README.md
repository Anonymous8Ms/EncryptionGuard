# EncryptionGuard v5

> ML-powered encryption compliance monitoring platform with real-time graph analysis, risk scoring, and automated remediation workflows.

## Overview

EncryptionGuard analyzes your infrastructure's encryption posture by building a property graph of certificates, keys, services, and their relationships. An XGBoost risk-scoring model flags non-compliant configurations in real time, while a Celery worker pipeline handles automated certificate rotation and alerting.

### Key Features

- **Graph-based asset mapping** — Neo4j stores certificates, keys, services, and their relationships for deep traversal queries.
- **ML risk scoring** — XGBoost model with SHAP explainability scores every asset; Optuna tunes hyper-parameters.
- **Real-time monitoring** — Celery workers poll for expiring certs, revoked keys, and policy violations.
- **Interactive dashboard** — React + Cytoscape.js visualizes the encryption graph with drill-down risk details.
- **Payment integration** — Razorpay handles subscription billing for the SaaS tier.

## Quick Start

```bash
# 1. Clone and install
git clone <repo-url> && cd encryption-guard
make install

# 2. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env with your credentials

# 3. Generate synthetic data
make generate

# 4. Train the ML model
make train

# 5. Run development servers
make dev
# Backend API → http://localhost:8000
# Frontend   → http://localhost:5173

# 6. Run tests
make test
```

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│  FastAPI     │────▶│  PostgreSQL  │
│  React+Vite  │     │  Backend     │     │  (Supabase)  │
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
             │ XGBoost  │     │ Razorpay │
             │ ML Model │     │ Billing  │
             └──────────┘     └──────────┘
```

## API Endpoints

| Method | Endpoint                    | Description                          |
|--------|-----------------------------|--------------------------------------|
| GET    | `/api/v1/health`            | Health check                         |
| GET    | `/api/v1/assets`            | List all encryption assets           |
| GET    | `/api/v1/assets/{id}`       | Get asset detail with risk score     |
| POST   | `/api/v1/assets`            | Register a new asset                 |
| GET    | `/api/v1/graph`             | Full graph data for visualization    |
| GET    | `/api/v1/graph/neighbors/{id}` | N-hop neighbors of an asset      |
| GET    | `/api/v1/risks`             | List flagged risks                   |
| POST   | `/api/v1/risks/{id}/remediate` | Trigger remediation workflow      |
| GET    | `/api/v1/scores`            | Aggregate risk scores                |
| POST   | `/api/v1/webhooks/razorpay` | Razorpay payment webhook             |

## Project Structure

```
encryption-guard/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI route handlers
│   │   ├── models/         # SQLAlchemy & Pydantic models
│   │   ├── services/       # Business logic layer
│   │   ├── workers/        # Celery task definitions
│   │   └── config.py       # Pydantic-settings configuration
│   ├── data/               # Synthetic data generator
│   ├── features/           # Feature engineering pipelines
│   ├── ml/                 # Model training & evaluation
│   ├── migrations/         # Alembic migration scripts
│   ├── tests/              # Pytest test suite
│   ├── .env.example        # Environment variable template
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/     # Reusable UI components
│   │   ├── pages/          # Route-level page components
│   │   └── services/       # API client & state management
│   └── package.json        # Node.js dependencies
├── notebooks/              # Jupyter notebooks for exploration
├── docs/
│   └── compose/            # Design specs & implementation plans
│       ├── specs/
│       └── plans/
├── Makefile                # Dev workflow commands
└── README.md               # This file
```

## License

Proprietary — Xiaomi Internal Use Only

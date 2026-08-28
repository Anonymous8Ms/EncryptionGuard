# EncryptionGuard v5 (Cloud-Light) — Design Spec

## [S1] Problem

EncryptionGuard detects coordinated refund abuse on Razorpay: multiple accounts, devices, IPs, and payment tokens collectively exhibiting refund-abuse behavior. The system identifies suspicious events and communities, estimates merchant exposure, explains evidence, and recommends bounded responses.

## [S2] Solution Overview

Cloud-first architecture using managed services (Supabase, Neo4j Aura, Redis Cloud) with no local Docker required. FastAPI backend, React+TypeScript frontend, XGBoost model with SHAP explainability, and Xiaomi MiMo API for analyst assistant.

## [S3] Tech Stack

| Concern | Choice |
|---------|--------|
| API | Python + FastAPI |
| Database | Supabase (PostgreSQL) |
| Graph store | Neo4j Aura |
| Velocity cache | Redis Cloud (free tier) |
| Background queue | Celery with Redis broker |
| Frontend | React + TypeScript + Vite + Tailwind + Cytoscape.js |
| ML model | XGBoost with Optuna tuning |
| Explainability | SHAP TreeExplainer |
| Analyst assistant | Xiaomi MiMo API |
| Policy checker | Deterministic Python + Pydantic |

## [S4] Project Structure

```
Encryption Guard/
├── Makefile                    # generate, train, evaluate, dev
├── notebooks/                  # EDA, feature correlation, PR curves, SHAP plots
├── backend/
│   ├── tests/                  # webhook, features, split, policy tests
│   ├── app/                    # FastAPI app, models, API, services, workers
│   ├── features/               # shared by app/ and ml/ (prevents training-serving skew)
│   ├── ml/                     # training, evaluation, model card
│   ├── data/                   # scenario generator
│   ├── migrations/             # SQL schema
│   ├── requirements.txt
│   └── .env.example
├── frontend/                   # React dashboard
└── README.md
```

## [S5] Shared Feature Library

`backend/features/` is imported by both `app/` (online scoring) and `ml/` (offline training). Same Python functions, same outputs. CI parity tests verify numeric equivalence.

## [S6] Data Generation

Versioned scenario generator creates merchants, accounts, devices, IPs, payment tokens, orders, payments, and refunds. Labels: Normal, Legitimate Refund, Shared Network, Single Abuse, Coordinated Ring. Time-aware/group-aware train/validation/test splits.

## [S7] Webhook Security

HMAC-SHA256 signature validation, idempotent processing with event_id + merchant_id key, raw envelope storage before returning 2xx, out-of-order reconciliation.

## [S8] Graph Model

Nodes: accounts, devices, IPs, address hashes, payment tokens, orders, payments, refunds. Edges: USES, ORIGINATED_FROM, SHIPS_TO, PAID_WITH, PLACED, HAS_PAYMENT, HAS_REFUND. 90-day edge TTL with query-time filtering and weekly hard delete.

## [S9] ML Pipeline

XGBoost binary classifier with class-weighted loss. Bayesian optimization via Optuna (100 trials). Metrics: PR-AUC, precision, recall, ring-level F1, calibration. Cost-sensitive threshold selection.

## [S10] LLM Integration

Xiaomi MiMo API for analyst assistant. Strict JSON schema output. Policy checker validates citations, blocks prohibited content, redacts secrets. Fallback to deterministic response on failure.

## [S11] Frontend Dashboard

Investigator console with: alert queue with financial exposure, case detail with evidence timeline and SHAP explanations, interactive Cytoscape.js graph visualization, analyst feedback loop (confirmed abuse / legitimate).

## [S12] Deployment

Local development via Makefile. Cloud services: Supabase, Neo4j Aura, Redis Cloud. All credentials in `.env`.

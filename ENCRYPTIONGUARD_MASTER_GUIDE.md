# EncryptionGuard — Master Implementation Guide
## Everything missing, everything broken, and how to fix it

---

## CURRENT STATE (Honest Assessment)

You have a demo shell right now:
- Frontend on Vercel showing fake seed data
- Backend on Render receiving webhooks but doing nothing with them
- No ML model, no features, no graph, no scoring, no metrics

The deployment plumbing works. The actual project does not exist yet.

---

## PART 1 — FIX CURRENT ISSUES FIRST

Do these before building anything new. They will cause confusion later if left.

---

### Issue 1 — Two PostgreSQL databases

**Problem:** `DATABASE_URL1` (Render PostgreSQL) and `DATABASE_URL` (Supabase) both exist.
This is a mess — you will not know which one has real data.

**Fix in `backend/app/models/base.py`:**

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")  # Supabase only, no fallback

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
```

**Fix in Render environment variables:**
- Delete `DATABASE_URL1`
- Set `DATABASE_URL` = your Supabase connection string
- Delete the Render PostgreSQL database — you do not need it

---

### Issue 2 — Duplicate routes

**Problem:** `/cases/` and `/api/cases/` both exist. Added as a workaround.
This is wrong. The fix is to correct the frontend baseURL.

**Fix in `frontend/src/services/api.ts`:**

```typescript
const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"

export const apiClient = axios.create({
    baseURL: BASE_URL,  // e.g. https://encryptionguard.onrender.com
})
```

All API calls must use relative paths from this client:
```typescript
// WRONG
axios.get("https://encryptionguard.onrender.com/cases/")

// RIGHT
apiClient.get("/api/cases/")
```

**Fix in `backend/app/main.py`:**
Remove all duplicate routes without the `/api/` prefix. Keep only `/api/` prefixed routes.

---

### Issue 3 — 360 fake seed cases

**Problem:** `/api/seed` populated dummy data with no labels, no ring_id, no scenario_id.
These are useless for ML evaluation.

**Fix:**
- Delete all seeded rows from the database
- Remove the `/api/seed` endpoint entirely
- Remove the `@app.on_event("startup")` auto-seed handler
- Data will come from `data/generator.py` in Phase 1

---

### Issue 4 — SQLite reference in init_db.py

**Problem:** `backend/init_db.py` was created for local SQLite. This conflicts with Supabase PostgreSQL.

**Fix:**
Delete `backend/init_db.py`. Migrations handle schema creation. Use `migrations/` only.

---

## PART 2 — DATABASE SCHEMA

Before building anything, ensure these tables exist in Supabase via your `migrations/` folder.

```sql
-- migrations/001_initial_schema.sql

CREATE TABLE IF NOT EXISTS raw_webhook_envelopes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id TEXT NOT NULL,
    razorpay_event_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    raw_body TEXT NOT NULL,
    signature_valid BOOLEAN NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delivery_attempt INTEGER NOT NULL DEFAULT 1,
    UNIQUE(merchant_id, razorpay_event_id)
);

CREATE TABLE IF NOT EXISTS accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id TEXT UNIQUE NOT NULL,
    merchant_id TEXT NOT NULL,
    created_at TIMESTAMPTZ,
    account_age_days INTEGER,
    event_label INTEGER DEFAULT NULL,  -- 0=legitimate, 1=abuse
    ring_id TEXT DEFAULT NULL,
    scenario_id TEXT DEFAULT NULL,
    generator_version TEXT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id TEXT UNIQUE NOT NULL,
    account_id UUID REFERENCES accounts(id),
    merchant_id TEXT NOT NULL,
    amount_paise INTEGER NOT NULL,
    currency TEXT DEFAULT 'INR',
    status TEXT NOT NULL,
    captured_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_label INTEGER DEFAULT NULL,
    ring_id TEXT DEFAULT NULL,
    scenario_id TEXT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS refunds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id TEXT UNIQUE NOT NULL,
    payment_id UUID REFERENCES payments(id),
    account_id UUID REFERENCES accounts(id),
    merchant_id TEXT NOT NULL,
    amount_paise INTEGER NOT NULL,
    status TEXT NOT NULL,
    requested_at TIMESTAMPTZ NOT NULL,
    processed_at TIMESTAMPTZ,
    time_to_refund_hours FLOAT,
    event_label INTEGER DEFAULT NULL,
    ring_id TEXT DEFAULT NULL,
    scenario_id TEXT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_fingerprint TEXT UNIQUE NOT NULL,
    first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ip_addresses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ip_hash TEXT UNIQUE NOT NULL,
    first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS payment_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_id TEXT UNIQUE NOT NULL,  -- opaque, e.g. ptok_demo_00127
    first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id TEXT NOT NULL,
    ring_id TEXT,
    risk_score FLOAT,
    risk_label TEXT,  -- allow, monitor, step_up_verification, manual_review, hold_for_review
    estimated_exposure_paise INTEGER,
    model_version TEXT,
    point_score FLOAT,
    graph_score FLOAT,
    evidence_source TEXT,  -- point_only, graph_enriched, both
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS case_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES cases(id),
    evidence_type TEXT NOT NULL,  -- payment, refund, shap, graph_edge, velocity
    evidence_payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analyst_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES cases(id),
    disposition TEXT NOT NULL,  -- confirmed_abuse, legitimate, needs_more_evidence, unknown
    analyst_id TEXT NOT NULL,
    model_version TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    -- append-only: never UPDATE or DELETE rows here
);

CREATE TABLE IF NOT EXISTS model_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_version TEXT UNIQUE NOT NULL,
    model_type TEXT NOT NULL,
    artifact_path TEXT NOT NULL,
    pr_auc FLOAT,
    ring_precision FLOAT,
    ring_recall FLOAT,
    expected_cost FLOAT,
    is_active BOOLEAN DEFAULT FALSE,
    deployed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action TEXT NOT NULL,
    actor TEXT NOT NULL,
    target_type TEXT,
    target_id TEXT,
    payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    -- append-only: never UPDATE or DELETE rows here
);
```

Run this against Supabase SQL editor before starting any phase.

---

## PART 3 — PHASE-BY-PHASE IMPLEMENTATION

---

## PHASE 1 — Data Generator
**File:** `backend/data/generator.py`
**Depends on:** Database schema created
**Output:** Labeled synthetic events in Supabase + Neo4j edges

This is the most important file. Everything else depends on it.

### What it must produce

Every generated event must have:
- `event_label` — 0 (legitimate) or 1 (abuse)
- `ring_id` — unique ID for each coordinated group (e.g. `ring_001`)
- `scenario_id` — which scenario template generated it
- `generator_version` — version string for reproducibility
- `generated_at` — timestamp

### Scenario families to generate

| Scenario | Label | Behavior |
|---|---|---|
| normal_no_refund | 0 | Ordinary payment, no refund |
| normal_occasional_refund | 0 | One legitimate refund |
| benign_shared_network | 0 | 3-5 accounts share IP (hostel/office), normal refund rate |
| single_account_abuse | 1 | One account with repeated refunds, high refund ratio |
| coordinated_ring_small | 1 | 3-5 accounts share device + IP, coordinated refunds |
| coordinated_ring_large | 1 | 8-15 accounts share multiple entities, high exposure |
| near_miss_shared_infra | 0 | Looks suspicious (shared device) but no abusive refund pattern |
| high_loss_ring | 1 | Large amounts, multiple entities shared, ring_id + exposure tier |

### Stable payment token IDs

```python
import random
import hashlib

def generate_token_id(seed_value: str) -> str:
    """Stable opaque token — no real card data"""
    return f"ptok_demo_{hashlib.md5(seed_value.encode()).hexdigest()[:8]}"

# Reuse tokens across accounts in rings
# Control probability: legit_reuse_prob=0.05, abuse_reuse_prob=0.6
```

### Split control

```python
from datetime import datetime, timedelta

# Time windows for splits
TRAIN_START = datetime(2026, 1, 1)
TRAIN_END   = datetime(2026, 5, 31)
VAL_START   = datetime(2026, 6, 1)
VAL_END     = datetime(2026, 7, 31)
TEST_START  = datetime(2026, 8, 1)
TEST_END    = datetime(2026, 8, 31)
```

### Prevalence targets

Run generator four times with different configs:
- Config A: 0.1% positive rate
- Config B: 0.5% positive rate
- Config C: 1.0% positive rate
- Config D: 5.0% positive rate

Primary evaluation uses Config B (0.5%).

### Run with seeds

```bash
python data/generator.py --seed 42 --config config_B.yaml
python data/generator.py --seed 123 --config config_B.yaml
python data/generator.py --seed 999 --config config_B.yaml
```

Report mean ± std across all three seeds.

### Neo4j edges to write

After writing to PostgreSQL, write these edges to Neo4j Aura:

```cypher
// Account uses device
MERGE (a:Account {id: $account_id})
MERGE (d:Device {fingerprint: $device_fingerprint})
MERGE (a)-[:USES {since: $timestamp, ring_id: $ring_id}]->(d)

// Account from IP
MERGE (a:Account {id: $account_id})
MERGE (ip:IP {hash: $ip_hash})
MERGE (a)-[:ORIGINATED_FROM {since: $timestamp}]->(ip)

// Account paid with token
MERGE (a:Account {id: $account_id})
MERGE (t:PaymentToken {token_id: $token_id})
MERGE (a)-[:PAID_WITH {since: $timestamp}]->(t)

// Account ships to address
MERGE (a:Account {id: $account_id})
MERGE (addr:Address {hash: $address_hash})
MERGE (a)-[:SHIPS_TO {since: $timestamp}]->(addr)

// Payment has refund
MERGE (p:Payment {id: $payment_id})
MERGE (r:Refund {id: $refund_id})
MERGE (p)-[:HAS_REFUND {amount: $amount, at: $timestamp}]->(r)
```

---

## PHASE 2 — Feature Engineering
**Files:** `backend/features/schema.py`, `backend/features/velocity.py`, `backend/features/graph.py`
**Depends on:** Phase 1 complete, Redis Cloud connected, Neo4j Aura connected

### 2A — Feature schema (write this first)

**`backend/features/schema.py`:**

```python
from pydantic import BaseModel
from typing import Optional

class FeatureVector(BaseModel):
    # Transaction features
    amount_paise: float
    refund_amount_paise: float
    refund_ratio: float
    time_to_refund_hours: float
    payment_failure_count: int
    attempt_count: int
    account_age_days: int
    historical_successful_payments: int

    # Velocity features (from Redis)
    refunds_per_account_1h: int
    refunds_per_account_24h: int
    refunds_per_account_7d: int
    refunds_per_device_24h: int
    accounts_per_device_24h: int
    accounts_per_ip_24h: int
    distinct_tokens_per_device_7d: int
    refund_amount_per_device_24h: float

    # Graph features (from Neo4j)
    connected_component_size: int
    shared_entity_count: int
    high_risk_neighbor_count: int
    weighted_degree: float
    community_id: Optional[int]
    community_refund_ratio: float
    two_hop_suspicious_count: int

    # Metadata (not used as model features, only for logging)
    account_id: str
    payment_id: str
    refund_id: str
    ring_id: Optional[str] = None
    event_label: Optional[int] = None
```

**This is the contract.** Both `ml/train.py` and `app/services/scoring.py` must produce this exact schema. Never deviate.

### 2B — Velocity features (Redis)

**`backend/features/velocity.py`:**

```python
import redis
import os
from datetime import datetime

r = redis.from_url(os.getenv("REDIS_URL"))

WINDOWS = {
    "5m": 300,
    "1h": 3600,
    "24h": 86400,
    "7d": 604800
}

def increment_and_get(key: str, window_seconds: int) -> int:
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, window_seconds)
    result = pipe.execute()
    return result[0]

def get_velocity_features(account_id: str, device_fp: str, ip_hash: str) -> dict:
    now = int(datetime.now().timestamp())
    return {
        "refunds_per_account_1h": increment_and_get(f"vel:refund:acc:{account_id}:1h", 3600),
        "refunds_per_account_24h": increment_and_get(f"vel:refund:acc:{account_id}:24h", 86400),
        "refunds_per_account_7d": increment_and_get(f"vel:refund:acc:{account_id}:7d", 604800),
        "refunds_per_device_24h": increment_and_get(f"vel:refund:dev:{device_fp}:24h", 86400),
        "accounts_per_device_24h": increment_and_get(f"vel:acc:dev:{device_fp}:24h", 86400),
        "accounts_per_ip_24h": increment_and_get(f"vel:acc:ip:{ip_hash}:24h", 86400),
        "distinct_tokens_per_device_7d": int(r.pfcount(f"vel:tokens:dev:{device_fp}:7d")),
        "refund_amount_per_device_24h": float(r.incrbyfloat(f"vel:amount:dev:{device_fp}:24h", 0)),
    }
```

Connect Redis Cloud:
- Render environment variable: `REDIS_URL = redis://default:password@host:port`
- Redis Cloud free tier gives you a real TCP URL

### 2C — Graph features (Neo4j)

**`backend/features/graph.py`:**

```python
from neo4j import GraphDatabase
import os

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)

EDGE_TTL_DAYS = 90  # Default TTL from v3 architecture

def get_graph_features(account_id: str) -> dict:
    with driver.session() as session:
        # Connected component size
        result = session.run("""
            MATCH (a:Account {id: $account_id})-[*1..3]-(connected)
            WHERE NOT (connected)-[:REFUND_ABUSE]->()
            RETURN count(DISTINCT connected) as component_size
        """, account_id=account_id)
        component_size = result.single()["component_size"]

        # High risk neighbors
        result = session.run("""
            MATCH (a:Account {id: $account_id})-[]-(neighbor:Account)
            WHERE neighbor.risk_score > 0.7
            RETURN count(neighbor) as high_risk_count
        """, account_id=account_id)
        high_risk_count = result.single()["high_risk_count"]

        # Weighted degree
        result = session.run("""
            MATCH (a:Account {id: $account_id})-[r]-()
            RETURN count(r) as degree
        """, account_id=account_id)
        degree = result.single()["degree"]

        return {
            "connected_component_size": component_size,
            "high_risk_neighbor_count": high_risk_count,
            "weighted_degree": float(degree),
            "shared_entity_count": component_size - 1,
            "community_id": None,  # Set by Louvain batch job
            "community_refund_ratio": 0.0,  # Set by Louvain batch job
            "two_hop_suspicious_count": 0,  # Set by Louvain batch job
        }

def prune_stale_edges():
    """Run periodically as a Celery task — every 24 hours"""
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(days=EDGE_TTL_DAYS)
    with driver.session() as session:
        session.run("""
            MATCH ()-[r:USES|ORIGINATED_FROM|SHIPS_TO|PAID_WITH]->()
            WHERE r.since < $cutoff
            DELETE r
        """, cutoff=cutoff.isoformat())
```

**Neo4j TTL implementation:** Neo4j has no native TTL for edges. Use `prune_stale_edges()` as a daily Celery beat task. This is the mechanism from v3 architecture.

---

## PHASE 3 — ML Training Pipeline
**Files:** `backend/ml/train.py`
**Depends on:** Phase 1 and Phase 2 complete

### 3A — Data loading and split

```python
import pandas as pd
from sqlalchemy import create_engine
import os

def load_and_split():
    engine = create_engine(os.getenv("DATABASE_URL"))

    df = pd.read_sql("""
        SELECT f.*, r.event_label, r.ring_id, r.scenario_id, r.requested_at
        FROM refunds r
        JOIN feature_snapshots f ON f.refund_id = r.external_id
        WHERE r.event_label IS NOT NULL
    """, engine)

    # Time-aware split
    train = df[df["requested_at"] < "2026-06-01"].copy()
    val   = df[(df["requested_at"] >= "2026-06-01") & (df["requested_at"] < "2026-08-01")].copy()
    test  = df[df["requested_at"] >= "2026-08-01"].copy()

    # Group-aware: remove ring_ids that appear in test from train/val
    test_rings = set(test["ring_id"].dropna().unique())
    train = train[~train["ring_id"].isin(test_rings)]
    val   = val[~val["ring_id"].isin(test_rings)]

    return train, val, test
```

### 3B — Feature columns

```python
FEATURE_COLS = [
    "amount_paise", "refund_amount_paise", "refund_ratio",
    "time_to_refund_hours", "payment_failure_count", "attempt_count",
    "account_age_days", "historical_successful_payments",
    "refunds_per_account_1h", "refunds_per_account_24h", "refunds_per_account_7d",
    "refunds_per_device_24h", "accounts_per_device_24h", "accounts_per_ip_24h",
    "distinct_tokens_per_device_7d", "refund_amount_per_device_24h",
    "connected_component_size", "shared_entity_count",
    "high_risk_neighbor_count", "weighted_degree",
    "community_refund_ratio", "two_hop_suspicious_count",
]
TARGET_COL = "event_label"
```

### 3C — Three models

```python
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import average_precision_score
import xgboost as xgb
import optuna

# Model 1: Rules baseline
def rules_baseline(df):
    score = (
        (df["refund_ratio"] > 0.5).astype(int) +
        (df["refunds_per_account_24h"] > 3).astype(int) +
        (df["accounts_per_device_24h"] > 4).astype(int) +
        (df["connected_component_size"] > 5).astype(int)
    )
    return (score >= 2).astype(int), score / 4.0  # label, score

# Model 2: Logistic regression baseline
def train_lr(X_train, y_train, X_val, y_val):
    model = LogisticRegression(class_weight="balanced", max_iter=1000)
    model.fit(X_train, y_train)
    calibrated = CalibratedClassifierCV(model, cv="prefit")
    calibrated.fit(X_val, y_val)
    return calibrated

# Model 3: XGBoost primary (with Optuna)
def train_xgboost(X_train, y_train, X_val, y_val):
    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()

    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 100, 500),
            "max_depth": trial.suggest_int("max_depth", 3, 8),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "scale_pos_weight": scale_pos_weight,
            "eval_metric": "aucpr",
            "use_label_encoder": False,
        }
        model = xgb.XGBClassifier(**params)
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
        proba = model.predict_proba(X_val)[:, 1]
        return average_precision_score(y_val, proba)

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=50)

    best_model = xgb.XGBClassifier(**study.best_params, scale_pos_weight=scale_pos_weight)
    best_model.fit(X_train, y_train)

    calibrated = CalibratedClassifierCV(best_model, cv="prefit", method="isotonic")
    calibrated.fit(X_val, y_val)

    return calibrated, study.best_params
```

### 3D — Cost matrix and threshold optimization

```python
import numpy as np

# Default cost matrix (configurable)
COST_CONFIG = {
    "C_FP": 500,      # Blocked legitimate transaction (review labor + friction)
    "C_FN": 5000,     # Fraud loss absorbed (refund amount estimate)
    "C_REVIEW": 200,  # Analyst time per case
    "C_FRICTION": 100 # Step-up verification friction cost
}

def optimize_threshold(y_true, y_proba, cost_config=COST_CONFIG):
    thresholds = np.arange(0.01, 0.99, 0.01)
    best_threshold = 0.5
    best_cost = float("inf")

    for t in thresholds:
        y_pred = (y_proba >= t).astype(int)
        fp = ((y_pred == 1) & (y_true == 0)).sum()
        fn = ((y_pred == 0) & (y_true == 1)).sum()
        review = y_pred.sum()  # everything flagged goes to review

        cost = (fp * cost_config["C_FP"] +
                fn * cost_config["C_FN"] +
                review * cost_config["C_REVIEW"])

        if cost < best_cost:
            best_cost = cost
            best_threshold = t

    return best_threshold, best_cost
```

### 3E — Save artifacts

```python
import joblib, json, os

def save_model(model, params, threshold, feature_cols, version="v1.0"):
    os.makedirs("ml/artifacts", exist_ok=True)
    joblib.dump(model, f"ml/artifacts/model_{version}.pkl")
    joblib.dump(threshold, f"ml/artifacts/threshold_{version}.pkl")
    with open(f"ml/artifacts/params_{version}.json", "w") as f:
        json.dump({"params": params, "features": feature_cols, "version": version}, f, indent=2)
```

---

## PHASE 4 — Evaluation
**File:** `backend/ml/evaluate.py`
**Depends on:** Phase 3 complete, test set FROZEN

**CRITICAL: Never use the test set for tuning. Run evaluate.py only once per model version.**

### Event-level metrics

```python
from sklearn.metrics import (
    precision_score, recall_score, f1_score,
    average_precision_score, confusion_matrix, brier_score_loss
)
import matplotlib.pyplot as plt

def evaluate_event_level(y_true, y_proba, threshold):
    y_pred = (y_proba >= threshold).astype(int)
    return {
        "precision": precision_score(y_true, y_pred),
        "recall": recall_score(y_true, y_pred),
        "f1": f1_score(y_true, y_pred),
        "pr_auc": average_precision_score(y_true, y_proba),
        "brier_score": brier_score_loss(y_true, y_proba),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
        "fp_count": int(((y_pred == 1) & (y_true == 0)).sum()),
        "fn_count": int(((y_pred == 0) & (y_true == 1)).sum()),
        "fp_cost": int(((y_pred == 1) & (y_true == 0)).sum()) * COST_CONFIG["C_FP"],
        "fn_cost": int(((y_pred == 0) & (y_true == 1)).sum()) * COST_CONFIG["C_FN"],
    }
```

### Ring-level metrics

```python
def evaluate_ring_level(df_test, y_proba, threshold, min_overlap=0.5):
    """
    A predicted ring is a connected candidate cluster above threshold.
    A ring is TP when it overlaps a ground-truth abuse ring by min_overlap.
    """
    df_test = df_test.copy()
    df_test["y_pred"] = (y_proba >= threshold).astype(int)

    ground_truth_rings = set(
        df_test[df_test["event_label"] == 1]["ring_id"].dropna().unique()
    )

    # Group predictions by ring_id
    predicted_rings = set(
        df_test[df_test["y_pred"] == 1]["ring_id"].dropna().unique()
    )

    # TP: predicted ring overlaps a real ring
    true_positives = ground_truth_rings & predicted_rings
    false_positives = predicted_rings - ground_truth_rings
    false_negatives = ground_truth_rings - predicted_rings

    ring_precision = len(true_positives) / len(predicted_rings) if predicted_rings else 0
    ring_recall    = len(true_positives) / len(ground_truth_rings) if ground_truth_rings else 0
    ring_f1 = (2 * ring_precision * ring_recall /
               (ring_precision + ring_recall)) if (ring_precision + ring_recall) > 0 else 0

    # Member coverage: % of abusive accounts inside detected rings
    detected_accounts = df_test[
        (df_test["ring_id"].isin(true_positives)) & (df_test["event_label"] == 1)
    ]["account_id"].nunique()
    total_abusive_accounts = df_test[df_test["event_label"] == 1]["account_id"].nunique()
    member_coverage = detected_accounts / total_abusive_accounts if total_abusive_accounts > 0 else 0

    return {
        "ring_precision": ring_precision,
        "ring_recall": ring_recall,
        "ring_f1": ring_f1,
        "member_coverage": member_coverage,
        "ground_truth_ring_count": len(ground_truth_rings),
        "predicted_ring_count": len(predicted_rings),
        "true_positive_rings": len(true_positives),
    }
```

### Cross-seed reporting

```python
import numpy as np

def report_across_seeds(seed_results: list[dict]):
    """seed_results is a list of metric dicts, one per seed"""
    all_keys = seed_results[0].keys()
    report = {}
    for key in all_keys:
        values = [r[key] for r in seed_results if isinstance(r[key], (int, float))]
        if values:
            report[key] = {
                "mean": float(np.mean(values)),
                "std": float(np.std(values)),
                "worst": float(np.min(values)),
                "best": float(np.max(values)),
            }
    return report
```

---

## PHASE 5 — Model Card
**File:** `backend/ml/model_card.py`

The model card must be auto-generated from evaluation results and saved as a JSON file.
Required fields:

```python
model_card = {
    "model_version": version,
    "created_at": datetime.now().isoformat(),
    "intended_use": "Detect coordinated refund abuse rings for merchant risk management",
    "prohibited_use": "Do not use as sole basis for automated bans or account termination",
    "selected_loss_class": "Coordinated refund abuse",
    "training_data": {
        "source": "Synthetic scenario generator",
        "generator_version": generator_version,
        "prevalence": prevalence,
        "seeds": seeds_used,
        "split_manifest": split_manifest_path,
    },
    "model_type": "XGBoost binary classifier",
    "hyperparameters": best_params,
    "class_weight_strategy": "scale_pos_weight from training split only",
    "calibration_method": "Isotonic regression on validation set",
    "feature_definitions": feature_cols,
    "graph_ttl_days": 90,
    "event_level_metrics": event_metrics,
    "ring_level_metrics": ring_metrics,
    "cross_seed_report": cross_seed_report,
    "cost_matrix": COST_CONFIG,
    "threshold": threshold,
    "known_limitations": [
        "Trained on synthetic data — real-world performance may differ",
        "Graph features depend on Neo4j availability",
        "Benign shared infrastructure can raise false positive rate",
        "Model should not be used without human review for high-impact actions",
    ],
    "llm_model": "Xiaomi MiMo API",
    "policy_checker_version": "1.0",
    "deployment_version": version,
    "rollback_target": previous_version,
}
```

---

## PHASE 6 — Live Scoring Pipeline
**Files:** `backend/app/services/scoring.py`, `backend/app/workers/tasks.py`
**Depends on:** Phase 3 artifacts saved

### 6A — Scoring service

**`backend/app/services/scoring.py`:**

```python
import joblib
import shap
import numpy as np
from features.schema import FeatureVector
from features.velocity import get_velocity_features
from features.graph import get_graph_features

class ScoringService:
    def __init__(self, model_path: str, threshold_path: str):
        self.model = joblib.load(model_path)
        self.threshold = joblib.load(threshold_path)
        self.explainer = shap.TreeExplainer(self.model.estimator)  # for XGBoost

    def score(self, feature_vector: FeatureVector) -> dict:
        X = np.array([[getattr(feature_vector, col) for col in FEATURE_COLS]])
        proba = self.model.predict_proba(X)[0][1]
        label = self._get_label(proba)

        shap_values = self.explainer.shap_values(X)[0]
        top_features = sorted(
            zip(FEATURE_COLS, shap_values),
            key=lambda x: abs(x[1]),
            reverse=True
        )[:5]

        return {
            "risk_score": float(proba),
            "risk_label": label,
            "threshold_used": self.threshold,
            "shap_contributions": [{"feature": f, "contribution": float(v)} for f, v in top_features],
        }

    def _get_label(self, proba: float) -> str:
        if proba < 0.2: return "allow"
        if proba < 0.4: return "monitor"
        if proba < 0.6: return "step_up_verification"
        if proba < 0.8: return "manual_review"
        return "hold_for_review"
```

### 6B — Celery tasks

**`backend/app/workers/tasks.py`:**

```python
from celery import Celery
import os

celery_app = Celery(
    "encryptionguard",
    broker=os.getenv("REDIS_URL"),
    backend=os.getenv("REDIS_URL")
)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_webhook_event(self, event_id: str, event_type: str, payload: dict):
    try:
        # 1. Update Neo4j graph edges
        update_graph_edges(payload)

        # 2. Run graph analysis
        graph_features = get_graph_features(payload["account_id"])

        # 3. Compute full feature vector
        velocity_features = get_velocity_features(
            payload["account_id"],
            payload.get("device_fingerprint"),
            payload.get("ip_hash")
        )

        # 4. Score with XGBoost
        feature_vector = build_feature_vector(payload, velocity_features, graph_features)
        scoring_result = scoring_service.score(feature_vector)

        # 5. Update case in PostgreSQL
        update_case(event_id, scoring_result, graph_features)

        # 6. Run Louvain (async, lower priority)
        run_community_detection.delay(payload.get("merchant_id"))

    except Exception as exc:
        raise self.retry(exc=exc)

@celery_app.task
def run_community_detection(merchant_id: str):
    """Louvain community detection — runs asynchronously"""
    import networkx as nx
    from community import best_partition  # python-louvain

    # Build NetworkX graph from Neo4j for this merchant
    G = build_nx_graph_from_neo4j(merchant_id)
    partition = best_partition(G)

    # Write community IDs back to Neo4j and PostgreSQL
    update_community_ids(merchant_id, partition)

@celery_app.task
def prune_stale_neo4j_edges():
    """Runs daily — removes edges older than 90 days"""
    from features.graph import prune_stale_edges
    prune_stale_edges()
```

---

## PHASE 7 — LLM Assistant + Policy Checker
**Files:** `backend/app/services/llm.py`, `backend/app/services/policy_checker.py`

### 7A — MiMo integration

**`backend/app/services/llm.py`:**

```python
import openai
import os
from pydantic import BaseModel
from typing import Optional

class AssistantResponse(BaseModel):
    summary: str
    evidence_ids: list[str]
    risk_factors: list[str]
    recommended_next_step: str
    uncertainties: list[str]
    refusal_reason: Optional[str] = None

client = openai.OpenAI(
    api_key=os.getenv("MIMO_API_KEY"),
    base_url=os.getenv("MIMO_BASE_URL")  # Xiaomi MiMo API base URL
)

SYSTEM_PROMPT = """
You are a fraud analyst assistant. Your job is to summarize evidence and answer questions.
You must:
- Only cite evidence from the provided evidence bundle
- Return strict JSON matching the required schema
- Never invent facts not in the evidence bundle
- Never recommend irreversible actions (bans, refunds, captures)
- Never provide evasion instructions, malware, or exploit guidance
- If evidence is insufficient, set refusal_reason and leave summary minimal
"""

def get_case_summary(evidence_bundle: dict) -> AssistantResponse:
    response = client.chat.completions.create(
        model=os.getenv("MIMO_MODEL_ID", "mimo-v2-flash"),
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": str(evidence_bundle)}
        ],
        max_tokens=1000,
        timeout=10.0  # Never let LLM block the UI for more than 10s
    )

    raw = response.choices[0].message.content
    return AssistantResponse.model_validate_json(raw)

def get_case_summary_with_fallback(evidence_bundle: dict) -> AssistantResponse:
    """Always returns something — LLM failure never breaks the UI"""
    try:
        return get_case_summary(evidence_bundle)
    except Exception as e:
        # Fallback: rule-based summary when LLM is unavailable
        return AssistantResponse(
            summary=f"Case flagged with risk score {evidence_bundle.get('risk_score', 'N/A')}. LLM assistant temporarily unavailable.",
            evidence_ids=evidence_bundle.get("event_ids", []),
            risk_factors=evidence_bundle.get("top_shap_features", []),
            recommended_next_step="manual_review",
            uncertainties=["LLM assistant unavailable — review evidence manually"],
            refusal_reason=f"LLM error: {str(e)}"
        )
```

### 7B — Policy checker

**`backend/app/services/policy_checker.py`:**

```python
from pydantic import BaseModel, ValidationError
from app.services.llm import AssistantResponse

PROHIBITED_PATTERNS = [
    "ban ", "blacklist", "block permanently",
    "how to evade", "rotate device", "bypass verification",
    "phishing", "credential", "malware", "exploit", "attack",
    "api_key", "webhook_secret", "password", "token:",
    "automatically refund", "auto-capture", "delete evidence",
    "alter label", "suppress alert",
]

IRREVERSIBLE_ACTIONS = [
    "ban", "permanently block", "auto-refund",
    "auto-capture", "delete account"
]

class PolicyCheckResult(BaseModel):
    passed: bool
    blocked_reason: str | None = None
    needs_human_review: bool = False
    response: AssistantResponse | None = None

def check_response(response: AssistantResponse, evidence_bundle: dict) -> PolicyCheckResult:
    # 1. Validate JSON schema (already done by Pydantic)

    # 2. Verify all cited event IDs exist in evidence bundle
    valid_ids = set(evidence_bundle.get("event_ids", []))
    for eid in response.evidence_ids:
        if eid not in valid_ids:
            return PolicyCheckResult(
                passed=False,
                blocked_reason=f"Cited event ID {eid} not found in evidence bundle"
            )

    # 3. Check for prohibited content patterns
    full_text = f"{response.summary} {response.recommended_next_step}".lower()
    for pattern in PROHIBITED_PATTERNS:
        if pattern in full_text:
            return PolicyCheckResult(
                passed=False,
                blocked_reason=f"Prohibited content detected: {pattern}"
            )

    # 4. Block irreversible actions
    for action in IRREVERSIBLE_ACTIONS:
        if action in response.recommended_next_step.lower():
            return PolicyCheckResult(
                passed=False,
                blocked_reason=f"Irreversible action blocked: {action}"
            )

    # 5. Flag low-confidence responses for human review
    if response.refusal_reason or len(response.uncertainties) > 3:
        return PolicyCheckResult(
            passed=True,
            needs_human_review=True,
            response=response
        )

    return PolicyCheckResult(passed=True, response=response)
```

---

## PHASE 8 — Deploy Celery Worker on Render

1. Go to Render dashboard
2. Click **New +** → **Background Worker**
3. Select same GitHub repo
4. Set:
   ```
   Name:          encryptionguard-worker
   Root Dir:      backend
   Build Command: pip install -r requirements.txt
   Start Command: celery -A app.workers.tasks worker --loglevel=info
   ```
5. Add ALL the same environment variables as the Web Service
6. Add one extra:
   ```
   CELERY_BROKER_URL = same value as REDIS_URL
   ```

Background Workers on Render never sleep. This is different from Web Services.

Also add a Celery Beat scheduler for periodic tasks:

```
# Second background worker for scheduled tasks
Name:          encryptionguard-beat
Start Command: celery -A app.workers.tasks beat --loglevel=info
```

---

## PHASE 9 — Tests
**Files:** `backend/tests/`

These must pass before submission. Judges will check the test suite.

### test_webhook.py

```python
import pytest
import hmac, hashlib, json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
WEBHOOK_SECRET = "test_secret"

def make_signature(body: bytes) -> str:
    return hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()

def test_valid_webhook():
    payload = {"event": "refund.created", "payload": {"refund": {"id": "rfnd_001"}}}
    body = json.dumps(payload).encode()
    sig = make_signature(body)
    response = client.post(
        "/api/webhooks/razorpay",
        content=body,
        headers={"X-Razorpay-Signature": sig, "x-razorpay-event-id": "evt_001"}
    )
    assert response.status_code == 200

def test_invalid_signature_rejected():
    payload = json.dumps({"event": "refund.created"}).encode()
    response = client.post(
        "/api/webhooks/razorpay",
        content=payload,
        headers={"X-Razorpay-Signature": "bad_signature", "x-razorpay-event-id": "evt_002"}
    )
    assert response.status_code == 400

def test_duplicate_event_idempotent():
    payload = {"event": "refund.created", "payload": {}}
    body = json.dumps(payload).encode()
    sig = make_signature(body)
    headers = {"X-Razorpay-Signature": sig, "x-razorpay-event-id": "evt_duplicate_001"}
    response1 = client.post("/api/webhooks/razorpay", content=body, headers=headers)
    response2 = client.post("/api/webhooks/razorpay", content=body, headers=headers)
    assert response1.status_code == 200
    assert response2.status_code == 200  # Must not raise 500 or create duplicate
```

### test_features.py

```python
def test_online_offline_feature_parity():
    """Same input must produce identical feature vectors from both paths"""
    sample_input = {
        "account_id": "acc_test_001",
        "payment_id": "pay_test_001",
        "refund_id": "rfnd_test_001",
        "amount_paise": 50000,
        "refund_amount_paise": 50000,
    }

    from features.schema import FeatureVector
    from app.services.scoring import build_feature_vector as online_build
    from ml.train import build_feature_vector as offline_build

    online_vector = online_build(sample_input)
    offline_vector = offline_build(sample_input)

    assert online_vector.dict() == offline_vector.dict(), \
        "Training-serving skew detected — feature vectors do not match"
```

### test_split.py

```python
def test_no_ring_leakage():
    """No ring_id should appear in both train and test sets"""
    train_rings = set(train_df["ring_id"].dropna().unique())
    test_rings  = set(test_df["ring_id"].dropna().unique())
    overlap = train_rings & test_rings
    assert len(overlap) == 0, f"Ring leakage detected: {overlap}"

def test_time_ordering():
    """All train events must be before all test events"""
    assert train_df["requested_at"].max() < test_df["requested_at"].min()
```

### test_policy.py

```python
def test_blocks_evasion_content():
    from app.services.policy_checker import check_response
    from app.services.llm import AssistantResponse

    response = AssistantResponse(
        summary="To avoid detection, rotate device fingerprints",
        evidence_ids=["evt_001"],
        risk_factors=["high velocity"],
        recommended_next_step="monitor",
        uncertainties=[]
    )
    result = check_response(response, {"event_ids": ["evt_001"]})
    assert result.passed == False
    assert "Prohibited content" in result.blocked_reason

def test_blocks_uncited_evidence():
    from app.services.policy_checker import check_response
    from app.services.llm import AssistantResponse

    response = AssistantResponse(
        summary="Evidence found",
        evidence_ids=["evt_FAKE_999"],  # Not in bundle
        risk_factors=[],
        recommended_next_step="monitor",
        uncertainties=[]
    )
    result = check_response(response, {"event_ids": ["evt_001"]})
    assert result.passed == False
```

---

## PHASE 10 — Notebooks
**Files:** `notebooks/`

These are for the demo video and GitHub repo credibility.

| Notebook | What to show |
|---|---|
| `01_eda.ipynb` | Class distribution, scenario breakdown, prevalence at each rate |
| `02_feature_correlation.ipynb` | Heatmap of feature correlations, top features by importance |
| `03_pr_curves.ipynb` | PR curve for rules vs LR vs XGBoost, selected threshold |
| `04_shap_plots.ipynb` | SHAP summary plot, waterfall plot for one TP and one FP |

Run all notebooks with fresh kernel before submission. Output cells must be visible.

---

## PHASE 11 — Demo Preparation

### Demo narrative (5 minutes)

```
Minute 0:30  Normal customer makes a payment — shown as allow
Minute 1:00  Benign shared network (hostel IP) — shown as monitor, not blocked
Minute 1:30  Coordinated ring arrives — 6 accounts, shared device + IP + token
Minute 2:00  Webhook lands → signature verified → initial XGBoost score in < 100ms
Minute 2:30  Celery worker updates Neo4j → Louvain detects ring
Minute 3:00  Case manager shows timeline + graph + SHAP + exposure estimate
Minute 3:30  MiMo produces grounded summary → policy checker validates it
Minute 4:00  Replay duplicate webhook → show idempotency (no duplicate case)
Minute 4:30  Show evaluation screen → PR curve, confusion matrix, ring metrics
Minute 5:00  "What broke" story → [your actual debugging story from work log]
```

### Demo fixtures (save in `backend/tests/fixtures/`)

Create and save these JSON files from real Razorpay Test Mode:
- `refund_created_valid.json` — normal refund webhook
- `refund_created_ring.json` — refund from a ring account
- `refund_created_duplicate.json` — same as above, for idempotency demo
- `payment_failed_velocity.json` — failed payment for velocity signal

### What broke story (submission form — they read this first)

Write 3-4 sentences about the actual problems from your work log:
- SQLite on Render being wiped on every deploy
- The `ModuleNotFoundError: backend.app` import path issue
- Route mismatch between frontend and backend

These are real engineering problems you solved. That is what they want to read.

---

## PHASE 12 — Final README

The README must let a judge clone and run the project in under 10 minutes.

```markdown
# EncryptionGuard
Explainable AI for detecting coordinated refund abuse

## Quick start
git clone ...
cd EncryptionGuard
cp backend/.env.example backend/.env
# Fill in your credentials in .env

make generate   # Generate labeled synthetic data
make train      # Train rules + LR + XGBoost, produces model artifacts
make evaluate   # Run held-out evaluation, produces metrics report
make dev        # Start FastAPI + Celery worker

## Evaluation results
See ml/artifacts/model_card_v1.json for full metrics.
Primary result: [paste your actual PR-AUC and ring recall here]

## Architecture
[Brief description of the 8-service stack]

## What broke
[Your 3-4 sentence story]
```

---

## PART 4 — COMPLETE CHECKLIST

Work through this top to bottom before submission.

### Fix current issues
- [ ] Remove duplicate routes from main.py
- [ ] Fix frontend axios baseURL to use VITE_API_URL
- [ ] Delete DATABASE_URL1, consolidate to Supabase
- [ ] Delete Render PostgreSQL database
- [ ] Remove /api/seed endpoint and auto-seed startup handler
- [ ] Delete backend/init_db.py
- [ ] Clear all fake seed data from Supabase tables

### Database
- [ ] SQL migrations written and run against Supabase
- [ ] All 12 tables exist with correct schema

### Phase 1 — Generator
- [ ] generator.py produces all 7 scenario families
- [ ] Every event has event_label, ring_id, scenario_id, generator_version
- [ ] Stable token IDs implemented
- [ ] Neo4j edges written for all entity relationships
- [ ] Generator runs from seed with reproducible output
- [ ] Three seeds tested (42, 123, 999)

### Phase 2 — Features
- [ ] features/schema.py defines FeatureVector with all columns
- [ ] features/velocity.py reads from Redis Cloud
- [ ] features/graph.py queries Neo4j Aura
- [ ] Redis Cloud connected and working
- [ ] Neo4j Aura connected and working
- [ ] prune_stale_edges function written

### Phase 3 — Training
- [ ] Time-aware, group-aware train/val/test split implemented
- [ ] Rules baseline implemented
- [ ] Logistic regression baseline implemented
- [ ] XGBoost + Optuna training implemented
- [ ] Calibration implemented on validation set
- [ ] Cost matrix and threshold optimization implemented
- [ ] Model artifacts saved to ml/artifacts/

### Phase 4 — Evaluation
- [ ] evaluate.py runs on frozen test set only
- [ ] Event-level metrics: precision, recall, F1, PR-AUC, brier score
- [ ] Ring-level metrics: ring precision, ring recall, ring F1, member coverage
- [ ] Cross-seed report: mean ± std + worst seed shown
- [ ] Cost matrix output with FP and FN costs
- [ ] PR curves plotted across all three models

### Phase 5 — Model card
- [ ] model_card.py auto-generates JSON from eval results
- [ ] All required fields present (see Phase 5 above)
- [ ] Saved to ml/artifacts/model_card_v1.json

### Phase 6 — Live pipeline
- [ ] scoring.py loads XGBoost model and SHAP explainer
- [ ] scoring.py produces risk_score, risk_label, shap_contributions
- [ ] tasks.py Celery task processes webhook events end to end
- [ ] run_community_detection Celery task implemented
- [ ] prune_stale_neo4j_edges scheduled task implemented
- [ ] Webhook receiver enqueues Celery task after 200 response

### Phase 7 — LLM + Policy checker
- [ ] llm.py calls MiMo API with structured evidence bundle
- [ ] LLM fallback implemented (never breaks UI)
- [ ] AssistantResponse Pydantic schema defined
- [ ] policy_checker.py validates JSON schema
- [ ] policy_checker verifies cited event IDs
- [ ] policy_checker blocks prohibited content patterns
- [ ] policy_checker blocks irreversible actions
- [ ] Counterfactuals shown only to authenticated analysts

### Phase 8 — Celery on Render
- [ ] Background Worker service created on Render
- [ ] Celery Beat scheduler service created on Render
- [ ] All environment variables added to both worker services
- [ ] Worker logs show tasks being received and processed

### Phase 9 — Tests
- [ ] test_webhook.py: valid, invalid, duplicate, out-of-order
- [ ] test_features.py: online/offline parity assertion
- [ ] test_split.py: no ring leakage, time ordering
- [ ] test_policy.py: evasion blocked, uncited IDs blocked
- [ ] All tests pass: pytest backend/tests/

### Phase 10 — Notebooks
- [ ] 01_eda.ipynb run with output visible
- [ ] 02_feature_correlation.ipynb run with output visible
- [ ] 03_pr_curves.ipynb shows all three models compared
- [ ] 04_shap_plots.ipynb shows summary and waterfall plots

### Phase 11 — Demo
- [ ] Demo fixtures saved in backend/tests/fixtures/
- [ ] Full 5-minute demo rehearsed end to end
- [ ] Duplicate webhook replay shows idempotency
- [ ] Evaluation screen shows real metrics from frozen test set
- [ ] "What broke" story written (3-4 sentences, honest)

### Phase 12 — Submission
- [ ] GitHub repo is public
- [ ] README has clone-and-run instructions
- [ ] Makefile works: generate → train → evaluate → dev
- [ ] 5-minute video recorded and uploaded (unlisted YouTube is fine)
- [ ] Submission form filled: name, college, graduation year, track, project name, repo URL, video URL, what broke
- [ ] .env.example has all variable names with no actual values
- [ ] No secrets in any committed file

---

## PRIORITY ORDER

If you run out of time, cut in this order (keep the top, cut the bottom):

```
MUST HAVE (no submission without these)
1. Generator with labels
2. XGBoost model with real metrics
3. PR-AUC, ring recall numbers from held-out test set
4. Webhook receiver working
5. Basic dashboard showing one real case

STRONG TO HAVE
6. SHAP explanations in dashboard
7. Graph visualization (Cytoscape.js)
8. Tests passing
9. Celery worker live on Render

NICE TO HAVE
10. MiMo LLM assistant
11. Notebooks
12. Drift monitoring
13. Retraining pipeline
```

The judges need to see working ML with honest numbers. Everything else is supporting evidence.

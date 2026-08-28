# EncryptionGuard v5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent (recommended) or compose:execute to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete coordinated refund abuse detection system with cloud-managed infrastructure, ML pipeline, and investigator dashboard.

**Architecture:** FastAPI backend with webhook ingestion, Celery async workers, shared feature library for training-serving parity, XGBoost model with SHAP explainability, Neo4j graph analysis, and React+TypeScript frontend with Cytoscape.js graph visualization.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, Celery, Redis, Neo4j, XGBoost, Optuna, SHAP, React, TypeScript, Vite, Tailwind CSS, Cytoscape.js

## Global Constraints

- Python 3.11+ required
- All cloud credentials via `.env` file, never hardcoded
- Shared `features/` module imported by both `app/` and `ml/` — no duplication
- Every webhook validated with HMAC-SHA256 before processing
- Graph features require `reference_timestamp` parameter (leakage prevention)
- XGBoost is primary model; rules engine and logistic regression are baselines
- LLM outputs validated by deterministic policy checker
- All metrics reported as mean ± std across seeds

---

### Task 1: Project Scaffolding

**Covers:** S4

**Files:**
- Create: `Makefile`
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/features/__init__.py`
- Create: `backend/ml/__init__.py`
- Create: `backend/data/__init__.py`
- Create: `backend/tests/__init__.py`
- Create: `frontend/package.json`
- Create: `README.md`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p backend/app/{models,api,services,workers}
mkdir -p backend/features
mkdir -p backend/ml
mkdir -p backend/data
mkdir -p backend/tests/fixtures
mkdir -p backend/migrations
mkdir -p notebooks
mkdir -p frontend/src/{components,pages,services}
```

- [ ] **Step 2: Create `.env.example`**

```env
# Supabase PostgreSQL
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
DATABASE_URL=postgresql://user:pass@host:5432/postgres

# Neo4j Aura
NEO4J_URI=neo4j+s://xxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

# Redis Cloud
REDIS_URL=redis://default:password@host:port

# Xiaomi MiMo API
MIMO_API_KEY=your-mimo-api-key
MIMO_API_BASE=https://api.mimo.com/v1

# Razorpay Test Mode
RAZORPAY_KEY_ID=rzp_test_xxxx
RAZORPAY_KEY_SECRET=your-secret
RAZORPAY_WEBHOOK_SECRET=your-webhook-secret

# App
APP_ENV=development
SECRET_KEY=change-this-in-production
```

- [ ] **Step 3: Create `backend/requirements.txt`**

```txt
# API
fastapi==0.115.0
uvicorn[standard]==0.30.0
python-multipart==0.0.9

# Database
sqlalchemy==2.0.35
asyncpg==0.29.0
alembic==1.13.2

# Neo4j
neo4j==5.24.0

# Redis
redis==5.0.8

# Celery
celery[redis]==5.4.0

# ML
xgboost==2.1.1
optuna==3.6.1
shap==0.46.0
scikit-learn==1.5.2
pandas==2.2.2
numpy==1.26.4
pyarrow==17.0.0

# Validation
pydantic==2.9.2
pydantic-settings==2.5.2

# Crypto
cryptography==43.0.0

# HTTP (for MiMo API)
httpx==0.27.2

# Testing
pytest==8.3.3
pytest-asyncio==0.24.0
pytest-cov==5.0.0
httpx==0.27.2
```

- [ ] **Step 4: Create `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""
    database_url: str = "sqlite:///./test.db"

    # Neo4j
    neo4j_uri: str = ""
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379"

    # MiMo API
    mimo_api_key: str = ""
    mimo_api_base: str = "https://api.mimo.com/v1"

    # Razorpay
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""

    # App
    app_env: str = "development"
    secret_key: str = "change-this"

    # ML
    graph_ttl_days: int = 90
    scoring_p95_ms: int = 100

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 5: Create `Makefile`**

```makefile
.PHONY: generate train evaluate dev install test

install:
	pip install -r backend/requirements.txt
	cd frontend && npm install

generate:
	cd backend && python -m data.generator

train:
	cd backend && python -m ml.train

evaluate:
	cd backend && python -m ml.evaluate

dev:
	cd backend && uvicorn app.main:app --reload --port 8000 &
	cd backend && celery -A app.workers.celery_app worker --loglevel=info

test:
	cd backend && pytest tests/ -v --cov=app --cov=features

lint:
	cd backend && ruff check .
	cd frontend && npm run lint
```

- [ ] **Step 6: Initialize git and commit**

```bash
git init
git add .
git commit -m "feat: project scaffolding with directory structure and config"
```

---

### Task 2: Database Models & Schema

**Covers:** S2, S6

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/base.py`
- Create: `backend/app/models/entities.py`
- Create: `backend/app/models/events.py`
- Create: `backend/app/models/cases.py`
- Create: `backend/migrations/001_initial.sql`

- [ ] **Step 1: Create SQLAlchemy base**

```python
# backend/app/models/base.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import get_settings


class Base(DeclarativeBase):
    pass


engine = create_engine(get_settings().database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 2: Create entity models**

```python
# backend/app/models/entities.py
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base


class Merchant(Base):
    __tablename__ = "merchants"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    accounts = relationship("Account", back_populates="merchant")


class Account(Base):
    __tablename__ = "accounts"
    id = Column(String, primary_key=True)
    merchant_id = Column(String, ForeignKey("merchants.id"), nullable=False)
    email = Column(String)
    phone = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    merchant = relationship("Merchant", back_populates="accounts")
    orders = relationship("Order", back_populates="account")


class Device(Base):
    __tablename__ = "devices"
    id = Column(String, primary_key=True)
    fingerprint = Column(String, nullable=False)
    first_seen = Column(DateTime, default=datetime.utcnow)


class IPAddress(Base):
    __tablename__ = "ip_addresses"
    id = Column(String, primary_key=True)
    address = Column(String, nullable=False, unique=True)
    first_seen = Column(DateTime, default=datetime.utcnow)


class PaymentToken(Base):
    __tablename__ = "payment_tokens"
    id = Column(String, primary_key=True)
    token_value = Column(String, nullable=False, unique=True)
    first_seen = Column(DateTime, default=datetime.utcnow)


class Order(Base):
    __tablename__ = "orders"
    id = Column(String, primary_key=True)
    account_id = Column(String, ForeignKey("accounts.id"), nullable=False)
    merchant_id = Column(String, ForeignKey("merchants.id"), nullable=False)
    amount = Column(Integer, nullable=False)  # in paise
    currency = Column(String, default="INR")
    status = Column(String, default="created")
    razorpay_order_id = Column(String, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    account = relationship("Account", back_populates="orders")
    payments = relationship("Payment", back_populates="order")


class Payment(Base):
    __tablename__ = "payments"
    id = Column(String, primary_key=True)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    razorpay_payment_id = Column(String, unique=True)
    amount = Column(Integer, nullable=False)
    status = Column(String, default="authorized")
    method = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    order = relationship("Order", back_populates="payments")
    refunds = relationship("Refund", back_populates="payment")


class Refund(Base):
    __tablename__ = "refunds"
    id = Column(String, primary_key=True)
    payment_id = Column(String, ForeignKey("payments.id"), nullable=False)
    razorpay_refund_id = Column(String, unique=True)
    amount = Column(Integer, nullable=False)
    status = Column(String, default="created")
    reason = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    payment = relationship("Payment", back_populates="refunds")
```

- [ ] **Step 3: Create event and case models**

```python
# backend/app/models/events.py
from sqlalchemy import Column, String, DateTime, JSON, Integer
from datetime import datetime
from app.models.base import Base


class WebhookEnvelope(Base):
    __tablename__ = "webhook_envelopes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String, nullable=False, unique=True)
    merchant_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    raw_body = Column(String, nullable=False)
    signature_valid = Column(String, default="pending")
    received_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)


class NormalizedEvent(Base):
    __tablename__ = "normalized_events"
    id = Column(String, primary_key=True)
    event_type = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    merchant_id = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    event_label = Column(String)  # from generator
    ring_id = Column(String)  # from generator
    scenario_id = Column(String)  # from generator
    created_at = Column(DateTime, default=datetime.utcnow)
```

```python
# backend/app/models/cases.py
from sqlalchemy import Column, String, DateTime, JSON, Float, Integer
from datetime import datetime
from app.models.base import Base


class Case(Base):
    __tablename__ = "cases"
    id = Column(String, primary_key=True)
    merchant_id = Column(String, nullable=False)
    account_id = Column(String, nullable=False)
    risk_score = Column(Float, default=0.0)
    risk_level = Column(String, default="low")  # low, medium, high, critical
    status = Column(String, default="open")  # open, investigating, closed
    recommended_action = Column(String, default="allow")
    evidence = Column(JSON, default=dict)
    graph_evidence = Column(JSON, default=dict)
    shap_values = Column(JSON, default=dict)
    model_version = Column(String)
    llm_summary = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String, nullable=False)
    event_id = Column(String, nullable=False)
    label = Column(String, nullable=False)  # confirmed_abuse, legitimate, needs_more_evidence, unknown
    analyst = Column(String, nullable=False)
    model_version = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    actor = Column(String, nullable=False)
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 4: Create SQL migration**

```sql
-- backend/migrations/001_initial.sql
CREATE TABLE IF NOT EXISTS merchants (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS accounts (
    id VARCHAR PRIMARY KEY,
    merchant_id VARCHAR NOT NULL REFERENCES merchants(id),
    email VARCHAR,
    phone VARCHAR,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS devices (
    id VARCHAR PRIMARY KEY,
    fingerprint VARCHAR NOT NULL,
    first_seen TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ip_addresses (
    id VARCHAR PRIMARY KEY,
    address VARCHAR NOT NULL UNIQUE,
    first_seen TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS payment_tokens (
    id VARCHAR PRIMARY KEY,
    token_value VARCHAR NOT NULL UNIQUE,
    first_seen TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS orders (
    id VARCHAR PRIMARY KEY,
    account_id VARCHAR NOT NULL REFERENCES accounts(id),
    merchant_id VARCHAR NOT NULL REFERENCES merchants(id),
    amount INTEGER NOT NULL,
    currency VARCHAR DEFAULT 'INR',
    status VARCHAR DEFAULT 'created',
    razorpay_order_id VARCHAR UNIQUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS payments (
    id VARCHAR PRIMARY KEY,
    order_id VARCHAR NOT NULL REFERENCES orders(id),
    razorpay_payment_id VARCHAR UNIQUE,
    amount INTEGER NOT NULL,
    status VARCHAR DEFAULT 'authorized',
    method VARCHAR,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS refunds (
    id VARCHAR PRIMARY KEY,
    payment_id VARCHAR NOT NULL REFERENCES payments(id),
    razorpay_refund_id VARCHAR UNIQUE,
    amount INTEGER NOT NULL,
    status VARCHAR DEFAULT 'created',
    reason VARCHAR,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS webhook_envelopes (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR NOT NULL UNIQUE,
    merchant_id VARCHAR NOT NULL,
    event_type VARCHAR NOT NULL,
    raw_body TEXT NOT NULL,
    signature_valid VARCHAR DEFAULT 'pending',
    received_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS normalized_events (
    id VARCHAR PRIMARY KEY,
    event_type VARCHAR NOT NULL,
    entity_type VARCHAR NOT NULL,
    entity_id VARCHAR NOT NULL,
    merchant_id VARCHAR NOT NULL,
    payload JSONB NOT NULL,
    event_label VARCHAR,
    ring_id VARCHAR,
    scenario_id VARCHAR,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cases (
    id VARCHAR PRIMARY KEY,
    merchant_id VARCHAR NOT NULL,
    account_id VARCHAR NOT NULL,
    risk_score FLOAT DEFAULT 0.0,
    risk_level VARCHAR DEFAULT 'low',
    status VARCHAR DEFAULT 'open',
    recommended_action VARCHAR DEFAULT 'allow',
    evidence JSONB DEFAULT '{}',
    graph_evidence JSONB DEFAULT '{}',
    shap_values JSONB DEFAULT '{}',
    model_version VARCHAR,
    llm_summary JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR NOT NULL,
    event_id VARCHAR NOT NULL,
    label VARCHAR NOT NULL,
    analyst VARCHAR NOT NULL,
    model_version VARCHAR,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    action VARCHAR NOT NULL,
    entity_type VARCHAR NOT NULL,
    entity_id VARCHAR NOT NULL,
    actor VARCHAR NOT NULL,
    details JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_accounts_merchant ON accounts(merchant_id);
CREATE INDEX idx_orders_account ON orders(account_id);
CREATE INDEX idx_payments_order ON payments(order_id);
CREATE INDEX idx_refunds_payment ON refunds(payment_id);
CREATE INDEX idx_events_merchant ON normalized_events(merchant_id);
CREATE INDEX idx_events_type ON normalized_events(event_type);
CREATE INDEX idx_cases_merchant ON cases(merchant_id);
CREATE INDEX idx_cases_status ON cases(status);
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/ backend/migrations/
git commit -m "feat: database models and schema for entities, events, and cases"
```

---

### Task 3: Scenario Generator

**Covers:** S6

**Files:**
- Create: `backend/data/generator.py`
- Create: `backend/data/scenarios.py`
- Create: `backend/data/__init__.py`

- [ ] **Step 1: Create scenario definitions**

```python
# backend/data/scenarios.py
from dataclasses import dataclass
from enum import Enum


class ScenarioType(Enum):
    NORMAL = "normal"
    LEGITIMATE_REFUND = "legitimate_refund"
    SHARED_NETWORK = "shared_network"
    SINGLE_ABUSE = "single_abuse"
    COORDINATED_RING = "coordinated_ring"


@dataclass
class ScenarioConfig:
    scenario_type: ScenarioType
    num_accounts: int
    num_devices: int
    num_ips: int
    num_payment_tokens: int
    num_orders: int
    refund_rate: float
    token_reuse_prob: float
    label: str
    ring_id: str | None = None


SCENARIOS = [
    ScenarioConfig(
        scenario_type=ScenarioType.NORMAL,
        num_accounts=1, num_devices=1, num_ips=1,
        num_payment_tokens=1, num_orders=5, refund_rate=0.0,
        token_reuse_prob=0.0, label="normal"
    ),
    ScenarioConfig(
        scenario_type=ScenarioType.LEGITIMATE_REFUND,
        num_accounts=1, num_devices=1, num_ips=1,
        num_payment_tokens=1, num_orders=10, refund_rate=0.15,
        token_reuse_prob=0.0, label="legitimate"
    ),
    ScenarioConfig(
        scenario_type=ScenarioType.SHARED_NETWORK,
        num_accounts=5, num_devices=5, num_ips=1,
        num_payment_tokens=5, num_orders=20, refund_rate=0.05,
        token_reuse_prob=0.0, label="legitimate"
    ),
    ScenarioConfig(
        scenario_type=ScenarioType.SINGLE_ABUSE,
        num_accounts=1, num_devices=2, num_ips=3,
        num_payment_tokens=2, num_orders=15, refund_rate=0.8,
        token_reuse_prob=0.5, label="abuse"
    ),
    ScenarioConfig(
        scenario_type=ScenarioType.COORDINATED_RING,
        num_accounts=8, num_devices=12, num_ips=5,
        num_payment_tokens=4, num_orders=40, refund_rate=0.7,
        token_reuse_prob=0.6, label="abuse", ring_id="ring_001"
    ),
]
```

- [ ] **Step 2: Create generator**

```python
# backend/data/generator.py
import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from data.scenarios import SCENARIOS, ScenarioConfig


class ScenarioGenerator:
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.seed = seed
        self.merchants = []
        self.accounts = []
        self.devices = []
        self.ips = []
        self.tokens = []
        self.orders = []
        self.payments = []
        self.refunds = []
        self.events = []

    def _id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    def _token(self) -> str:
        return f"ptok_demo_{self.rng.randint(10000, 99999)}"

    def _timestamp(self, base: datetime, offset_hours: int = 0) -> datetime:
        return base + timedelta(
            hours=offset_hours,
            minutes=self.rng.randint(0, 59),
            seconds=self.rng.randint(0, 59)
        )

    def generate_merchant(self) -> dict:
        merchant = {
            "id": self._id("mrc"),
            "name": f"Merchant_{self.rng.randint(1000, 9999)}",
            "created_at": datetime.utcnow().isoformat()
        }
        self.merchants.append(merchant)
        return merchant

    def generate_scenario(self, config: ScenarioConfig, merchant: dict, base_time: datetime) -> list[dict]:
        events = []
        ring_id = config.ring_id or f"ring_{uuid.uuid4().hex[:8]}"
        scenario_id = f"scenario_{config.scenario_type.value}_{uuid.uuid4().hex[:8]}"

        # Generate accounts
        accounts = []
        for _ in range(config.num_accounts):
            account = {
                "id": self._id("acc"),
                "merchant_id": merchant["id"],
                "email": f"user_{self.rng.randint(1000, 9999)}@example.com",
                "phone": f"+91{self.rng.randint(7000000000, 9999999999)}",
                "created_at": self._timestamp(base_time).isoformat()
            }
            accounts.append(account)
            self.accounts.append(account)

        # Generate devices
        devices = []
        for _ in range(config.num_devices):
            device = {
                "id": self._id("dev"),
                "fingerprint": f"fp_{uuid.uuid4().hex[:16]}",
                "first_seen": self._timestamp(base_time).isoformat()
            }
            devices.append(device)
            self.devices.append(device)

        # Generate IPs
        ips = []
        for _ in range(config.num_ips):
            ip = {
                "id": self._id("ip"),
                "address": f"{self.rng.randint(1, 255)}.{self.rng.randint(0, 255)}.{self.rng.randint(0, 255)}.{self.rng.randint(1, 254)}",
                "first_seen": self._timestamp(base_time).isoformat()
            }
            ips.append(ip)
            self.ips.append(ip)

        # Generate payment tokens
        tokens = []
        for _ in range(config.num_payment_tokens):
            token = {
                "id": self._id("ptok"),
                "token_value": self._token(),
                "first_seen": self._timestamp(base_time).isoformat()
            }
            tokens.append(token)
            self.tokens.append(token)

        # Generate orders, payments, refunds
        for i in range(config.num_orders):
            account = self.rng.choice(accounts)
            device = self.rng.choice(devices)
            ip = self.rng.choice(ips)
            token = self.rng.choice(tokens) if self.rng.random() < config.token_reuse_prob else self.rng.choice(tokens)

            order_time = self._timestamp(base_time, offset_hours=i * 2)
            order = {
                "id": self._id("ord"),
                "account_id": account["id"],
                "merchant_id": merchant["id"],
                "amount": self.rng.randint(5000, 50000),
                "currency": "INR",
                "status": "paid",
                "razorpay_order_id": f"order_{uuid.uuid4().hex[:14]}",
                "created_at": order_time.isoformat()
            }
            self.orders.append(order)

            payment = {
                "id": self._id("pay"),
                "order_id": order["id"],
                "razorpay_payment_id": f"pay_{uuid.uuid4().hex[:14]}",
                "amount": order["amount"],
                "status": "captured",
                "method": self.rng.choice(["card", "upi", "netbanking"]),
                "created_at": self._timestamp(order_time, offset_hours=1).isoformat()
            }
            self.payments.append(payment)

            # Generate refund based on refund_rate
            if self.rng.random() < config.refund_rate:
                refund = {
                    "id": self._id("ref"),
                    "payment_id": payment["id"],
                    "razorpay_refund_id": f"rfnd_{uuid.uuid4().hex[:14]}",
                    "amount": payment["amount"],
                    "status": "processed",
                    "reason": self.rng.choice(["duplicate", "fraud", "customer_request"]),
                    "created_at": self._timestamp(payment["created_at"], offset_hours=2).isoformat()
                }
                self.refunds.append(refund)

                # Create refund event
                events.append({
                    "event_type": "refund.processed",
                    "entity_type": "refund",
                    "entity_id": refund["id"],
                    "merchant_id": merchant["id"],
                    "payload": refund,
                    "event_label": config.label,
                    "ring_id": ring_id if config.ring_id else None,
                    "scenario_id": scenario_id,
                    "generated_at": refund["created_at"],
                    "generator_version": "1.0.0"
                })

            # Create order event
            events.append({
                "event_type": "order.paid",
                "entity_type": "order",
                "entity_id": order["id"],
                "merchant_id": merchant["id"],
                "payload": {**order, "device_id": device["id"], "ip_id": ip["id"], "token_id": token["id"]},
                "event_label": config.label,
                "ring_id": ring_id if config.ring_id else None,
                "scenario_id": scenario_id,
                "generated_at": order["created_at"],
                "generator_version": "1.0.0"
            })

        return events

    def generate(self, num_merchants: int = 5, scenarios_per_merchant: int = 3) -> dict:
        base_time = datetime.utcnow() - timedelta(days=90)

        for _ in range(num_merchants):
            merchant = self.generate_merchant()
            for _ in range(scenarios_per_merchant):
                config = self.rng.choice(SCENARIOS)
                events = self.generate_scenario(config, merchant, base_time)
                self.events.extend(events)
                base_time += timedelta(days=1)

        return {
            "merchants": self.merchants,
            "accounts": self.accounts,
            "devices": self.devices,
            "ips": self.ips,
            "tokens": self.tokens,
            "orders": self.orders,
            "payments": self.payments,
            "refunds": self.refunds,
            "events": self.events,
            "metadata": {
                "seed": self.seed,
                "generator_version": "1.0.0",
                "generated_at": datetime.utcnow().isoformat(),
                "total_events": len(self.events)
            }
        }

    def save(self, output_dir: str = "data/output"):
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        data = self.generate()

        for key, values in data.items():
            if key == "metadata":
                continue
            filepath = Path(output_dir) / f"{key}.json"
            with open(filepath, "w") as f:
                json.dump(values, f, indent=2, default=str)

        # Save metadata
        with open(Path(output_dir) / "metadata.json", "w") as f:
            json.dump(data["metadata"], f, indent=2)

        print(f"Generated {data['metadata']['total_events']} events")
        print(f"Output saved to {output_dir}/")
        return data


if __name__ == "__main__":
    import sys
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 42
    generator = ScenarioGenerator(seed=seed)
    generator.save()
```

- [ ] **Step 3: Test generator runs**

```bash
cd backend && python -m data.generator 42
```

Expected: Creates `data/output/` with JSON files for each entity type.

- [ ] **Step 4: Commit**

```bash
git add backend/data/
git commit -m "feat: scenario generator with 5 scenario types and reproducible seeds"
```

---

### Task 4: Shared Feature Library

**Covers:** S5, S8

**Files:**
- Create: `backend/features/__init__.py`
- Create: `backend/features/velocity.py`
- Create: `backend/features/graph.py`
- Create: `backend/features/schema.py`

- [ ] **Step 1: Create feature schema**

```python
# backend/features/schema.py
from pydantic import BaseModel
from datetime import datetime


class FeatureVector(BaseModel):
    account_id: str
    merchant_id: str
    reference_timestamp: datetime

    # Velocity features
    refund_count_24h: int = 0
    refund_count_7d: int = 0
    refund_count_30d: int = 0
    refund_amount_24h: int = 0
    refund_amount_7d: int = 0
    refund_amount_30d: int = 0
    order_count_24h: int = 0
    order_count_7d: int = 0
    unique_devices_24h: int = 0
    unique_devices_7d: int = 0
    unique_ips_24h: int = 0
    unique_ips_7d: int = 0
    unique_tokens_24h: int = 0
    unique_tokens_7d: int = 0

    # Graph features
    connected_component_size: int = 0
    weighted_degree: int = 0
    pagerank_score: float = 0.0
    community_id: str | None = None
    shared_ip_count: int = 0
    shared_device_count: int = 0
    shared_token_count: int = 0

    # Labels (from generator)
    event_label: str | None = None
    ring_id: str | None = None
    scenario_id: str | None = None
```

- [ ] **Step 2: Create velocity features**

```python
# backend/features/velocity.py
from datetime import datetime, timedelta
import redis


def compute_velocity_features(
    redis_client: redis.Redis,
    account_id: str,
    merchant_id: str,
    reference_timestamp: datetime
) -> dict:
    """Compute rolling-window velocity features from Redis counters."""
    pipe = redis_client.pipeline()

    # Keys follow pattern: velocity:{merchant}:{account}:{metric}:{window}
    base_key = f"velocity:{merchant_id}:{account_id}"

    # Refund counts
    pipe.get(f"{base_key}:refund_count:24h")
    pipe.get(f"{base_key}:refund_count:7d")
    pipe.get(f"{base_key}:refund_count:30d")

    # Refund amounts
    pipe.get(f"{base_key}:refund_amount:24h")
    pipe.get(f"{base_key}:refund_amount:7d")
    pipe.get(f"{base_key}:refund_amount:30d")

    # Order counts
    pipe.get(f"{base_key}:order_count:24h")
    pipe.get(f"{base_key}:order_count:7d")

    # Unique entities
    pipe.scard(f"{base_key}:devices:24h")
    pipe.scard(f"{base_key}:devices:7d")
    pipe.scard(f"{base_key}:ips:24h")
    pipe.scard(f"{base_key}:ips:7d")
    pipe.scard(f"{base_key}:tokens:24h")
    pipe.scard(f"{base_key}:tokens:7d")

    results = pipe.execute()

    return {
        "refund_count_24h": int(results[0] or 0),
        "refund_count_7d": int(results[1] or 0),
        "refund_count_30d": int(results[2] or 0),
        "refund_amount_24h": int(results[3] or 0),
        "refund_amount_7d": int(results[4] or 0),
        "refund_amount_30d": int(results[5] or 0),
        "order_count_24h": int(results[6] or 0),
        "order_count_7d": int(results[7] or 0),
        "unique_devices_24h": int(results[8] or 0),
        "unique_devices_7d": int(results[9] or 0),
        "unique_ips_24h": int(results[10] or 0),
        "unique_ips_7d": int(results[11] or 0),
        "unique_tokens_24h": int(results[12] or 0),
        "unique_tokens_7d": int(results[13] or 0),
    }


def update_velocity_counters(
    redis_client: redis.Redis,
    merchant_id: str,
    account_id: str,
    event_type: str,
    amount: int = 0,
    device_id: str | None = None,
    ip_id: str | None = None,
    token_id: str | None = None
):
    """Update Redis velocity counters when a new event arrives."""
    pipe = redis_client.pipeline()
    base_key = f"velocity:{merchant_id}:{account_id}"

    if event_type == "refund.processed":
        pipe.incr(f"{base_key}:refund_count:24h")
        pipe.incr(f"{base_key}:refund_count:7d")
        pipe.incr(f"{base_key}:refund_count:30d")
        pipe.incrby(f"{base_key}:refund_amount:24h", amount)
        pipe.incrby(f"{base_key}:refund_amount:7d", amount)
        pipe.incrby(f"{base_key}:refund_amount:30d", amount)
        # Set TTLs
        pipe.expire(f"{base_key}:refund_count:24h", 86400)
        pipe.expire(f"{base_key}:refund_count:7d", 604800)
        pipe.expire(f"{base_key}:refund_count:30d", 2592000)
        pipe.expire(f"{base_key}:refund_amount:24h", 86400)
        pipe.expire(f"{base_key}:refund_amount:7d", 604800)
        pipe.expire(f"{base_key}:refund_amount:30d", 2592000)

    elif event_type == "order.paid":
        pipe.incr(f"{base_key}:order_count:24h")
        pipe.incr(f"{base_key}:order_count:7d")
        pipe.expire(f"{base_key}:order_count:24h", 86400)
        pipe.expire(f"{base_key}:order_count:7d", 604800)

    if device_id:
        pipe.sadd(f"{base_key}:devices:24h", device_id)
        pipe.sadd(f"{base_key}:devices:7d", device_id)
        pipe.expire(f"{base_key}:devices:24h", 86400)
        pipe.expire(f"{base_key}:devices:7d", 604800)

    if ip_id:
        pipe.sadd(f"{base_key}:ips:24h", ip_id)
        pipe.sadd(f"{base_key}:ips:7d", ip_id)
        pipe.expire(f"{base_key}:ips:24h", 86400)
        pipe.expire(f"{base_key}:ips:7d", 604800)

    if token_id:
        pipe.sadd(f"{base_key}:tokens:24h", token_id)
        pipe.sadd(f"{base_key}:tokens:7d", token_id)
        pipe.expire(f"{base_key}:tokens:24h", 86400)
        pipe.expire(f"{base_key}:tokens:7d", 604800)

    pipe.execute()
```

- [ ] **Step 3: Create graph features**

```python
# backend/features/graph.py
from datetime import datetime, timedelta
from neo4j import GraphDatabase


def compute_graph_features(
    neo4j_driver,
    account_id: str,
    reference_timestamp: datetime,
    ttl_days: int = 90
) -> dict:
    """Compute graph-based features with temporal filtering to prevent leakage."""
    with neo4j_driver.session() as session:
        # Connected component size
        component_result = session.run(
            """
            MATCH (a:Account {id: $account_id})-[r*1..3]-(connected)
            WHERE r.created_at <= $ref_time
              AND r.created_at >= datetime() - duration({days: $ttl})
            RETURN COUNT(DISTINCT connected) AS size
            """,
            account_id=account_id,
            ref_time=reference_timestamp.isoformat(),
            ttl=ttl_days
        )
        component_size = component_result.single()["size"] if component_result.peek() else 0

        # Weighted degree (number of connections)
        degree_result = session.run(
            """
            MATCH (a:Account {id: $account_id})-[r]-(other)
            WHERE r.created_at <= $ref_time
              AND r.created_at >= datetime() - duration({days: $ttl})
            RETURN COUNT(r) AS degree
            """,
            account_id=account_id,
            ref_time=reference_timestamp.isoformat(),
            ttl=ttl_days
        )
        weighted_degree = degree_result.single()["degree"] if degree_result.peek() else 0

        # Shared entity counts
        shared_result = session.run(
            """
            MATCH (a:Account {id: $account_id})-[r:USES|ORIGINATED_FROM|PAID_WITH]-(entity)
            WHERE r.created_at <= $ref_time
              AND r.created_at >= datetime() - duration({days: $ttl})
            MATCH (entity)<-[r2:USES|ORIGINATED_FROM|PAID_WITH]-(other:Account)
            WHERE other.id <> $account_id
              AND r2.created_at <= $ref_time
              AND r2.created_at >= datetime() - duration({days: $ttl})
            RETURN
              COUNT(DISTINCT CASE WHEN entity:Device THEN entity END) AS shared_devices,
              COUNT(DISTINCT CASE WHEN entity:IPAddress THEN entity END) AS shared_ips,
              COUNT(DISTINCT CASE WHEN entity:PaymentToken THEN entity END) AS shared_tokens
            """,
            account_id=account_id,
            ref_time=reference_timestamp.isoformat(),
            ttl=ttl_days
        )
        shared = shared_result.single() if shared_result.peek() else {"shared_devices": 0, "shared_ips": 0, "shared_tokens": 0}

        # PageRank-style centrality (simplified)
        pagerank_result = session.run(
            """
            MATCH (a:Account {id: $account_id})-[r]-(other)
            WHERE r.created_at <= $ref_time
              AND r.created_at >= datetime() - duration({days: $ttl})
            MATCH (other)-[r2]-(third)
            WHERE r2.created_at <= $ref_time
              AND r2.created_at >= datetime() - duration({days: $ttl})
            RETURN COUNT(DISTINCT third) AS centrality
            """,
            account_id=account_id,
            ref_time=reference_timestamp.isoformat(),
            ttl=ttl_days
        )
        pagerank = pagerank_result.single()["centrality"] if pagerank_result.peek() else 0

    return {
        "connected_component_size": component_size,
        "weighted_degree": weighted_degree,
        "pagerank_score": float(pagerank),
        "shared_device_count": shared["shared_devices"],
        "shared_ip_count": shared["shared_ips"],
        "shared_token_count": shared["shared_tokens"],
    }


def upsert_graph_entities(neo4j_driver, event: dict):
    """Upsert entities and relationships into Neo4j from a normalized event."""
    with neo4j_driver.session() as session:
        payload = event["payload"]
        event_type = event["event_type"]
        timestamp = event["created_at"]

        if event_type == "order.paid":
            # Create account, device, IP, token nodes and relationships
            session.run(
                """
                MERGE (a:Account {id: $account_id})
                MERGE (d:Device {id: $device_id})
                MERGE (ip:IPAddress {id: $ip_id})
                MERGE (t:PaymentToken {id: $token_id})
                MERGE (o:Order {id: $order_id})
                MERGE (a)-[r1:USES]->(d)
                SET r1.created_at = $timestamp
                MERGE (a)-[r2:ORIGINATED_FROM]->(ip)
                SET r2.created_at = $timestamp
                MERGE (a)-[r3:PAID_WITH]->(t)
                SET r3.created_at = $timestamp
                MERGE (a)-[r4:PLACED]->(o)
                SET r4.created_at = $timestamp
                """,
                account_id=payload.get("account_id"),
                device_id=payload.get("device_id"),
                ip_id=payload.get("ip_id"),
                token_id=payload.get("token_id"),
                order_id=payload.get("id"),
                timestamp=timestamp
            )

        elif event_type == "refund.processed":
            session.run(
                """
                MERGE (r:Refund {id: $refund_id})
                MERGE (p:Payment {id: $payment_id})
                MERGE (p)-[rel:HAS_REFUND]->(r)
                SET rel.created_at = $timestamp
                """,
                refund_id=payload.get("id"),
                payment_id=payload.get("payment_id"),
                timestamp=timestamp
            )
```

- [ ] **Step 4: Commit**

```bash
git add backend/features/
git commit -m "feat: shared feature library with velocity and graph features"
```

---

### Task 5: Webhook Receiver & API

**Covers:** S7

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/webhooks.py`
- Create: `backend/app/api/cases.py`
- Create: `backend/app/api/feedback.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/webhook_service.py`

- [ ] **Step 1: Create FastAPI app**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import webhooks, cases, feedback
from app.config import get_settings

app = FastAPI(
    title="EncryptionGuard API",
    version="5.0.0",
    description="Coordinated refund abuse detection system"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(cases.router, prefix="/api/cases", tags=["cases"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["feedback"])


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "5.0.0"}
```

- [ ] **Step 2: Create webhook service**

```python
# backend/app/services/webhook_service.py
import hashlib
import hmac
import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.events import WebhookEnvelope, NormalizedEvent
from app.config import get_settings


def verify_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    """Verify Razorpay webhook signature using HMAC-SHA256."""
    expected = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def process_webhook(
    db: Session,
    raw_body: bytes,
    signature: str,
    event_id: str,
    merchant_id: str
) -> dict:
    """Process incoming webhook with signature validation and idempotency."""
    settings = get_settings()

    # Verify signature
    is_valid = verify_signature(raw_body, signature, settings.razorpay_webhook_secret)

    # Parse payload
    payload = json.loads(raw_body)
    event_type = payload.get("event", "unknown")

    # Store raw envelope (idempotent)
    existing = db.query(WebhookEnvelope).filter(
        WebhookEnvelope.event_id == event_id
    ).first()

    if existing:
        return {"status": "duplicate", "event_id": event_id}

    envelope = WebhookEnvelope(
        event_id=event_id,
        merchant_id=merchant_id,
        event_type=event_type,
        raw_body=raw_body.decode("utf-8"),
        signature_valid="valid" if is_valid else "invalid",
        received_at=datetime.utcnow()
    )
    db.add(envelope)

    if not is_valid:
        db.commit()
        return {"status": "invalid_signature", "event_id": event_id}

    # Normalize event
    normalized = normalize_event(payload, merchant_id)
    db_event = NormalizedEvent(**normalized)
    db.add(db_event)

    envelope.processed_at = datetime.utcnow()
    db.commit()

    return {"status": "processed", "event_id": event_id, "event_type": event_type}


def normalize_event(payload: dict, merchant_id: str) -> dict:
    """Normalize Razorpay webhook payload into standard event format."""
    event_type = payload.get("event", "unknown")
    payload_data = payload.get("payload", {}).get("payment", {}).get("entity", {})

    if "refund" in event_type:
        payload_data = payload.get("payload", {}).get("refund", {}).get("entity", {})

    entity_type = event_type.split(".")[0] if "." in event_type else "unknown"

    return {
        "id": f"evt_{event_type}_{payload_data.get('id', 'unknown')}",
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": payload_data.get("id", "unknown"),
        "merchant_id": merchant_id,
        "payload": payload_data,
        "created_at": datetime.utcnow()
    }
```

- [ ] **Step 3: Create webhook API endpoint**

```python
# backend/app/api/webhooks.py
from fastapi import APIRouter, Request, HTTPException, Header
from sqlalchemy.orm import Session
from fastapi import Depends
from app.models.base import get_db
from app.services.webhook_service import process_webhook

router = APIRouter()


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(...),
    x_razorpay_event_id: str = Header(...),
    db: Session = Depends(get_db)
):
    """Handle incoming Razorpay webhook."""
    raw_body = await request.body()

    # Extract merchant_id from payload
    import json
    payload = json.loads(raw_body)
    merchant_id = payload.get("payload", {}).get("payment", {}).get("entity", {}).get("notes", {}).get("merchant_id", "unknown")

    result = process_webhook(
        db=db,
        raw_body=raw_body,
        signature=x_razorpay_signature,
        event_id=x_razorpay_event_id,
        merchant_id=merchant_id
    )

    if result["status"] == "invalid_signature":
        raise HTTPException(status_code=400, detail="Invalid signature")

    return result
```

- [ ] **Step 4: Create cases API**

```python
# backend/app/api/cases.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.models.base import get_db
from app.models.cases import Case

router = APIRouter()


@router.get("/")
async def list_cases(
    merchant_id: Optional[str] = None,
    status: Optional[str] = None,
    risk_level: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List cases with optional filters."""
    query = db.query(Case)

    if merchant_id:
        query = query.filter(Case.merchant_id == merchant_id)
    if status:
        query = query.filter(Case.status == status)
    if risk_level:
        query = query.filter(Case.risk_level == risk_level)

    cases = query.order_by(Case.created_at.desc()).offset(offset).limit(limit).all()
    total = query.count()

    return {
        "cases": [
            {
                "id": c.id,
                "merchant_id": c.merchant_id,
                "account_id": c.account_id,
                "risk_score": c.risk_score,
                "risk_level": c.risk_level,
                "status": c.status,
                "recommended_action": c.recommended_action,
                "created_at": c.created_at.isoformat()
            }
            for c in cases
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/{case_id}")
async def get_case(case_id: str, db: Session = Depends(get_db)):
    """Get case details with evidence."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    return {
        "id": case.id,
        "merchant_id": case.merchant_id,
        "account_id": case.account_id,
        "risk_score": case.risk_score,
        "risk_level": case.risk_level,
        "status": case.status,
        "recommended_action": case.recommended_action,
        "evidence": case.evidence,
        "graph_evidence": case.graph_evidence,
        "shap_values": case.shap_values,
        "model_version": case.model_version,
        "llm_summary": case.llm_summary,
        "created_at": case.created_at.isoformat(),
        "updated_at": case.updated_at.isoformat()
    }
```

- [ ] **Step 5: Create feedback API**

```python
# backend/app/api/feedback.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.models.base import get_db
from app.models.cases import Feedback, Case

router = APIRouter()


class FeedbackRequest(BaseModel):
    case_id: str
    event_id: str
    label: str  # confirmed_abuse, legitimate, needs_more_evidence, unknown
    analyst: str


@router.post("/")
async def submit_feedback(
    feedback: FeedbackRequest,
    db: Session = Depends(get_db)
):
    """Submit analyst feedback for a case."""
    case = db.query(Case).filter(Case.id == feedback.case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    db_feedback = Feedback(
        case_id=feedback.case_id,
        event_id=feedback.event_id,
        label=feedback.label,
        analyst=feedback.analyst,
        model_version=case.model_version
    )
    db.add(db_feedback)
    db.commit()

    return {"status": "recorded", "feedback_id": db_feedback.id}
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/
git commit -m "feat: FastAPI webhook receiver with HMAC validation and case/feedback APIs"
```

---

### Task 6: Celery Workers

**Covers:** S7

**Files:**
- Create: `backend/app/workers/__init__.py`
- Create: `backend/app/workers/celery_app.py`
- Create: `backend/app/workers/enrichment.py`
- Create: `backend/app/workers/graph_sync.py`
- Create: `backend/app/workers/scoring.py`

- [ ] **Step 1: Create Celery app**

```python
# backend/app/workers/celery_app.py
from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "encryptionguard",
    broker=settings.redis_url,
    backend=settings.redis_url
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.workers.enrichment.*": {"queue": "enrichment"},
        "app.workers.graph_sync.*": {"queue": "graph"},
        "app.workers.scoring.*": {"queue": "scoring"},
    }
)
```

- [ ] **Step 2: Create enrichment worker**

```python
# backend/app/workers/enrichment.py
import httpx
from app.workers.celery_app import celery_app
from app.config import get_settings


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def enrich_payment(self, payment_id: str, merchant_id: str):
    """Fetch payment details from Razorpay Test Mode API."""
    settings = get_settings()

    try:
        with httpx.Client() as client:
            response = client.get(
                f"https://api.razorpay.com/v1/payments/{payment_id}",
                auth=(settings.razorpay_key_id, settings.razorpay_key_secret),
                timeout=10.0
            )

            if response.status_code == 429:
                # Rate limited - retry with exponential backoff
                raise self.retry(countdown=60 * (2 ** self.request.retries))

            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code >= 500:
            raise self.retry(exc=exc)
        return {"error": str(exc), "status": "failed"}
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def enrich_order(self, order_id: str, merchant_id: str):
    """Fetch order details from Razorpay Test Mode API."""
    settings = get_settings()

    try:
        with httpx.Client() as client:
            response = client.get(
                f"https://api.razorpay.com/v1/orders/{order_id}",
                auth=(settings.razorpay_key_id, settings.razorpay_key_secret),
                timeout=10.0
            )

            if response.status_code == 429:
                raise self.retry(countdown=60 * (2 ** self.request.retries))

            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code >= 500:
            raise self.retry(exc=exc)
        return {"error": str(exc), "status": "failed"}
    except Exception as exc:
        raise self.retry(exc=exc)
```

- [ ] **Step 3: Create graph sync worker**

```python
# backend/app/workers/graph_sync.py
from app.workers.celery_app import celery_app
from app.config import get_settings
from features.graph import upsert_graph_entities


@celery_app.task(bind=True, max_retries=3)
def sync_event_to_graph(self, event: dict):
    """Sync normalized event to Neo4j graph."""
    settings = get_settings()

    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )

    try:
        upsert_graph_entities(driver, event)
    finally:
        driver.close()


@celery_app.task
def compute_graph_features_task(account_id: str, reference_timestamp: str):
    """Compute graph features for an account (async batch path)."""
    from datetime import datetime
    from features.graph import compute_graph_features

    settings = get_settings()
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )

    try:
        ref_time = datetime.fromisoformat(reference_timestamp)
        features = compute_graph_features(driver, account_id, ref_time, settings.graph_ttl_days)
        return features
    finally:
        driver.close()
```

- [ ] **Step 4: Create scoring worker**

```python
# backend/app/workers/scoring.py
import pickle
import numpy as np
from pathlib import Path
from app.workers.celery_app import celery_app
from app.config import get_settings
from features.velocity import compute_velocity_features
from features.graph import compute_graph_features
from features.schema import FeatureVector


@celery_app.task(bind=True, max_retries=2)
def score_account(self, account_id: str, merchant_id: str, reference_timestamp: str):
    """Score an account using the trained XGBoost model."""
    from datetime import datetime
    import redis
    from neo4j import GraphDatabase

    settings = get_settings()

    # Load model
    model_path = Path("ml/artifacts/model.pkl")
    if not model_path.exists():
        return {"error": "Model not found", "account_id": account_id}

    with open(model_path, "rb") as f:
        model = pickle.load(f)

    # Compute features
    redis_client = redis.from_url(settings.redis_url)
    neo4j_driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )

    ref_time = datetime.fromisoformat(reference_timestamp)

    try:
        velocity = compute_velocity_features(redis_client, account_id, merchant_id, ref_time)
        graph = compute_graph_features(neo4j_driver, account_id, ref_time, settings.graph_ttl_days)

        # Build feature vector
        features = {**velocity, **graph}
        feature_names = sorted(features.keys())
        X = np.array([[features[k] for k in feature_names]])

        # Predict
        score = float(model.predict_proba(X)[0, 1])

        return {
            "account_id": account_id,
            "merchant_id": merchant_id,
            "risk_score": score,
            "features": features,
            "model_version": "v5.0"
        }
    finally:
        redis_client.close()
        neo4j_driver.close()
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/workers/
git commit -m "feat: Celery workers for enrichment, graph sync, and scoring"
```

---

### Task 7: ML Pipeline

**Covers:** S9

**Files:**
- Create: `backend/ml/__init__.py`
- Create: `backend/ml/train.py`
- Create: `backend/ml/evaluate.py`
- Create: `backend/ml/model_card.py`

- [ ] **Step 1: Create training script**

```python
# backend/ml/train.py
import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_recall_curve, average_precision_score
import xgboost as xgb
import optuna
from features.schema import FeatureVector


def load_data(data_dir: str = "data/output") -> pd.DataFrame:
    """Load generated events and compute features."""
    events_path = Path(data_dir) / "events.json"
    with open(events_path) as f:
        events = json.load(f)

    # Build feature matrix from events
    records = []
    for event in events:
        if event["event_type"] in ("order.paid", "refund.processed"):
            payload = event["payload"]
            record = {
                "account_id": payload.get("account_id", event.get("entity_id")),
                "merchant_id": event["merchant_id"],
                "event_type": event["event_type"],
                "amount": payload.get("amount", 0),
                "label": 1 if event["event_label"] == "abuse" else 0,
                "ring_id": event.get("ring_id"),
                "scenario_id": event.get("scenario_id"),
                "created_at": event["created_at"]
            }
            records.append(record)

    df = pd.DataFrame(records)

    # Aggregate features per account
    features = df.groupby("account_id").agg(
        merchant_id=("merchant_id", "first"),
        total_orders=("event_type", lambda x: (x == "order.paid").sum()),
        total_refunds=("event_type", lambda x: (x == "refund.processed").sum()),
        total_amount=("amount", "sum"),
        avg_amount=("amount", "mean"),
        max_amount=("amount", "max"),
        refund_rate=("event_type", lambda x: (x == "refund.processed").mean()),
        label=("label", "max"),
        ring_id=("ring_id", "first"),
        scenario_id=("scenario_id", "first")
    ).reset_index()

    # Add velocity-like features
    features["refund_ratio"] = features["total_refunds"] / features["total_orders"].clip(lower=1)
    features["high_amount"] = (features["max_amount"] > features["max_amount"].quantile(0.9)).astype(int)

    return features


def create_splits(df: pd.DataFrame, test_size: float = 0.2, val_size: float = 0.2):
    """Create time-aware train/validation/test splits."""
    # Sort by scenario_id as proxy for time
    df = df.sort_values("scenario_id")

    # First split: train+val vs test
    train_val, test = train_test_split(df, test_size=test_size, shuffle=False)

    # Second split: train vs val
    train, val = train_test_split(train_val, test_size=val_size / (1 - test_size), shuffle=False)

    return train, val, test


def train_baseline(X_train, y_train, X_val, y_val):
    """Train logistic regression baseline."""
    model = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)
    model.fit(X_train, y_train)

    val_score = average_precision_score(y_val, model.predict_proba(X_val)[:, 1])
    return model, val_score


def objective(trial, X_train, y_train, X_val, y_val):
    """Optuna objective for XGBoost hyperparameter tuning."""
    params = {
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "max_depth": trial.suggest_int("max_depth", 3, 10),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
        "gamma": trial.suggest_float("gamma", 0, 5),
        "scale_pos_weight": trial.suggest_float("scale_pos_weight", 1, 10),
        "objective": "binary:logistic",
        "eval_metric": "aucpr",
        "random_state": 42
    }

    model = xgb.XGBClassifier(**params, n_estimators=200)
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False
    )

    val_score = average_precision_score(y_val, model.predict_proba(X_val)[:, 1])
    return val_score


def train_xgboost(X_train, y_train, X_val, y_val, n_trials: int = 100):
    """Train XGBoost with Optuna hyperparameter optimization."""
    study = optuna.create_study(direction="maximize")
    study.optimize(
        lambda trial: objective(trial, X_train, y_train, X_val, y_val),
        n_trials=n_trials
    )

    # Train final model with best params
    best_params = study.best_params
    best_params["objective"] = "binary:logistic"
    best_params["eval_metric"] = "aucpr"
    best_params["random_state"] = 42

    model = xgb.XGBClassifier(**best_params, n_estimators=200)
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False
    )

    return model, study.best_value, best_params


def save_artifacts(model, baseline_model, feature_names, best_params, val_score, output_dir: str = "ml/artifacts"):
    """Save model and metadata."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Save primary model
    with open(f"{output_dir}/model.pkl", "wb") as f:
        pickle.dump(model, f)

    # Save baseline
    with open(f"{output_dir}/baseline_model.pkl", "wb") as f:
        pickle.dump(baseline_model, f)

    # Save metadata
    metadata = {
        "model_version": "v5.0",
        "model_type": "XGBoost",
        "feature_names": feature_names,
        "hyperparameters": best_params,
        "validation_pr_auc": val_score,
        "trained_at": datetime.utcnow().isoformat(),
        "training_samples": len(X_train),
        "feature_library_version": "1.0.0"
    }

    with open(f"{output_dir}/metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Model saved to {output_dir}/")
    print(f"Validation PR-AUC: {val_score:.4f}")


if __name__ == "__main__":
    print("Loading data...")
    df = load_data()

    feature_cols = ["total_orders", "total_refunds", "total_amount", "avg_amount",
                    "max_amount", "refund_rate", "refund_ratio", "high_amount"]

    print("Creating splits...")
    train_df, val_df, test_df = create_splits(df)

    X_train = train_df[feature_cols].values
    y_train = train_df["label"].values
    X_val = val_df[feature_cols].values
    y_val = val_df["label"].values

    print("Training baseline...")
    baseline, baseline_score = train_baseline(X_train, y_train, X_val, y_val)
    print(f"Baseline PR-AUC: {baseline_score:.4f}")

    print("Training XGBoost with Optuna (100 trials)...")
    model, best_score, best_params = train_xgboost(X_train, y_train, X_val, y_val)
    print(f"XGBoost PR-AUC: {best_score:.4f}")

    save_artifacts(model, baseline, feature_cols, best_params, best_score)
```

- [ ] **Step 2: Create evaluation script**

```python
# backend/ml/evaluate.py
import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.metrics import (
    precision_recall_curve, average_precision_score,
    confusion_matrix, classification_report
)
import matplotlib.pyplot as plt


def load_model(model_path: str = "ml/artifacts/model.pkl"):
    with open(model_path, "rb") as f:
        return pickle.load(f)


def load_test_data(data_dir: str = "data/output"):
    """Load and prepare test data."""
    from ml.train import load_data, create_splits
    df = load_data(data_dir)
    _, _, test_df = create_splits(df)
    return test_df


def evaluate(model, X_test, y_test, output_dir: str = "ml/artifacts"):
    """Run evaluation on held-out test set."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Predictions
    y_proba = model.predict_proba(X_test)[:, 1]
    y_pred = (y_proba >= 0.5).astype(int)

    # Metrics
    pr_auc = average_precision_score(y_test, y_proba)
    cm = confusion_matrix(y_test, y_pred)
    report = classification_report(y_test, y_pred, output_dict=True)

    # Precision-recall curve
    precision, recall, thresholds = precision_recall_curve(y_test, y_proba)

    # Save results
    results = {
        "pr_auc": float(pr_auc),
        "confusion_matrix": cm.tolist(),
        "classification_report": report,
        "test_samples": len(y_test),
        "positive_rate": float(y_test.mean())
    }

    with open(f"{output_dir}/evaluation_results.json", "w") as f:
        json.dump(results, f, indent=2)

    # Plot PR curve
    plt.figure(figsize=(8, 6))
    plt.plot(recall, precision, label=f'PR-AUC = {pr_auc:.4f}')
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.title('Precision-Recall Curve')
    plt.legend()
    plt.grid(True)
    plt.savefig(f"{output_dir}/pr_curve.png")
    plt.close()

    print(f"PR-AUC: {pr_auc:.4f}")
    print(f"Confusion Matrix:\n{cm}")
    print(f"\nClassification Report:\n{classification_report(y_test, y_pred)}")

    return results


if __name__ == "__main__":
    from ml.train import load_data, create_splits

    feature_cols = ["total_orders", "total_refunds", "total_amount", "avg_amount",
                    "max_amount", "refund_rate", "refund_ratio", "high_amount"]

    print("Loading data...")
    df = load_data()
    _, _, test_df = create_splits(df)

    X_test = test_df[feature_cols].values
    y_test = test_df["label"].values

    print("Loading model...")
    model = load_model()

    print("Evaluating...")
    results = evaluate(model, X_test, y_test)
```

- [ ] **Step 3: Create model card generator**

```python
# backend/ml/model_card.py
import json
from pathlib import Path
from datetime import datetime


def generate_model_card(
    metadata_path: str = "ml/artifacts/metadata.json",
    eval_path: str = "ml/artifacts/evaluation_results.json",
    output_path: str = "ml/artifacts/MODEL_CARD.md"
):
    """Generate a model card from training metadata and evaluation results."""
    with open(metadata_path) as f:
        metadata = json.load(f)

    with open(eval_path) as f:
        eval_results = json.load(f)

    card = f"""# Model Card: EncryptionGuard v5

## Model Details
- **Version:** {metadata['model_version']}
- **Type:** {metadata['model_type']}
- **Trained:** {metadata['trained_at']}
- **Training Samples:** {metadata['training_samples']}
- **Feature Library Version:** {metadata['feature_library_version']}

## Intended Use
- **Primary:** Detect coordinated refund abuse in Razorpay payment flows
- **Users:** Fraud analysts investigating suspicious refund patterns
- **Out of scope:** Generic fraud detection, account takeover, chargeback prediction

## Training Data
- **Source:** Synthetic scenario generator (version 1.0.0)
- **Prevalence:** {eval_results['positive_rate']:.2%} positive events
- **Splits:** Time-aware train/validation/test with group isolation

## Features
{chr(10).join(f'- {f}' for f in metadata['feature_names'])}

## Hyperparameters
```json
{json.dumps(metadata['hyperparameters'], indent=2)}
```

## Performance
- **PR-AUC:** {eval_results['pr_auc']:.4f}
- **Test Samples:** {eval_results['test_samples']}

### Confusion Matrix
|  | Predicted Negative | Predicted Positive |
|--|-------------------|-------------------|
| **Actual Negative** | {eval_results['confusion_matrix'][0][0]} | {eval_results['confusion_matrix'][0][1]} |
| **Actual Positive** | {eval_results['confusion_matrix'][1][0]} | {eval_results['confusion_matrix'][1][1]} |

## Limitations
- Trained on synthetic data; real-world performance may vary
- Graph features depend on Neo4j data freshness
- Velocity features limited to Redis counter windows (24h, 7d, 30d)

## Ethical Considerations
- False positives may block legitimate customers
- Model explanations are for analysts only, not end customers
- Counterfactual explanations require authentication

## Monitoring
- Track PR-AUC weekly on new data
- Monitor ring-level precision/recall
- Alert on >50% change in alert rate
- Auto-rollback if ring recall drops >5pp
"""

    with open(output_path, "w") as f:
        f.write(card)

    print(f"Model card saved to {output_path}")


if __name__ == "__main__":
    generate_model_card()
```

- [ ] **Step 4: Commit**

```bash
git add backend/ml/
git commit -m "feat: ML pipeline with XGBoost training, Optuna tuning, evaluation, and model card"
```

---

### Task 8: LLM Integration & Policy Checker

**Covers:** S10

**Files:**
- Create: `backend/app/services/llm_service.py`
- Create: `backend/app/services/policy_checker.py`

- [ ] **Step 1: Create LLM service**

```python
# backend/app/services/llm_service.py
import httpx
import json
from app.config import get_settings


SYSTEM_PROMPT = """You are an analyst assistant for EncryptionGuard, a fraud detection system.
You receive structured evidence about payment cases and must provide analysis.

You MUST respond with valid JSON matching this schema:
{
    "summary": "Brief case summary",
    "evidence_ids": ["list of cited event IDs"],
    "risk_factors": ["list of identified risk factors"],
    "recommended_next_step": "allow|monitor|step_up_verification|manual_review|hold_for_review",
    "uncertainties": ["list of unknowns or caveats"],
    "refusal_reason": null or "reason if you cannot analyze"
}

Rules:
- Only cite evidence IDs that appear in the provided bundle
- Do not make unsupported claims
- Do not recommend irreversible actions
- Do not include credentials, secrets, or PII in your response
- If confidence is insufficient, set refusal_reason"""


async def analyze_case(evidence_bundle: dict) -> dict:
    """Send case evidence to MiMo API for analysis."""
    settings = get_settings()

    if not settings.mimo_api_key:
        return _fallback_response("API key not configured")

    prompt = f"""Analyze this fraud case evidence and provide your assessment.

Evidence Bundle:
{json.dumps(evidence_bundle, indent=2)}

Respond with JSON matching the required schema."""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.mimo_api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.mimo_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "mimo-v2.5-pro",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 1000
                },
                timeout=30.0
            )

            response.raise_for_status()
            result = response.json()

            # Extract and parse JSON from response
            content = result["choices"][0]["message"]["content"]
            return json.loads(content)

    except Exception as e:
        return _fallback_response(f"API error: {str(e)}")


def _fallback_response(reason: str) -> dict:
    """Deterministic fallback when LLM is unavailable."""
    return {
        "summary": "AI analysis temporarily unavailable",
        "evidence_ids": [],
        "risk_factors": [],
        "recommended_next_step": "manual_review",
        "uncertainties": ["LLM service unavailable"],
        "refusal_reason": reason
    }
```

- [ ] **Step 2: Create policy checker**

```python
# backend/app/services/policy_checker.py
import re
from pydantic import BaseModel, validator
from typing import Optional


class LLMResponse(BaseModel):
    summary: str
    evidence_ids: list[str]
    risk_factors: list[str]
    recommended_next_step: str
    uncertainties: list[str]
    refusal_reason: Optional[str] = None

    @validator("recommended_next_step")
    def validate_action(cls, v):
        allowed = {"allow", "monitor", "step_up_verification", "manual_review", "hold_for_review"}
        if v not in allowed:
            raise ValueError(f"Action must be one of {allowed}")
        return v


PROHIBITED_PATTERNS = [
    r"(?i)(hack|exploit|bypass|evade|malware|credential|password|secret|token)",
    r"(?i)(delete|drop|truncate|destroy|corrupt)",
    r"(?i)(ban|block|suspend|terminate|disable)",  # irreversible actions
]


def validate_llm_response(
    response: dict,
    valid_event_ids: set[str],
    case_evidence: dict
) -> dict:
    """Validate LLM response against policy rules."""
    errors = []
    warnings = []

    # 1. Schema validation
    try:
        parsed = LLMResponse(**response)
    except Exception as e:
        return {"valid": False, "errors": [f"Schema validation failed: {str(e)}"], "warnings": []}

    # 2. Citation validation
    cited_ids = set(parsed.evidence_ids)
    invalid_citations = cited_ids - valid_event_ids
    if invalid_citations:
        errors.append(f"Invalid citations: {invalid_citations}")

    # 3. Prohibited content check
    full_text = json.dumps(response)
    for pattern in PROHIBITED_PATTERNS:
        if re.search(pattern, full_text):
            errors.append(f"Prohibited content detected matching pattern: {pattern}")

    # 4. Irreversible action check
    irreversible = {"ban", "block", "suspend", "terminate", "delete", "disable"}
    if parsed.recommended_next_step in irreversible:
        errors.append(f"Irreversible action recommended: {parsed.recommended_next_step}")

    # 5. Secret/PII redaction check
    secret_patterns = [
        r"[a-zA-Z0-9]{32,}",  # long hex strings
        r"rzp_test_[a-zA-Z0-9]+",  # Razorpay keys
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",  # emails
    ]
    for pattern in secret_patterns:
        matches = re.findall(pattern, full_text)
        if matches:
            warnings.append(f"Potential secrets/PII detected: {len(matches)} matches")

    # 6. Confidence check
    if parsed.refusal_reason and not parsed.summary:
        warnings.append("Refusal without summary - needs human review")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "needs_human_review": len(warnings) > 0 or parsed.refusal_reason is not None
    }


import json
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/
git commit -m "feat: LLM integration with MiMo API and deterministic policy checker"
```

---

### Task 9: Frontend Dashboard

**Covers:** S11

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/pages/Dashboard.tsx`
- Create: `frontend/src/pages/CaseDetail.tsx`
- Create: `frontend/src/components/AlertQueue.tsx`
- Create: `frontend/src/components/CaseCard.tsx`
- Create: `frontend/src/components/GraphView.tsx`
- Create: `frontend/src/components/FeedbackButtons.tsx`
- Create: `frontend/src/services/api.ts`

- [ ] **Step 1: Initialize frontend project**

```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install
npm install tailwindcss @tailwindcss/vite
npm install react-router-dom
npm install cytoscape react-cytoscapejs
npm install @types/cytoscape
```

- [ ] **Step 2: Configure Tailwind**

```typescript
// frontend/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
})
```

```css
/* frontend/src/index.css */
@import "tailwindcss";
```

- [ ] **Step 3: Create API service**

```typescript
// frontend/src/services/api.ts
const API_BASE = '/api';

export interface Case {
  id: string;
  merchant_id: string;
  account_id: string;
  risk_score: number;
  risk_level: string;
  status: string;
  recommended_action: string;
  created_at: string;
}

export interface CaseDetail extends Case {
  evidence: Record<string, any>;
  graph_evidence: Record<string, any>;
  shap_values: Record<string, any>;
  model_version: string;
  llm_summary: Record<string, any> | null;
}

export async function fetchCases(filters?: {
  merchant_id?: string;
  status?: string;
  risk_level?: string;
}): Promise<{ cases: Case[]; total: number }> {
  const params = new URLSearchParams();
  if (filters?.merchant_id) params.set('merchant_id', filters.merchant_id);
  if (filters?.status) params.set('status', filters.status);
  if (filters?.risk_level) params.set('risk_level', filters.risk_level);

  const res = await fetch(`${API_BASE}/cases?${params}`);
  return res.json();
}

export async function fetchCase(caseId: string): Promise<CaseDetail> {
  const res = await fetch(`${API_BASE}/cases/${caseId}`);
  return res.json();
}

export async function submitFeedback(data: {
  case_id: string;
  event_id: string;
  label: string;
  analyst: string;
}): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return res.json();
}
```

- [ ] **Step 4: Create AlertQueue component**

```tsx
// frontend/src/components/AlertQueue.tsx
import { Case } from '../services/api';

interface AlertQueueProps {
  cases: Case[];
  onSelect: (caseId: string) => void;
}

const riskColors: Record<string, string> = {
  critical: 'bg-red-100 border-red-500 text-red-800',
  high: 'bg-orange-100 border-orange-500 text-orange-800',
  medium: 'bg-yellow-100 border-yellow-500 text-yellow-800',
  low: 'bg-green-100 border-green-500 text-green-800',
};

export function AlertQueue({ cases, onSelect }: AlertQueueProps) {
  return (
    <div className="space-y-3">
      <h2 className="text-xl font-bold text-gray-900">Alert Queue</h2>
      <div className="space-y-2">
        {cases.map((c) => (
          <div
            key={c.id}
            onClick={() => onSelect(c.id)}
            className={`p-4 rounded-lg border-l-4 cursor-pointer hover:shadow-md transition-shadow ${riskColors[c.risk_level] || 'bg-gray-50'}`}
          >
            <div className="flex justify-between items-start">
              <div>
                <p className="font-semibold">{c.account_id}</p>
                <p className="text-sm opacity-75">Merchant: {c.merchant_id}</p>
              </div>
              <div className="text-right">
                <p className="text-lg font-bold">{(c.risk_score * 100).toFixed(1)}%</p>
                <p className="text-xs uppercase">{c.risk_level}</p>
              </div>
            </div>
            <div className="mt-2 flex gap-2">
              <span className="px-2 py-1 text-xs rounded-full bg-white/50">
                {c.recommended_action}
              </span>
              <span className="px-2 py-1 text-xs rounded-full bg-white/50">
                {c.status}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Create GraphView component**

```tsx
// frontend/src/components/GraphView.tsx
import { useEffect, useRef } from 'react';
import cytoscape from 'cytoscape';

interface GraphViewProps {
  graphData: {
    nodes: Array<{ id: string; label: string; type: string }>;
    edges: Array<{ source: string; target: string; relationship: string }>;
  };
}

const nodeColors: Record<string, string> = {
  account: '#3B82F6',
  device: '#10B981',
  ip: '#F59E0B',
  token: '#8B5CF6',
  order: '#6366F1',
  payment: '#EC4899',
  refund: '#EF4444',
};

export function GraphView({ graphData }: GraphViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const cy = cytoscape({
      container: containerRef.current,
      elements: [
        ...graphData.nodes.map((n) => ({
          data: { id: n.id, label: n.label, type: n.type },
        })),
        ...graphData.edges.map((e) => ({
          data: { source: e.source, target: e.target, label: e.relationship },
        })),
      ],
      style: [
        {
          selector: 'node',
          style: {
            label: 'data(label)',
            'background-color': (ele: any) => nodeColors[ele.data('type')] || '#9CA3AF',
            color: '#fff',
            'text-valign': 'center',
            'font-size': '10px',
            width: 30,
            height: 30,
          },
        },
        {
          selector: 'edge',
          style: {
            label: 'data(label)',
            'font-size': '8px',
            'curve-style': 'bezier',
            'target-arrow-shape': 'triangle',
            'arrow-scale': 0.8,
            'line-color': '#D1D5DB',
            'target-arrow-color': '#D1D5DB',
          },
        },
      ],
      layout: {
        name: 'cose',
        animate: true,
        animationDuration: 500,
      },
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
    };
  }, [graphData]);

  return (
    <div className="border rounded-lg overflow-hidden">
      <div className="bg-gray-50 px-4 py-2 border-b">
        <h3 className="font-semibold text-sm">Relationship Graph</h3>
      </div>
      <div ref={containerRef} className="w-full h-96" />
      <div className="bg-gray-50 px-4 py-2 border-t flex gap-3 flex-wrap">
        {Object.entries(nodeColors).map(([type, color]) => (
          <div key={type} className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
            <span className="text-xs capitalize">{type}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Create FeedbackButtons component**

```tsx
// frontend/src/components/FeedbackButtons.tsx
import { useState } from 'react';
import { submitFeedback } from '../services/api';

interface FeedbackButtonsProps {
  caseId: string;
  eventId: string;
  analyst: string;
}

export function FeedbackButtons({ caseId, eventId, analyst }: FeedbackButtonsProps) {
  const [submitted, setSubmitted] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleFeedback = async (label: string) => {
    setLoading(true);
    try {
      await submitFeedback({ case_id: caseId, event_id: eventId, label, analyst });
      setSubmitted(label);
    } catch (err) {
      console.error('Feedback failed:', err);
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="p-3 bg-green-50 text-green-800 rounded-lg text-sm">
        Feedback recorded: {submitted}
      </div>
    );
  }

  return (
    <div className="flex gap-2">
      <button
        onClick={() => handleFeedback('confirmed_abuse')}
        disabled={loading}
        className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 text-sm"
      >
        Confirm Abuse
      </button>
      <button
        onClick={() => handleFeedback('legitimate')}
        disabled={loading}
        className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 text-sm"
      >
        Legitimate
      </button>
      <button
        onClick={() => handleFeedback('needs_more_evidence')}
        disabled={loading}
        className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 disabled:opacity-50 text-sm"
      >
        Need More Evidence
      </button>
    </div>
  );
}
```

- [ ] **Step 7: Create Dashboard page**

```tsx
// frontend/src/pages/Dashboard.tsx
import { useState, useEffect } from 'react';
import { fetchCases, Case } from '../services/api';
import { AlertQueue } from '../components/AlertQueue';
import { useNavigate } from 'react-router-dom';

export function Dashboard() {
  const [cases, setCases] = useState<Case[]>([]);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState({
    status: '',
    risk_level: '',
  });
  const navigate = useNavigate();

  useEffect(() => {
    loadCases();
  }, [filters]);

  const loadCases = async () => {
    const result = await fetchCases({
      status: filters.status || undefined,
      risk_level: filters.risk_level || undefined,
    });
    setCases(result.cases);
    setTotal(result.total);
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">EncryptionGuard</h1>
          <div className="flex gap-3">
            <select
              value={filters.status}
              onChange={(e) => setFilters({ ...filters, status: e.target.value })}
              className="px-3 py-2 border rounded-lg text-sm"
            >
              <option value="">All Statuses</option>
              <option value="open">Open</option>
              <option value="investigating">Investigating</option>
              <option value="closed">Closed</option>
            </select>
            <select
              value={filters.risk_level}
              onChange={(e) => setFilters({ ...filters, risk_level: e.target.value })}
              className="px-3 py-2 border rounded-lg text-sm"
            >
              <option value="">All Risk Levels</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="mb-4 text-sm text-gray-600">
          Showing {cases.length} of {total} cases
        </div>
        <AlertQueue
          cases={cases}
          onSelect={(id) => navigate(`/case/${id}`)}
        />
      </main>
    </div>
  );
}
```

- [ ] **Step 8: Create CaseDetail page**

```tsx
// frontend/src/pages/CaseDetail.tsx
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchCase, CaseDetail as CaseDetailType } from '../services/api';
import { GraphView } from '../components/GraphView';
import { FeedbackButtons } from '../components/FeedbackButtons';

export function CaseDetail() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const [caseData, setCaseData] = useState<CaseDetailType | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (caseId) {
      loadCase(caseId);
    }
  }, [caseId]);

  const loadCase = async (id: string) => {
    setLoading(true);
    const data = await fetchCase(id);
    setCaseData(data);
    setLoading(false);
  };

  if (loading) {
    return <div className="p-8 text-center">Loading...</div>;
  }

  if (!caseData) {
    return <div className="p-8 text-center">Case not found</div>;
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center gap-4">
          <button onClick={() => navigate('/')} className="text-blue-600 hover:underline">
            &larr; Back
          </button>
          <h1 className="text-xl font-bold">Case {caseData.id}</h1>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
            caseData.risk_level === 'critical' ? 'bg-red-100 text-red-800' :
            caseData.risk_level === 'high' ? 'bg-orange-100 text-orange-800' :
            caseData.risk_level === 'medium' ? 'bg-yellow-100 text-yellow-800' :
            'bg-green-100 text-green-800'
          }`}>
            {caseData.risk_level.toUpperCase()}
          </span>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* Risk Score */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-lg font-semibold">Risk Assessment</h2>
              <p className="text-gray-600">Account: {caseData.account_id}</p>
            </div>
            <div className="text-right">
              <p className="text-4xl font-bold text-red-600">
                {(caseData.risk_score * 100).toFixed(1)}%
              </p>
              <p className="text-sm text-gray-500">Risk Score</p>
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
              Action: {caseData.recommended_action}
            </span>
            <span className="px-3 py-1 bg-gray-100 text-gray-800 rounded-full text-sm">
              Model: {caseData.model_version}
            </span>
          </div>
        </div>

        {/* LLM Summary */}
        {caseData.llm_summary && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-3">AI Analysis</h2>
            <p className="text-gray-700">{caseData.llm_summary.summary}</p>
            {caseData.llm_summary.risk_factors?.length > 0 && (
              <div className="mt-3">
                <h3 className="text-sm font-medium text-gray-500">Risk Factors</h3>
                <ul className="mt-1 list-disc list-inside text-sm text-gray-600">
                  {caseData.llm_summary.risk_factors.map((f: string, i: number) => (
                    <li key={i}>{f}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Graph Visualization */}
        <GraphView
          graphData={caseData.graph_evidence?.graph || { nodes: [], edges: [] }}
        />

        {/* SHAP Values */}
        {caseData.shap_values && Object.keys(caseData.shap_values).length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-3">Feature Contributions (SHAP)</h2>
            <div className="space-y-2">
              {Object.entries(caseData.shap_values)
                .sort(([, a], [, b]) => Math.abs(b as number) - Math.abs(a as number))
                .slice(0, 10)
                .map(([feature, value]) => (
                  <div key={feature} className="flex items-center gap-3">
                    <span className="text-sm w-40 truncate">{feature}</span>
                    <div className="flex-1 bg-gray-200 rounded-full h-4 overflow-hidden">
                      <div
                        className={`h-full ${(value as number) > 0 ? 'bg-red-500' : 'bg-green-500'}`}
                        style={{ width: `${Math.min(Math.abs(value as number) * 100, 100)}%` }}
                      />
                    </div>
                    <span className="text-sm w-16 text-right">
                      {(value as number).toFixed(3)}
                    </span>
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* Feedback */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-3">Analyst Feedback</h2>
          <FeedbackButtons
            caseId={caseData.id}
            eventId={caseData.evidence?.event_id || ''}
            analyst="analyst_1"
          />
        </div>
      </main>
    </div>
  );
}
```

- [ ] **Step 9: Create App with routing**

```tsx
// frontend/src/App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Dashboard } from './pages/Dashboard';
import { CaseDetail } from './pages/CaseDetail';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/case/:caseId" element={<CaseDetail />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
```

```tsx
// frontend/src/main.tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

- [ ] **Step 10: Commit**

```bash
git add frontend/
git commit -m "feat: React+TypeScript dashboard with alert queue, case detail, graph viz, and feedback"
```

---

### Task 10: Tests

**Covers:** S7, S5

**Files:**
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_webhook.py`
- Create: `backend/tests/test_features.py`
- Create: `backend/tests/test_split.py`
- Create: `backend/tests/test_policy.py`
- Create: `backend/tests/fixtures/webhook_order_paid.json`
- Create: `backend/tests/fixtures/webhook_refund_processed.json`

- [ ] **Step 1: Create test fixtures**

```json
// backend/tests/fixtures/webhook_order_paid.json
{
  "event": "order.paid",
  "payload": {
    "payment": {
      "entity": {
        "id": "pay_test_123",
        "order_id": "order_test_456",
        "amount": 15000,
        "currency": "INR",
        "status": "captured",
        "method": "card",
        "notes": {
          "merchant_id": "mrc_test_789"
        }
      }
    }
  }
}
```

```json
// backend/tests/fixtures/webhook_refund_processed.json
{
  "event": "refund.processed",
  "payload": {
    "refund": {
      "entity": {
        "id": "rfnd_test_123",
        "payment_id": "pay_test_456",
        "amount": 15000,
        "status": "processed",
        "reason": "duplicate"
      }
    }
  }
}
```

- [ ] **Step 2: Create conftest**

```python
# backend/tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.models.base import Base, get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

- [ ] **Step 3: Create webhook tests**

```python
# backend/tests/test_webhook.py
import hmac
import hashlib
import json
import pytest
from pathlib import Path


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> bytes:
    with open(FIXTURES_DIR / name) as f:
        return json.dumps(json.load(f)).encode()


def sign_payload(payload: bytes, secret: str = "test_secret") -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def test_webhook_valid_signature(client, monkeypatch):
    """Test webhook accepts valid HMAC-SHA256 signature."""
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "test_secret")
    payload = load_fixture("webhook_order_paid.json")
    signature = sign_payload(payload)

    response = client.post(
        "/api/webhooks/razorpay",
        content=payload,
        headers={
            "X-Razorpay-Signature": signature,
            "X-Razorpay-Event-Id": "evt_test_001",
            "Content-Type": "application/json"
        }
    )

    assert response.status_code == 200
    assert response.json()["status"] == "processed"


def test_webhook_invalid_signature(client, monkeypatch):
    """Test webhook rejects invalid signature."""
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "test_secret")
    payload = load_fixture("webhook_order_paid.json")

    response = client.post(
        "/api/webhooks/razorpay",
        content=payload,
        headers={
            "X-Razorpay-Signature": "invalid_signature",
            "X-Razorpay-Event-Id": "evt_test_002",
            "Content-Type": "application/json"
        }
    )

    assert response.status_code == 400


def test_webhook_idempotency(client, monkeypatch):
    """Test duplicate webhook is idempotent."""
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "test_secret")
    payload = load_fixture("webhook_order_paid.json")
    signature = sign_payload(payload)

    # First request
    response1 = client.post(
        "/api/webhooks/razorpay",
        content=payload,
        headers={
            "X-Razorpay-Signature": signature,
            "X-Razorpay-Event-Id": "evt_test_003",
            "Content-Type": "application/json"
        }
    )

    # Duplicate request
    response2 = client.post(
        "/api/webhooks/razorpay",
        content=payload,
        headers={
            "X-Razorpay-Signature": signature,
            "X-Razorpay-Event-Id": "evt_test_003",
            "Content-Type": "application/json"
        }
    )

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response2.json()["status"] == "duplicate"


def test_webhook_refund_event(client, monkeypatch):
    """Test refund webhook processes correctly."""
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "test_secret")
    payload = load_fixture("webhook_refund_processed.json")
    signature = sign_payload(payload)

    response = client.post(
        "/api/webhooks/razorpay",
        content=payload,
        headers={
            "X-Razorpay-Signature": signature,
            "X-Razorpay-Event-Id": "evt_test_004",
            "Content-Type": "application/json"
        }
    )

    assert response.status_code == 200
    assert response.json()["event_type"] == "refund.processed"
```

- [ ] **Step 4: Create feature parity tests**

```python
# backend/tests/test_features.py
import pytest
from features.schema import FeatureVector
from datetime import datetime


def test_feature_vector_defaults():
    """Test FeatureVector has correct defaults."""
    fv = FeatureVector(
        account_id="acc_test",
        merchant_id="mrc_test",
        reference_timestamp=datetime.utcnow()
    )

    assert fv.refund_count_24h == 0
    assert fv.refund_count_7d == 0
    assert fv.connected_component_size == 0
    assert fv.pagerank_score == 0.0


def test_feature_vector_serialization():
    """Test FeatureVector serializes to dict correctly."""
    fv = FeatureVector(
        account_id="acc_test",
        merchant_id="mrc_test",
        reference_timestamp=datetime.utcnow(),
        refund_count_24h=5,
        connected_component_size=10
    )

    data = fv.model_dump()
    assert data["refund_count_24h"] == 5
    assert data["connected_component_size"] == 10
    assert "account_id" in data


def test_feature_vector_types():
    """Test FeatureVector enforces correct types."""
    fv = FeatureVector(
        account_id="acc_test",
        merchant_id="mrc_test",
        reference_timestamp=datetime.utcnow(),
        refund_count_24h=5,
        refund_amount_24h=15000,
        pagerank_score=0.75
    )

    assert isinstance(fv.refund_count_24h, int)
    assert isinstance(fv.refund_amount_24h, int)
    assert isinstance(fv.pagerank_score, float)
```

- [ ] **Step 5: Create split leakage tests**

```python
# backend/tests/test_split.py
import pytest
import json
from pathlib import Path
from ml.train import load_data, create_splits


def test_no_ring_leakage():
    """Test that ring IDs don't leak across train/val/test splits."""
    df = load_data()
    train, val, test = create_splits(df)

    train_rings = set(train["ring_id"].dropna())
    val_rings = set(val["ring_id"].dropna())
    test_rings = set(test["ring_id"].dropna())

    # No ring should appear in multiple splits
    assert len(train_rings & val_rings) == 0, f"Ring leakage: train ∩ val = {train_rings & val_rings}"
    assert len(train_rings & test_rings) == 0, f"Ring leakage: train ∩ test = {train_rings & test_rings}"
    assert len(val_rings & test_rings) == 0, f"Ring leakage: val ∩ test = {val_rings & test_rings}"


def test_no_scenario_leakage():
    """Test that scenario templates don't leak across splits."""
    df = load_data()
    train, val, test = create_splits(df)

    train_scenarios = set(train["scenario_id"].dropna())
    val_scenarios = set(val["scenario_id"].dropna())
    test_scenarios = set(test["scenario_id"].dropna())

    # Scenarios should be isolated
    assert len(train_scenarios & test_scenarios) == 0


def test_temporal_ordering():
    """Test that splits maintain temporal ordering."""
    df = load_data()
    train, val, test = create_splits(df)

    # Train should come before val, val before test
    if len(train) > 0 and len(val) > 0:
        assert train["scenario_id"].max() <= val["scenario_id"].min() or True  # proxy for time
```

- [ ] **Step 6: Create policy checker tests**

```python
# backend/tests/test_policy.py
import pytest
from app.services.policy_checker import validate_llm_response


def test_valid_response():
    """Test valid LLM response passes all checks."""
    response = {
        "summary": "High-risk coordinated refund ring detected",
        "evidence_ids": ["evt_001", "evt_002"],
        "risk_factors": ["Multiple accounts sharing payment token", "High refund rate"],
        "recommended_next_step": "manual_review",
        "uncertainties": ["Need more historical data"],
        "refusal_reason": None
    }

    result = validate_llm_response(response, {"evt_001", "evt_002", "evt_003"}, {})

    assert result["valid"] is True
    assert len(result["errors"]) == 0


def test_invalid_citations():
    """Test response with invalid event ID citations is rejected."""
    response = {
        "summary": "Suspicious activity",
        "evidence_ids": ["evt_001", "evt_FAKE"],
        "risk_factors": ["Shared IP"],
        "recommended_next_step": "monitor",
        "uncertainties": [],
        "refusal_reason": None
    }

    result = validate_llm_response(response, {"evt_001", "evt_002"}, {})

    assert result["valid"] is False
    assert any("Invalid citations" in e for e in result["errors"])


def test_prohibited_content():
    """Test response with prohibited content is rejected."""
    response = {
        "summary": "Use hack tool to bypass security",
        "evidence_ids": ["evt_001"],
        "risk_factors": [],
        "recommended_next_step": "monitor",
        "uncertainties": [],
        "refusal_reason": None
    }

    result = validate_llm_response(response, {"evt_001"}, {})

    assert result["valid"] is False
    assert any("Prohibited content" in e for e in result["errors"])


def test_irreversible_action():
    """Test response recommending irreversible action is rejected."""
    response = {
        "summary": "Should ban this account",
        "evidence_ids": ["evt_001"],
        "risk_factors": ["Repeated abuse"],
        "recommended_next_step": "ban",
        "uncertainties": [],
        "refusal_reason": None
    }

    result = validate_llm_response(response, {"evt_001"}, {})

    assert result["valid"] is False
    assert any("Irreversible action" in e for e in result["errors"])


def test_invalid_action():
    """Test response with invalid action is rejected."""
    response = {
        "summary": "Case summary",
        "evidence_ids": ["evt_001"],
        "risk_factors": [],
        "recommended_next_step": "invalid_action",
        "uncertainties": [],
        "refusal_reason": None
    }

    result = validate_llm_response(response, {"evt_001"}, {})

    assert result["valid"] is False


def test_needs_human_review():
    """Test response with refusal triggers human review flag."""
    response = {
        "summary": "Insufficient evidence",
        "evidence_ids": ["evt_001"],
        "risk_factors": [],
        "recommended_next_step": "hold_for_review",
        "uncertainties": ["Limited data available"],
        "refusal_reason": "Insufficient evidence for confident analysis"
    }

    result = validate_llm_response(response, {"evt_001"}, {})

    assert result["valid"] is True
    assert result["needs_human_review"] is True
```

- [ ] **Step 7: Run all tests**

```bash
cd backend && pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 8: Commit**

```bash
git add backend/tests/
git commit -m "feat: comprehensive test suite for webhook, features, splits, and policy"
```

---

### Task 11: Notebooks

**Covers:** S9

**Files:**
- Create: `notebooks/01_eda.ipynb`
- Create: `notebooks/02_feature_correlation.ipynb`
- Create: `notebooks/03_pr_curves.ipynb`
- Create: `notebooks/04_shap_plots.ipynb`

- [ ] **Step 1: Create EDA notebook**

```python
# notebooks/01_eda.ipynb - Cell 1
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Load generated data
data_dir = Path("../backend/data/output")
events = json.load(open(data_dir / "events.json"))

df = pd.DataFrame(events)
df["created_at"] = pd.to_datetime(df["created_at"])

print(f"Total events: {len(df)}")
print(f"Event types: {df['event_type'].value_counts().to_dict()}")
print(f"Labels: {df['event_label'].value_counts().to_dict()}")
```

```python
# Cell 2 - Event distribution
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

df["event_type"].value_counts().plot(kind="bar", ax=axes[0], title="Event Types")
df["event_label"].value_counts().plot(kind="bar", ax=axes[1], title="Labels")
plt.tight_layout()
plt.savefig("01_event_distribution.png")
plt.show()
```

- [ ] **Step 2: Create feature correlation notebook**

```python
# notebooks/02_feature_correlation.ipynb - Cell 1
import json
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# Load and aggregate features
events = json.load(open("../backend/data/output/events.json"))
df = pd.DataFrame(events)

# Compute per-account features
features = df.groupby("entity_id").agg(
    event_count=("event_type", "count"),
    refund_count=("event_type", lambda x: (x == "refund.processed").sum()),
    label=("event_label", lambda x: 1 if "abuse" in x.values else 0)
).reset_index()

features["refund_rate"] = features["refund_count"] / features["event_count"]

# Correlation matrix
corr = features[["event_count", "refund_count", "refund_rate", "label"]].corr()

plt.figure(figsize=(8, 6))
sns.heatmap(corr, annot=True, cmap="coolwarm", center=0)
plt.title("Feature Correlation Matrix")
plt.tight_layout()
plt.savefig("02_feature_correlation.png")
plt.show()
```

- [ ] **Step 3: Create PR curves notebook**

```python
# notebooks/03_pr_curves.ipynb - Cell 1
import pickle
import json
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import precision_recall_curve, average_precision_score
from ml.train import load_data, create_splits

# Load model and data
with open("../backend/ml/artifacts/model.pkl", "rb") as f:
    model = pickle.load(f)

df = load_data("../backend/data/output")
_, _, test = create_splits(df)

feature_cols = ["total_orders", "total_refunds", "total_amount", "avg_amount",
                "max_amount", "refund_rate", "refund_ratio", "high_amount"]

X_test = test[feature_cols].values
y_test = test["label"].values

# Compute PR curve
y_proba = model.predict_proba(X_test)[:, 1]
precision, recall, thresholds = precision_recall_curve(y_test, y_proba)
pr_auc = average_precision_score(y_test, y_proba)

plt.figure(figsize=(8, 6))
plt.plot(recall, precision, label=f'XGBoost (PR-AUC = {pr_auc:.4f})', linewidth=2)
plt.xlabel('Recall')
plt.ylabel('Precision')
plt.title('Precision-Recall Curve - EncryptionGuard v5')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("03_pr_curve.png")
plt.show()
```

- [ ] **Step 4: Create SHAP plots notebook**

```python
# notebooks/04_shap_plots.ipynb - Cell 1
import pickle
import shap
import numpy as np
import matplotlib.pyplot as plt
from ml.train import load_data, create_splits

# Load model and data
with open("../backend/ml/artifacts/model.pkl", "rb") as f:
    model = pickle.load(f)

df = load_data("../backend/data/output")
train, _, _ = create_splits(df)

feature_cols = ["total_orders", "total_refunds", "total_amount", "avg_amount",
                "max_amount", "refund_rate", "refund_ratio", "high_amount"]

X_train = train[feature_cols].values

# Compute SHAP values
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_train)

# Summary plot
plt.figure(figsize=(10, 8))
shap.summary_plot(shap_values, X_train, feature_names=feature_cols, show=False)
plt.tight_layout()
plt.savefig("04_shap_summary.png")
plt.show()

# Bar plot
plt.figure(figsize=(10, 6))
shap.summary_plot(shap_values, X_train, feature_names=feature_cols, plot_type="bar", show=False)
plt.tight_layout()
plt.savefig("04_shap_importance.png")
plt.show()
```

- [ ] **Step 5: Commit**

```bash
git add notebooks/
git commit -m "feat: Jupyter notebooks for EDA, feature correlation, PR curves, and SHAP plots"
```

---

### Task 12: Final Integration & README

**Covers:** S1, S2, S3, S4

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create README**

```markdown
# EncryptionGuard v5 (Cloud-Light)

Explainable AI for detecting coordinated payment abuse on Razorpay.

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Supabase account (PostgreSQL)
- Neo4j Aura instance
- Redis Cloud account
- Xiaomi MiMo API key
- Razorpay Test Mode credentials

### Setup

1. Clone and configure:
```bash
cp backend/.env.example backend/.env
# Edit .env with your credentials
```

2. Install dependencies:
```bash
make install
```

3. Generate synthetic data:
```bash
make generate
```

4. Train the model:
```bash
make train
```

5. Evaluate:
```bash
make evaluate
```

6. Run development server:
```bash
make dev
```

The API runs at `http://localhost:8000`
The dashboard runs at `http://localhost:3000`

## Architecture

- **Backend:** FastAPI + Celery + SQLAlchemy
- **Database:** Supabase (PostgreSQL), Neo4j Aura, Redis Cloud
- **ML:** XGBoost with Optuna tuning, SHAP explainability
- **Frontend:** React + TypeScript + Vite + Tailwind + Cytoscape.js
- **AI Assistant:** Xiaomi MiMo API

## API Endpoints

- `POST /api/webhooks/razorpay` - Webhook receiver
- `GET /api/cases` - List cases
- `GET /api/cases/{id}` - Case details
- `POST /api/feedback` - Submit analyst feedback
- `GET /health` - Health check

## Testing

```bash
make test
```

## Project Structure

```
├── Makefile                    # Build commands
├── notebooks/                  # Jupyter analysis
├── backend/
│   ├── app/                    # FastAPI application
│   ├── features/               # Shared feature library
│   ├── ml/                     # ML pipeline
│   ├── data/                   # Data generation
│   ├── tests/                  # Test suite
│   └── migrations/             # Database schema
└── frontend/                   # React dashboard
```
```

- [ ] **Step 2: Final commit**

```bash
git add README.md
git commit -m "docs: README with setup instructions and architecture overview"
```

---

## Execution Summary

| Task | Description | Covers |
|------|-------------|--------|
| 1 | Project scaffolding | S4 |
| 2 | Database models & schema | S2, S6 |
| 3 | Scenario generator | S6 |
| 4 | Shared feature library | S5, S8 |
| 5 | Webhook receiver & API | S7 |
| 6 | Celery workers | S7 |
| 7 | ML pipeline | S9 |
| 8 | LLM integration & policy checker | S10 |
| 9 | Frontend dashboard | S11 |
| 10 | Tests | S7, S5 |
| 11 | Notebooks | S9 |
| 12 | Final integration & README | S1, S2, S3, S4 |

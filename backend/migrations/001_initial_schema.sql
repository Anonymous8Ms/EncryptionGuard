-- migrations/001_initial_schema.sql
-- EncryptionGuard v5 Database Schema

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
    event_label INTEGER DEFAULT NULL,
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
    token_id TEXT UNIQUE NOT NULL,
    first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id TEXT NOT NULL,
    ring_id TEXT,
    risk_score FLOAT,
    risk_label TEXT,
    estimated_exposure_paise INTEGER,
    model_version TEXT,
    point_score FLOAT,
    graph_score FLOAT,
    evidence_source TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS case_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES cases(id),
    evidence_type TEXT NOT NULL,
    evidence_payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analyst_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES cases(id),
    disposition TEXT NOT NULL,
    analyst_id TEXT NOT NULL,
    model_version TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
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
);

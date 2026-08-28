"""
FeatureVector schema — shared between online scoring (app/) and offline training (ml/).

Every field is optional at construction time so that partial feature vectors
can be built incrementally (e.g. velocity features populated first, then graph).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FeatureVector(BaseModel):
    """Unified feature vector consumed by the scoring model and training pipeline."""

    # ── Identifiers ────────────────────────────────────────────────────────
    account_id: str
    merchant_id: str
    reference_timestamp: datetime

    # ── Velocity features ──────────────────────────────────────────────────
    refund_count_24h: int = 0
    refund_count_7d: int = 0
    refund_count_30d: int = 0

    refund_amount_24h: float = 0.0
    refund_amount_7d: float = 0.0
    refund_amount_30d: float = 0.0

    order_count_24h: int = 0
    order_count_7d: int = 0

    unique_devices_24h: int = 0
    unique_devices_7d: int = 0

    unique_ips_24h: int = 0
    unique_ips_7d: int = 0

    unique_tokens_24h: int = 0
    unique_tokens_7d: int = 0

    # ── Graph features ─────────────────────────────────────────────────────
    connected_component_size: int = 0
    weighted_degree: float = 0.0
    pagerank_score: float = 0.0
    community_id: Optional[int] = None

    shared_ip_count: int = 0
    shared_device_count: int = 0
    shared_token_count: int = 0

    # ── Labels (populated only during training) ────────────────────────────
    event_label: Optional[int] = None
    ring_id: Optional[str] = None
    scenario_id: Optional[str] = None

    class Config:
        frozen = False
        json_schema_extra = {
            "example": {
                "account_id": "acct_abc123",
                "merchant_id": "merch_xyz789",
                "reference_timestamp": "2025-01-15T10:30:00Z",
                "refund_count_24h": 2,
                "refund_amount_24h": 1500.00,
                "connected_component_size": 5,
                "pagerank_score": 0.032,
                "event_label": 1,
            }
        }

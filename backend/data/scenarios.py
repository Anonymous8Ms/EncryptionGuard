"""Scenario definitions for synthetic refund-abuse data generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ScenarioType(str, Enum):
    """Types of behavioural scenarios the generator can produce."""

    NORMAL = "normal"
    LEGITIMATE_REFUND = "legitimate_refund"
    SHARED_NETWORK = "shared_network"
    SINGLE_ABUSE = "single_abuse"
    COORDINATED_RING = "coordinated_ring"


@dataclass(frozen=True)
class ScenarioConfig:
    """Configuration for a single synthetic scenario.

    Attributes:
        scenario_type: The behavioural pattern to simulate.
        num_accounts: Number of distinct customer accounts in the scenario.
        num_devices: Number of distinct device fingerprints.
        num_ips: Number of distinct IP addresses used.
        num_payment_tokens: Number of unique payment tokens (cards / wallets).
        num_orders: Total orders placed across all accounts.
        refund_rate: Probability [0, 1] that a completed order is refunded.
        token_reuse_prob: Probability [0, 1] that a payment token is reused
            across accounts (higher ⇒ more suspicious).
        label: Ground-truth label for ML training (0 = benign, 1 = abusive).
        ring_id: Optional identifier linking accounts in a coordinated ring.
    """

    scenario_type: ScenarioType
    num_accounts: int
    num_devices: int
    num_ips: int
    num_payment_tokens: int
    num_orders: int
    refund_rate: float
    token_reuse_prob: float
    label: int
    ring_id: Optional[str] = None


# ── Pre-defined scenarios ────────────────────────────────────────────────────

SCENARIOS: list[ScenarioConfig] = [
    # 1. Normal behaviour — many accounts, unique tokens, very low refund rate
    ScenarioConfig(
        scenario_type=ScenarioType.NORMAL,
        num_accounts=50,
        num_devices=50,
        num_ips=45,
        num_payment_tokens=50,
        num_orders=200,
        refund_rate=0.02,
        token_reuse_prob=0.0,
        label=0,
    ),
    # 2. Legitimate refund — moderate refund rate but no shared infrastructure
    ScenarioConfig(
        scenario_type=ScenarioType.LEGITIMATE_REFUND,
        num_accounts=20,
        num_devices=20,
        num_ips=18,
        num_payment_tokens=20,
        num_orders=80,
        refund_rate=0.25,
        token_reuse_prob=0.0,
        label=0,
    ),
    # 3. Shared network — several accounts share IPs / devices
    ScenarioConfig(
        scenario_type=ScenarioType.SHARED_NETWORK,
        num_accounts=15,
        num_devices=6,
        num_ips=4,
        num_payment_tokens=12,
        num_orders=60,
        refund_rate=0.15,
        token_reuse_prob=0.3,
        label=1,
    ),
    # 4. Single abuser — one person operating many accounts
    ScenarioConfig(
        scenario_type=ScenarioType.SINGLE_ABUSE,
        num_accounts=10,
        num_devices=2,
        num_ips=2,
        num_payment_tokens=3,
        num_orders=40,
        refund_rate=0.60,
        token_reuse_prob=0.7,
        label=1,
    ),
    # 5. Coordinated ring — organised group with high token sharing
    ScenarioConfig(
        scenario_type=ScenarioType.COORDINATED_RING,
        num_accounts=25,
        num_devices=8,
        num_ips=5,
        num_payment_tokens=6,
        num_orders=100,
        refund_rate=0.55,
        token_reuse_prob=0.8,
        label=1,
        ring_id="RING_001",
    ),
]

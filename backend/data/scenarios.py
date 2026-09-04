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
    COORDINATED_RING_LARGE = "coordinated_ring_large"
    NEAR_MISS_SHARED_INFRA = "near_miss_shared_infra"
    HIGH_LOSS_RING = "high_loss_ring"


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
        num_accounts=100,
        num_devices=100,
        num_ips=90,
        num_payment_tokens=100,
        num_orders=500,
        refund_rate=0.02,
        token_reuse_prob=0.0,
        label=0,
    ),
    # 2. Legitimate refund — moderate refund rate but no shared infrastructure
    ScenarioConfig(
        scenario_type=ScenarioType.LEGITIMATE_REFUND,
        num_accounts=50,
        num_devices=50,
        num_ips=45,
        num_payment_tokens=50,
        num_orders=200,
        refund_rate=0.25,
        token_reuse_prob=0.0,
        label=0,
    ),
    # 3. Shared network — several accounts share IPs / devices (legitimate)
    ScenarioConfig(
        scenario_type=ScenarioType.SHARED_NETWORK,
        num_accounts=30,
        num_devices=12,
        num_ips=8,
        num_payment_tokens=24,
        num_orders=120,
        refund_rate=0.15,
        token_reuse_prob=0.3,
        label=0,
    ),
    # 4. Single abuser — one person operating many accounts
    ScenarioConfig(
        scenario_type=ScenarioType.SINGLE_ABUSE,
        num_accounts=3,
        num_devices=2,
        num_ips=2,
        num_payment_tokens=3,
        num_orders=12,
        refund_rate=0.60,
        token_reuse_prob=0.7,
        label=1,
    ),
    # 5. Coordinated ring — organised group with high token sharing
    ScenarioConfig(
        scenario_type=ScenarioType.COORDINATED_RING,
        num_accounts=5,
        num_devices=3,
        num_ips=2,
        num_payment_tokens=3,
        num_orders=20,
        refund_rate=0.55,
        token_reuse_prob=0.8,
        label=1,
        ring_id="RING_001",
    ),
    # 6. Coordinated ring large — 8-15 accounts, multiple shared entities
    ScenarioConfig(
        scenario_type=ScenarioType.COORDINATED_RING_LARGE,
        num_accounts=4,
        num_devices=2,
        num_ips=2,
        num_payment_tokens=2,
        num_orders=20,
        refund_rate=0.65,
        token_reuse_prob=0.9,
        label=1,
        ring_id="RING_002",
    ),
    # 7. Near-miss shared infra — looks suspicious but legitimate
    ScenarioConfig(
        scenario_type=ScenarioType.NEAR_MISS_SHARED_INFRA,
        num_accounts=20,
        num_devices=8,
        num_ips=5,
        num_payment_tokens=20,
        num_orders=80,
        refund_rate=0.10,
        token_reuse_prob=0.2,
        label=0,
    ),
    # 8. High loss ring — large amounts, multiple entities shared
    ScenarioConfig(
        scenario_type=ScenarioType.HIGH_LOSS_RING,
        num_accounts=3,
        num_devices=2,
        num_ips=2,
        num_payment_tokens=2,
        num_orders=15,
        refund_rate=0.70,
        token_reuse_prob=0.85,
        label=1,
        ring_id="RING_003",
    ),
]

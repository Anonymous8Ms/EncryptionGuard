"""Synthetic data generator for coordinated refund-abuse detection.

Usage:
    python -m backend.data.generator [SEED]

Generates reproducible JSON event files under ``data/output/``.
"""

from __future__ import annotations

import json
import os
import random
import string
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from .scenarios import SCENARIOS, ScenarioConfig, ScenarioType

GENERATOR_VERSION = "5.0.0"

# ── Lightweight entity dataclasses ───────────────────────────────────────────


@dataclass
class Merchant:
    merchant_id: str
    name: str
    category: str
    created_at: str


@dataclass
class Account:
    account_id: str
    merchant_id: str
    email: str
    created_at: str


@dataclass
class Device:
    device_id: str
    fingerprint: str
    user_agent: str
    created_at: str


@dataclass
class IPAddress:
    ip_id: str
    address: str
    asn: str
    country: str


@dataclass
class PaymentToken:
    token_id: str
    token_value: str  # ptok_demo_XXXXX
    brand: str
    last4: str
    created_at: str


@dataclass
class Order:
    order_id: str
    account_id: str
    merchant_id: str
    device_id: str
    ip_id: str
    token_id: str
    amount_cents: int
    currency: str
    status: str  # pending | completed | refunded
    created_at: str


@dataclass
class Payment:
    payment_id: str
    order_id: str
    token_id: str
    amount_cents: int
    status: str  # captured | refunded
    created_at: str


@dataclass
class Refund:
    refund_id: str
    payment_id: str
    order_id: str
    amount_cents: int
    reason: str
    created_at: str


@dataclass
class Event:
    event_type: str
    entity_type: str
    entity_id: str
    merchant_id: str
    payload: dict[str, Any]
    event_label: int
    ring_id: Optional[str]
    scenario_id: str
    generated_at: str
    generator_version: str


# ── Helper utilities ─────────────────────────────────────────────────────────

_CATEGORIES = ["electronics", "fashion", "home_goods", "digital_goods", "food_delivery"]
_DOMAINS = ["gmail.com", "outlook.com", "yahoo.com", "protonmail.com", "fastmail.com"]
_BRANDS = ["visa", "mastercard", "amex"]
_REFUND_REASONS = [
    "item_not_received",
    "not_as_described",
    "changed_mind",
    "duplicate_order",
    "fraudulent",
    "defective",
]
_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) Safari/17.4",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4) Mobile/15E148",
    "Mozilla/5.0 (Linux; Android 14) Chrome/124.0",
]


def _uid(rng: random.Random, prefix: str = "") -> str:
    short = uuid.UUID(int=rng.getrandbits(128)).hex[:12]
    return f"{prefix}{short}" if prefix else short


def _ip(rng: random.Random) -> str:
    return f"{rng.randint(10, 223)}.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}"


def _email(rng: random.Random) -> str:
    user = "".join(rng.choices(string.ascii_lowercase, k=rng.randint(6, 12)))
    domain = rng.choice(_DOMAINS)
    return f"{user}@{domain}"


def _payment_token(rng: random.Random) -> str:
    suffix = "".join(rng.choices(string.ascii_lowercase + string.digits, k=5))
    return f"ptok_demo_{suffix}"


def _last4(rng: random.Random) -> str:
    return f"{rng.randint(0, 9999):04d}"


# ── ScenarioGenerator ────────────────────────────────────────────────────────


class ScenarioGenerator:
    """Generates synthetic merchant, account, order, payment, refund, and
    event data for each scenario configuration.

    Fully reproducible given the same *seed*.
    """

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed
        self.rng = random.Random(seed)

    # ── Public API ───────────────────────────────────────────────────────

    def generate_merchant(self) -> Merchant:
        return Merchant(
            merchant_id=_uid(self.rng, "mch_"),
            name=f"Merchant_{''.join(self.rng.choices(string.ascii_uppercase, k=4))}",
            category=self.rng.choice(_CATEGORIES),
            created_at=self._ts(days_ago=365),
        )

    def generate_scenario(
        self,
        config: ScenarioConfig,
        merchant: Merchant,
        base_time: Optional[datetime] = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Generate all entities and events for one scenario instance.

        Returns a dict with keys: merchants, accounts, devices, ips,
        payment_tokens, orders, payments, refunds, events.
        """
        if base_time is None:
            base_time = datetime.now(tz=timezone.utc)

        scenario_id = _uid(self.rng, "scn_")

        # ── Build entity pools ───────────────────────────────────────────
        devices = [self._make_device() for _ in range(config.num_devices)]
        ips = [self._make_ip() for _ in range(config.num_ips)]
        tokens = [self._make_payment_token() for _ in range(config.num_payment_tokens)]

        accounts: list[Account] = []
        for _ in range(config.num_accounts):
            accounts.append(
                Account(
                    account_id=_uid(self.rng, "acc_"),
                    merchant_id=merchant.merchant_id,
                    email=_email(self.rng),
                    created_at=self._ts_from(base_time, days_ago=180),
                )
            )

        # ── Orders / payments / refunds ──────────────────────────────────
        orders: list[Order] = []
        payments: list[Payment] = []
        refunds: list[Refund] = []
        events: list[Event] = []

        for i in range(config.num_orders):
            acct = self.rng.choice(accounts)
            dev = self.rng.choice(devices)
            ip = self.rng.choice(ips)
            tok = self._pick_token(tokens, config)

            order_ts = base_time + timedelta(hours=i * 2 + self.rng.randint(0, 6))
            order_id = _uid(self.rng, "ord_")
            amount = self.rng.randint(500, 150000)  # $5 – $1500

            order = Order(
                order_id=order_id,
                account_id=acct.account_id,
                merchant_id=merchant.merchant_id,
                device_id=dev.device_id,
                ip_id=ip.ip_id,
                token_id=tok.token_id,
                amount_cents=amount,
                currency="USD",
                status="completed",
                created_at=order_ts.isoformat(),
            )
            orders.append(order)

            # Payment event
            payment_id = _uid(self.rng, "pay_")
            payment = Payment(
                payment_id=payment_id,
                order_id=order_id,
                token_id=tok.token_id,
                amount_cents=amount,
                status="captured",
                created_at=order_ts.isoformat(),
            )
            payments.append(payment)

            events.append(self._make_event(
                event_type="payment_captured",
                entity_type="payment",
                entity_id=payment_id,
                merchant_id=merchant.merchant_id,
                payload=asdict(payment),
                event_label=config.label,
                ring_id=config.ring_id,
                scenario_id=scenario_id,
                ts=order_ts,
            ))

            # Maybe refund
            if self.rng.random() < config.refund_rate:
                refund_ts = order_ts + timedelta(
                    hours=self.rng.randint(1, 72),
                    minutes=self.rng.randint(0, 59),
                )
                refund_id = _uid(self.rng, "ref_")
                refund = Refund(
                    refund_id=refund_id,
                    payment_id=payment_id,
                    order_id=order_id,
                    amount_cents=amount,
                    reason=self.rng.choice(_REFUND_REASONS),
                    created_at=refund_ts.isoformat(),
                )
                refunds.append(refund)
                order.status = "refunded"
                payment.status = "refunded"

                events.append(self._make_event(
                    event_type="refund_issued",
                    entity_type="refund",
                    entity_id=refund_id,
                    merchant_id=merchant.merchant_id,
                    payload=asdict(refund),
                    event_label=config.label,
                    ring_id=config.ring_id,
                    scenario_id=scenario_id,
                    ts=refund_ts,
                ))

        # ── Account-creation events ──────────────────────────────────────
        for acct in accounts:
            events.append(self._make_event(
                event_type="account_created",
                entity_type="account",
                entity_id=acct.account_id,
                merchant_id=merchant.merchant_id,
                payload=asdict(acct),
                event_label=config.label,
                ring_id=config.ring_id,
                scenario_id=scenario_id,
                ts=datetime.fromisoformat(acct.created_at),
            ))

        # Sort events chronologically
        events.sort(key=lambda e: e.generated_at)

        return {
            "scenario_type": config.scenario_type.value,
            "scenario_id": scenario_id,
            "merchant": [asdict(merchant)],
            "accounts": [asdict(a) for a in accounts],
            "devices": [asdict(d) for d in devices],
            "ips": [asdict(ip) for ip in ips],
            "payment_tokens": [asdict(t) for t in tokens],
            "orders": [asdict(o) for o in orders],
            "payments": [asdict(p) for p in payments],
            "refunds": [asdict(r) for r in refunds],
            "events": [asdict(e) for e in events],
        }

    def generate(
        self,
        num_merchants: int = 3,
        scenarios_per_merchant: Optional[list[ScenarioConfig]] = None,
    ) -> list[dict[str, list[dict[str, Any]]]]:
        """Generate data for *num_merchants* merchants, each running every
        scenario in *scenarios_per_merchant* (defaults to ``SCENARIOS``)."""
        if scenarios_per_merchant is None:
            scenarios_per_merchant = SCENARIOS

        results: list[dict[str, list[dict[str, Any]]]] = []
        base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)

        for m_idx in range(num_merchants):
            merchant = self.generate_merchant()
            for s_idx, cfg in enumerate(scenarios_per_merchant):
                offset = timedelta(days=m_idx * 30 + s_idx * 7)
                result = self.generate_scenario(cfg, merchant, base_time + offset)
                results.append(result)

        return results

    def save(self, output_dir: str | Path = "data/output") -> list[Path]:
        """Generate all data and persist as JSON files.

        Returns list of written file paths.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        all_data = self.generate()
        written: list[Path] = []

        # Write a combined file
        combined_path = output_dir / "all_scenarios.json"
        with open(combined_path, "w") as f:
            json.dump(all_data, f, indent=2, default=str)
        written.append(combined_path)

        # Write per-scenario-type files
        for idx, scenario_data in enumerate(all_data):
            stype = scenario_data.get("scenario_type", "unknown")
            fname = f"{stype}_{idx:03d}.json"
            fpath = output_dir / fname
            with open(fpath, "w") as f:
                json.dump(scenario_data, f, indent=2, default=str)
            written.append(fpath)

        # Write a manifest
        manifest = {
            "generator_version": GENERATOR_VERSION,
            "seed": self.seed,
            "num_scenarios": len(all_data),
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "files": [str(p.name) for p in written],
        }
        manifest_path = output_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        written.append(manifest_path)

        return written

    # ── Private helpers ──────────────────────────────────────────────────

    def _make_device(self) -> Device:
        return Device(
            device_id=_uid(self.rng, "dev_"),
            fingerprint=_uid(self.rng, "fp_"),
            user_agent=self.rng.choice(_UAS),
            created_at=self._ts(days_ago=180),
        )

    def _make_ip(self) -> IPAddress:
        return IPAddress(
            ip_id=_uid(self.rng, "ip_"),
            address=_ip(self.rng),
            asn=f"AS{self.rng.randint(1000, 65000)}",
            country="US",
        )

    def _make_payment_token(self) -> PaymentToken:
        brand = self.rng.choice(_BRANDS)
        return PaymentToken(
            token_id=_uid(self.rng, "tok_"),
            token_value=_payment_token(self.rng),
            brand=brand,
            last4=_last4(self.rng),
            created_at=self._ts(days_ago=180),
        )

    def _pick_token(
        self, tokens: list[PaymentToken], config: ScenarioConfig
    ) -> PaymentToken:
        """Pick a payment token, potentially reusing one across accounts."""
        if tokens and self.rng.random() < config.token_reuse_prob and len(tokens) > 1:
            # Reuse: pick a token that is NOT the "natural" one for this slot
            return self.rng.choice(tokens)
        return self.rng.choice(tokens)

    def _make_event(
        self,
        *,
        event_type: str,
        entity_type: str,
        entity_id: str,
        merchant_id: str,
        payload: dict[str, Any],
        event_label: int,
        ring_id: Optional[str],
        scenario_id: str,
        ts: datetime,
    ) -> Event:
        return Event(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            merchant_id=merchant_id,
            payload=payload,
            event_label=event_label,
            ring_id=ring_id,
            scenario_id=scenario_id,
            generated_at=ts.isoformat(),
            generator_version=GENERATOR_VERSION,
        )

    def _ts(self, days_ago: int = 30) -> str:
        delta = timedelta(days=self.rng.randint(0, days_ago))
        dt = datetime.now(tz=timezone.utc) - delta
        return dt.isoformat()

    def _ts_from(self, base: datetime, days_ago: int = 30) -> str:
        delta = timedelta(days=self.rng.randint(0, days_ago))
        return (base - delta).isoformat()


# ── CLI entry point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 42
    print(f"Generating synthetic data with seed={seed} ...")

    gen = ScenarioGenerator(seed=seed)
    written = gen.save(output_dir="data/output")

    print(f"Done. {len(written)} files written:")
    for p in written:
        print(f"  {p}")

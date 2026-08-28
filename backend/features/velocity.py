"""
Velocity features — rolling-window counters stored in Redis.

Used by both the online scoring path (app/) and the offline training
feature-extraction pipeline (ml/).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import redis

# ── Key schema ─────────────────────────────────────────────────────────────
#   velocity:{merchant}:{account}:{metric}:{window}
#   e.g. velocity:merch_001:acct_abc:refund_count:24h
#   Unique-entity keys use Redis sets:
#   velocity:{merchant}:{account}:{entity_type}:{window}:members

_WINDOWS = {
    "24h": 86_400,
    "7d": 604_800,
    "30d": 2_592_000,
}


def _key(merchant_id: str, account_id: str, metric: str, window: str) -> str:
    return f"velocity:{merchant_id}:{account_id}:{metric}:{window}"


# ── Public API ─────────────────────────────────────────────────────────────


def compute_velocity_features(
    redis_client: redis.Redis,
    account_id: str,
    merchant_id: str,
    reference_timestamp: datetime,
) -> dict[str, Any]:
    """Return all velocity feature values for the given account/merchant.

    Uses a single Redis pipeline to minimise round-trips.
    """
    pipe = redis_client.pipeline()

    # Scalar counters
    scalar_keys: list[tuple[str, str, str]] = [
        ("refund_count", "24h"),
        ("refund_count", "7d"),
        ("refund_count", "30d"),
        ("refund_amount", "24h"),
        ("refund_amount", "7d"),
        ("refund_amount", "30d"),
        ("order_count", "24h"),
        ("order_count", "7d"),
    ]
    for metric, window in scalar_keys:
        pipe.get(_key(merchant_id, account_id, metric, window))

    # Unique-entity set cardinalities
    entity_keys: list[tuple[str, str]] = [
        ("device", "24h"),
        ("device", "7d"),
        ("ip", "24h"),
        ("ip", "7d"),
        ("token", "24h"),
        ("token", "7d"),
    ]
    for entity_type, window in entity_keys:
        pipe.scard(_key(merchant_id, account_id, entity_type, window))

    results = pipe.execute()

    # Unpack results — Redis returns None for missing keys
    def _int(val: Any) -> int:
        return int(val) if val is not None else 0

    def _float(val: Any) -> float:
        return float(val) if val is not None else 0.0

    return {
        "refund_count_24h": _int(results[0]),
        "refund_count_7d": _int(results[1]),
        "refund_count_30d": _int(results[2]),
        "refund_amount_24h": _float(results[3]),
        "refund_amount_7d": _float(results[4]),
        "refund_amount_30d": _float(results[5]),
        "order_count_24h": _int(results[6]),
        "order_count_7d": _int(results[7]),
        "unique_devices_24h": _int(results[8]),
        "unique_devices_7d": _int(results[9]),
        "unique_ips_24h": _int(results[10]),
        "unique_ips_7d": _int(results[11]),
        "unique_tokens_24h": _int(results[12]),
        "unique_tokens_7d": _int(results[13]),
    }


def update_velocity_counters(
    redis_client: redis.Redis,
    merchant_id: str,
    account_id: str,
    event_type: str,
    amount: float,
    device_id: str,
    ip_id: str,
    token_id: str,
) -> None:
    """Increment rolling-window counters after a new event.

    * Scalar counters (refund_count, refund_amount, order_count) are
      incremented with INCRBY / INCRBYFLOAT and expire at the window TTL.
    * Unique-entity sets (device, ip, token) use SADD with the same TTL.

    TTLs: 24h = 86 400 s, 7d = 604 800 s, 30d = 2 592 000 s.
    """
    pipe = redis_client.pipeline()

    # Determine which scalar counters to bump
    is_refund = event_type == "refund"
    is_order = event_type == "order"

    for window, ttl in _WINDOWS.items():
        if is_refund:
            rk = _key(merchant_id, account_id, "refund_count", window)
            pipe.incrby(rk, 1)
            pipe.expire(rk, ttl)

            ak = _key(merchant_id, account_id, "refund_amount", window)
            pipe.incrbyfloat(ak, amount)
            pipe.expire(ak, ttl)

        if is_order:
            ok = _key(merchant_id, account_id, "order_count", window)
            pipe.incrby(ok, 1)
            pipe.expire(ok, ttl)

        # Unique-entity sets — always tracked regardless of event type
        for entity_id, entity_type in [
            (device_id, "device"),
            (ip_id, "ip"),
            (token_id, "token"),
        ]:
            if entity_id:
                ek = _key(merchant_id, account_id, entity_type, window)
                pipe.sadd(ek, entity_id)
                pipe.expire(ek, ttl)

    pipe.execute()

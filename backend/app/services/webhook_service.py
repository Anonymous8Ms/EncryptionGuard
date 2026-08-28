"""
EncryptionGuard v5 — Webhook processing service.

Handles incoming payment gateway webhooks (e.g. Razorpay):
  1. Verify HMAC-SHA256 signature.
  2. Parse event type and payload.
  3. Persist Order / Payment / Refund records.
  4. Return a structured result dict.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.payment import Payment
from app.models.refund import Refund

logger = logging.getLogger(__name__)


# ── Signature verification ───────────────────────────────────────────────────


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify an HMAC-SHA256 webhook signature.

    Args:
        payload: Raw request body bytes.
        signature: Hex-encoded HMAC digest from the ``X-Webhook-Signature`` header.
        secret: Shared webhook secret.

    Returns:
        True if the signature matches, False otherwise.
    """
    expected = hmac.new(
        key=secret.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


# ── Webhook event processing ─────────────────────────────────────────────────


def process_webhook(
    db: Session,
    event_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Process a verified webhook event and persist the result.

    Args:
        db: SQLAlchemy session.
        event_type: One of ``order.paid``, ``payment.captured``,
                    ``refund.processed``.
        payload: Parsed JSON body of the webhook.

    Returns:
        Result dict with ``status`` and entity identifiers.

    Raises:
        ValueError: If *event_type* is not recognised.
    """
    if event_type == "order.paid":
        return _handle_order_paid(db, payload)
    elif event_type == "payment.captured":
        return _handle_payment_captured(db, payload)
    elif event_type == "refund.processed":
        return _handle_refund_processed(db, payload)
    else:
        raise ValueError(f"Unknown webhook event type: {event_type!r}")


# ── Private handlers ─────────────────────────────────────────────────────────


def _handle_order_paid(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    order = Order(
        order_id=payload["order_id"],
        account_id=payload["account_id"],
        merchant_id=payload["merchant_id"],
        amount_cents=payload["amount_cents"],
        currency=payload.get("currency", "USD"),
        status="completed",
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    logger.info("Order %s created via webhook", order.order_id)
    return {"status": "order_created", "order_id": order.order_id}


def _handle_payment_captured(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    payment = Payment(
        payment_id=payload["payment_id"],
        order_id=payload["order_id"],
        token_id=payload.get("token_id"),
        amount_cents=payload["amount_cents"],
        status="captured",
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    logger.info("Payment %s captured via webhook", payment.payment_id)
    return {"status": "payment_captured", "payment_id": payment.payment_id}


def _handle_refund_processed(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    refund = Refund(
        refund_id=payload["refund_id"],
        payment_id=payload["payment_id"],
        order_id=payload["order_id"],
        amount_cents=payload["amount_cents"],
        reason=payload.get("reason", ""),
    )
    db.add(refund)
    db.commit()
    db.refresh(refund)
    logger.info("Refund %s processed via webhook", refund.refund_id)
    return {"status": "refund_processed", "refund_id": refund.refund_id}

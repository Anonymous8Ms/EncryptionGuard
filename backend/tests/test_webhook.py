"""
Tests for webhook processing — signature verification and event handling.

Covers:
  1. HMAC-SHA256 signature verification (valid + invalid)
  2. order.paid webhook → Order row created
  3. refund.processed webhook → Refund row created
  4. Unknown event type → ValueError
"""

from __future__ import annotations

import hashlib
import hmac

import pytest
from sqlalchemy.orm import Session

from backend.app.models.order import Order
from backend.app.models.refund import Refund
from backend.app.services.webhook_service import process_webhook, verify_signature

WEBHOOK_SECRET = "test_webhook_secret_12345"


# ── Signature verification ───────────────────────────────────────────────────


class TestVerifySignature:
    """HMAC-SHA256 signature verification."""

    def test_valid_signature(self):
        payload = b'{"event_type": "order.paid"}'
        expected_sig = hmac.new(
            WEBHOOK_SECRET.encode(), payload, hashlib.sha256
        ).hexdigest()
        assert verify_signature(payload, expected_sig, WEBHOOK_SECRET) is True

    def test_invalid_signature(self):
        payload = b'{"event_type": "order.paid"}'
        assert verify_signature(payload, "bad_signature", WEBHOOK_SECRET) is False

    def test_tampered_payload(self):
        payload = b'{"event_type": "order.paid"}'
        sig = hmac.new(
            WEBHOOK_SECRET.encode(), payload, hashlib.sha256
        ).hexdigest()
        tampered = b'{"event_type": "refund.processed"}'
        assert verify_signature(tampered, sig, WEBHOOK_SECRET) is False


# ── Webhook event processing ─────────────────────────────────────────────────


class TestProcessWebhook:
    """Database writes from webhook events."""

    def test_order_paid_creates_order(
        self, db: Session, webhook_order_paid_payload: dict
    ):
        result = process_webhook(
            db,
            event_type=webhook_order_paid_payload["event_type"],
            payload=webhook_order_paid_payload["payload"],
        )
        assert result["status"] == "order_created"
        assert result["order_id"] == "ord_test_001"

        order = db.query(Order).filter_by(order_id="ord_test_001").first()
        assert order is not None
        assert order.account_id == "acc_test_001"
        assert order.amount_cents == 4999
        assert order.status == "completed"

    def test_refund_processed_creates_refund(
        self, db: Session, webhook_refund_processed_payload: dict
    ):
        result = process_webhook(
            db,
            event_type=webhook_refund_processed_payload["event_type"],
            payload=webhook_refund_processed_payload["payload"],
        )
        assert result["status"] == "refund_processed"
        assert result["refund_id"] == "ref_test_001"

        refund = db.query(Refund).filter_by(refund_id="ref_test_001").first()
        assert refund is not None
        assert refund.payment_id == "pay_test_001"
        assert refund.amount_cents == 4999
        assert refund.reason == "item_not_received"

    def test_unknown_event_type_raises(self, db: Session):
        with pytest.raises(ValueError, match="Unknown webhook event type"):
            process_webhook(db, event_type="unknown.event", payload={})

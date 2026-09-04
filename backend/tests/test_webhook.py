"""
Tests for webhook processing — signature verification and event handling.
"""

from __future__ import annotations

import hashlib
import hmac
import json

import pytest
from sqlalchemy.orm import Session

from app.models.cases import Case
from app.models.events import WebhookEnvelope
from app.services.webhook_service import process_webhook, verify_signature

WEBHOOK_SECRET = "test_webhook_secret_12345"


class TestVerifySignature:
    """HMAC-SHA256 signature verification."""

    def test_valid_signature(self):
        payload = b'{"event": "payment.captured"}'
        expected_sig = hmac.new(
            WEBHOOK_SECRET.encode(), payload, hashlib.sha256
        ).hexdigest()
        assert verify_signature(payload, expected_sig, WEBHOOK_SECRET) is True

    def test_invalid_signature(self):
        payload = b'{"event": "payment.captured"}'
        assert verify_signature(payload, "bad_signature", WEBHOOK_SECRET) is False

    def test_tampered_payload(self):
        payload = b'{"event": "payment.captured"}'
        sig = hmac.new(
            WEBHOOK_SECRET.encode(), payload, hashlib.sha256
        ).hexdigest()
        tampered = b'{"event": "refund.created"}'
        assert verify_signature(tampered, sig, WEBHOOK_SECRET) is False


class TestProcessWebhook:
    """Webhook processing with database."""

    def test_valid_webhook_creates_case(self, db: Session, monkeypatch):
        # Mock the webhook secret
        monkeypatch.setattr("app.config.settings.razorpay_webhook_secret", WEBHOOK_SECRET)

        payload = json.dumps({
            "event": "payment.captured",
            "payload": {"payment": {"entity": {"id": "pay_test_001", "amount": 50000}}}
        }).encode()
        sig = hmac.new(WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()

        result = process_webhook(
            db=db,
            raw_body=payload,
            signature=sig,
            event_id="evt_test_001",
            merchant_id="merch_test"
        )
        assert result["status"] == "processed"
        assert result["event_id"] == "evt_test_001"

    def test_duplicate_event_returns_duplicate(self, db: Session, monkeypatch):
        monkeypatch.setattr("app.config.settings.razorpay_webhook_secret", WEBHOOK_SECRET)

        payload = json.dumps({
            "event": "payment.captured",
            "payload": {"payment": {"entity": {"id": "pay_test_002", "amount": 50000}}}
        }).encode()
        sig = hmac.new(WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()

        # First call
        process_webhook(db, payload, sig, "evt_dup_001", "merch_test")

        # Second call - should return duplicate
        result = process_webhook(db, payload, sig, "evt_dup_001", "merch_test")
        assert result["status"] == "duplicate"

    def test_invalid_signature_returns_invalid(self, db: Session, monkeypatch):
        monkeypatch.setattr("app.config.settings.razorpay_webhook_secret", WEBHOOK_SECRET)

        payload = json.dumps({"event": "payment.captured"}).encode()

        result = process_webhook(
            db=db,
            raw_body=payload,
            signature="bad_signature",
            event_id="evt_invalid_001",
            merchant_id="merch_test"
        )
        assert result["status"] == "invalid_signature"

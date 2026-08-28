"""
Tests for the Razorpay webhook receiver.

Covers:
- Valid HMAC-SHA256 signature → 200
- Invalid signature → 400
- Idempotency (duplicate event_id → same response, no double insert)
- Refund event processing
"""

import hashlib
import hmac
import json
import os
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WEBHOOK_SECRET = "test_webhook_secret"
WEBHOOK_URL = "/webhooks/razorpay"

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _sign(body: bytes, secret: str = WEBHOOK_SECRET) -> str:
    """Compute HMAC-SHA256 signature the same way Razorpay does."""
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def _load_fixture(name: str) -> dict:
    with open(FIXTURES_DIR / name) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestWebhookSignature:
    """Signature verification tests."""

    def test_valid_signature_returns_200(self, client, db, monkeypatch):
        """A correctly signed webhook should be accepted."""
        monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)

        payload = _load_fixture("webhook_order_paid.json")
        body = json.dumps(payload).encode("utf-8")
        sig = _sign(body)

        resp = client.post(
            WEBHOOK_URL,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Razorpay-Signature": sig,
                "X-Razorpay-Event-Id": "evt_valid_001",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_invalid_signature_returns_400(self, client, db, monkeypatch):
        """A webhook with a bad signature must be rejected."""
        monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)

        payload = _load_fixture("webhook_order_paid.json")
        body = json.dumps(payload).encode("utf-8")

        resp = client.post(
            WEBHOOK_URL,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Razorpay-Signature": "deadbeef" * 8,  # obviously wrong
                "X-Razorpay-Event-Id": "evt_bad_sig_001",
            },
        )
        assert resp.status_code == 400


class TestWebhookIdempotency:
    """Duplicate event_id must not create duplicate records."""

    def test_duplicate_event_returns_ok_without_double_insert(
        self, client, db, monkeypatch
    ):
        monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)

        payload = _load_fixture("webhook_order_paid.json")
        body = json.dumps(payload).encode("utf-8")
        sig = _sign(body)
        headers = {
            "Content-Type": "application/json",
            "X-Razorpay-Signature": sig,
            "X-Razorpay-Event-Id": "evt_idem_001",
        }

        resp1 = client.post(WEBHOOK_URL, content=body, headers=headers)
        resp2 = client.post(WEBHOOK_URL, content=body, headers=headers)

        assert resp1.status_code == 200
        assert resp2.status_code == 200

        # Verify only one WebhookEnvelope was created
        from backend.app.models.events import WebhookEnvelope

        count = db.query(WebhookEnvelope).filter_by(event_id="evt_idem_001").count()
        assert count == 1


class TestWebhookRefundEvent:
    """Refund events should be processed and normalized correctly."""

    def test_refund_event_is_processed(self, client, db, monkeypatch):
        monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)

        payload = _load_fixture("webhook_refund_processed.json")
        body = json.dumps(payload).encode("utf-8")
        sig = _sign(body)

        resp = client.post(
            WEBHOOK_URL,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Razorpay-Signature": sig,
                "X-Razorpay-Event-Id": "evt_refund_001",
            },
        )
        assert resp.status_code == 200

        # Verify a NormalizedEvent was created with event_type containing "refund"
        from backend.app.models.events import NormalizedEvent

        evt = (
            db.query(NormalizedEvent)
            .filter_by(entity_id="rfnd_test_123")
            .first()
        )
        assert evt is not None
        assert "refund" in evt.event_type.lower()

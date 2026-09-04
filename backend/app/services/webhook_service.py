"""
EncryptionGuard v5 — Webhook processing service.

Handles incoming Razorpay webhooks:
  1. Verify HMAC-SHA256 signature.
  2. Parse event type and payload.
  3. Persist normalized events and create/update cases.
  4. Return a structured result dict.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid
from typing import Any
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.cases import Case
from app.models.events import WebhookEnvelope, NormalizedEvent

logger = logging.getLogger(__name__)


def verify_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    """Verify an HMAC-SHA256 webhook signature."""
    expected = hmac.new(
        key=secret.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def process_webhook(
    db: Session,
    raw_body: bytes,
    signature: str,
    event_id: str,
    merchant_id: str,
) -> dict[str, Any]:
    """Process a verified webhook event and persist the result."""
    from app.config import get_settings
    settings = get_settings()
    
    # Verify signature
    is_valid = verify_signature(raw_body, signature, settings.razorpay_webhook_secret)
    
    # Parse payload
    payload = json.loads(raw_body)
    event_type = payload.get("event", "unknown")
    
    # Check for duplicate
    existing = db.query(WebhookEnvelope).filter(
        WebhookEnvelope.event_id == event_id
    ).first()
    
    if existing:
        return {"status": "duplicate", "event_id": event_id}
    
    # Store raw envelope
    envelope = WebhookEnvelope(
        event_id=event_id,
        merchant_id=merchant_id,
        event_type=event_type,
        raw_body=raw_body.decode("utf-8"),
        signature_valid="valid" if is_valid else "invalid",
        received_at=datetime.utcnow()
    )
    db.add(envelope)
    
    if not is_valid:
        db.commit()
        return {"status": "invalid_signature", "event_id": event_id}
    
    # Normalize and store event
    normalized = _normalize_event(payload, merchant_id, event_type)
    db_event = NormalizedEvent(**normalized)
    db.add(db_event)
    
    # Create or update case based on event type
    _update_case(db, normalized, merchant_id)
    
    envelope.processed_at = datetime.utcnow()
    db.commit()

    # Score the event directly (no Celery needed)
    try:
        from app.services.scoring import get_scoring_service
        scoring_service = get_scoring_service()
        entity = _normalize_event(payload, merchant_id, event_type)
        features = _extract_features(entity)
        scoring_result = scoring_service.score(features)

        # Update case with scoring result
        case = db.query(Case).filter(Case.account_id == entity.get("entity_id")).first()
        if case:
            case.risk_score = scoring_result["risk_score"]
            case.risk_level = scoring_result["risk_label"]
            case.recommended_action = scoring_result["risk_label"]
            case.shap_values = json.dumps({
                c["feature"]: c["contribution"]
                for c in scoring_result.get("shap_contributions", [])
            })
            db.commit()
            logger.info("Case %s scored: risk=%.3f label=%s", case.id, scoring_result["risk_score"], scoring_result["risk_label"])
    except Exception as e:
        logger.warning("Scoring failed: %s", e)

    logger.info("Webhook processed: %s (event: %s)", event_id, event_type)
    return {"status": "processed", "event_id": event_id, "event_type": event_type}


def _normalize_event(payload: dict, merchant_id: str, event_type: str) -> dict:
    """Normalize Razorpay webhook payload into standard event format."""
    # Extract entity based on event type
    if "refund" in event_type:
        entity = payload.get("payload", {}).get("refund", {}).get("entity", {})
        entity_type = "refund"
    elif "payment" in event_type:
        entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        entity_type = "payment"
    elif "order" in event_type:
        entity = payload.get("payload", {}).get("order", {}).get("entity", {})
        entity_type = "order"
    else:
        entity = payload.get("payload", {}).get("entity", {})
        entity_type = "unknown"
    
    return {
        "id": f"evt_{uuid.uuid4().hex[:12]}",
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": entity.get("id", "unknown"),
        "merchant_id": merchant_id,
        "payload": json.dumps(entity),
        "created_at": datetime.utcnow()
    }


def _update_case(db: Session, event: dict, merchant_id: str):
    """Create or update a case based on the event."""
    entity_id = event["entity_id"]
    event_type = event["event_type"]
    
    # Check if case exists for this entity
    case = db.query(Case).filter(
        Case.account_id == entity_id
    ).first()
    
    if not case:
        # Create new case
        case = Case(
            id=f"case_{uuid.uuid4().hex[:12]}",
            merchant_id=merchant_id,
            account_id=entity_id,
            risk_score=0.5,  # Default score
            risk_level="medium",
            status="open",
            recommended_action="monitor",
            evidence=json.dumps({"events": [event_type]}),
            model_version="v5.0"
        )
        db.add(case)
    else:
        # Update existing case
        evidence = json.loads(case.evidence) if case.evidence else {"events": []}
        evidence["events"] = evidence.get("events", []) + [event_type]
        case.evidence = json.dumps(evidence)
        case.updated_at = datetime.utcnow()


def _extract_features(event: dict) -> dict:
    """Extract feature values from normalized event."""
    return {
        "total_orders": 1,
        "total_refunds": 1 if event.get("event_type") == "refund" else 0,
        "total_amount": 0,
        "avg_amount": 0,
        "max_amount": 0,
        "refund_rate": 1.0 if event.get("event_type") == "refund" else 0.0,
        "refund_ratio": 1.0 if event.get("event_type") == "refund" else 0.0,
        "high_amount": 0,
    }

"""Celery tasks for webhook processing and scoring."""

import json
import logging
import os
import uuid
from datetime import datetime

from celery import Celery

logger = logging.getLogger(__name__)

# Celery app
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery(
    "encryptionguard",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_webhook_event(self, event_id: str, event_type: str, payload: dict):
    """Process a webhook event: score it and create/update case."""
    try:
        from app.services.scoring import get_scoring_service
        from app.models.base import SessionLocal
        from app.models.cases import Case

        # Extract features from payload
        features = _extract_features(payload)

        # Score the event
        scoring_service = get_scoring_service()
        result = scoring_service.score(features)

        # Update or create case in database
        db = SessionLocal()
        try:
            account_id = payload.get("account_id", payload.get("id", "unknown"))
            merchant_id = payload.get("merchant_id", "unknown")

            case = db.query(Case).filter(Case.account_id == account_id).first()
            if not case:
                case = Case(
                    id=f"case_{uuid.uuid4().hex[:12]}",
                    merchant_id=merchant_id,
                    account_id=account_id,
                    risk_score=result["risk_score"],
                    risk_level=result["risk_label"],
                    status="open",
                    recommended_action=result["risk_label"],
                    evidence=json.dumps({"events": [event_type]}),
                    shap_values=json.dumps({
                        c["feature"]: c["contribution"]
                        for c in result.get("shap_contributions", [])
                    }),
                    model_version=result.get("model_version", "v5.0"),
                )
                db.add(case)
            else:
                case.risk_score = result["risk_score"]
                case.risk_level = result["risk_label"]
                case.recommended_action = result["risk_label"]
                case.shap_values = json.dumps({
                    c["feature"]: c["contribution"]
                    for c in result.get("shap_contributions", [])
                })
                case.updated_at = datetime.utcnow()

            db.commit()
            logger.info("Event %s scored: risk=%.3f label=%s", event_id, result["risk_score"], result["risk_label"])
        finally:
            db.close()

        return {"status": "scored", "event_id": event_id, "risk_score": result["risk_score"]}

    except Exception as exc:
        logger.error("Failed to process event %s: %s", event_id, exc)
        raise self.retry(exc=exc)


def _extract_features(payload: dict) -> dict:
    """Extract feature values from webhook payload."""
    return {
        "total_orders": 1,
        "total_refunds": 1 if "refund" in str(payload.get("event_type", "")) else 0,
        "total_amount": payload.get("amount", payload.get("amount_cents", 0)),
        "avg_amount": payload.get("amount", payload.get("amount_cents", 0)),
        "max_amount": payload.get("amount", payload.get("amount_cents", 0)),
        "refund_rate": 1.0 if "refund" in str(payload.get("event_type", "")) else 0.0,
        "refund_ratio": 1.0 if "refund" in str(payload.get("event_type", "")) else 0.0,
        "high_amount": 1 if payload.get("amount", 0) > 100000 else 0,
    }


@celery_app.task
def run_community_detection(merchant_id: str):
    """Louvain community detection — placeholder for Neo4j integration."""
    logger.info("Community detection for merchant %s (placeholder)", merchant_id)
    return {"status": "placeholder", "merchant_id": merchant_id}


@celery_app.task
def prune_stale_edges():
    """Remove edges older than 90 days — placeholder for Neo4j integration."""
    logger.info("Pruning stale edges (placeholder)")
    return {"status": "placeholder"}

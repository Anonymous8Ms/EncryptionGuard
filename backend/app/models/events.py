from sqlalchemy import Column, String, DateTime, JSON, Integer, func
from app.models.base import Base


class WebhookEnvelope(Base):
    __tablename__ = "webhook_envelopes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String, nullable=False, unique=True)
    merchant_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    raw_body = Column(String, nullable=False)
    signature_valid = Column(String, default="pending")
    received_at = Column(DateTime, server_default=func.now())
    processed_at = Column(DateTime)


class NormalizedEvent(Base):
    __tablename__ = "normalized_events"
    id = Column(String, primary_key=True)
    event_type = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    merchant_id = Column(String, nullable=False)
    payload = Column(String, nullable=False)
    event_label = Column(String)
    ring_id = Column(String)
    scenario_id = Column(String)
    created_at = Column(DateTime, server_default=func.now())

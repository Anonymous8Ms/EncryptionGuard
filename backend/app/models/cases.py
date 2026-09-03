from sqlalchemy import Column, String, DateTime, JSON, Float, Integer, Boolean, func
from app.models.base import Base


class Case(Base):
    __tablename__ = "cases"
    id = Column(String, primary_key=True)
    merchant_id = Column(String, nullable=False)
    account_id = Column(String, nullable=False)
    ring_id = Column(String, nullable=True)
    risk_score = Column(Float, default=0.0)
    risk_level = Column(String, default="low")
    risk_label = Column(String, nullable=True)
    status = Column(String, default="open")
    recommended_action = Column(String, default="allow")
    estimated_exposure_paise = Column(Integer, nullable=True)
    model_version = Column(String, default="v5.0")
    point_score = Column(Float, nullable=True)
    graph_score = Column(Float, nullable=True)
    evidence_source = Column(String, nullable=True)
    evidence = Column(String, default="{}")
    graph_evidence = Column(String, default="{}")
    shap_values = Column(String, default="{}")
    llm_summary = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Feedback(Base):
    __tablename__ = "analyst_feedback"
    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String, nullable=False)
    disposition = Column(String, nullable=False)
    analyst_id = Column(String, nullable=False)
    model_version = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

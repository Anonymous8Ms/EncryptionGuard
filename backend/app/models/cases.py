from sqlalchemy import Column, String, DateTime, JSON, Float, Integer, func
from app.models.base import Base


class Case(Base):
    __tablename__ = "cases"
    id = Column(String, primary_key=True)
    merchant_id = Column(String, nullable=False)
    account_id = Column(String, nullable=False)
    risk_score = Column(Float, default=0.0)
    risk_level = Column(String, default="low")
    status = Column(String, default="open")
    recommended_action = Column(String, default="allow")
    evidence = Column(String, default="{}")
    graph_evidence = Column(String, default="{}")
    shap_values = Column(String, default="{}")
    model_version = Column(String)
    llm_summary = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String, nullable=False)
    event_id = Column(String, nullable=False)
    label = Column(String, nullable=False)
    analyst = Column(String, nullable=False)
    model_version = Column(String)
    created_at = Column(DateTime, server_default=func.now())

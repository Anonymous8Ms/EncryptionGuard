"""
EncryptionGuard v5 — Refund ORM model.
"""

from __future__ import annotations

from sqlalchemy import Column, Integer, String

from .base import Base


class Refund(Base):
    __tablename__ = "refunds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    refund_id = Column(String, unique=True, nullable=False, index=True)
    payment_id = Column(String, nullable=False, index=True)
    order_id = Column(String, nullable=False, index=True)
    amount_cents = Column(Integer, nullable=False)
    reason = Column(String, nullable=True)

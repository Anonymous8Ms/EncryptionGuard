"""
EncryptionGuard v5 — Payment ORM model.
"""

from __future__ import annotations

from sqlalchemy import Column, Integer, String

from .base import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    payment_id = Column(String, unique=True, nullable=False, index=True)
    order_id = Column(String, nullable=False, index=True)
    token_id = Column(String, nullable=True)
    amount_cents = Column(Integer, nullable=False)
    status = Column(String, default="captured")  # captured | refunded

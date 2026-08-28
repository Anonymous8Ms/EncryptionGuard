"""
EncryptionGuard v5 — Order ORM model.
"""

from __future__ import annotations

from sqlalchemy import Column, Float, Integer, String

from .base import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String, unique=True, nullable=False, index=True)
    account_id = Column(String, nullable=False, index=True)
    merchant_id = Column(String, nullable=False, index=True)
    device_id = Column(String, nullable=True)
    ip_id = Column(String, nullable=True)
    token_id = Column(String, nullable=True)
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String, default="USD")
    status = Column(String, default="pending")  # pending | completed | refunded

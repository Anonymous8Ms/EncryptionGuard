"""
EncryptionGuard v5 — SQLAlchemy base and session configuration.

Provides the declarative Base, engine, session factory, and a FastAPI
dependency (get_db) for database access.
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


# ── Database engine ──────────────────────────────────────────────────────────
# Reads DATABASE_URL from environment. Falls back to local SQLite for dev.

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./encryption_guard.db")

# SQLite needs check_same_thread; Postgres does not.
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Alias used by tests
TestingSessionLocal = SessionLocal


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

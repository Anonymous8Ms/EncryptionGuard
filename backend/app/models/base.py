"""
EncryptionGuard v5 — SQLAlchemy base and session configuration.

Provides the declarative Base, engine, session factory, and a FastAPI
dependency (get_db) for database access.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


# ── Default (production) engine ──────────────────────────────────────────────
# Override DATABASE_URL in .env for production; default is a local SQLite file
# so the app can start without Postgres during development / testing.

DEFAULT_DATABASE_URL = "sqlite:///./encryption_guard.db"

engine = create_engine(
    DEFAULT_DATABASE_URL,
    connect_args={"check_same_thread": False},  # needed for SQLite
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

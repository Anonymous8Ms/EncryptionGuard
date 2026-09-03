"""
EncryptionGuard v5 — SQLAlchemy base and session configuration.
"""

from __future__ import annotations

import logging
import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


def _build_engine():
    """Try PostgreSQL first; fall back to SQLite if unreachable."""
    db_url = os.getenv("DATABASE_URL", "")

    if db_url and db_url.startswith("postgresql"):
        try:
            eng = create_engine(db_url, pool_pre_ping=True, echo=False)
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Connected to PostgreSQL")
            return eng
        except Exception as e:
            logger.warning("PostgreSQL unreachable (%s), falling back to SQLite", e)

    sqlite_url = "sqlite:///./encryption_guard.db"
    logger.info("Using SQLite: %s", sqlite_url)
    return create_engine(
        sqlite_url,
        connect_args={"check_same_thread": False},
        echo=False,
    )


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
TestingSessionLocal = SessionLocal


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

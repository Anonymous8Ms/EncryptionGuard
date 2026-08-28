"""
Shared pytest fixtures for EncryptionGuard test suite.

Provides:
  - SQLite in-memory database engine + session
  - FastAPI TestClient with dependency overrides
  - Webhook fixture data loaders
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.models.base import Base, get_db

# ── SQLite in-memory test database ───────────────────────────────────────────

TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Yield a fresh database session for each test.

    Creates all tables before the test and drops them afterwards.
    """
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db: Session):
    """Yield a FastAPI TestClient with the test DB injected."""
    from fastapi.testclient import TestClient

    # Import the app — adjust path if your main app module differs
    try:
        from backend.app.main import app
    except ImportError:
        # If there's no main.py yet, create a minimal FastAPI app for testing
        from fastapi import FastAPI
        app = FastAPI()

    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Fixture data loaders ─────────────────────────────────────────────────────

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def webhook_order_paid_payload() -> dict:
    """Load the order.paid webhook fixture."""
    with open(FIXTURES_DIR / "webhook_order_paid.json") as f:
        return json.load(f)


@pytest.fixture
def webhook_refund_processed_payload() -> dict:
    """Load the refund.processed webhook fixture."""
    with open(FIXTURES_DIR / "webhook_refund_processed.json") as f:
        return json.load(f)

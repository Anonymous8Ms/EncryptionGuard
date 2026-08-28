"""
Shared test fixtures for EncryptionGuard v5 test suite.

Provides:
- SQLite in-memory test database (isolated per test session)
- SQLAlchemy session fixture (auto-rollback after each test)
- FastAPI TestClient fixture wired to the test DB
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from backend.app.main import app
from backend.app.models.base import DeclarativeBase, get_db


# ---------------------------------------------------------------------------
# SQLite in-memory engine — fresh per test module
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db() -> Session:
    """Create all tables, yield a session, then tear down."""
    DeclarativeBase.metadata.create_all(bind=engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        DeclarativeBase.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session):
    """FastAPI TestClient that overrides ``get_db`` with the test session."""

    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

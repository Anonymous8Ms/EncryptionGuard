"""
EncryptionGuard v5 — Application configuration.

Loads all settings from environment variables / .env file
using pydantic-settings for validation and type coercion.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration loaded once at import time."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Supabase ──────────────────────────────
    supabase_url: str = ""
    supabase_key: str = ""
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/encryption_guard"

    # ── Neo4j Aura ────────────────────────────
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4j"

    # ── Redis Cloud ───────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Xiaomi MiMo API ──────────────────────
    mimo_api_key: str = ""
    mimo_api_base: str = "https://api.mimo.xiaomi.com/v1"

    # ── Razorpay Test Mode ───────────────────
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""

    # ── App Settings ──────────────────────────
    app_env: str = "development"
    secret_key: str = "change-me"

    # ── ML Settings ───────────────────────────
    graph_ttl_days: int = 90
    scoring_p95_ms: int = 100

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


settings = Settings()


def get_settings() -> Settings:
    return settings

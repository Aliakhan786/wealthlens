"""Central configuration, loaded from environment variables / .env file."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    # Storage — SQLite by default so the project runs with zero setup.
    # Point at Postgres (Supabase / Neon / docker-compose) for production.
    database_url: str = f"sqlite:///{(ROOT_DIR / 'data' / 'wealthlens.db').as_posix()}"
    redis_url: str | None = None  # e.g. rediss://...upstash.io:6379 — falls back to in-memory cache

    # API
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    rate_limit: str = "120/minute"
    ai_rate_limit: str = "15/minute"

    # Pipeline
    history_years: int = 20
    live_interval_minutes: int = 2
    enable_scheduler: bool = True  # run the pipeline scheduler inside the API process
    offline_mode: bool = False  # force synthetic sample data (no network)

    # AI
    anthropic_api_key: str | None = None
    llm_model: str = "claude-opus-5-5"
    ai_cache_ttl_seconds: int = 6 * 3600

    # Monitoring
    sentry_dsn: str | None = None
    environment: str = "development"

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()

from typing import Literal

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    DATABASE_URL: str

    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str

    # App
    SECRET_KEY: str = "change-me-in-development"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    CORS_ORIGINS: list[str] = []

    # Crowd promotion: minimum distinct users required to promote a user tag to canonical
    CROWD_PROMOTION_THRESHOLD: int = 3
    # Genome embedding gate: minimum canonical tropes required before genome is embedded
    TROPE_THRESHOLD: int = 3
    # Review re-embed: only re-embed review stream when review count grows by this many
    REVIEW_EMBED_BATCH_SIZE: int = 5

    @computed_field
    @property
    def SYNC_DATABASE_URL(self) -> str:
        """Sync URL for Alembic (replaces asyncpg with psycopg2)."""
        return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


settings = Settings()

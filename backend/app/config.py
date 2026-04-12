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
    # Allowed CORS origins in staging/production.
    # Format: JSON list, e.g. CORS_ORIGINS=["https://myapp.com"]
    CORS_ORIGINS: list[str] = []

    @computed_field
    @property
    def SYNC_DATABASE_URL(self) -> str:
        """Sync URL for Alembic (replaces asyncpg with psycopg2)."""
        return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


settings = Settings()

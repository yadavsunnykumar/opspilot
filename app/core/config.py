from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="OPSPILOT_", extra="ignore")

    app_name: str = "OpsPilot"
    version: str = "0.1.0"
    environment: Literal["local", "ci", "staging", "production"] = "local"
    debug: bool = False
    api_v1_prefix: str = "/v1"
    cors_origins: list[str] = ["http://localhost:3000"]

    database_url: str = "postgresql+asyncpg://opspilot:opspilot@localhost:5432/opspilot"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()

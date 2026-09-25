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

    # Logging. JSON is what a log platform indexes; console is readable locally.
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_json: bool | None = None

    database_url: str = "postgresql+asyncpg://opspilot:opspilot@localhost:5432/opspilot"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"

    # Connection pool. Defaults suit one API process; raise pool_size only after
    # checking Postgres' own max_connections, which every process shares.
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def use_json_logs(self) -> bool:
        """JSON everywhere except local development, unless set explicitly."""
        if self.log_json is not None:
            return self.log_json
        return self.environment != "local"

    @property
    def sync_database_url(self) -> str:
        """Same database, synchronous driver. Used by tooling that cannot await."""
        return self.database_url.replace("+asyncpg", "+psycopg")


@lru_cache
def get_settings() -> Settings:
    return Settings()

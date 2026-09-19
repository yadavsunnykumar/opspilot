from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="OPSPILOT_", extra="ignore")

    app_name: str = "OpsPilot"
    environment: Literal["local", "ci", "staging", "production"] = "local"
    debug: bool = False
    api_v1_prefix: str = "/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()

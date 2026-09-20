from app.core.config import Settings


def test_datastore_defaults_are_local() -> None:
    settings = Settings(_env_file=None)

    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert settings.redis_url.startswith("redis://")
    assert settings.qdrant_url.startswith("http://")
    assert settings.is_production is False


def test_environment_can_be_overridden(monkeypatch) -> None:
    monkeypatch.setenv("OPSPILOT_ENVIRONMENT", "production")

    settings = Settings(_env_file=None)

    assert settings.is_production is True

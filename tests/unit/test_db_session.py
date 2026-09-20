from collections.abc import AsyncIterator

import pytest

from app.core.config import Settings
from app.db import session as db_session
from app.db.base import Base


@pytest.fixture(autouse=True)
async def _clean_engine() -> AsyncIterator[None]:
    await db_session.dispose_engine()
    yield
    await db_session.dispose_engine()


def test_engine_is_not_available_before_init() -> None:
    with pytest.raises(RuntimeError, match="not initialised"):
        db_session.get_engine()


async def test_init_engine_is_idempotent() -> None:
    settings = Settings(_env_file=None)

    first = db_session.init_engine(settings)
    second = db_session.init_engine(settings)

    assert first is second
    assert db_session.get_session_factory() is not None


async def test_engine_uses_pool_settings_from_config() -> None:
    settings = Settings(_env_file=None, db_pool_size=7, db_max_overflow=3)

    engine = db_session.init_engine(settings)

    assert engine.pool.size() == 7
    assert engine.url.drivername == "postgresql+asyncpg"


def test_sync_database_url_swaps_the_driver() -> None:
    settings = Settings(_env_file=None)

    assert settings.sync_database_url.startswith("postgresql+psycopg://")
    assert "asyncpg" not in settings.sync_database_url


def test_constraint_naming_convention_is_applied() -> None:
    convention = Base.metadata.naming_convention

    assert convention["pk"] == "pk_%(table_name)s"
    assert convention["fk"].startswith("fk_")
    assert convention["uq"] == "uq_%(table_name)s_%(column_0_name)s"

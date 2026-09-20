"""Integration tests that need a live Postgres (docker compose up).

They are skipped automatically when the database is unreachable, so `make test`
still passes on a machine with no stack running.
"""

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings
from app.db.session import check_database, dispose_engine, get_session_factory, init_engine

pytestmark = pytest.mark.integration


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    await dispose_engine()
    settings = Settings(_env_file=None)
    engine = init_engine(settings)
    try:
        await check_database()
    except Exception as exc:  # database not running
        await dispose_engine()
        pytest.skip(f"Postgres is not reachable: {exc}")
    yield engine
    await dispose_engine()


async def test_health_check_passes_against_live_database(engine: AsyncEngine) -> None:
    await check_database()


async def test_session_can_query(engine: AsyncEngine) -> None:
    factory = get_session_factory()

    async with factory() as session:
        result = await session.execute(text("SELECT 1 AS one"))

        assert result.scalar_one() == 1


async def test_gen_random_uuid_is_available(engine: AsyncEngine) -> None:
    """The UUID primary key default relies on pgcrypto/pg13+ gen_random_uuid()."""
    factory = get_session_factory()

    async with factory() as session:
        result = await session.execute(text("SELECT gen_random_uuid()"))

        assert result.scalar_one() is not None

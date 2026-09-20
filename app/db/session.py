"""Async engine, session factory and the request-scoped session dependency."""

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.database_url,
        echo=settings.db_echo,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
        # Checks a pooled connection is still alive before handing it out, so a
        # database restart or an idle timeout surfaces as a retry, not a 500.
        pool_pre_ping=True,
    )


def init_engine(settings: Settings | None = None) -> AsyncEngine:
    """Create the process-wide engine and session factory. Called once at startup."""
    global _engine, _session_factory

    settings = settings or get_settings()
    if _engine is None:
        _engine = create_engine(settings)
        _session_factory = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            # Keep attributes loaded after commit, so a response can still read
            # the object it just saved without issuing another query.
            expire_on_commit=False,
            autoflush=False,
        )
    return _engine


async def dispose_engine() -> None:
    """Close every pooled connection. Called once at shutdown."""
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError("Database engine is not initialised. Call init_engine() first.")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Session factory is not initialised. Call init_engine() first.")
    return _session_factory


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding one session per request.

    The session is committed when the handler returns normally and rolled back
    if it raises, so a half-finished write never reaches the database.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_database() -> None:
    """Health check: fail loudly if the database cannot answer a trivial query."""
    engine = get_engine()
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))

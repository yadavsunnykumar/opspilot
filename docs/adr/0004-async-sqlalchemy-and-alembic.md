# 4. Use async SQLAlchemy 2.0 with Alembic migrations

Date: 2026-09-20

## Status
Accepted

## Context
OpsPilot is an async FastAPI service whose endpoints mostly wait on I/O. A
synchronous database driver would block the event loop on every query, so a slow
query would stall unrelated requests. The schema also has to evolve safely across
environments, with every change reviewable and reversible.

## Decision
SQLAlchemy 2.0 with the asyncpg driver, `Mapped[...]` typed models, and Alembic
for migrations. One engine and one `async_sessionmaker` are created per process
in the app's lifespan; a FastAPI dependency yields one session per request,
committing on success and rolling back on any exception.

The metadata carries an explicit constraint naming convention, and Alembic runs
with `compare_type=True` and `compare_server_default=True`.

## Alternatives
- Sync SQLAlchemy with a thread pool: simpler, but wastes the async model and
  caps throughput at the pool size.
- SQLModel: less boilerplate, thinner async and migration story.
- Tortoise or Piccolo: async-native, far smaller ecosystem.

## Consequences
Queries no longer block the event loop. Named constraints mean migrations can
drop and alter them reliably, and downgrades actually work. Every model must be
imported in `app/db/models/__init__.py` or autogenerate will not see it — this is
the single most common way to lose a table in a migration.

Tests that need a real database are marked `integration` and skip themselves when
Postgres is unreachable, so `make test` passes with no stack running.

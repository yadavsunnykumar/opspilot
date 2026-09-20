"""Model package.

Import every model module here. Alembic imports this package so that
`Base.metadata` is fully populated before autogenerate compares it against the
database; a model that is never imported is invisible to autogenerate and gets
silently dropped from migrations.
"""

from app.db.base import Base

__all__ = ["Base"]

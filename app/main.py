"""Application factory.

`create_app` builds a fully configured FastAPI instance. Tests call it directly
so each test gets a clean app; `app` at the bottom is what uvicorn serves.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.health import clear_checks, register_check
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestContextMiddleware
from app.db.session import check_database, dispose_engine, init_engine

# Probes are called every few seconds by the orchestrator; logging them would
# bury real traffic.
QUIET_PATHS = frozenset({"/health/live", "/health/ready", "/metrics"})

DESCRIPTION = """
OpsPilot ingests alerts from monitoring tools, groups them into incidents, and
runs an AI agent that investigates each one against your runbooks and past
postmortems. Remediations are proposed, never applied without human approval.
"""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Open shared resources once per process, and close them on shutdown.

    The connection pool belongs here rather than at import time: creating it per
    request would exhaust Postgres, and creating it at import would make tests
    and CLI tools open sockets just by importing the module.
    """
    settings = get_settings()
    logger = get_logger("app.lifespan")
    init_engine(settings)
    register_check("database", check_database)
    logger.info(
        "application_started",
        environment=settings.environment,
        version=settings.version,
    )
    try:
        yield
    finally:
        clear_checks()
        await dispose_engine()
        logger.info("application_stopped")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(level=settings.log_level, json_format=settings.use_json_logs)

    app = FastAPI(
        title=settings.app_name,
        description=DESCRIPTION,
        version=settings.version,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
        openapi_url=None if settings.is_production else "/openapi.json",
    )

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Added last, so it wraps every other middleware and sees the final status.
    app.add_middleware(RequestContextMiddleware, quiet_paths=QUIET_PATHS)

    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()

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
from app.core.health import clear_checks

DESCRIPTION = """
OpsPilot ingests alerts from monitoring tools, groups them into incidents, and
runs an AI agent that investigates each one against your runbooks and past
postmortems. Remediations are proposed, never applied without human approval.
"""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start and stop shared resources.

    Connection pools and the background scheduler are opened here in later
    sprints, so they are created once per process rather than per request.
    """
    yield
    clear_checks()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

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

    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()

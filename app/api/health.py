"""Liveness and readiness probes.

These sit outside the versioned API because orchestrators, not clients, call
them. Liveness answers "is the process running"; readiness answers "can it
serve traffic", which means its dependencies must be reachable too.
"""

from fastapi import APIRouter, Response, status

from app.core.config import get_settings
from app.core.health import run_checks
from app.schemas.health import HealthReport

router = APIRouter(tags=["health"])


@router.get("/health/live", summary="Liveness probe")
async def live() -> dict[str, str]:
    """Return ok as long as the process can serve a request."""
    return {"status": "ok"}


@router.get(
    "/health/ready",
    summary="Readiness probe",
    response_model=HealthReport,
    responses={503: {"description": "One or more dependencies are unavailable"}},
)
async def ready(response: Response) -> HealthReport:
    """Run every registered dependency check and report the aggregate."""
    settings = get_settings()
    report = await run_checks(version=settings.version, environment=settings.environment)
    if report.status != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return report

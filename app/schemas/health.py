from typing import Literal

from pydantic import BaseModel, Field

HealthStatus = Literal["ok", "degraded", "unavailable"]


class ComponentHealth(BaseModel):
    """Result of one dependency check."""

    status: HealthStatus
    latency_ms: float | None = None
    detail: str | None = None


class HealthReport(BaseModel):
    """Aggregate readiness of the service and its dependencies."""

    status: HealthStatus
    version: str
    environment: str
    checks: dict[str, ComponentHealth] = Field(default_factory=dict)

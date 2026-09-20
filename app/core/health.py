"""Dependency health checks behind a small registry.

Each dependency (database, cache, vector store) registers an async callable
that returns a `ComponentHealth`. The readiness endpoint runs them
concurrently, so adding a dependency later means registering one function
rather than editing the endpoint.
"""

import asyncio
import time
from collections.abc import Awaitable, Callable

from app.schemas.health import ComponentHealth, HealthReport, HealthStatus

CheckFn = Callable[[], Awaitable[None]]

_checks: dict[str, CheckFn] = {}

# How long a single dependency check may take before it counts as unavailable.
CHECK_TIMEOUT_SECONDS = 2.0


def register_check(name: str, check: CheckFn) -> None:
    """Register a dependency check. Raising inside `check` means unhealthy."""
    _checks[name] = check


def clear_checks() -> None:
    """Drop every registered check. Used by tests and app teardown."""
    _checks.clear()


def registered_checks() -> tuple[str, ...]:
    return tuple(_checks)


async def _run_check(name: str, check: CheckFn) -> tuple[str, ComponentHealth]:
    started = time.perf_counter()
    try:
        await asyncio.wait_for(check(), timeout=CHECK_TIMEOUT_SECONDS)
    except TimeoutError:
        return name, ComponentHealth(
            status="unavailable",
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            detail=f"timed out after {CHECK_TIMEOUT_SECONDS}s",
        )
    except Exception as exc:
        # Any failure means the dependency is not usable right now.
        return name, ComponentHealth(
            status="unavailable",
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            detail=f"{type(exc).__name__}: {exc}",
        )
    return name, ComponentHealth(
        status="ok",
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
    )


async def run_checks(*, version: str, environment: str) -> HealthReport:
    """Run every registered check concurrently and aggregate the result."""
    results = await asyncio.gather(*(_run_check(name, check) for name, check in _checks.items()))
    checks = dict(results)
    overall: HealthStatus = (
        "unavailable" if any(c.status != "ok" for c in checks.values()) else "ok"
    )
    return HealthReport(status=overall, version=version, environment=environment, checks=checks)

import os

import pytest
from httpx import AsyncClient

from app.core.health import register_check


async def test_liveness_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_readiness_is_ok_when_no_dependencies_registered(client: AsyncClient) -> None:
    response = await client.get("/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"] == {}
    assert body["environment"] == os.getenv("OPSPILOT_ENVIRONMENT", "local")


async def test_readiness_reports_ok_check(client: AsyncClient) -> None:
    async def healthy() -> None:
        return None

    register_check("database", healthy)

    response = await client.get("/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"]["database"]["status"] == "ok"
    assert body["checks"]["database"]["latency_ms"] >= 0


async def test_readiness_returns_503_when_a_dependency_fails(client: AsyncClient) -> None:
    async def broken() -> None:
        raise ConnectionError("connection refused")

    register_check("redis", broken)

    response = await client.get("/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["checks"]["redis"]["status"] == "unavailable"
    assert "connection refused" in body["checks"]["redis"]["detail"]


@pytest.mark.parametrize("path", ["/health/live", "/health/ready"])
async def test_probes_are_not_versioned(client: AsyncClient, path: str) -> None:
    versioned = await client.get(f"/v1{path}")

    assert versioned.status_code == 404
    assert (await client.get(path)).status_code in {200, 503}

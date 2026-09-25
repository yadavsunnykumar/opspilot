import json
import logging
import uuid

import pytest
import structlog
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.core.errors import NotFoundError
from app.main import create_app


@pytest.fixture(autouse=True)
def _reset_structlog() -> None:
    yield
    structlog.reset_defaults()
    logging.getLogger("uvicorn.access").disabled = False


async def test_response_carries_a_generated_request_id(client: AsyncClient) -> None:
    response = await client.get("/health/live")

    request_id = response.headers["x-request-id"]
    assert uuid.UUID(request_id)


async def test_inbound_request_id_is_preserved(client: AsyncClient) -> None:
    response = await client.get("/health/live", headers={"X-Request-ID": "trace-abc"})

    assert response.headers["x-request-id"] == "trace-abc"


async def test_each_request_gets_a_distinct_id(client: AsyncClient) -> None:
    first = await client.get("/health/live")
    second = await client.get("/health/live")

    assert first.headers["x-request-id"] != second.headers["x-request-id"]


async def test_problem_detail_includes_the_request_id(client: AsyncClient) -> None:
    response = await client.get("/v1/nope", headers={"X-Request-ID": "trace-xyz"})

    assert response.status_code == 404
    assert response.json()["request_id"] == "trace-xyz"


async def test_request_is_logged_with_status_and_duration(
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = create_app(Settings(_env_file=None, environment="ci", log_json=True))

    @app.get("/thing")
    async def thing() -> dict[str, str]:
        return {"ok": "yes"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.get("/thing", headers={"X-Request-ID": "trace-1"})

    events = [
        json.loads(line)
        for line in capsys.readouterr().out.strip().splitlines()
        if line.startswith("{")
    ]
    finished = next(e for e in events if e["event"] == "request_finished")

    assert finished["request_id"] == "trace-1"
    assert finished["status_code"] == 200
    assert finished["path"] == "/thing"
    assert finished["duration_ms"] >= 0


async def test_failing_handler_logs_the_error_with_its_request_id(
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = create_app(Settings(_env_file=None, environment="ci", log_json=True))

    @app.get("/broken")
    async def broken() -> None:
        raise NotFoundError("gone")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/broken", headers={"X-Request-ID": "trace-2"})

    assert response.status_code == 404
    events = [
        json.loads(line)
        for line in capsys.readouterr().out.strip().splitlines()
        if line.startswith("{")
    ]
    finished = next(e for e in events if e["event"] == "request_finished")
    assert finished["status_code"] == 404
    assert finished["request_id"] == "trace-2"


async def test_health_probes_are_not_logged(capsys: pytest.CaptureFixture[str]) -> None:
    app = create_app(Settings(_env_file=None, environment="ci", log_json=True))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.get("/health/live")

    assert "request_finished" not in capsys.readouterr().out

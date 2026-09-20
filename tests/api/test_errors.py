from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.errors import ConflictError, NotFoundError
from app.main import create_app


async def test_unknown_route_returns_problem_detail(client: AsyncClient) -> None:
    response = await client.get("/v1/does-not-exist")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["status"] == 404
    assert body["instance"] == "/v1/does-not-exist"


async def test_app_error_maps_to_its_status_and_type() -> None:
    app: FastAPI = create_app()

    @app.get("/boom")
    async def boom() -> None:
        raise NotFoundError("Incident 42 does not exist", resource="incident")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/boom")

    assert response.status_code == 404
    body = response.json()
    assert body["title"] == "Resource not found"
    assert body["detail"] == "Incident 42 does not exist"
    assert body["type"].endswith("/not-found")
    assert body["resource"] == "incident"


async def test_conflict_error_uses_409() -> None:
    app: FastAPI = create_app()

    @app.get("/conflict")
    async def conflict() -> None:
        raise ConflictError("Incident already open")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/conflict")

    assert response.status_code == 409
    assert response.json()["detail"] == "Incident already open"


async def test_validation_error_lists_fields() -> None:
    app: FastAPI = create_app()

    @app.get("/items")
    async def items(limit: int) -> dict[str, int]:
        return {"limit": limit}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/items", params={"limit": "not-a-number"})

    assert response.status_code == 422
    body = response.json()
    assert body["title"] == "Invalid request"
    assert body["errors"][0]["field"] == "limit"

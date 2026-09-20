from app.core.config import Settings
from app.main import create_app


def test_docs_are_exposed_outside_production() -> None:
    app = create_app(Settings(_env_file=None, environment="local"))

    assert app.docs_url == "/docs"
    assert app.openapi_url == "/openapi.json"


def test_docs_are_hidden_in_production() -> None:
    app = create_app(Settings(_env_file=None, environment="production"))

    assert app.docs_url is None
    assert app.redoc_url is None
    assert app.openapi_url is None


def test_openapi_schema_builds() -> None:
    app = create_app(Settings(_env_file=None))

    schema = app.openapi()

    assert schema["info"]["title"] == "OpsPilot"
    assert "/health/live" in schema["paths"]
    assert "/health/ready" in schema["paths"]

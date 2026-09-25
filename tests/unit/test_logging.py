import json
import logging

import pytest
import structlog

from app.core.config import Settings
from app.core.context import request_id_var, tenant_id_var
from app.core.logging import REDACTED, configure_logging, get_logger


@pytest.fixture(autouse=True)
def _reset_structlog() -> None:
    structlog.reset_defaults()
    yield
    structlog.reset_defaults()
    logging.getLogger("uvicorn.access").disabled = False


def _emit(capsys: pytest.CaptureFixture[str], **fields: object) -> dict[str, object]:
    configure_logging(level="INFO", json_format=True)
    get_logger("test").info("something_happened", **fields)
    line = capsys.readouterr().out.strip().splitlines()[-1]
    parsed: dict[str, object] = json.loads(line)
    return parsed


def test_log_line_is_json_with_standard_fields(capsys: pytest.CaptureFixture[str]) -> None:
    entry = _emit(capsys, incident_id="inc-1")

    assert entry["event"] == "something_happened"
    assert entry["level"] == "info"
    assert entry["incident_id"] == "inc-1"
    assert "timestamp" in entry


def test_request_context_is_attached_automatically(
    capsys: pytest.CaptureFixture[str],
) -> None:
    token = request_id_var.set("req-123")
    tenant_token = tenant_id_var.set("acme")
    try:
        entry = _emit(capsys)
    finally:
        request_id_var.reset(token)
        tenant_id_var.reset(tenant_token)

    assert entry["request_id"] == "req-123"
    assert entry["tenant_id"] == "acme"


def test_sensitive_fields_are_redacted(capsys: pytest.CaptureFixture[str]) -> None:
    entry = _emit(
        capsys,
        authorization="Bearer supersecret",
        headers={"X-API-Key": "op_live_abc", "user-agent": "curl"},
    )

    assert entry["authorization"] == REDACTED
    assert entry["headers"] == {"X-API-Key": REDACTED, "user-agent": "curl"}
    assert "supersecret" not in json.dumps(entry)
    assert "op_live_abc" not in json.dumps(entry)


def test_console_format_is_not_json(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(level="INFO", json_format=False)

    get_logger("test").info("readable_line", key="value")

    output = capsys.readouterr().out
    assert "readable_line" in output
    with pytest.raises(json.JSONDecodeError):
        json.loads(output.strip().splitlines()[-1])


def test_local_environment_defaults_to_console_logs() -> None:
    assert Settings(_env_file=None, environment="local").use_json_logs is False
    assert Settings(_env_file=None, environment="production").use_json_logs is True
    assert Settings(_env_file=None, environment="local", log_json=True).use_json_logs is True

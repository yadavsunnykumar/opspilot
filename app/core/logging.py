"""Structured logging.

Every log line is an event with fields, not a sentence. In production the
renderer emits one JSON object per line, which a log platform can index and
filter — `tenant_id="acme" AND status_code>=500` is a query rather than a regex.
Locally it renders coloured key-value pairs, which are easier to read.

Logs from libraries (uvicorn, SQLAlchemy, Alembic) are routed through the same
pipeline, so the output is uniform no matter who emitted it.
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from app.core.context import current_context

# Header values that must never reach the logs.
REDACTED = "[redacted]"
SENSITIVE_KEYS = frozenset(
    {
        "authorization",
        "x-api-key",
        "x-opspilot-signature",
        "cookie",
        "set-cookie",
        "password",
        "token",
        "secret",
        "api_key",
    }
)


def add_request_context(_logger: Any, _method_name: str, event_dict: EventDict) -> EventDict:
    """Attach request id, tenant and user to every line emitted in a request."""
    for key, value in current_context().items():
        event_dict.setdefault(key, value)
    return event_dict


def redact_sensitive(_logger: Any, _method_name: str, event_dict: EventDict) -> EventDict:
    """Replace the value of any sensitive key, at the top level or in a dict."""
    for key, value in list(event_dict.items()):
        if key.lower() in SENSITIVE_KEYS:
            event_dict[key] = REDACTED
        elif isinstance(value, dict):
            event_dict[key] = {
                k: (REDACTED if k.lower() in SENSITIVE_KEYS else v) for k, v in value.items()
            }
    return event_dict


def configure_logging(*, level: str = "INFO", json_format: bool = True) -> None:
    """Configure structlog and the standard library to share one pipeline."""
    shared: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        add_request_context,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        redact_sensitive,
    ]

    renderer: Processor = (
        structlog.processors.JSONRenderer()
        if json_format
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    # structlog does not render here. It hands the event dict to the stdlib
    # handler below, which renders exactly once. Rendering in both places is
    # what produces log lines whose "event" is itself a JSON string.
    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelNamesMapping()[level.upper()]
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        # Applied only to records from libraries that never touched structlog,
        # so their lines end up with the same fields as ours.
        foreign_pre_chain=shared,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            renderer,
        ],
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())

    # uvicorn installs its own handlers; drop them so lines are not printed twice.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True

    # The access log is replaced by our own request_finished event.
    logging.getLogger("uvicorn.access").disabled = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger

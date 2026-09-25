"""Request context middleware.

Written as raw ASGI rather than Starlette's `BaseHTTPMiddleware`, which wraps
the response in a queue: that breaks streaming responses (the SSE incident feed
in a later sprint) and changes how background tasks and exceptions propagate.
A plain ASGI middleware just passes the messages through.
"""

import time
import uuid
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from starlette.datastructures import Headers, MutableHeaders

from app.core.context import request_id_var
from app.core.logging import get_logger

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

REQUEST_ID_HEADER = "x-request-id"

logger = get_logger("app.request")


class RequestContextMiddleware:
    """Assign every request an id, log its outcome, and echo the id back.

    The id is taken from the inbound `X-Request-ID` when a gateway or client
    supplied one, so a single identifier follows a request across services.
    """

    def __init__(self, app: ASGIApp, *, quiet_paths: frozenset[str] = frozenset()) -> None:
        self.app = app
        self.quiet_paths = quiet_paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        request_id = headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        token = request_id_var.set(request_id)

        path: str = scope.get("path", "")
        method: str = scope.get("method", "")
        quiet = path in self.quiet_paths
        started = time.perf_counter()
        status_code = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                MutableHeaders(scope=message).append("X-Request-ID", request_id)
            await send(message)

        if not quiet:
            logger.info("request_started", method=method, path=path)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.exception(
                "request_failed",
                method=method,
                path=path,
                duration_ms=duration_ms,
            )
            raise
        else:
            if not quiet:
                duration_ms = round((time.perf_counter() - started) * 1000, 2)
                logger.info(
                    "request_finished",
                    method=method,
                    path=path,
                    status_code=status_code,
                    duration_ms=duration_ms,
                )
        finally:
            request_id_var.reset(token)

"""Application errors and RFC 7807 problem-detail responses.

Every error leaving the API has the same JSON shape, so clients never have to
guess. Services raise the exceptions below; the handlers registered in
`register_exception_handlers` turn them into responses.
"""

from typing import Any, cast

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.context import get_request_id

PROBLEM_CONTENT_TYPE = "application/problem+json"

# Spelled out rather than imported: Starlette renamed its 422 constant, and the
# old name emits a DeprecationWarning on newer versions.
HTTP_422_UNPROCESSABLE = 422


class AppError(Exception):
    """Base class for errors that map to a known HTTP status."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    title: str = "Internal server error"
    error_type: str = "about:blank"

    def __init__(self, detail: str | None = None, **extra: Any) -> None:
        self.detail = detail or self.title
        self.extra = extra
        super().__init__(self.detail)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    title = "Resource not found"
    error_type = "https://opspilot.dev/errors/not-found"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    title = "Conflict"
    error_type = "https://opspilot.dev/errors/conflict"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    title = "Not authenticated"
    error_type = "https://opspilot.dev/errors/unauthorized"


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    title = "Not permitted"
    error_type = "https://opspilot.dev/errors/forbidden"


class RateLimitedError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    title = "Rate limit exceeded"
    error_type = "https://opspilot.dev/errors/rate-limited"


class ServiceUnavailableError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    title = "Service unavailable"
    error_type = "https://opspilot.dev/errors/service-unavailable"


def problem_response(
    *,
    status_code: int,
    title: str,
    detail: str,
    instance: str,
    error_type: str = "about:blank",
    headers: dict[str, str] | None = None,
    **extra: Any,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": error_type,
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": instance,
    }
    request_id = get_request_id()
    if request_id is not None:
        body["request_id"] = request_id
    body.update({k: v for k, v in extra.items() if v is not None})
    return JSONResponse(
        status_code=status_code,
        content=body,
        media_type=PROBLEM_CONTENT_TYPE,
        headers=headers,
    )


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    error = cast(AppError, exc)
    return problem_response(
        status_code=error.status_code,
        title=error.title,
        detail=error.detail,
        instance=request.url.path,
        error_type=error.error_type,
        **error.extra,
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    error = cast(StarletteHTTPException, exc)
    headers = dict(error.headers) if error.headers else None
    return problem_response(
        status_code=error.status_code,
        title=str(error.detail),
        detail=str(error.detail),
        instance=request.url.path,
        headers=headers,
    )


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    error = cast(RequestValidationError, exc)
    errors = [
        {
            "field": ".".join(str(part) for part in item["loc"][1:]) or str(item["loc"][0]),
            "message": item["msg"],
        }
        for item in error.errors()
    ]
    return problem_response(
        status_code=HTTP_422_UNPROCESSABLE,
        title="Invalid request",
        detail="The request body or parameters failed validation.",
        instance=request.url.path,
        error_type="https://opspilot.dev/errors/validation",
        errors=errors,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

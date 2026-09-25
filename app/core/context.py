"""Request-scoped context.

`contextvars` carry values down an async call stack without threading them
through every function signature. A value set at the start of a request is
visible to any code that request awaits, and is isolated from other requests
running concurrently on the same worker.
"""

from contextvars import ContextVar, Token
from typing import Any

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
tenant_id_var: ContextVar[str | None] = ContextVar("tenant_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)


def get_request_id() -> str | None:
    return request_id_var.get()


def get_tenant_id() -> str | None:
    return tenant_id_var.get()


def get_user_id() -> str | None:
    return user_id_var.get()


def set_tenant_id(tenant_id: str | None) -> Token[str | None]:
    """Bind the tenant for the rest of this request. Auth calls this later."""
    return tenant_id_var.set(tenant_id)


def set_user_id(user_id: str | None) -> Token[str | None]:
    return user_id_var.set(user_id)


def current_context() -> dict[str, Any]:
    """Every bound value that is set, ready to attach to a log line."""
    context = {
        "request_id": request_id_var.get(),
        "tenant_id": tenant_id_var.get(),
        "user_id": user_id_var.get(),
    }
    return {key: value for key, value in context.items() if value is not None}

# 5. Log structured events with a request id on every line

Date: 2026-09-25

## Status
Accepted

## Context
OpsPilot spans an API process and a worker process, and one incident produces
log lines in both. Free-text logs can only be searched with regular expressions,
and without a shared identifier there is no way to gather the lines belonging to
one request or one incident.

## Decision
structlog renders every line as a JSON object outside local development, where
it renders readable key-value pairs instead. A raw-ASGI middleware assigns each
request an id — reusing an inbound `X-Request-ID` when a caller supplied one —
stores it in a `contextvar`, echoes it in the response header, and logs
`request_started` and `request_finished` with method, path, status and duration.

A processor copies the request id, tenant id and user id onto every line emitted
during that request, and another replaces the value of sensitive keys such as
`authorization` and `x-api-key` with `[redacted]`. Standard-library loggers are
routed through the same pipeline, so library output matches ours. Health probes
are excluded from request logging.

## Alternatives
- `logging` with a JSON formatter: no context propagation, so every call site
  would have to pass the request id by hand.
- Starlette's `BaseHTTPMiddleware`: convenient, but it buffers responses through
  a queue, which breaks the SSE incident stream planned for Sprint 6.

## Consequences
Support questions become queries: filter on `request_id` to get one request's
full story across processes. The same id appears in the response body of every
error, so a user can quote it. Anything logged under a sensitive key is redacted
by default rather than by remembering at each call site. Every new dependency
must add its own context key to `app/core/context.py` to be logged automatically.

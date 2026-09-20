# 3. Return errors as RFC 7807 problem details

Date: 2026-09-20

## Status
Accepted

## Context
FastAPI's default error body is `{"detail": ...}`, where `detail` is sometimes a
string and sometimes a list of validation objects. Clients then need different
parsing per status code, and there is nowhere to attach context such as which
tenant or resource was involved.

## Decision
Every error response uses `application/problem+json` (RFC 7807) with the fields
`type`, `title`, `status`, `detail` and `instance`, plus optional extras such as
`errors` for validation failures. Services raise subclasses of `AppError`
(`NotFoundError`, `ConflictError`, `RateLimitedError`, and so on); handlers
registered on the app translate those, Starlette's `HTTPException` and
`RequestValidationError` into that one shape.

## Alternatives
- Keep FastAPI's default shape: less code, but inconsistent and not extensible.
- A bespoke envelope (`{"error": {...}}`): equivalent work, no standard behind it.

## Consequences
Clients parse one shape for every failure. Business logic raises domain errors
without importing FastAPI, which keeps the service layer framework-free.
Handlers are the single place where status codes are decided.

# 2. Run the local development stack in Docker Compose

Date: 2026-09-19

## Status
Accepted

## Context
OpsPilot depends on three stateful services: PostgreSQL (system of record),
Redis (queue, cache, pub/sub) and Qdrant (vector store). Installing these
natively differs per machine and makes CI and local development drift apart.

## Decision
A single `docker-compose.yml` runs Postgres 16, Redis 7 and Qdrant 1.12 plus the
API container. Postgres and Redis declare healthchecks, and the API waits for
`service_healthy` so it never starts against a database that is not accepting
connections. Data lives in named volumes so it survives a restart.

The Dockerfile is multi-stage: `builder` resolves dependencies with uv, `dev`
adds development dependencies and is what Compose builds, and `runtime` is a slim
non-root image for staging and production.

## Alternatives
- Native installs via Homebrew: fast, but versions drift between machines.
- pgvector instead of Qdrant: one less service, but weaker filtering and payload
  support. Revisit in the RAG sprint (see NFR and FR-KB-03).

## Consequences
`make up` gives every contributor an identical stack. Docker Desktop becomes a
prerequisite for local development. Image size stays small in production because
development dependencies never reach the `runtime` stage.

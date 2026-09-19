# OpsPilot

AI incident-response platform built with FastAPI, LangGraph and RAG.
Alerts are deduplicated into incidents, investigated by an AI agent using
runbooks and past postmortems, and fixes are applied only after human approval.

## Quick start

Requirements: Python 3.12+, [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env
make install     # install deps and git hooks
make run         # http://localhost:8000/docs
make check       # lint, type check, tests
```

## Project layout

```
app/
  api/v1/         routers (thin)
  core/           config, security, logging
  db/             session, models
  schemas/        Pydantic models
  repositories/   DB access (tenant-scoped)
  services/       business logic
  ingestion/      webhook adapters, fingerprinting
  agents/         LangGraph graph, nodes, tools, prompts
  rag/            chunking, embeddings, retrieval
  llm/            LLM gateway
  workers/        background jobs
  observability/  tracing, metrics
tests/            unit, integration, api, evals, load
docs/adr/         architecture decision records
```

## Status
Sprint 1 — Foundation (in progress)

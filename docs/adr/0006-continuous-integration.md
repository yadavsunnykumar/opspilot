# 6. Run lint, types, tests and an image build on every pull request

Date: 2026-09-25

## Status
Accepted

## Context
Every change reaches `develop` through a pull request, and the project's
definition of done requires that formatting, typing and tests all pass. Checks
that only run on a laptop get skipped under time pressure, and "works on my
machine" differences appear later in staging.

## Decision
A GitHub Actions workflow runs on every push to `main` or `develop` and on every
pull request targeting them, in three parallel jobs:

- **quality** — `ruff check`, `ruff format --check` and `mypy`.
- **test** — Postgres and Redis service containers, `alembic upgrade head`, then
  the full pytest suite with coverage. The integration tests that skip locally
  actually execute here.
- **build** — builds the Dockerfile's `runtime` stage and imports the app inside
  the resulting image.

Runs are cancelled when a newer commit arrives on the same branch, and uv's
cache is keyed on `uv.lock`.

## Alternatives
- One sequential job: simpler, but a lint typo would be reported only after the
  slowest step had finished.
- `docker compose up` in CI instead of service containers: reuses the local
  file, but is slower and gives no health-gating of the runner's steps.

## Consequences
A pull request cannot be merged with broken formatting, a type error, a failing
test or a migration that does not apply. `uv sync --frozen` means CI fails if
`uv.lock` and `pyproject.toml` disagree, which keeps the lockfile honest.
Security scanning (Bandit, pip-audit, Trivy) is added to this same workflow in
Sprint 8, and branch protection on `develop` is what makes the checks mandatory.

.PHONY: install run lint format typecheck test check up down logs ps reset db-shell redis-cli

install:
	uv sync
	uv run pre-commit install

run:
	uv run uvicorn app.main:app --reload

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

typecheck:
	uv run mypy

test:
	uv run pytest --cov --cov-report=term-missing

check: lint typecheck test

# --- Local stack -------------------------------------------------------------

up:
	docker compose up -d --build
	docker compose ps

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

reset:
	docker compose down -v

db-shell:
	docker compose exec postgres psql -U opspilot -d opspilot

redis-cli:
	docker compose exec redis redis-cli

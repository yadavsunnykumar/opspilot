.PHONY: install run lint format typecheck test check

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

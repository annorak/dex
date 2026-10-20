.PHONY: check

check:
	uv run --locked ruff check --no-cache .
	uv run --locked pyright
	uv run --locked lint-imports --no-cache --no-logo
	uv run --locked python -B scripts/check_core.py
	uv run --locked python -B scripts/check_secrets.py
	uv run --locked pytest -vv -s
	uv run --locked dex --help

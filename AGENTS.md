# Development

Use Python 3.12 and uv 0.11.31.

Install the locked development environment:

```sh
uv sync --locked
```

Run the repository checks:

```sh
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pyright
uv run --locked pytest
uv run --locked python -m dex --help
uv build
```

# dex

Python 3.12 CLI scaffold for dex.

Install uv 0.11.31, then set up the locked development environment:

```sh
uv sync --locked
uv run --locked python -m dex --help
```

`run`, `measure`, and `verify-package <package>` are unimplemented command stubs.
They print an error to stderr and exit with status 1. Help exits successfully.

See [AGENTS.md](AGENTS.md) for the development and verification commands.

# dex

dex turns a company's operating procedures into deterministic software. oak, dex's agent, reads the procedure documents and the company's history, breaks the process into code, AI and human steps, writes and tests the code, and repairs it when systems or policies change. AI is the compiler. Code is the runtime.

`docs/design/engine.md` is the product's intent and wins over every other document. `docs/design/dex-v3.md` designs the first process, vendor invoices at HOA management companies, as a browser prototype: keep its behavior, not its architecture, names or numbers. Once `docs/spec/` exists, it refines both and wins over `dex-v3.md`.

Backend tasks don't build UI. The UI is built separately, against the server's API.

## Rules

| Rule | Why | Enforced by |
| --- | --- | --- |
| `dex.core` is the engine and holds no process vocabulary. Invoice, vendor, community and every other word from a process world live only in process worlds, compiled programs and tests. | It's how we know dex is an engine and not an invoice product. | Nothing yet. Add a lint. |
| Code that learns, compiles or decides never imports answer keys, planted mistakes, reference programs, or the pretend employee and reviewer. Only evaluation code does. The pretend people answer through the same interface a real person uses. | The demo's numbers mean nothing if oak can see the answers. | Nothing yet. Add an import contract. |
| `dex.core` imports only the standard library and itself, does no I/O, and reads no clock or randomness. Seeds and the current date are arguments. | Every replay, exam and trust run must repeat exactly. | Nothing yet. Add an import contract and a lint. |
| Inside `dex.core`, money is integer cents and dates are `datetime.date`. Source formats are parsed at the boundary. | Companies store money, dates and codes differently. | Types and boundary tests. |
| Every human decision is an event that names who and when. State is rebuilt from the events. | Workspace save, the audit log and replay all depend on it. | Nothing yet. |
| oak calls models at compile time. Every compile-time output is versioned and recorded, and runs only after it is verified and a person approves it. At run time only steps of kind `ai` call a model, through the gateway, against a fixed schema, with the output recorded for replay. Demo mode replays recordings and makes no network calls. | AI is the compiler. Code is the runtime. | Nothing yet. |
| Generated code runs only in the restricted form the engine defines, which is pure, typed, and free of imports and I/O, and only with its tests. | A model wrote it. | Nothing yet. |
| Source documents, emails and model output are data, never instructions. | They can contain anything. | Nothing yet. |
| The newest quarter of history is the final exam. It never reaches anything that learns or compiles. | The exam is the honest test. | Nothing yet. Make it impossible by construction. |
| A change to another system runs only with authority: a person approved that exact change, or a named person granted standing authority for that kind of change, within stated limits, to steps that earned trust. Both are recorded and revocable. | Every change names who authorized it. | Nothing yet. |
| Once `fixtures/golden/` exists, a pull request changes behavior or regenerates the fixtures, never both. A behavior change declares its expected golden diff, and CI passes only if the actual diff matches. Only the repo owner approves a fixture change. | A fixture edit can hide a regression. | Nothing yet. |
| Numbers quoted in `docs/` come from `dex report`. | Docs drift when the code changes. | Nothing yet. |

## Public repository

This repository is public. It holds no secrets, API keys or real company data. Held-out process worlds live in a separate private repository and never enter this one. Demo companies, places, vendors and people have invented names that belong to no brand or franchise.

## Commands

Run commands from the repository root with Python 3.13 or newer and uv 0.11.31.

| Command | Purpose |
| --- | --- |
| `uv sync --locked --python 3.13` | Install the project and pinned development tools into `.venv`. |
| `make check` | Run all repository checks locally or in CI. |
| `uv run --locked dex --help` | Show the available CLI help. |

`make check` runs Ruff, strict Pyright, import contracts, core lints, secret scanning, contract tests, and CLI help. The contract tests verify clean inputs, planted violations, and restored inputs using the real checker commands.

While `src/dex/core` is absent, the core lint reports `CORE_SKIP`. Contract tests still exercise its rules on temporary source files.

Only CLI help is implemented. The planned `dex bundle`, `dex demo`, `dex eval`, `dex report`, and `dex workspace` commands are unavailable.

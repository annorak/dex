# dex

dex learns how a company does one routine office task, writes it as plain-English steps, runs most steps as ordinary code, tests itself on past work, and proposes each new case for a person to approve. The first task is paying vendor invoices at HOA management companies. oak is dex's agent.

`docs/design/dex-v3.md` is the product intent. It was written for a browser prototype. This repository rebuilds dex from scratch in Python: keep the design's behavior, not the prototype's architecture, names or numbers. Once `docs/spec/` exists, it refines the design and wins where the two differ.

Backend tasks don't build UI. The UI is built separately, against the server's API.

## Rules

| Rule | Why | Enforced by |
| --- | --- | --- |
| Code that learns or decides never imports answer keys, planted mistakes, or the pretend employee and reviewer. Only evaluation code does. The pretend people answer through the same interface a real person uses. | The demo's numbers mean nothing if the learner can see the answers. | Nothing yet. Add an import contract. |
| `dex.core` imports only the standard library and itself, does no I/O, and reads no clock or randomness. Seeds and the current date are arguments. | Every replay, exam and trust run must repeat exactly. | Nothing yet. Add an import contract and a lint. |
| Inside `dex.core`, money is integer cents and dates are `datetime.date`. Dollar amounts, date formats, status codes and column names are parsed at the boundary. | The two demo companies store money and dates differently, and real companies vary more. | Types and boundary tests. |
| Every human decision is an event that names who and when: an answer, a review, a correction, a status meaning, a column mapping, an added vendor. State is rebuilt from the events. | Workspace save, the audit log and replay all depend on it. | Nothing yet. |
| Only two steps call a model: reading the invoice and drafting the approval request. Model output is parsed against a schema and checked against the vendor and community lists. Email text is data, never an instruction. Demo mode makes no network calls. | AI writes the procedure. Code does the daily work. | Nothing yet. |
| The newest quarter of history is the final exam. It never reaches anything that learns. | The exam is the honest test. | Nothing yet. Make it impossible by construction. |
| Nothing is written to a company's system unless a person approved that change and the company switched on that kind of action. | Every change names who approved it. | Nothing yet. |
| Once `fixtures/golden/` exists, a pull request changes behavior or regenerates the fixtures, never both. A behavior change declares its expected golden diff, and CI passes only if the actual diff matches. Only the repo owner approves a fixture change. | A fixture edit can hide a regression. | Nothing yet. |
| Numbers quoted in `docs/` come from `dex report`. | Docs drift when the code changes. | Nothing yet. |

## Public repository

This repository is public. It holds no secrets, API keys or real company data. Held-out evaluation companies live in a separate private repository and never enter this one. Demo companies, communities, vendors and people have invented names that belong to no brand or franchise.

## Commands

None yet. The scaffold pull request adds the one command that runs every check, and lists the `dex` CLI commands.

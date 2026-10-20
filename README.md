# dex

dex turns a company's operating procedures into software that does the work.
oak reads the company's documents and history, asks people about gaps, and
compiles a cited procedure into tested code, narrow AI steps, and human decisions.

AI is the compiler. Code is the runtime.

This tutorial describes the whole product. The repository currently contains
its design. Commands below are proposed interfaces.
Sections marked "This milestone" define the first build.
Sections marked "Later" describe subsequent milestones.

## Bring the company's sources

This milestone.

Put the procedure documents, exported tables, and historical work into a
[company bundle](docs/bundle.md). Keep the company's original files and formats.
The bundle records where each file came from and when it became available.

To start with invented companies, build the demo bundles:

```sh
uv run dex demo build --seed 7 --out .work/demo
```

The output contains Bramblewick and Fennor in World 1, and Veldren in World 2.
Building again with the same seed produces identical file bytes.
The company procedure files are copied byte for byte.

Check a bundle before importing it:

```sh
uv run dex bundle check .work/demo/world-1/bramblewick
```

The check reports malformed records, missing files, broken references,
unsupported formats, and inconsistent history dates before changing a workspace.

## Watch oak build the procedure

Later, through `dex compile`.

Give oak the permitted company sources. Inspect the procedure it drafts.
Each step shows its intent, input and output types, source passages, and kind.
Its kind is code, AI, or human.

Follow a case through the branches. Code handles rules, recurring formats,
lookups, and templates. An unfamiliar format can reach an AI step.
An invalid or unresolved result reaches a person.
Adding a parser later keeps this fallback path in place.

Answer oak's questions about missing mappings, contradictory instructions,
and unwritten rules. Each answer records who answered and when.
General rules need evidence, tests, and approval before activation.

## Replay the past and take the exam

Later, through `dex demo learn`.

Replay the learning history in order. Inspect disagreements with past work.
Some disagreements expose missing rules. Others expose mistakes in the history.
Keep those two explanations separate.

Freeze the program before its final exam. The newest calendar quarter stays
outside learning and compilation, including its outcomes and event histories.
Exam feedback cannot become another training example.

Without usable history, start with procedure-derived scenarios and shadow mode.
There is no replay score or exam result to claim.

## Prove the engine before building the compiler

This milestone.

Run the evaluator-authored reference programs for both worlds:

```sh
uv run dex eval .work/demo --reference --out .work/reference-run
uv run dex report .work/reference-run
```

The references use the engine's own representation. Every historical case
must match an independently established answer key, including its decisions,
proposed effects, and waits.
This proves what the representation can express. It does not demonstrate
oak compiling a program.

`dex eval` owns reference programs and answer keys.
Ordinary execution cannot select or load them.
`dex run BUNDLE --program PROGRAM --out RUN` runs a separately verified,
approved program and produces its execution transcript.

The report lists implemented acceptance checks and their evidence.
Requirements that have not been built remain visibly unimplemented.

## Review new cases

Later, through `dex demo run`.

Open a proposed case and follow its evidence, decisions, and exact changes.
Approve, correct, or reject the proposal.

In World 1, dex records an invoice, requests business approval, and schedules
payment after the required decisions and holds resolve.
The manager or board decides in the AP application.
Dex observes that person's decision and the invoice revision it covers.

Permission for dex to write is separate.
Initially, a person approves each exact external change.
An interrupted write resumes through reconciliation of the same operation.

## Watch trust grow

Later, through the complete operational demo.

Inspect the reviewed evidence for each step.
The demo requires 300 consecutive clean reviews before a step qualifies to
skip routine review. Mistakes and behavior changes reset affected counts.

The controller then grants bounded, revocable standing authority.
Trust alone never grants permission to write.
Every twentieth otherwise review-free case still requires review.
Required business decisions remain human.

Use `dex report` to inspect model calls and human touches by case, week,
and program version. Pending cases and continuing business decisions remain
in the report as routine review declines.

## Change the systems and policy

Later.

Rename an exported column. Move a button in the AP application.
Watch oak propose a repair, rerun the saved tests, and verify the interface
operation in a sandbox.

A verified repair that preserves behavior keeps its trust.
An unfamiliar status needs a person's explanation.
A policy change creates a dated rule.
Older cases retain the policy that applied when they arrived.

## Compile the next company

Later.

Compile Fennor with and without Bramblewick's generalized library.
Compare the questions, first replay, calls, and final results.
Fennor supplies its own records, meanings, and rule values.
The library transfers neither company data nor trust or authority.

Then compile Veldren on the same engine build.
Its cases contain nested records and independent service branches.
One branch can finish while another waits days for a client.
The branches join before the service owner makes the required human decision.

## Build against the acceptance contract

This milestone uses Python 3.13 or newer, uv, and one package under `src/dex`.

```sh
make check
```

CI runs this command on every pull request.
It runs Ruff, strict Pyright, pytest with Hypothesis, import-linter,
and the engine's isolation and purity checks.

Later milestones add `dex compile`, `dex demo learn`, `dex golden`,
`dex demo run`, and `dex serve`.
The product UI is built separately against the server API.

[Product intent](docs/design/engine.md) defines the product.
[Acceptance](docs/spec/acceptance.md) defines the required evidence.

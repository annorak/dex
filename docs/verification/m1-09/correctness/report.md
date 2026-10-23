# M1-09 independent correctness review

Verdict: FAIL.

Head: b509d09f63b2e4bc92ea2e02430b313600941882.
Base: 9d66353dd4136abccda85ee4d1b49fb88d7fae3c.
Stable patch ID: 8efe2fc3e33ff5cf20b5be342bb67cd6e729e61a.
Checkout: /private/tmp/dex-m1-09-correctness, detached and clean.
Applicability: this exact head and base only. Fixes require focused revalidation.

## Blocking findings

### C1. P1. Future deliveries execute before their availability

`src/dex/bundle/commands.py:92` checks only source availability against now.
Lines 98-125 construct and submit every nonhistorical case, including future
deliveries. Manifest validation checks delivery time against case opening time,
so a future delivery and future opening agree with each other and pass.

The probe supplies source evidence from January 2026, then sets delivery receipt,
delivery availability, and case opening to January 2099. It uses real program
registration, complete verification, and persisted approval. `run_bundle`
returns zero and persists a succeeded case. The receipt prints
`FUTURE {"exit": 0, "mutated": true, "cases": ["case-1"]}`.

Availability is a release boundary, distinct from when source bytes originated.
Premature execution persists runtime decisions, waits, and potential proposals.
Reopening does not undo them. Check the runnable case and delivery chronology
against the run cutoff before workspace mutation. Existing checks against future
sources do not establish that a delivered business arrival is available.

### C2. P1. Reordering inputs admits one delivery twice across restart

`src/dex/bundle/history.py:193` hashes the raw inputs and fact-selector arrays
as case membership. Line 239 uses that hash as the durable admission key.
Those presentation choices are not stable identity for a delivered record.

The probe runs one case, closes the workspace, changes only the case ID and
input-reference order, then runs again. Both runs succeed. Reopening shows
two cases, two arrivals, and one delivery. A second probe changes only a
fact's target name for the same source and record. Public admission accepts
both cases and assigns different admission keys.

This defeats the required distinction between a retry and a legitimate resend.
The reducer persists the supplied key correctly, but the boundary derives it
from mutable selectors. Use stable delivered record identity, independent of
reference ordering and target aliases. Preserve distinct deliveries for equal
bytes, and preserve separate records within one tabular delivery.

### C3. P1. Multiple text sources cannot share a verified program catalog

`src/dex/bundle/formats.py:498` uses the extractor version as
`SourcePin.extraction`. Every text source receives `utf8-1`. The existing core
catalog contract at `src/dex/core/program.py:709` requires extraction identities
to be unique and resolves citations by that identity.

A valid bundle with two text documents produces
`StructuralFailure(diagnostics=(Diagnostic(code='duplicate_identity',
path='sources.utf8-1', message='utf8-1'),), function_failure=None)`.
Actual workspace registration returns `Refused(code='program_verification')`.
The retry probe proceeds only after explicitly restricting the program catalog
to its one cited source. That workaround is confined to the probe.

Normal programs must cite several company documents. Give each immutable
extraction its own stable identity and retain extractor version separately.
Do not weaken the core catalog's citation-identity contract.

## Evidence and scope

- `04-counterexamples.txt` records all three findings and exits zero.
- `02-counterexamples.txt` and `03-counterexamples.txt` preserve failed probe
  setup attempts. They are not counted as passing checks.
- `05-revision.txt` records revision, clean status, stable patch ID, Python
  3.13.11, and uv 0.11.31.
- `01-sync.txt` records the pinned dependency setup.
- The reproducer is `/private/tmp/dex-m1-09-correctness-probe.py`.
  Generated inputs and SQLite workspaces are under
  `/private/tmp/dex-m1-09-correctness-probes-3`.

Reviewed public admission, formats, mappings, history, recordings, provenance,
writing, collection separation, StartCase, and the shared transactional reducer.
The new batch path computes all decisions before event insertion and uses the
existing verification and persisted approval boundary. No separate interpreter
or dispatch path was introduced. Findings above prevent an overall pass.

The maintainability, deslop, and no-comments pass found no separate actionable
cosmetic issue. No suppression or explanatory comment was added in the bundle
implementation. No product or test files were edited by this reviewer.
The user-specified staffing override kept these passes within this reviewer.

Full gates, live lanes, and performance belong to the assigned verifier and were
not duplicated here. M1-10 projections, UI, OCR, and production adapters were
excluded. Missing verification checks remain required; this review clears none.
CPU-heavy probing is finished. Raw receipts remain local durable evidence.

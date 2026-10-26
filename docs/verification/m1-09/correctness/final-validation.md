# M1-09 independent correctness fix validation

Verdict: PASS for the assigned correctness review at the exact revision below.

Head: 0d1575242d01b75035af158def47cc8030eb1215.
Base: 9d66353dd4136abccda85ee4d1b49fb88d7fae3c.
Stable patch ID: 47edd7cc1d10ec842d894803a307d56085079342.
Checkout: /private/tmp/dex-m1-09-correctness, detached and clean.
Python 3.13.11; uv 0.11.31.

The complete b509d09-to-head delta was reviewed. The three original blocking
findings are closed by independent focused probes, recorded in
`06-fixed-counterexamples.txt`, exit zero. `07-fixed-revision.txt` records
the head, clean status, environment, and patch identity.

## Findings closed

- C1. A delivery and case dated 2099 now fail with the named availability
  error before workspace mutation. Database bytes stay identical and no output
  directory appears. The source evidence itself remains already available.
- C2. Repeated identical runs remain no-ops across reopen. Changing case ID
  and reversing input references fails with `delivery_case_conflict`.
  Changing fact target names or column selectors preserves the record identity
  and fails with the same conflict. Combining already admitted rows into a
  grouped case also fails, both within one manifest and after reopening.
  All refused runs leave database bytes identical. Distinct rows in one
  delivery succeed, as does an equal-byte resend with a new delivery ID.
- C3. Two text documents now have distinct extraction identities and pass real
  registration without missing checks. A catalog with two text documents and
  a table also registers and runs. Writing and loading the bundle preserves
  complete source values, including the separate extractor version.

## Shared contracts and change review

Each probe uses real registration and persisted program approval. Unapproved
runs fail. Recorded case actors remain bound to the session. Rebuilding the
event log produces identical state with the interpreter patched to raise,
so replay does not reinterpret the program.

The record-key change uses the existing arrivals map and shared reducer.
Batch refusal happens before event insertion. It introduces no dispatcher,
authority shortcut, interpreter, or second persistence mechanism.
The new StartCase tuple field is confined to this not-yet-landed M1-09 change;
the M1-08 base has no StartCase events requiring migration.

The additional fix delta validates mapping schema shapes before rows are read,
preserves unreadable extraction outcomes, uses an actual image-only PDF fixture,
and includes stdout serialization in the scenario processing timer. The
maintainability, deslop, and no-comments pass found no further actionable issue.
No product or test files were edited by this reviewer.

## Durable evidence and applicability

The original `report.md` and receipts 01-05 remain unchanged. Both probe scripts
and their generated inputs, program artifacts, outputs, and SQLite workspaces
are copied beside this report:

- `dex-m1-09-correctness-probe.py`
- `dex-m1-09-correctness-fixed-probe.py`
- `dex-m1-09-correctness-probes-3/`
- `dex-m1-09-correctness-fixed-probes/`

The scripts use fresh temporary output roots. Reproduction requires choosing
a new root if the recorded directories already exist. Receipts preserve exact
executed arguments, revision, stdout, stderr, and exit status.

This verdict applies to the exact head and base above. It supersedes the earlier
correctness FAIL only for that revision. Repository gates, all live lanes,
isolation, and measured performance remain the assigned verifiers' independent
responsibility. No missing gate is treated as passed here. No PR, push, merge,
or auto-merge action was performed by this reviewer. CPU-heavy work is finished.

# M1-07 verification

Product verification: PASS at `3aae66219121f96f604d213a90847881a457a9dd`.
PR: https://github.com/annorak/dex/pull/6, against `master`.
Frozen base: `80e60aac6ab78017020e5fce4c625c5fcb169ac1`, the verified PR #5 merge.
Product cumulative stable patch ID: `835d86eb815fca315da88999f05490ae805d439e`.

This report records product evidence. The final evidence-only commit must separately pass committed-head `make check`, pre-push merge-safety readback, and CI. The final PR description and local `HANDOFF.json` pin that head and its cumulative patch ID. The operator lands this PR; no merge or auto-merge is authorized.

## What changed

Workspace commands now persist atomic SQLite event batches against an expected revision, together with versioned, hash-checked artifacts. Reopen rebuilds projections from events through the existing deterministic reducer.

External writes persist their attempt and dispatch reservation before contacting an adapter. Dispatch rechecks the current revision, decisions, preconditions, session permissions and exact approval. The adapter contract requires atomic operation deduplication or fencing and conclusive reconciliation. A pending earlier attempt prevents retry or replacement; retries are bounded and retain operation identity. Recovery can record an already-completed write after approval revocation without authorizing another write.

`dex workspace command WORKSPACE --command FILE` supports verified-program registration and approval. Actors come from the configured local session, outside program or bundle data. Roles, company scope and expected revision are enforced. Source actors and approval flags do not grant authority.

## What remains unavailable

Effect recovery is demonstrated with the evaluator-owned deterministic SQLite adapter and sandbox workspace. Normal effect-program activation remains blocked by missing verification checks. Registration does not silently mark unproved checks complete.

No standing-authority dispatch, production authentication, live adapter integration, UI, live model-network verification or later milestone is included. Evaluator verification made no live model calls. The local session configuration is a trusted development boundary, not production authentication. Pure replay performs no I/O, interpretation or dispatch; opening the SQLite shell necessarily reads persisted data.

## Evidence and applicability

| Check | Revision and result | Evidence |
| --- | --- | --- |
| Full repository gates | Initial committed head `e7eabc8`: 671 tests; current product head `3aae662`: 672 tests, Ruff, strict Pyright, import contracts, core checks, secret scanning and CLI help pass | [Initial committed check](owner/053-committed-check.txt), [current committed check](owner/069-committed-startup-check.txt), [independent gate lane](formal/11-gates/report.md) |
| Ten independent live CLI lanes | All passed at `e7eabc8`; all ten reran successfully at `3aae662` | [Final verifier](final-verifier/report.md), formal reports below |
| Independent correctness | No introduced finding in assigned scope; 77 focused tests and deterministic probes passed | [Correctness](formal/13-correctness/report.md) |
| Independent isolation | 211 focused tests, import contracts and normal CLI authority/codec probes passed | [Isolation](formal/14-isolation/report.md) |
| Changed CLI behavior | 47 focused CLI/recovery tests passed at `3aae662` | [Final verifier](final-verifier/report.md) |
| Recovery-size-1000 | All absolute and supported-comparison gates passed at `3aae662` | [Samples](final-verifier/measurements.json), [method and results](final-verifier/report.md) |

The initial full independent round used `e7eabc89ac47e6abb870e4e4f4306dc891b53217`. Fix-forward 1 changed only CLI parser construction and its regression test. All other production sources, scenario inputs, engine tests, lockfile and check configuration are unchanged. The fresh verifier checked this diff, compared source hashes, reran the changed CLI and all ten live scenarios, and performed fresh performance verification. Earlier correctness, isolation and detailed barrier/replay probes therefore remain applicable to unchanged subjects; they are not represented as executions on the newer head. See [source hashes](final-verifier/source-hashes.json) and [carry-forward receipt](final-verifier/carry-forward.txt).

The final evidence-only commit changes documentation and saved receipts. Product evidence carries forward only after confirming that its source, tests, configuration and dependencies equal `3aae662`; the final head receives a new full check and CI result.

## Ten CLI lanes

| Lane | Proven behavior | Report |
| --- | --- | --- |
| 1 | Normal registration and approval, stale refusal, one confirmed write and equal rebuild | [Complete](formal/01-complete/report.md) |
| 2 | Interruption before durable intent leaves no attempt or external write | [Before attempt](formal/02-before-attempt/report.md) |
| 3 | Durable intent survives restart; conclusive fence precedes retry of the same operation | [Before write](formal/03-before-write/report.md) |
| 4 | Remote commit with lost confirmation reconciles the original receipt once | [After commit](formal/04-after-commit/report.md) |
| 5 | Absent lookup while pending cannot permit another admission; late commit reconciles | [In-flight](formal/05-inflight/report.md) |
| 6 | Delayed superseded completion retains original identity; revocation blocks dispatch but allows observation | [Old revision](formal/06-old-revision/report.txt) |
| 7 | Concurrent reviews and task answers yield one atomic winner and one stale refusal | [Concurrency](formal/07-concurrency/report.md) |
| 8 | Fresh-process reopen preserves tasks, due times, decisions and projections without interpretation or dispatch | [Rebuild](formal/08-rebuild/report.md) |
| 9 | Retry bound persists across restart; repeated refusal has no new event or adapter contact | [Retry bound](formal/09-retry-bound/report.txt) |
| 10 | Corrupt artifacts and unsupported stored/command versions are rejected without mutation | [Invalid state](formal/10-invalid-import/report.md) |

Concurrency and delayed-completion probes use deterministic barriers, not timing sleeps. Additional source and database probes check persisted identities and rows independently of evaluator expected values.

## Performance

The final run used the unchanged historical shared Timer V2: monotonic nanosecond wall time, adjacent UTC drift validation, and per-command child RSS. Its SHA-256 is `64349ee4f8d8959cb8a9cede296988d00e78941e38744a3b4805e99649f6b4b9`. The [schedule](final-verifier/schedule.json) was frozen before measurement. Samples ran serially after other CPU-heavy verification, using fresh databases, pinned environments and identical input bytes.

There was one complete first trunk invocation, five alternating trunk/head startup pairs, and five alternating supported-parent/head recovery pairs. Trunk lacks recovery and workspace commands: its actual exit-2 refusals are unsupported comparisons, never passes. Immediate parent `e7eabc8` supports recovery and was measured in all five pairs.

| Metric | Head median | Head maximum | Original gate |
| --- | ---: | ---: | --- |
| Recovery workload, including persistence and reconciliation | 6.794466 s | 6.945291 s | Every sample <=10 s |
| Full CLI completion | 6.996325 s | 7.174634 s | Every sample <=20 s |
| Peak RSS | 292.921875 MiB | 293.984375 MiB | Every sample <=512 MiB |

Supported median ratios were 1.043827 for startup wall, 1.040517 for recovery workload, 1.019174 for full CLI wall, and 0.995434 for recovery RSS; all meet the unchanged 1.20 ceiling. Startup RSS ratio was 0.999464. Overlapping ranges do not establish a speed difference.

All ten timed parent/head databases independently contained 18,008 contiguous events, one artifact, 1,000 applied remote operations, 1,000 local confirmations and zero unresolved attempts. Fresh-process reopen preserved database bytes and produced the same state hash. Durable append, reopen/rebuild and reconciliation phase timings are separately recorded in the [final report](final-verifier/report.md).

The [first M1-07 performance round](formal/12-performance/report.md) remains **ISSUES**. Its declared centisecond startup metric rose from 0.06 to 0.08 seconds, exceeding 20%, and its original cold sample lacked RSS. Higher-precision wrapper values were not substituted to call that round a pass. A measured CLI parser correction produced the new head; the fresh verifier restored the historical shared timer before its scheduled run. No original limit changed, and no valid slow sample was discarded.

## Success and rejection for operator review

- [Register a verified program](cli/register.txt): exit 0, local actor `operator`, revision 1, no missing checks.
- [Approve that program](cli/approve.txt): exit 0, actor `operator`, revision 2, approved.
- [Reject stale approval](cli/stale-approval.txt): exit 1, `stale_revision`, revision remains 2.

These are exact normal CLI transcripts at `3aae662`, including arguments, revision, stdout, stderr and exit status.

## Audit trail and limits

The complete command receipts, earlier revisions, failed attempts, proposed diffs, probes and generated databases are preserved locally under `docs/verification/m1-07-3aae662/full-audit/`, with a SHA-256 manifest. The PR contains a selected portable text evidence set; paths in exact transcripts intentionally retain their original execution locations. The full local set resolves report references without depending on temporary worktrees.

The first install recorder failed before launching its child and left an empty receipt. [Its reconstruction](owner/001-install-reconstructed-failure.txt) explicitly leaves unavailable original stderr, status and time unknown. Some early bootstrap/read commands predated the recorder. These are documented audit gaps, not passing checks. Substantive final functional, performance, database and source-integrity checks have separate receipts. Setup denials, verifier-script errors and corrected assertions remain preserved.

An interim review was interrupted by runtime filtering and is not counted as completed. Its snapshot findings were fixed and covered by later independent reviews. The decision log also preserves a timestamp edit that was corrected by appending the original row and an explanation; exact command times govern chronology.

All available independent reviewers use the GPT model family, so model-family diversity is reduced. An hourly scheduled wake-up was unavailable; the root audited work at execution boundaries. The implementation had one owner. Only M1-07 was pursued.

## Inherited history

PR #1 passed CI and 173 tests, but performance checks and the full independent reviewer round were incomplete before merge.

PR #5 passed CI, 638 tests, twenty live CLI lanes and applicable correctness reviews. Its formal M1-06 performance gate failed: one valid effect CLI sample took **15.030444625 seconds against the unchanged 15-second limit**. The owner subsequently merged it. That inherited failure and other documented limitations remain; this PR does not claim to repair them.

reviewed by gpt-6.1-sol


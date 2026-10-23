# M1-09 independent verification

PASS for this verifier's twelve assigned outcomes at `0d15752`, against trunk and dependency parent `9d66353`. Both independent reviewers also pass at that exact head and base. Full revisions are recorded in each raw command receipt. Root owns the aggregate stack decision. This report does not authorize landing.

The committed-head `make check` passes Ruff, strict Pyright, import contracts, core lints, the unchanged secret scanner, all 741 tests, and CLI help. Pytest takes 79.07 seconds. The required focused command passes 38 tests. The independent checkout is clean and pinned. Root did not duplicate the full suite before the first push.

| Outcome | Verdict | Receipt |
| --- | --- | --- |
| bundle-roundtrip | PASS | [Lane 1](lane-01-bundle-roundtrip.txt) |
| bundle-money-dates | PASS | [Lane 2](lane-02-bundle-money-dates.txt) |
| bundle-fractional-invalid | PASS | [Lane 3](lane-03-bundle-fractional-invalid.txt) |
| bundle-email-attachments | PASS | [Lane 4](lane-04-bundle-email-attachments.txt) |
| bundle-xlsx-sheets | PASS | [Lane 5](lane-05-bundle-xlsx-sheets.txt) |
| bundle-path-hash | PASS | [Lane 6](lane-06-bundle-path-hash.txt) |
| bundle-delivery-identities | PASS | [Lane 7](lane-07-bundle-delivery-identities.txt) |
| bundle-chronology | PASS | [Lane 8](lane-08-bundle-chronology.txt) |
| bundle-eval-unreadable | PASS | [Lane 9](lane-09-bundle-eval-unreadable.txt) |
| bundle-ordinary-run | PASS | [Lane 10](lane-10-bundle-ordinary-run.txt) |
| repository-gates | PASS | [Committed-head gate](repository-gates.txt) |
| performance | PASS | [Frozen schedule execution](performance-run.txt) |
| correctness | PASS within reviewer scope | [Final independent review](../../correctness/final-validation.md) |
| isolation | PASS within reviewer scope | [Final independent review](../../isolation/final-validation.md) |

All ten actual CLI scenarios complete successfully. All expected matches are true. The verifier executes all 31 emitted bundle-check commands, including the five roundtrip checks in the frozen driver. Each gets its own exact receipt. [Emitted checks](emitted-checks.txt) cover the other 26. Fractional cents, impossible dates, conflicting mappings, unknown status meanings, unsafe paths, symlinks, missing and undeclared files, bad hashes, unsupported versions, conflicting source identities, XLS, and invalid arrival chronology fail for their named reason. Existing workspace bytes remain unchanged.

[Independent live readback](independent-live-validation.txt) checks SQL event contiguity and integrity, immutable database bytes, exact normalized values, cell provenance, message-part and page provenance, original hashes and bytes, late evidence, and the unreadable evaluator subtree. The public loader passes open and traversal instrumentation while the evaluator subtree has mode zero and an actual read raises PermissionError. [Supplemental validation](image-and-ordinary-validation.txt) confirms the PDF contains a literal inline image and no selectable text. Unreadable XLSX and the image-only PDF remain unresolved.

The normal [registration](live/bundle-ordinary-run/register.txt) reports no missing checks for a program with two text sources. Explicit [approval](live/bundle-ordinary-run/approve.txt) persists the local operator as actor. [Approved execution](live/bundle-ordinary-run/success-run.txt) returns seven through the ordinary workspace runtime. The [unapproved command](live/bundle-ordinary-run/rejection-unapproved.txt) exits one with program_unapproved. The [tampered program](live/bundle-ordinary-run/rejection-tampered.txt) exits two with verified_artifact_hash_mismatch. Both refusals preserve the database and create no result directory. Duplicate execution preserves database bytes. Rebuild equals the persisted state with file opening, SQLite connection, subprocesses, sockets, interpretation and runtime decision calls blocked. No grants or effects appear.

## Frozen performance evidence

The [schedule](schedule.json) and [input inventory](../inputs/inventory.json) were frozen before measurement. The complete proposed schedule is in freeze-proposed.txt and its application is in freeze-applied.txt. The 46 steps run serially after root releases the CPU barrier. There are 26 measured children and no discarded, replacement, or repeated formal samples. Every measured child exits zero with a valid clock. Every declared unsupported refusal exits two for the absent capability.

Separate fresh detached trunk, parent and head checkouts use Python 3.13.11 and uv 0.11.31 with pinned dependencies. Dependency setup finishes before any baseline CLI invocation. PYTHONPATH and VIRTUAL_ENV are removed, UV_OFFLINE is set, and no live model calls occur. The first trunk CLI invocation is the measured help command. It takes 0.594203834 seconds and 30441472 bytes of peak RSS. Cold means the first CLI invocation in that fresh checkout after dependency setup. OS caches are not flushed.

The unchanged historical Timer V2 uses monotonic nanoseconds, adjacent UTC validation within 0.050 seconds, and Darwin child peak RSS in bytes. Each command has its own timer process. [Controls](../018-controls.txt) validate allocation RSS, success, nonzero exit propagation, forward and backward clock-jump rejection, and preservation of a child failure during a clock jump. Receipt-wrapper durations are not performance metrics.

The host has ten logical CPUs. Load averages are 5.43, 4.90, 4.79 before the schedule and 5.77, 5.00, 4.83 afterward. Root and reviewers release heavy work before measurement. User background processes remain running. Startup pairs use T/H, H/T, T/H, H/T, T/H, followed by the same orientation for P/H. The parent's first help invocation takes 0.522232 seconds and remains in its five samples.

| Supported startup comparison | Baseline median seconds | Head median seconds | Wall ratio | Baseline median RSS bytes | Head median RSS bytes | RSS ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| trunk and head | 0.085279208 | 0.089322667 | 1.047414359 | 30343168 | 30375936 | 1.001079914 |
| parent and head | 0.084499000 | 0.093924000 | 1.111539782 | 30326784 | 30359552 | 1.001080497 |

Trunk startup wall range is 0.084827541 to 0.087205833 seconds. Its paired head range is 0.086562208 to 0.098999291. Parent range is 0.081470375 to 0.522232. Its paired head range is 0.089135792 to 0.106561625. RSS ranges and full precision are in [validated results](validated-results.json). Both supported median wall and RSS comparisons meet the unchanged 1.20 ceiling. These are startup observations, not a claim of product speedup.

The identical frozen roundtrip and size scenario bytes run on trunk first, then the dependency parent, then head. Both baselines actually refuse the bundle scenario format with scenario_error and create no output. Their five emitted roundtrip checks each refuse the unavailable bundle command. The new feature is unsupported at both baselines. No intermediate implementation substitutes for the dependency parent. There is no supported identical bundle-workload regression comparison and no bundle speedup claim.

| Head size sample | Processing seconds | Full command seconds | Peak RSS bytes |
| --- | ---: | ---: | ---: |
| 1 | 1.213906417018734 | 1.481322750 | 244432896 |
| 2 | 1.199410583009012 | 1.461512000 | 245923840 |
| 3 | 1.217870375025086 | 1.493649917 | 246480896 |
| 4 | 1.191838625003584 | 1.458699250 | 246333440 |
| 5 | 1.183176750026178 | 1.452599125 | 244170752 |
| Median | 1.199410583009012 | 1.461512000 | 245923840 |
| Unchanged limit | 10 | 20 | 536870912 |

Every individual sample meets all three limits. Processing range is 1.1831767500261776 to 1.217870375025086 seconds. Full command range is 1.452599125 to 1.493649917 seconds. RSS range is 244170752 to 246480896 bytes. [Raw timer records](measurements.json) retain exact precision.

The processing timer includes actual source reads, public validation, exact normalization, deterministic directory and ZIP writes, actual and expected result serialization, and final stdout serialization and flush. Only timing.json measurement metadata follows that timer. Full-command Timer V2 also includes timing.json, imports, uv, process startup and shutdown. Both writers use the shipped configuration. No tuning, caching shortcut, or changed workload supplies a pass.

[Outside-timing validation](persisted-output-validation.txt) reads every saved directory and ZIP with the ordinary public loader. Each preserves 10000 normalized tabular rows, their exact business dates and status meanings, a sum of 50005000 integer cents, and the complete 10485760-byte packet. Original source bytes total 10664732. Original bytes, source identities, extractions, cases and deliveries equal the frozen input. Every ZIP has sorted paths, fixed 1980 timestamps and stored entries. All five ZIP byte strings are identical. Validation checks every output file hash before and after and changes no saved output. Fast refusal, missing output or skipped normalization cannot satisfy these checks.

The separate [untimed profile](profile-analysis.txt) runs after the formal schedule at the same head on a fresh output. Extraction snapshot serialization is the main cost. Two write_bundle calls account for 1.886 instrumented cumulative seconds of the size function's 2.239. extraction_bytes accounts for 1.818 and 60006 codec.dumps calls account for 1.316. These nested times are not added. This CPU work serializes the typed records twice for the required directory and ZIP outputs. The profile is qualitative limiter evidence only. Instrumented durations never enter the formal statistics.

## Retained failures and applicability

The initial b509d09 full gate fails the stale unavailable-run contract, with 730 tests passing and one failing. The original receipt ../023-repository-gates.txt remains unchanged. The final-head full gate fixes that contract and passes. Both reviewers preserve their original findings and prove focused fixes at the final head. Earlier probes are not relabeled as final-head executions.

Verifier receipt ../026-independent-live-validation.txt fails because the probe assumes RuntimeEvent has a revision attribute. The corrected probe checks SQL revision columns in ../027 and runs again at the final head here. The first excluded profile attempts to execute dex as a module and fails because dex has no __main__. profile-excluded.txt remains unchanged. The corrected profile executes the installed CLI script. Neither failed probe counts as a passing check or a formal measurement. Preflight missing PATH tools, the watcher sandbox failure and the raw evidence scanner rejection also remain preserved.

PR #1 passed CI and 173 tests, but performance and the full independent reviewer round were incomplete before merge. PR #5 passed CI, 638 tests, twenty CLI lanes and applicable reviews, but its formal M1-06 performance gate failed at 15.030444625 seconds against the unchanged 15-second limit before the owner merged it. M1-07 documented failures, evidence limitations and final applicability remain unchanged. M1-08 final gates passed, while its earlier correctness findings, typing failure and failed development performance attempt remain historical failures. Its revised probe is not a product speedup.

This report's twelve executions apply to exact head 0d15752 and base 9d66353. The two reviewer verdicts apply to that same pair. Later evidence-only commits require exact unchanged product and test evidence plus a fresh committed-head make check before push. CI, PR applicability and merge-safety readback belong to root.

Raw receipts, frozen inputs, output bundles, workspaces, schedule, failed attempts and profile data remain unchanged in the durable M1-09 evidence tree. [Packaging preflight](../019-packaging-preflight.txt) rejects raw hash-bearing transcripts with the unchanged scanner. Receipts are not edited, escaped, allowlisted or exempted. The unchanged scanner passes report.md, coverage.json and the separate [performance summary](performance-results.json), recorded in packaging-safe-scan.txt. Exact raw measurements.json and validated-results.json are scanner-rejected in packaging-candidates-scan.txt and remain unchanged locally. Links to raw .txt files resolve in the complete local evidence tree, not necessarily a tracked GitHub subset.

The [saved scripts](scripts/) preserve the exact frozen measurement driver, independent validators, input preparation, profile analysis, recorder and Timer V2. Script bodies are recovered from their exact executed command arguments. The recorder and timer copies are byte-identical to the historical tools. Their original receipts and filenames remain unchanged. Reproduction requires fresh output paths because the evidence files deliberately refuse overwrite.

Production authentication, production adapters, OCR, UI, learning projection and later milestones remain unavailable. Verification of the supported pure-code path clears no missing checks on other program capabilities. Ordinary run retains the existing verifier, persisted approval, shared reducer and workspace authority boundary. The complete final test suite exercises inherited recovery, trust, grants, revocation, actor binding and expected-revision checks. No product edits, commits, pushes, merge operations, extra agents or model-network calls were made by this verifier.

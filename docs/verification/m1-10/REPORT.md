# M1-10 verification report

Status: BLOCKED. Not STACK-READY. The formal performance outcome fails the unchanged startup regression limit. Do not merge or enable auto-merge.

[PR 9](https://github.com/annorak/dex/pull/9) implements only M1-10. Product verification covers ecd4b9a against master and the actual merged M1-09 dependency c7c1976. Full revisions, the stable product patch ID and final evidence-head applicability are retained in the local checkpoint and handoff receipts. Later evidence-only commits do not change the product tree.

## What changed

The bundle command freezes cohorts from the declared history interval and case-opening event before constructing a learning view. It uses the final three calendar months, preserves incomplete and no-history declarations, and filters evidence by availability at the requested cutoff.

The emitted view owns its permitted bytes. Mixed native exports retain only permitted records or cells. Citations preserve original extraction identity, exact quotations and Unicode code-point spans while projected text receives its own identity and spans. Excluded evaluator, exam and future material cannot enter the view or its derived serialization destinations. Original bundle roots, symlinks and recovery handles are absent.

Existing admission, extraction and runtime contracts remain in use. Projection does not approve programs, grant authority or complete effects. Root-denial checks block file recovery and network, subprocess and SQLite access while reading and serializing the saved view. The workspace and its authority events remain unchanged.

Compile recordings without sufficient case provenance are excluded. Shared-library transfers reject company evidence. Compiler expansion, M1-11 worlds, golden fixtures, production authentication, production adapters, OCR and UI remain unavailable.

## Fourteen coverage outcomes

| Outcome | Result | Evidence |
| --- | --- | --- |
| Repository gates | PASS | Final product head: 788 tests, Ruff, strict Pyright, import contracts, core checks, unchanged scanner and CLI help |
| projection-learning | PASS | Real trunk and dependency refusals, exact head membership and emitted project command |
| projection-quarter-boundary | PASS | Declared calendar boundary and complete case assignment |
| projection-exam-recording | PASS | Exam recordings, outcomes, aggregates and excluded producers absent |
| projection-mixed-export | PASS | Exact permitted native records, citations and inaccessible originals |
| projection-future-delivery | PASS | Availability wins over earlier issue or effective dates |
| projection-evaluator-leak | PASS | Named evaluator-artifact refusals and unchanged existing state |
| projection-root-capability | PASS | Path, symlink and resolver refusals; denied-root readback |
| projection-derived-leak | PASS | Twenty-four planted refusals across six serialization destinations |
| projection-no-history | PASS | Explicit no-history and incomplete declarations; no invented score or exam |
| projection-self-contained | PASS | Saved view works without original-root access; authority unchanged |
| Performance | FAIL | Trunk/head help median wall-time regression is 21.6666%, above 20% |
| Correctness review | PASS | [Second focused validation](correctness/round2-validation.md) |
| Isolation review | PASS | [Second focused validation](isolation/round2-validation.md) |

The required projection suite passes 47 tests. The independent verifier executed every emitted CLI command. Named rejection lanes returned the required nonzero code and preserved source, workspace and destination state. A setup failure was never counted as a successful rejection.

The [verifier report](verifier/round3/report.md) and [coverage record](verifier/round3/coverage.json) identify exact receipts and carried-forward lanes. Five lanes retain their b9d6794 evidence because the complete final delta only changes cross-extractor alias propagation and tests, and those frozen inputs have unique original hashes and no attachment origins. Four affected lanes and the ordered regression lane pass at ecd4b9a. Both reviewers validated that head. The final documentation head receives a separate mandatory committed-head make check before push.

## Performance result

The frozen schedule used separate pinned trunk, actual dependency and head checkouts. Dependencies were warmed separately. Trunk's first CLI invocation was measured before the command was warmed. Five alternating trunk/head pairs and five alternating dependency/head pairs used the identical supported help workload. The actual projection commands and scenarios are unsupported on both baselines; all eight expected baseline refusals were recorded. No projection speedup is claimed.

All five 10,000-case runs passed the absolute limits. Projection work took 6.347145 to 6.727569 seconds against 10 seconds. Full command completion took 6.683084 to 7.101315 seconds against 20 seconds. Peak RSS ranged from 422133760 to 487473152 bytes against 536870912 bytes. Every run partitioned all 10,000 cases, persisted exactly 8,000 permitted cases and records, validated the saved view and completed serialization. Outside timing, the verifier checked every retained row and reran all five emitted project commands.

The supported trunk/head help medians were 0.081288917 and 0.0989015 seconds, a ratio of 1.216666474. That fails the unchanged 1.20 limit. The actual-parent/head wall-time ratio was 1.026976519 and both RSS comparisons passed. The aggregate performance result remains FAIL.

Every formal child completed with a valid Timer V2 clock and expected exit status. No sample was replaced or discarded. The host reported ten logical CPUs and elevated load during measurement; that observation does not invalidate or excuse the failed gate. Separate excluded startup profiles did not isolate a cause. [Numeric results](verifier/round3/performance-summary.json) retain individual samples and comparisons.

## Findings and earlier failures

Initial independent reviews at 26bc6e6 found attachment aliases that leaked excluded material, missing permitted cell observations, and recordings that carried excluded producer inputs. The first focused fix closed the cell and recording findings but still allowed a raw text alias of a newly restricted parent email. The second fix closes that nested path. Independent CLI reproductions and regression tests pass. Initial reports, failed proofs and both fix rounds remain in the local evidence archive.

Development failures remain failures: early typing errors, the initial 22.768557-second projection-work result, the invalid profiler entry point, alias regression failures, an incorrect test filename, an incomplete fixture declaration and formatting checks before correction. Verifier and reviewer setup or assertion mistakes are also retained. The formal startup failure above is unresolved.

Historical facts are unchanged. PR 1 passed CI and 173 tests, but performance and its full independent review round were incomplete before merge. PR 5 passed CI, 638 tests, twenty CLI lanes and applicable reviews; its M1-06 performance gate failed at 15.030444625 seconds against 15 seconds, and the owner merged it. M1-07's recorded failures, limitations and applicability remain in its evidence. M1-08 passed its final gates; earlier correctness, typing and development performance failures remain failures, and its revised probe was not a product speedup. M1-09 passed its final 741-test gate, ten CLI scenarios, 31 emitted checks, both reviews and performance; its earlier findings and failed attempts remain historical failures.

## Evidence and handoff

[Reproduction instructions](REPRODUCE.md) and the recorder, Timer V2 and verifier scripts are included. The original checkout retains all raw .txt receipts, complete proposed diffs, frozen inputs, configs, independent probes, saved views and databases under docs/verification/m1-10. Each command receipt records exact arguments, revision, stdout, stderr and exit status.

Raw hash-bearing receipts fail the unchanged scanner. They remain unmodified locally; no receipt was edited, no exemption was added, and scanning was not weakened. The PR contains scanner-compatible reports, results and scripts. Success transcript verifier/round3/regression-head-emitted-1.txt and rejection transcripts under verifier/round2/lane-06-projection-evaluator-leak-emitted-*.txt are available in that local archive for the owner's review.

The PR stays open against master. Final GitHub state, CI, review-thread triage, head/base applicability and the absence of auto-merge or queue membership are recorded at handoff. Passing CI does not override the failed performance outcome. M1-11 has not started.

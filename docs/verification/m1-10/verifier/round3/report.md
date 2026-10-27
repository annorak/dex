# M1-10 independent verification

FAIL at code head `ecd4b9a` against trunk and the actual M1-09 dependency baseline `c7c1976`. The fourteen outcomes are thirteen PASS and one FAIL. This milestone is not STACK-READY.

The performance gate fails because trunk-to-head startup median wall time increases from 0.081288917 seconds to 0.098901500 seconds, a ratio of 1.216666474 against the unchanged 1.20 ceiling. All five absolute projection-size budgets pass. A busy host does not invalidate the frozen failure. No sample was discarded, replaced, or repeated.

The [coverage matrix](coverage.json) lists each separate outcome and the exact receipt or independent reviewer report. Full revisions, argv, checkout state, stdout, stderr, and statuses remain in the raw receipts.

## Repository and live evidence

The committed-head [repository gate](023-repository-gates.txt) passes Ruff, strict Pyright, import contracts, core lints, the unchanged secret scanner, all 788 tests, and CLI help. Tests take 98.46 seconds. The required [projection test command](024-projection-focused.txt) passes 47 tests in 2.91 seconds.

| Outcome | Verdict | Execution and evidence |
| --- | --- | --- |
| Repository gates | PASS | [Committed-head gate](023-repository-gates.txt) |
| projection-learning | PASS | [Ordered regression head run](head-projection-learning.txt) |
| projection-quarter-boundary | PASS | [Prior exact execution](../round2/lane-02-projection-quarter-boundary.txt), applicable by the [saved-input proof](005-live-applicability.txt) |
| projection-exam-recording | PASS | [Prior exact execution](../round2/lane-03-projection-exam-recording.txt), same applicability proof |
| projection-mixed-export | PASS | [Final-head execution](lane-04-projection-mixed-export.txt) |
| projection-future-delivery | PASS | [Prior exact execution](../round2/lane-05-projection-future-delivery.txt), same applicability proof |
| projection-evaluator-leak | PASS | [Prior exact execution](../round2/lane-06-projection-evaluator-leak.txt), same applicability proof |
| projection-root-capability | PASS | [Final-head execution](lane-07-projection-root-capability.txt) |
| projection-derived-leak | PASS | [Final-head execution](lane-08-projection-derived-leak.txt) |
| projection-no-history | PASS | [Prior exact execution](../round2/lane-09-projection-no-history.txt), same applicability proof |
| projection-self-contained | PASS | [Final-head execution](lane-10-projection-self-contained.txt) |
| Performance | FAIL | [Frozen execution](013-performance-driver.txt), [numeric summary](performance-summary.json) |
| Correctness | PASS within reviewer scope | [Second focused validation](../../correctness/round2-validation.md) |
| Isolation | PASS within reviewer scope | [Second focused validation](../../isolation/round2-validation.md) |

The verifier executes every emitted project command. The ten applicable lanes contain 21 commands, including eight named nonzero refusals. Fourteen commands carry forward with five unaffected lanes from `b9d6794`. Seven commands run at the final head. Every refusal checks exact error classification and unchanged source, workspace, and existing-destination snapshots.

The final two-file delta changes only alias restriction closure and its regression tests. For the five carried lanes, every saved source manifest has unique original hashes and no attachment edges. The changed cross-extractor ambiguity branch therefore adds no restrictions in either revision. The proof checks the complete changed-file list and exact saved manifests. These executions are carried forward by applicability, not described as final-head reruns.

Saved views have exact learning case, native-record, recording, event, and delivery membership. Unicode quote provenance retains original offsets 6 through 21 and projected offsets 0 through 15. Exam evidence, future unavailable evidence, evaluator material, and original-root paths are absent. Derived serialization checks all six destinations and 24 planted refusals. No-history and incomplete-history declarations retain their limits.

The separate [root-denial readback](011-independent-root-readback.txt) reopens mixed-export, root-capability, and self-contained views with original roots denied and sockets, subprocesses, and SQLite access blocked. Permitted serialization succeeds. Original bytes, saved views, and workspaces remain unchanged. Each workspace passes SQLite integrity checks and contains zero events.

## Frozen performance evidence

The [final configuration](frozen-config.json) records exact revisions, original input hashes, historical recorder and Timer V2 hashes, the portable driver hash, method, and 35-step schedule. [Freeze readback](012-formal-freeze-readback.txt) confirms every value before timing. Earlier freezes remain unchanged. Root explicitly finishes push work and acknowledges timing start before this schedule.

Separate clean trunk and dependency-parent checkouts both remain at the actual dependency commit. No intermediate feature implementation is used as a baseline. Their first product invocation is reserved until this schedule. Trunk's measured cold help is its first product invocation after dependency setup. It takes 0.534330666 seconds and 30490624 bytes of peak RSS. OS caches are not flushed.

The schedule contains cold trunk help, five alternating trunk/head startup pairs, five alternating parent/head pairs, eight actual unsupported baseline commands, the ordered head learning regression, and five head size samples. All 26 measured children exit zero with valid clocks. Both baselines actually refuse learning and size scenarios with scenario_error and refuse the missing project command through argparse. Both leave output absent. Head then runs the identical frozen learning scenario successfully. Projection is unsupported on both baselines, so no projection speedup or unlike-workload comparison is claimed.

Timer V2 uses monotonic nanoseconds and adjacent UTC validation within 0.050 seconds. Darwin child peak RSS is measured in bytes. Each measured child has a separate timer process. Historical success, nonzero, allocation, forward-clock, backward-clock, and failure-preservation controls pass. Receipt-wrapper duration is not a performance metric.

The host has ten logical CPUs. Load averages are 12.36, 11.76, and 10.15 before the schedule, and 12.13, 11.94, and 10.42 afterward. Root and both reviewers stop heavy local work. Other host activity remains an uncontrolled limitation. The startup cause is unresolved; the valid failure stands.

| Supported startup comparison | Baseline median seconds | Head median seconds | Wall ratio | RSS ratio | Verdict |
| --- | ---: | ---: | ---: | ---: | --- |
| Trunk/head | 0.081288917 | 0.098901500 | 1.216666474 | 1.000000000 | FAIL |
| Parent/head | 0.085781416 | 0.088095500 | 1.026976519 | 1.000540249 | PASS |

Trunk startup ranges from 0.080044042 to 0.089974792 seconds, and paired head startup from 0.086301875 to 0.106269375. Parent startup ranges from 0.079580291 to 0.416762375, and its paired head startup from 0.084008208 to 0.091616167. All samples remain included. The parent range contains its first invocation. RSS comparisons meet the unchanged ceiling.

| Size sample | Processing seconds | Complete command seconds | Peak RSS bytes |
| --- | ---: | ---: | ---: |
| 1 | 6.727569167 | 7.101314708 | 422641664 |
| 2 | 6.544609875 | 6.908090125 | 481099776 |
| 3 | 6.499055291 | 6.889496750 | 426721280 |
| 4 | 6.418736458 | 6.768811958 | 487473152 |
| 5 | 6.347144458 | 6.683083541 | 422133760 |
| Median | 6.499055291 | 6.889496750 | 426721280 |
| Unchanged limit | 10 | 20 | 536870912 |

Every size sample meets every absolute limit. Processing ranges from 6.347144458 to 6.727569167 seconds. Complete command time ranges from 6.683083541 to 7.101314708 seconds. Peak RSS ranges from 422133760 to 487473152 bytes. Raw exact values remain in performance-results.json and measurements.json.

Processing includes cohort partitioning, permitted source materialization, mixed-record projection, the written view, public-view validation, result serialization to disk, and stdout serialization and flush. Only timing metadata follows that processing timer. Timer V2 also includes imports, uv, process startup, timing metadata, and shutdown.

Outside each timer, the driver checks the reported 10000-case input count and exact 8000 saved learning case IDs and record locators. [Final readback](014-outside-timing-readback.txt) confirms all five emitted size views equal their already validated measured views. All ten views are byte-identical at 13582310 bytes. No saved output changes. Five additional emitted project commands succeed. Fast refusal or absent materialization cannot satisfy these checks. No extra verifier profile or timing follows the formal failure.

## Preserved failures and limits

The first code head passes 776 tests and 35 focused tests, but independent reviewers find attachment-alias leakage, lost permitted cell evidence, and recording producer-lineage gaps. The first fix passes 784 tests and 43 focused tests but leaves a nested raw-MIME alias leak. The second focused fix closes the review findings. Both final independent verdicts apply to `ecd4b9a`. Initial reports, first focused FAIL reports, raw CLI reproductions, and all earlier receipts remain unchanged.

The first verifier driver incorrectly indexes a typed citation envelope and fails after a successful preliminary head-only learning run. Receipt ../032-live-driver.txt remains unchanged. The corrected driver unwraps the typed value. That preliminary run does not satisfy the ordered regression lane. The actual baseline-first lane is executed only in this final schedule.

Preflight preserves the default-cache permission failure, watcher dependency-bootstrap permission failure, and scanner rejections. Approved retries complete setup. The unchanged scanner rejects full revision and hash fields in raw receipts and machine-specific initial scripts. No receipt is rewritten, escaped, exempted, or allowlisted. The separate public report, coverage, summary, and portable scripts receive their own packaging scan.

The [saved scripts](../../scripts/) contain the portable driver and byte-identical historical recorder and Timer V2. [Package validation](009-script-package-validation.txt) confirms byte identity and scanner compatibility. Frozen inputs, full configurations, workspaces, output views, raw measurements, and transcripts remain in the complete durable local evidence tree. Raw-transcript links can be absent from a smaller public GitHub package.

PR #1's performance checks and full independent reviewer round were incomplete before merge. M1-06's formal performance failure remains a historical failure despite merge. M1-07 and M1-08 limitations and earlier failures remain unchanged. M1-09's final verification and retained failures remain unchanged. This report does not repair or relabel those histories.

The verifier owns repository gates, ten live outcomes, and performance. Separate reviewers own correctness and isolation. No product edits, commits, pushes, merge operations, extra agents, or model-network calls are made by this verifier. UI, later milestones, production authentication, production adapters, and OCR remain unavailable. No claim of startup speedup, causal diagnosis, or overall performance PASS is made. The failing gate keeps this PR blocked.

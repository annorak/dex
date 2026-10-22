# M1-07 final independent verification

PASS for this final verifier's functional and performance predicates. No measurable performance difference is established by these overlapping ranges. This report does not declare STACK-READY. Root owns the aggregate decision.

Head: 3aae66219121f96f604d213a90847881a457a9dd.
Direct parent: e7eabc89ac47e6abb870e4e4f4306dc891b53217.
Frozen trunk/base: 80e60aac6ab78017020e5fce4c625c5fcb169ac1.
Independently computed cumulative stable patch ID: 835d86eb815fca315da88999f05490ae805d439e.
Detached worktrees: /private/tmp/dex-m1-07-final-{head,parent,trunk}.
Evidence root: /private/tmp/dex-m1-07-audit/final-verifier.

## Retained first failure and method

The first M1-07 performance report remains ISSUES at ../formal/12-performance/report.md, SHA256 427a11800b6ea5a87a268a2aa2b0ad6db6b8428981f488eda672ce83c3ddadd1. Its declared centisecond startup median 0.06 to 0.08 seconds failed the unchanged 20% gate, +33.3%; receipt-wrapper higher precision was +19.03%, which did not replace the declared metric. Its original cold invocation lacked RSS. None of those observations is erased or relabeled. The older M1-06 15.030444625-second failure against 15 seconds also remains a failure.

This round verifies a new commit that lazily builds nested workspace parsers only when selected. It restores the existing historical shared Timer V2, rather than inventing a metric after a failed sample. The historical report read was /Users/varunvis/workspace/dev/dex/docs/verification/m1-05-06-077493b/reports/performance-final/report.md.

measure.py is copied unchanged from /private/tmp/dex-m1-05-06-audit/measure.py, SHA256 64349ee4f8d8959cb8a9cede296988d00e78941e38744a3b4805e99649f6b4b9. It times one complete launched command with perf_counter_ns, checks adjacent UTC elapsed drift <=0.050 seconds, and uses single-child getrusage RUSAGE_CHILDREN. Darwin RSS is bytes, not KiB. A fresh timer process runs for every child. The outer receipt duration is never used as the performance metric.

timer-controls.txt verifies a successful allocating child with 23,052,288-byte RSS; child failure 7 remains 7; forward/backward UTC jumps return 125; child failure 7 wins over a simultaneous clock-invalid condition. Mocking is limited to bounded controls, never measured product commands.

schedule.json was read and frozen in frozen-schedule.txt before any measurement. SHA256 c8b46ac694fe5ea5c6149586bef6c124cd5dd4381e05e905044112dbf4b7352e. It specifies first trunk help, unsupported trunk commands, five alternating trunk/head help pairs T/H,H/T,T/H,H/T,T/H, and five alternating supported parent/head recovery pairs P/H,H/P,P/H,H/P,P/H. Every workload uses fresh SQLite/output directories and identical frozen input bytes. No valid slow sample is discarded, no timing sample repeated, and no gate changed.

## Identity, input and carry-forward

All three environments use product Python 3.13.11, uv 0.11.31, detect-secrets 1.5.0, and uv.lock SHA256 80663649dc0d95981af2122c4e86ec3b795313875263ea8bdc00dbb39d077950. The receipt/timer orchestration interpreter is Python 3.11.6; each actual uv-launched product uses its pinned 3.13.11 environment. PYTHONPATH and VIRTUAL_ENV are cleared consistently. UV_OFFLINE=1 prevents dependency networking. These evaluator paths use deterministic SQLite fixtures and make no model calls.

Frozen recovery-size-1000.json is 253 bytes, SHA256 21e810095b0f1306cdf7cf76429fc221a9ee6f9134169ff2c9ded20d2d0127af.
Frozen recovery-complete.json SHA256 3792599f24134e37e43bc3f7ebfb7874d378ddc60842c4213b6c8489be6f0095.

The exact direct-parent diff is only src/dex/cli.py and tests/test_cli.py, 19 added and 6 removed lines. sys.argv[1:2] selects the workspace parser, preserving all documented root/workspace/command help and workspace error paths. It does not move runtime execution or change registration/approval semantics.

source-hashes.json records every Python source hash at head and parent. Exactly src/dex/cli.py differs; the other 19 production Python files are byte-identical, including all core, persistence, codec, adapter, verifier and evaluator code. The Git diff also proves all earlier scenario, tests, checker, configuration and lock files unchanged except the added CLI regression test. final-integrity.txt rechecks every recorded source hash and clean status.

The 13 earlier non-performance lane results on e7eabc8 remain applicable to their unchanged semantic subjects: complete recovery, interruption boundaries, delayed/inflight outcomes, concurrency, rebuild, bounded retry, corrupt imports, correctness and isolation. Their reports are under ../formal/{01-complete,02-before-attempt,03-before-write,04-after-commit,05-inflight,06-old-revision,07-concurrency,08-rebuild,09-retry-bound,10-invalid-import,11-gates,13-correctness,14-isolation}. Lanes 06 and 09 use report.txt; the others use report.md. carry-forward.txt and carry-other.txt identify these historical receipts. Historical lane 11's 671-test full check is evidence on e7eabc8, not a freshly rerun full check on 3aae662. Root separately owns the updated final full gate. Fresh functional checks below cover the changed CLI.

## Fresh functional evidence

functional-retry/focused-tests.txt records 47 focused tests passed, including workspace/root/command help and missing/unknown-command errors. All ten actual recovery CLI scenarios exit 0 and every emitted expected match is true, recorded individually under functional-retry/cli-recovery-*.txt and functional-results.json:
complete, before-attempt, before-write, after-remote-commit, lookup-absent-inflight, delayed-old-revision, concurrent-review, rebuild, retry-bound and invalid-import.

The evaluator's source computes actual behavior independently of request.expected, which is used only for final matching. validation-source.txt and source-read.txt establish fault positions and phase timing boundaries.

Nested normal CLI transcripts were read directly. Complete registers a verified pure artifact with no missing checks at revision 1, persists approval as local actor operator at revision 2 despite source-impostor metadata, and returns stale_revision exit 1 on repeated approval without advancing revision. Recovery reopens one confirmed remote effect. Rebuild's fresh interpreter retains one answered and one open task, due time 2026-01-02T00:00:00+00:00, one business decision and two completed work records, with matching state hash. Invalid-import nested calls exit 2 for artifact_corrupt, event_version and workspace_version; actual reports the original corrupt bytes preserved. read-functional.txt and final-integrity.txt retain the full nested stdout/stderr/status.

This is evaluator-owned deterministic adapter and SandboxWorkspace protocol evidence. Normal activation of the effect program remains unavailable because missing verification checks block it. No production authentication, live integration, standing-authority dispatch, UI, live-model or compiler-learning capability is claimed.

## Performance observations

All times are seconds, RSS is bytes. Every supported timed command exits 0 and has valid UTC drift. measurements.json retains all 23 scheduled measurements, exact timer fields, CPU user/system seconds and status. Individual receipts record exact argv, revision, cwd, clean status, stdout, stderr and exit.

The first trunk CLI invocation after dependency setup, before any other trunk CLI command, completed help in 0.414299542 seconds with 30,720,000-byte RSS. cold-trunk-help.txt proves both. Cold means first CLI in this fresh worktree with dependencies warmed, not a flushed OS cache. This is a complete new cold observation, not a replacement for the original missing-RSS observation.

Trunk workspace exits 2 with argparse invalid-choice workspace. Identical frozen recovery bytes exit 2 with scenario_error requiring the older format fields; no output directory is created. These are unsupported capabilities, not passes or valid recovery performance comparisons. Parent e7eabc8 supports the input, so all five parent/head workload pairs are measured.

| Pair | trunk help wall | head help wall | trunk RSS | head RSS |
| --- | ---: | ---: | ---: | ---: |
| 1 | 0.091556625 | 0.083547750 | 30556160 | 30539776 |
| 2 | 0.074330959 | 0.082434542 | 30556160 | 30588928 |
| 3 | 0.072568667 | 0.076661709 | 30523392 | 30539776 |
| 4 | 0.078973375 | 0.072029792 | 30523392 | 30474240 |
| 5 | 0.093296250 | 0.086730167 | 30572544 | 30507008 |

Startup median wall trunk 0.078973375, head 0.082434542, ratio 1.043827011, +4.383%, PASS <=1.20. Ranges trunk 0.072568667–0.093296250, head 0.072029792–0.086730167 overlap.
Startup median RSS trunk 30,556,160, head 30,539,776, ratio 0.999463807, PASS. Ranges trunk 30,523,392–30,572,544, head 30,474,240–30,588,928.

| Sample | durable append | reopen/rebuild | recovery | inner workload | full CLI | RSS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| parent 1 | 3.617777 | 1.504410 | 1.318468 | 6.440655 | 7.184710 | 311951360 |
| head 1 | 4.117936 | 1.519740 | 1.307615 | 6.945291 | 7.174634 | 307150848 |
| head 2 | 3.990693 | 1.504443 | 1.300542 | 6.795678 | 7.011459 | 306528256 |
| parent 2 | 3.893766 | 1.530681 | 1.315089 | 6.739536 | 6.968413 | 308559872 |
| parent 3 | 3.698198 | 1.521295 | 1.308374 | 6.527867 | 6.776980 | 308215808 |
| head 3 | 3.666828 | 1.503026 | 1.238366 | 6.408220 | 6.634448 | 308264960 |
| head 4 | 4.079656 | 1.497225 | 1.217585 | 6.794466 | 6.996325 | 306757632 |
| parent 4 | 3.618646 | 1.519189 | 1.392060 | 6.529895 | 6.742703 | 305725440 |
| parent 5 | 3.904382 | 1.511806 | 1.245732 | 6.661921 | 6.864699 | 310050816 |
| head 5 | 3.826085 | 1.510530 | 1.260875 | 6.597490 | 6.812295 | 307429376 |

Inner workload median parent 6.529894958, head 6.794465541, ratio 1.040516821, PASS <=1.20. Ranges parent 6.440655167–6.739536042, head 6.408219666–6.945290875.
Full CLI median parent 6.864698667, head 6.996325042, ratio 1.019174385, PASS. Ranges parent 6.742703208–7.184710334, head 6.634447709–7.174634292.
RSS median parent 308,559,872, head 307,150,848, ratio 0.995433547, PASS. Ranges parent 305,725,440–311,951,360, head 306,528,256–308,264,960.

Every head sample independently passes inner workload <=10 seconds, full CLI <=20 seconds, RSS <=536,870,912 bytes. Maxima are 6.945290875 seconds, 7.174634292 seconds and 308,264,960 bytes, 293.984375 MiB.

Head phase medians and ranges:
durable append 3.990693292, 3.666827666–4.117936458;
reopen/rebuild 1.504443125, 1.497225042–1.519739709;
recovery 1.260875125, 1.217584916–1.307614708.
Parent phase medians and ranges:
durable append 3.698197916, 3.617776667–3.904382333;
reopen/rebuild 1.519188583, 1.504410458–1.530680875;
recovery 1.315088667, 1.245732417–1.392060333.
Phase medians need not sum to median workload. Full precision remains in each actual.json and measurements.json.

## Real work, boundaries and limiter

The unchanged inner timer starts before Workspace creation/setup and includes verified artifact registration, 1,000 approvals, durable attempts, 1,000 remote commits with injected lost confirmations, close, reopen/rebuild and reconciliation. It ends after final state inspection/hashing and close. It excludes input parsing, output-directory setup, initial adapter table creation and final JSON serialization. Full CLI includes those costs, uv startup, imports and completion.

validate-parent.txt and validate-head.txt independently read all ten timed databases outside paired timing, using each revision's own interpreter/source. Every sample has 18,008 contiguous events from 1 to 18,008, one artifact, SQLite integrity_check ok, 1,000 applied remote rows with 1,000 distinct operation IDs and 1,000 distinct attempt IDs. Actual and expected match. Each fresh-process ordinary Workspace reopen finds 1,000 confirmations, zero unresolved attempts, revision 18,008, state SHA256 3f57068aee2c94abb4afb444d6f798581ad03fcd9558f1282a2da2225897f098. Database bytes remain unchanged after readback. The two outside-timing validation processes overlapped inadvertently; no measurement or profile ran during them, so no timed pair is affected.

The earlier e7eabc8 cProfile remains applicable to byte-identical recovery/persistence/codec/adapter code. limiter-evidence.txt reads the actual historical profile receipt, not only its conclusion. It shows Workspace._append 4.910 seconds cumulative, _refresh 4.492, codec decode 3.499; SQLite execute 2.362 self and executemany 0.658 self. Nested cumulative values cannot be added. This is serial durable SQLite transaction and typed replay work, using shipped synchronous=FULL settings, rather than a load-generator or remote-network result. Historical instrumented times are diagnostic only and excluded from this round's budget statistics. No fresh profile or altered transaction tuning was substituted for shipped behavior.

One head sample has 3.923337 user +2.336902 system seconds over 6.996325 wall. Durable append is the largest phase. The work cannot simply double without reducing serial durable transaction and encoding/replay costs. Full CLI is measured alongside the inner phase, and database verification rules out fast errors, skipped work, no-op/cached recovery and unused results. No production throughput or speedup is inferred.

Host initial uptime load was 4.57/4.40/4.53. os.cpu_count confirms 10 logical CPUs. End snapshot load 3.74/4.38/4.52, QEMU 86.2% CPU, WindowServer 22.6%, cmux 15.3%. User processes were not stopped. These snapshots do not prove per-sample interference. Alternating order and all ranges remain visible. Root released the CPU barrier before measurements and performed no heavy work during the schedule.

## Preserved failures and final state

- functional.txt failed after the first focused-tests and first CLI receipts hit sandbox uv-cache access denial. The runner then tried to read missing actual.json and raised FileNotFoundError. focused-tests.txt and cli-recovery-after-remote-commit.txt are retained. These are infrastructure/verifier failures, not expected product refusals or passes.
- functional-escalated.txt reran under authorized cache access, using a new functional-retry directory and unique receipts; all 47 tests and ten scenarios passed.
- frozen-schedule.txt includes a sandbox-denied sysctl read. Uptime succeeded; later final-host.txt independently confirms CPU count 10 using os.cpu_count and records actual processes.
- other-lane-reports.txt exited 1 because two guessed historical directory names were wrong. progress.txt and carry-other.txt locate and read the actual 06-old-revision and 09-retry-bound reports.
- Trunk's two exit-2 unsupported refusals are expected limitations, never recovery passes.
- Clock-invalid and child-failure controls are expected nonzero statuses, retained in timer-controls.txt.
- Initial inspection reads before setup did not use the receipt helper; all substantive functional, timed, database, source-integrity and final checks have unique record.py transcripts. The initial full commit diff and skills were displayed directly.
- No product source edits, commits, pushes, fuzz campaign, head-code copying into baselines or model-network calls were performed by this verifier.

final-integrity.txt confirms exact revisions, all source hashes, identical locks and empty git status in all three worktrees. The original failure remains recorded. Final current-head predicates PASS within the limits stated above. Root must combine this with all other lane and final gate evidence.


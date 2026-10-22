# M1-07 lane 12 performance

Verdict: ISSUES. All five complete head recovery samples pass the unchanged absolute gates. The declared startup wall metric exceeds the 20% regression gate, with timer-resolution uncertainty. The original cold sample lacks RSS. Unsupported recovery baselines remain unavailable comparisons, never passes.

## Revisions and input

- Head: e7eabc89ac47e6abb870e4e4f4306dc891b53217.
- Parent, base, frozen trunk: 80e60aac6ab78017020e5fce4c625c5fcb169ac1.
- Stable patch ID: 98794acdc178e34957554428ff611fd4825b926d.
- Frozen scenario: recovery-size-1000.json in this directory, 253 bytes, SHA-256 21e810095b0f1306cdf7cf76429fc221a9ee6f9134169ff2c9ded20d2d0127af.
- Identical uv.lock SHA-256 on all three revisions: 80663649dc0d95981af2122c4e86ec3b795313875263ea8bdc00dbb39d077950.
- measure.py SHA-256: 0f54e4e8238042894d9b3ded4dd76273343662c4467f7df802b7a881f16064bb.
- measure-escalated.py SHA-256: b9d0fcf34f68f0cb6f87a47726cdfdac661c12a2f12800ca714d7488b26bb1a5.

## Environment and method

macOS 26.5.1 arm64, 10 logical CPUs, Python 3.13.11, uv 0.11.31, detect-secrets 1.5.0. Setup uses uv sync --frozen --all-groups --python 3.13 at each detached worktree. Initial uptime load averages were 4.94, 5.28, 5.09. Root released the CPU barrier after all other heavy verification ended. Measurements ran serially. This is a local synthetic workload, not a production performance claim.

All measurements invoke the installed normal CLI through uv run dex. UV_OFFLINE=1 prevents dependency network access; the recovery route is deterministic local SQLite and has no model calls. Each sample has a fresh process, output directory, workspace.db, and remote.db. No head source was copied into parent or trunk.

The external command is /usr/bin/time -l -o TIME_FILE uv run dex ARGS, wrapped by the existing record.py receipt helper. Every receipt records exact argv, revision, dirty status, stdout, stderr, status, and elapsed time. macOS maximum resident set size is bytes, converted to MiB with 1 MiB = 1,048,576 bytes. It is a fresh per-command process-tree maximum, not cumulative RSS from a reused Python evaluator.

The first series starts with the first trunk CLI invocation after dependency setup. No OS cache flush occurred; cold means first CLI invocation in this fresh worktree, not a cold filesystem or interpreter installation. That original sample completes help in 0.54 seconds, but the time wrapper cannot query kern.clockrate in the sandbox, exits 1, and produces no RSS. The actual help output is present. This original cold observation is incomplete and is not a pass.

The escalated 00-cold-trunk-help filename is inherited from the script, but its content is a warmed retry, not the original cold measurement. It completes in 0.15 seconds with 30,670,848 bytes RSS. A fresh additional worktree could establish another first-invocation scope, but cannot recreate the machine cache state of the original cold invocation. This lane makes no complete cold-RSS claim.

Each series next attempts missing workspace behavior and identical recovery bytes at trunk, then five help pairs in order T/H, H/T, T/H, H/T, T/H. It then attempts identical recovery bytes at parent. The parent cannot execute them, so no parent/head recovery comparison is manufactured. Five fresh head recovery samples follow.

## Recovery timing boundaries and real work

Source receipt source-recovery.txt records src/dex/eval/recovery.py. durable_append starts immediately before creating the local workspace and includes setup, registration, 1,000 approvals, durable dispatch intent, 1,000 remote commits, injected lost confirmations, and workspace close. reopen_rebuild includes reopening and replaying persisted events. recovery includes reconciliation of all uncertain operations, final state inspection and hashing, and closing the workspace. recovery_workload is the contiguous sum of these three phases.

The summed workload excludes scenario parsing, output-directory creation, initial remote table creation, and final JSON serialization. External whole-CLI wall and RSS include these, uv startup, imports, and CLI completion. No source timing phase was replaced or budget expanded.

Every complete sample exits 0 and matches all five scenario expectations: 1,000 remote writes, 1,000 confirmed effects, 1,000 unresolved attempts before reopening, zero unresolved afterward, and replay equality. Direct SQL inspection finds 18,008 event rows, one artifact, and 1,000 applied remote rows with 1,000 distinct operations and 1,000 distinct attempt IDs. A separate fresh process reopens all ten unprofiled databases and independently confirms 1,000 confirmations, zero unresolved, revision 18,008, and state hash 3f57068aee2c94abb4afb444d6f798581ad03fcd9558f1282a2da2225897f098. See durable-validation.txt.

This uses the evaluator-owned deterministic adapter and SandboxWorkspace. It proves recovery protocol behavior. Normal activation of this effect program remains unavailable because missing verification checks keep it blocked.

## Individual recovery observations

All units below are seconds except RSS bytes. No valid slow observation was discarded. A wrapper exit of 1 in the initial series is the documented time/sysctl infrastructure error; underlying actual/expected outputs and later database validation prove the recovery work completed. Those rows remain incomplete for RSS.

| Series/sample | durable append | reopen/rebuild | recovery | summed workload | full CLI | RSS bytes | wrapper status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| initial 1 | 3.852788 | 1.592476 | 1.331730 | 6.776994 | 7.19 | unavailable | 1 |
| initial 2 | 3.822281 | 1.504135 | 1.599250 | 6.925666 | 7.14 | unavailable | 1 |
| initial 3 | 4.207521 | 1.503994 | 1.338862 | 7.050377 | 7.26 | unavailable | 1 |
| initial 4 | 4.342627 | 1.519679 | 1.311577 | 7.173883 | 7.37 | unavailable | 1 |
| initial 5 | 3.739934 | 1.530549 | 1.234280 | 6.504762 | 6.81 | unavailable | 1 |
| complete 1 | 4.026421 | 1.520108 | 1.216160 | 6.762689 | 6.97 | 305659904 | 0 |
| complete 2 | 3.531202 | 1.508221 | 1.211473 | 6.250895 | 6.45 | 308363264 | 0 |
| complete 3 | 3.943127 | 1.515725 | 1.256489 | 6.715342 | 6.91 | 308084736 | 0 |
| complete 4 | 3.657582 | 1.506734 | 1.228158 | 6.392474 | 6.59 | 307789824 | 0 |
| complete 5 | 3.614598 | 1.501381 | 1.325794 | 6.441774 | 6.64 | 307314688 | 0 |

Complete-series median/range: summed workload 6.441774 / 6.250895–6.762689 seconds; full CLI 6.64 / 6.45–6.97 seconds; RSS 307,789,824 / 305,659,904–308,363,264 bytes. Every sample is below 10 seconds summed workload, 20 seconds full CLI, and 536,870,912 bytes RSS. Maximum measured RSS is 294.08 MiB. Median durable append is 3.657582 seconds, reopen/rebuild 1.508221 seconds, and recovery 1.228158 seconds. Medians of phases need not sum to the median total.

## Startup comparison and gate disposition

| Sample | trunk seconds | head seconds | trunk RSS bytes | head RSS bytes |
| --- | ---: | ---: | ---: | ---: |
| 1 | 0.06 | 0.13 | 30457856 | 30605312 |
| 2 | 0.07 | 0.08 | 30539776 | 30425088 |
| 3 | 0.06 | 0.09 | 30474240 | 30474240 |
| 4 | 0.07 | 0.07 | 30490624 | 30457856 |
| 5 | 0.06 | 0.07 | 30425088 | 30539776 |

All ten complete-series startup invocations exit 0. Median external wall increases from 0.06 to 0.08 seconds, ratio 1.333333, failing the unchanged 1.20 gate. Median RSS is 30,474,240 bytes on both revisions, ratio 1.0, passing that comparison.

The wall difference is small, ranges overlap, and /usr/bin/time reports only hundredths of a second. Receipt wall medians are 0.076902875 seconds trunk and 0.091538667 seconds head, approximately 19.03% higher, but those include extra wrapper/receipt overhead. They do not replace the declared metric. A stable product slowdown is inconclusive; the declared rounded-wall gate failure remains recorded and prevents PASS. No post-result startup rerun was used to erase it.

## Unsupported baselines

escalated/01-trunk-workspace-unsupported.txt exits 2 with argparse invalid choice workspace; trunk only exposes eval. escalated/02-trunk-recovery-unsupported.txt and escalated/parent-identical-attempt.txt both exit 2 with scenario_error requiring the older fields format scenario_id programs commands expected. Neither creates its requested output directory. These are actual unsupported-format refusals, not setup failures. Same SHA and same frozen bytes were used at parent/trunk. No recovery speedup, regression ratio, or baseline pass is claimed.

## Limiter and relevance

The separately declared instrumented profile is retained in profile.txt, profile.pstats, and profile-summary.txt. It is diagnostic and excluded from budget statistics because cProfile changes execution cost. It produces correct output with a 12.484536-second instrumented summed workload, above the uninstrumented 10-second limit. This observation is retained; it does not replace or invalidate the five uninstrumented budget samples.

The profile locates costs in workspace._append, workspace._refresh and codec decoding during replay, plus SQLite execute/executemany and deterministic adapter transactions. Largest internal costs include SQLite execute 2.362 seconds and executemany 0.658 seconds; codec encoding/decoding and type checks also consume substantial CPU. The first complete sample reports 3.82 user and 2.27 system seconds over 6.97 real seconds. This is serial local persistence and replay work, with no saturated load generator or remote network. The probe uses shipped transaction/durability settings, including synchronous=FULL; no tuning or source optimization was performed.

1,000 confirmations over the median 6.441774-second full recovery workload is about 155 effects/second, accompanied by 18,008 durable event rows. The contiguous phase sum, all expected outputs, remote SQL uniqueness, and independent replay establish that the timed work happened. These are synthetic fixture results only.

## Every failed attempt and disposition

- setup-worktrees.txt failed to create Git metadata under the sandbox. setup-worktrees-escalated.txt succeeded at exact pins. No product defect inferred.
- read-plan.txt, read-input-source.txt, read-engine.txt failed because the worktree was not yet created. Successful later source/docs receipts replace the missing reads; failures are preserved.
- sync-head.txt, sync-parent.txt, sync-trunk.txt failed opening the external uv cache. Their respective escalated retries installed identical locked dependencies successfully.
- The initial measurement series has 19 time-wrapper failures caused by forbidden kern.clockrate access, including cold help, unsupported attempts, ten startup samples, and five correct recovery workloads. All receipts, raw time files, initial samples.json, and output databases remain. No RSS pass is claimed. The script also failed during summary generation when attempting a median of missing RSS values; measurement-runner.txt retains that traceback.
- The escalated missing workspace and two recovery-format refusals are expected unsupported capabilities, not passing recovery comparisons.
- The complete startup wall ratio fails its declared 20% threshold with resolution uncertainty. No limit changes or selective sample removal occurred.
- The profile's instrumented workload exceeds 10 seconds and is excluded only under the instrumentation exclusion stated before the run, not because of its value.

## Evidence and cleanliness

Every verification/read command after worktree preparation uses record.py. Exact measured argv and individual stdout/stderr/status are in each series' 00-cold-trunk-help.txt, 01-trunk-workspace-unsupported.txt, 02-trunk-recovery-unsupported.txt, startup-N-SIDE.txt, parent-identical-attempt.txt, and recovery-N-head.txt. Each has its separate .time.txt. The original and escalated measurement-runner receipts retain the full orchestrations.

Machine-readable data: samples.json retains every original attempt; escalated/samples.json retains every complete retry; escalated/metrics.json contains complete-series medians, ranges, all absolute predicates, and startup gate ratios; manifest.json and escalated/manifest.json hold revision/input hashes. Every workload has actual.json and expected.json. durable-validation.txt embeds the full machine-readable ten-database validation result. report-data.txt and final-observations.txt preserve initial timing values, precise receipt values, unsupported output absence, and script hashes.

Source files stayed unchanged. Final git status --porcelain is empty in head, trunk, and parent worktrees in durable-validation.txt. No commits, pushes, product optimizations, fixture changes, or head-source copying occurred. Evidence on 80e60aa is explicitly baseline-only; all head recovery observations name e7eabc8. This lane does not declare the PR stack ready.

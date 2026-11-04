# M1-13 performance plan

The goal is to prove the M1-13 scoring and reporting budgets in one PR, without implementing process reference programs or starting M1-14.
This file records proposed measurements. No performance result is claimed here.

## Revisions and preparation

Trunk and the actual merged M1-12 dependency are both e990a3387fa2b1c8bce9e369e10c99db7079f89b at preparation.
The code-ready head is b40c6beea0b66e1c40de8d641858f8c749a160ea.
The prepared checkouts are `/private/tmp/dex-m1-13-verifier/trunk`, `parent`, and `head`.
Their local clone remotes point at a local source checkout and do not establish GitHub state.
Every measurement uses the explicit pinned revision recorded in its receipt and freeze file.

Python 3.13.11 and uv 0.11.31 are prepared separately from CLI invocation.
The unchanged recorder, Timer V2, and network-denying audit hook are reused from the tracked dependency tools.
Their exact content hashes remain in the preflight receipts and will be included in the final freeze.
All formal command outputs are fresh durable directories below this verifier's evidence tree.

## Frozen workloads

The absolute workload is `score-size-10000` with exactly 10,000 cases and 100,000 ledger events.
It runs the actual `uv run dex eval --scenario FILE --out RUN` command, then the actual `uv run dex report RUN` command separately.
The evaluation interval includes scoring, persistence, and serialization.
The separate reporting interval includes recorded-result loading, report construction, and serialization.
The combined command cost is the sum of those complete command intervals.
Scoring's internal phase is measured separately and retains its explicit exclusions.
Every emitted case and ledger event is read and checked after timing.

The supported regression workloads are `uv run dex --help` and the existing `language-arithmetic` scenario.
The arithmetic scenario exercises the shared evaluator dispatch, checked-function execution, expected-result comparison, and persisted output path.
Both baselines already support those exact frozen input bytes.
No complete demo generation or historical performance matrix is repeated because M1-13 does not change fixture generation.
Existing generator behavior is covered by relevant functional checks and unchanged-content evidence.

The new scoring scenario and report command are invoked on both baselines to retain their actual unsupported refusals.
They receive no relative performance comparison and no invented baseline success.

## Schedule and gates

The first trunk `dex` invocation is a measured cold `uv run dex --help` after dependency preparation.
Each supported workload runs five trunk and head pairs, then five actual-dependency and head pairs.
Odd pairs run baseline before head. Even pairs run head before baseline.
The added 10,000-case scoring and reporting workload runs five head samples with fresh output directories.
Every scheduled sample and host-contention record remains preserved, including failures.
No unchanged workload is repeated to obtain a pass.

Scoring must finish within 10 seconds.
Report generation must finish within 5 seconds.
The complete evaluation and report commands together must finish within 20 seconds.
Every supported command's peak RSS must remain within 1 GiB.
The median wall-time and peak-RSS ratios must remain at or below 1.20 for each identical supported comparison.
Invalid clocks, unexpected nonzero exits, missing output, incomplete work, and failed readback fail the measurement.

## Exclusions and release barrier

Dependency installation, checkout preparation, frozen-input generation, artifact hashing, independent byte readback, and profiling stay outside timed intervals.
An excluded profile identifies the limiting source paths before a performance claim is accepted.
Process snapshots, load averages, CPU count, runtime versions, exact arguments, and individual timer records accompany the samples.
Formal timing starts only after functional checks and both reviews settle and root confirms other owned CPU-heavy jobs have stopped.
The complete frozen schedule, input identities, revisions, and tool hashes must exist before the cold trunk invocation.
Reporting publishes recorded measurements separately from the immutable scored outcome and names the exact workload and exclusions.

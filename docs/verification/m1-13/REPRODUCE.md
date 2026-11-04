# Reproduce M1-13

Run from a clean checkout at the product revision named in REPORT.md. Use Python 3.13 and uv 0.11.31. The final HANDOFF.json identifies the exact final head and carried evidence. All commands below use fresh output directories. Never overwrite an earlier receipt or sample.

## Evidence storage

Original raw evidence is retained locally under `/Users/varunvis/workspace/dev/dex/docs/verification/m1-13/`. The unchanged scanner rejects raw receipt hashes and path strings. Reports and reusable drivers are tracked; raw receipts and generated runs remain intact locally. `owner/049-raw-receipt-scanner.txt` records that decision. No scanner exemption or receipt rewriting was used.

The original M1-12 seed-7 collection is under `docs/verification/m1-12/verifier/round1/demo7-a/` in the original checkout. `verifier/preflight/032-input-reuse-proof.txt` binds its bytes to the unchanged generator, packet and admission implementation. Other machines may generate seed 7 once in a fresh directory with the actual merged M1-12 revision. That is setup outside performance intervals, not evidence that M1-13 references exist.

## Functional commands

Install dependencies once with `uv sync --locked --python 3.13`. Use the preserved recorder at `docs/verification/m1-10/scripts/record.py` for each verification command. It saves exact arguments, checkout, revision, stdout, stderr and exit status. Use `--out RECEIPT.txt --cwd CHECKOUT -- COMMAND...` and distinct receipt paths.

```sh
uv run pytest tests/eval/test_scoring.py tests/eval/test_report.py -q
make check
uv run dex eval --scenario tests/scenarios/score-correct-history-mistake.json --out RUN
uv run dex report RUN
```

Valid scored failures return 1 and leave a complete reportable run. Invalid inputs return 2 without publication. Reporting a valid failed evaluation returns 0 because reading its evidence succeeded. A traceback, missing output or setup failure never proves a rejection.

`verifier/scripts/live.py` freezes the ten checked-in scenario files, executes each real CLI evaluation and report, and checks exact case IDs, differences, ledger rows, buckets, distributions, coverage and identities. Its final lane repeats reporting in a fresh process and compares bytes. Supply an untouched baseline checkout at the merged dependency, a head checkout, the preserved recorder, a prepared uv cache, the network-denying hook directory, and `src/dex/eval/acceptance.md` as the acceptance source.

```sh
python docs/verification/m1-13/verifier/scripts/live.py freeze --checkout HEAD_CHECKOUT --baseline BASELINE_CHECKOUT --evidence FRESH_LIVE --recorder RECORDER --cache CACHE --hook HOOK --acceptance ACCEPTANCE
python docs/verification/m1-13/verifier/scripts/live.py baselines --checkout HEAD_CHECKOUT --baseline BASELINE_CHECKOUT --evidence FRESH_LIVE --recorder RECORDER --cache CACHE --hook HOOK --acceptance ACCEPTANCE
python docs/verification/m1-13/verifier/scripts/live.py scenarios --checkout HEAD_CHECKOUT --baseline BASELINE_CHECKOUT --evidence FRESH_LIVE --recorder RECORDER --cache CACHE --hook HOOK --acceptance ACCEPTANCE
```

The driver examples run from the repository root. Other verifier-script references in this document are relative to this evidence directory. HOOK is the preserved `docs/verification/m1-11/verifier/round2/scripts` directory. The hook denies model/network access and records its activation and attempted operations. Keep every driver command's own recorder receipt in addition to its child CLI receipts.

The principal transcripts are `01-score.txt`, `02-copied.txt`, `03-effect.txt`, `04-unresolved.txt`, `05-key.txt`, `06-context.txt`, `07-ledger.txt`, `08-buckets.txt`, `09-coverage.txt` and `10-report.txt`. Each report has a separate `-report.txt` receipt. `10-report-fresh-report.txt` records the repeat.

Run the actual reference route against both a bundle and its collection. Both must return the named missing-reference error and publish no run. No Bramblewick, Fennor or Veldren reference is installed by M1-13.

```sh
uv run dex eval BUNDLE --reference --out FRESH_RUN
uv run dex eval COLLECTION --reference --out FRESH_COLLECTION_RUN
```

`verifier/scripts/refusals.py` copies only the needed inputs to a guarded workspace, retains every mutation, and compares complete before/after snapshots for every named rejection. Pass `--checkout`, `--collection`, `--recorded-run`, `--evidence`, `--recorder`, `--cache`, `--hook` and `--live-driver`. The collection is the seed-7 collection manifest and the recorded run is a successful current-schema scenario run.

`verifier/scripts/delta_checks.py` rechecks all ten prior lane artifacts against literal assertions, proves the exact admission-only source delta, executes a fresh scoring run and reports it twice, and rejects ten preserved malformed evaluator copies through the real reference CLI. Its required arguments name both revisions, the original malformed copies, prior live runs, collection, and current checkout. Use `--help` for the complete argument list. The independent correctness probes are `correctness/probe_contracts.py`, `correctness/probe_boundaries.py` and `correctness/probe_fix_forward.py`. The isolation driver is `isolation/probe.py`. Their `--help` lists the explicit checkout, revision, artifact and output arguments. The review reports distinguish direct checks from evidence carried through exact unchanged blobs. Driver failures are preserved separately from product findings.

## Formal performance

Prepare clean `trunk`, `parent` and `head` checkouts beneath one CHECKOUTS directory. Trunk and parent must be the actual merged dependency recorded in REPORT.md, never the intermediate M1-12 implementation head. Warm dependencies with uv only. Do not invoke dex in the formal trunk checkout before the cold sample. Use a separate baseline checkout for untimed CLI refusals.

The frozen workload has exactly 10,000 cases, 100,000 distinct ledger events and 10,000 checked function calls. Scoring's internal timer excludes execution, ledger admission, identity hashing, persistence and reporting. Timer V2 separately measures the complete evaluation and reporting commands. Combined cost is the sum of those complete command intervals; peak memory is their maximum. Output readback and the separate profile are excluded from timed intervals.

The supported regression workloads are CLI help and the existing language-arithmetic scenario because this milestone changes CLI dispatch and shared scenario execution. Generator code is unchanged. Do not repeat the old generation performance matrix.

`verifier/scripts/performance.py` has three sequential actions, `freeze`, `run`, and `summarize`. All accept these arguments:

```sh
--evidence FRESH_PERF_PARENT
--checkouts CHECKOUTS
--recorder RECORDER
--timer docs/verification/m1-10/scripts/measure.py
--cache CACHE
--hook HOOK
--score-scenario tests/scenarios/score-size-10000.json
--regression-scenario tests/scenarios/language-arithmetic.json
--baseline-revision ACTUAL_MERGED_DEPENDENCY
```

The freeze writes the exact revisions, source bytes, input hashes, environment, tool hashes and ordered schedule before measurement. The run requires `--cpu-idle-authorized`; use it only after functional checks and both independent reviews settle and other owned CPU-heavy jobs stop. The schedule starts with trunk's cold CLI invocation, retains unsupported-command/scenario refusals, uses five alternating trunk/head and parent/head pairs for each supported workload, then five complete head evaluation/report pairs.

The unchanged limits are scoring 10 seconds, reporting 5 seconds, combined completion 20 seconds, peak RSS 1 GiB and supported identical-workload median wall-time/RSS ratio 1.20. Every sample must finish with the expected exit, valid clock, active audit and complete output. Keep all samples and before/after contention records. Do not rerun unchanged measurements to obtain a pass.

`performance_controls.py` and `readback_controls.py` validate the timer, recorder, network guard and deliberately corrupted readback cases before the formal workload. Summarization verifies the exact case-ID set, literal decision values, ten distinct events for every case, exact score rows, recorded hashes, and all supported arithmetic output bytes outside timed regions. Same-count corruptions and missing/changed arithmetic outputs are rejected by preflight controls. The results must match the frozen task list exactly. The separately excluded profile identifies limiting source paths.

Finally run `publish_measurements.py` with `--performance`, `--run`, `--checkout`, `--evidence`, `--recorder`, `--cache`, `--hook` and `--live-driver`. It checks immutable artifacts across all five runs, binds the measurement supplement to the selected run, invokes `dex report` twice in fresh processes, and proves scored artifacts and outcome remain unchanged. The report exposes exact samples, workload, exclusions and gate failures.

## Final applicability

After an evidence-only commit, compare every non-evidence tracked blob and stable product patch ID with the measured product revision. Run `make check` on the committed final head before pushing. Record exact GitHub head/base, CI, review triage, queue and auto-merge state in the durable final HANDOFF.json without another evidence commit. The operator reviews the CLI transcripts and lands the PR. M1-14 remains out of scope.

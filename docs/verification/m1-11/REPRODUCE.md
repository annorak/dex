# Reproduce M1-11 verification

Final product revision: 07747f2. The earlier failed formal run is pinned at 7377a3e. Trunk and the actual merged M1-10 dependency parent: 1015457.
Use Python 3.13 or newer and uv 0.11.31. Start from clean, pinned checkouts and existing output parent directories. Never reuse an output destination.

## Repository and live commands

```sh
uv sync --locked --python 3.13
make check
uv run pytest tests/demo/test_world_1.py -q
uv run dex demo build --world world-1 --seed 7 --out "$RUN/seed7-a"
uv run dex demo build --world world-1 --seed 7 --out "$RUN/seed7-b"
uv run dex bundle check "$RUN/seed7-a/world-1/bramblewick"
uv run dex bundle check "$RUN/seed7-a/world-1/fennor"
uv run dex demo build --world world-1 --seed 11 --out "$RUN/seed11-a"
uv run dex demo build --world world-1 --seed 11 --out "$RUN/seed11-b"
```

Run each of the seven committed scenario files with the actual evaluator command:

```sh
uv run dex eval --scenario tests/scenarios/world1-packet-bytes.json --out "$RUN/packets"
uv run dex eval --scenario tests/scenarios/world1-history-membership.json --out "$RUN/membership"
uv run dex eval --scenario tests/scenarios/world1-mistake-sets.json --out "$RUN/mistakes"
uv run dex eval --scenario tests/scenarios/world1-duplicate-snow-sets.json --out "$RUN/paths"
uv run dex eval --scenario tests/scenarios/world1-stream-opening.json --out "$RUN/stream"
uv run dex eval --scenario tests/scenarios/world1-key-independence.json --out "$RUN/key"
uv run dex eval --scenario tests/scenarios/world1-seed-variation.json --out "$RUN/seed"
```

The verifier scripts under `verifier/round2/scripts/` independently inspect every generated file, exact named membership and dates, XLSX metadata, complete postings and emitted scenario results. `check_artifacts.py` accepts a world path, `--packets`, `--repeat` and `--out`. Run it for both repeated seeds. `check_refusals.py` accepts `--checkout`, `--evidence`, `--recorder` and `--cache`; it creates fresh guarded filesystem and SQLite state and retains one receipt per refusal. It expects `sitecustomize.py` under the evidence directory's `scripts/` subdirectory.

`sitecustomize.py` is an evaluator-owned audit hook. It denies network access and optionally evaluator or original-bundle reads. Negative controls establish that each denial is active. `check_projection.py` reads the saved views and checks exact learning membership, the mixed export, provenance and all five permitted company-evidence destinations. The transcripts retain exact environment variables and arguments for these runs.

## Formal timing

Use three separate pinned checkouts named `trunk`, `parent` and `head` under one directory. Warm dependency installation separately. Do not invoke the trunk CLI before its frozen cold-start task. Stop local build, test and review processes before timing.

`verifier/round2/scripts/performance.py` takes actions `freeze`, `run` and `summarize`. Supply the same arguments to each action:

- `--evidence`: an existing, fresh evidence directory.
- `--checkouts`: the directory containing the three pinned checkouts.
- `--recorder`: `docs/verification/m1-10/scripts/record.py`.
- `--timer`: `docs/verification/m1-10/scripts/measure.py`.
- `--cache`: the prepared uv cache directory.
- `--input`: the complete seed-7 output directory.

The tracked recorder and Timer V2 are byte-identical to the preserved tools used in this run. Freeze copies complete input bytes and writes the command schedule before measurement. It records revisions, tool and source hashes, environment, all limits and the alternating pair order. The schedule includes the first cold trunk help invocation, five startup pairs against each baseline, actual unsupported baseline build refusals, five paired validations of both complete public bundles, and five head probes with two complete builds and both public checks.

Every task gets a separate receipt. Preserve all samples, failures and host-load records. Compare manifests and run `check_performance_artifacts.py` only outside timed intervals. A failed threshold or invalid clock remains a failure. Unsupported generation is reported as a refusal and receives no speedup comparison. Do not replace the dependency parent with an implementation commit.

The final fix changes only snapshot admission and its tests. Its affected schedule uses `verifier/round3/scripts/affected_performance.py` with `freeze` and `summarize`, plus `--evidence`, `--previous` and `--checkouts`. The previous directory is the preserved round-2 evidence. The original `performance.py run` executes the new freeze with the same recorder, Timer V2 and cache arguments. `verifier/round3/scripts/check_performance_artifacts.py` verifies the final outputs afterward.

That schedule contains sixty commands: five alternating validation pairs against each baseline, checking both companies, then five complete build/check-both/repeat probes. It carries the original cold-start, startup pairs and unsupported baseline refusals only with the unchanged-source proof. Restore the archived frozen inputs at the absolute paths named in the original freeze before replaying that recorded schedule; choose fresh output and evidence directories. For a new complete benchmark, use the original full schedule and fresh baseline checkouts instead.

`verifier/preflight_controls.py` preserves the one-time recorder and Timer V2 success, failure, allocation and clock-jump controls. Those controls were validated once and were not rebuilt for the final fix.

## Evidence archive

Raw receipts, proposed diffs, complete frozen inputs and evaluator manifests are retained unchanged locally under `/Users/varunvis/workspace/dev/dex/docs/verification/m1-11/`. Exact hashes in raw receipts can trigger the unchanged public scanner. The PR tracks scanner-compatible reports and reproducible scripts; it does not rewrite raw receipts or add scanner exemptions. The final report identifies the measured revision, final-head checks and any carried-forward evidence.

M1-10's owner-merged 21.67% startup regression remains failed against its 20% limit. Reproduction must not treat that result as a waiver for M1-11.

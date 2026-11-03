# Reproduce M1-12 verification

Run from the repository root with Python 3.13 or newer and uv 0.11.31. Use fresh output directories. Product revision: 499198c. Actual merged dependency and baseline: 5a6faaa.

```sh
uv sync --locked --python 3.13
uv run pytest tests/demo/test_world_2.py -q
uv run pytest tests/demo/test_world_1.py -q
make check
```

Create one new run directory beneath an existing directory, then generate and check the complete collection.

```sh
RUN=/absolute/existing/directory/m1-12-run
mkdir "$RUN"
uv run dex demo build --seed 7 --out "$RUN/seed7"
uv run dex bundle check "$RUN/seed7/world-1/bramblewick"
uv run dex bundle check "$RUN/seed7/world-1/fennor"
uv run dex bundle check "$RUN/seed7/world-2/veldren"
uv run dex demo build --seed 7 --out "$RUN/repeat"
uv run dex demo build --world world-2 --seed 7 --out "$RUN/world2"
uv run dex demo build --seed 11 --out "$RUN/seed11"
```

Compare every relative file path and byte in the two seed-7 collections. Compare the Veldren subtrees from the standalone and complete builds. In a separate checkout pinned to 5a6faaa, generate World 1 with seed 7 and compare both World 1 subtrees with the head collection. The World 1 generator version remains unchanged.

The public checker accepts the existing World 1 unresolved register mappings as unresolved evidence; it does not grant mapping confirmation or execution authority. Veldren has no unresolved sources.

Run each supplied scenario through the actual evaluator CLI:

```sh
for SCENARIO in world2-packet-bytes world2-history-membership world2-nested-cohorts world2-wait-schedule world2-mistake-evidence-sets world2-stream-schedule world2-isolation world2-seed-variation world2-unfamiliar-status world2-changed-summary
do
  uv run dex eval --scenario "tests/scenarios/$SCENARIO.json" --out "$RUN/$SCENARIO"
done
```

Inspect both actual.json and expected.json in every scenario output. Every exact predicate must match. The outputs remain fixture_requirements and execution_claimed remains false. For build reuse, the existing scenario contract accepts input_world and seed11_world paths. The verifier freezes copies of the checked-in scenarios with only those paths added, preserving all expected predicates.

The [live driver](verifier/scripts/live.py) runs the real commands with the unchanged recorder, fresh outputs, readback assertions and refusal checks. Its recorded invocations preserve exact arguments. The [specification checklist](specification-checklist.json) supplies named sets and dates. The independent [correctness](correctness/round1/report.md) and [isolation](isolation/round1/report.md) reports explain their separate probes.

Use the unchanged tracked tools:

- docs/verification/m1-10/scripts/record.py
- docs/verification/m1-10/scripts/measure.py
- docs/verification/m1-11/verifier/round2/scripts/sitecustomize.py

The audit hook denies model-network access and can deny evaluator or original-bundle reads. Negative controls establish that those denials are active. Saved learning views must reopen with the original bundle denied. Source observations remain data and cannot supply authenticated authority.

The [performance driver](verifier/scripts/performance.py) has freeze, run and summarize actions. Prepare separate checkouts named trunk, parent and head, pinned to the recorded revisions. Install dependencies without invoking the trunk product command. Freeze all source/input bytes, tool hashes, revisions, environment, limits and command order before run. Its first timed command is the untouched trunk checkout's CLI help.

The frozen schedule contains five alternating trunk/head and five parent/head comparisons of supported startup and World 1 generation plus public validation. Generation, two-check validation and their combined costs are gated separately using the same samples. It records actual unsupported default and World 2 refusals on both baselines. Five head probes each build the complete collection, check all three public bundles, and build World 2 alone. Native exports and serialization are inside the command intervals; byte comparisons are outside timing.

Keep every sample and host-contention record. The limits are World 2 generation at most 5 seconds, complete generation plus three checks at most 60 seconds, peak RSS at most 1 GiB, and supported median wall/RSS regression at most 20 percent. Profiling is a separate excluded run. Never rerun unchanged samples to seek a passing result.

The final report links the frozen schedule, individual transcripts, readbacks and final post-commit handoff. Raw receipts and generated artifacts are retained in the local evidence tree under docs/verification/m1-12. A passing report does not establish reference execution, learned-stream execution, trust or touch-count acceptance.

The packaged independent review scripts use required arguments rather than the original machine-specific constants. Run them from a clean checkout at the product revision, with the current scripts available at an absolute path. Create a fresh review directory, build World 2 into its world child, then run:

```sh
uv run python "$SCRIPTS/../../correctness/round1/probe_native.py" \
  --bundle "$REVIEW/world/world-2/veldren"
uv run python "$SCRIPTS/../../correctness/round1/probe_boundaries.py" \
  --root "$REVIEW" --packets "$PACKETS" --base 5a6faaa --head 499198c
uv run python "$SCRIPTS/../../isolation/round1/probe.py" \
  --root "$FRESH_ISOLATION_OUTPUT" --base 5a6faaa --head 499198c
```

SCRIPTS is the absolute verifier/scripts directory, PACKETS is the supplied Veldren packet directory, and FRESH_ISOLATION_OUTPUT must not exist. The correctness boundary probe creates late-staging-failure beneath REVIEW, so do not reuse an earlier probe output directory. The two reviewers proved assertion/body identity after argument parameterization; original scripts and exact invocation receipts remain local.

The evidence-only final commit carries product verification only when all non-evidence blobs are identical to the product revision and the actual dependency remains applicable. It receives its own make check and CI. Consult the local post-commit HANDOFF.json for those final results and exact hashes. Raw .txt receipts, generated outputs, frozen timing inputs and HANDOFF.json are local-only because unchanged scanning rejects representative raw hashes and path strings; the tracked reports and scripts contain no scanner exemption.

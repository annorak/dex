# Independent M1-12 verification

The goal is one PR for Veldren and the deterministic three-company demo collection, stopping at M1-12 without merging.

PASS at pinned product head `499198c`. Trunk and the actual merged M1-11 dependency are both `5a6faaa`. Exact revisions, working-tree state, arguments, stdout, stderr and exit statuses remain in the linked raw receipts. This verifier authored no product, test or scenario changes. The later evidence-only commit still requires its own committed-head gate and unchanged-product proof.

## Fourteen separate outcomes

| Outcome | Result | Receipts |
| --- | --- | --- |
| Repository gate | PASS, 877 tests and all repository checks | [committed-head gate](004-make-check.txt) |
| Lane 1, default build | PASS, all three companies; actual baseline refusals retained | [trunk role](01-demo-trunk.txt), [parent role](01-demo-parent.txt), [head](01-demo.txt), [ordered repeated head](02-repeat.txt) |
| Lane 2, complete repeat | PASS, all 32,287 paths and file bytes identical | [repeat](02-repeat.txt), [byte comparison](driver-repeat.txt) |
| Lane 3, public admission | PASS, evaluator reads denied; all 30,860 World 1 subtree files match the actual dependency | [Veldren](03-admission.txt), [Bramblewick](03-admission-bramblewick.txt), [Fennor](03-admission-fennor.txt), [comparison](driver-admission.txt) |
| Lane 4, packets | PASS, two exact packets, no hidden rule or evaluator labels | [scenario](04-packets.txt), [independent readback](008-artifact-readback.txt) |
| Lane 5, history | PASS, exact 48 openings and full 36/12 split | [scenario](05-history.txt), [readback](008-artifact-readback.txt) |
| Lane 6, nesting | PASS, exact overlapping multi-site, both-service and waiting memberships | [scenario](06-nesting.txt), [readback](008-artifact-readback.txt) |
| Lane 7, waits | PASS, exact three/five-day waits, request identities, responses and times | [scenario](07-waits.txt), [readback](008-artifact-readback.txt) |
| Lane 8, independent keys | PASS, exact mistakes and evidence sets, frozen keys and expected payloads | [scenario](08-keys.txt), [readback](008-artifact-readback.txt) |
| Lane 9, stream | PASS, sixteen exact fixture schedules and cutoffs, no execution claim | [scenario](09-stream.txt), [readback](008-artifact-readback.txt) |
| Lane 10, isolation and seed | PASS, saved learning boundary and permitted seed variation | [isolation](10-isolation.txt), [variation](10-variation.txt), [full seed 11](10-seed11-collection.txt), [saved views](009-projection-readback.txt), [seed 11 readback](010-seed11-readback.txt), [bytes](011-seed11-byte-proof.txt) |
| Performance | PASS, all five absolute probes and every supported comparison | [summary](formal/023-performance-summary.txt), [full artifact readback](formal/025-performance-artifacts-corrected.txt) |
| Correctness review | Separate reviewer PASS at this head | [correctness](../../correctness/round1/report.md) |
| Isolation review | Separate reviewer PASS at this head | [isolation](../../isolation/round1/report.md) |

[coverage.json](coverage.json) retains the twelve verifier outcomes and two separate reviews. The exact requested `uv run pytest tests/demo/test_world_2.py -q` passes all 44 tests in [006-world2-exact-focused.txt](006-world2-exact-focused.txt). The combined World 2 and World 1 focused invocation passes 85 tests in [005-focused.txt](005-focused.txt).

## Functional evidence

The real default CLI creates Bramblewick, Fennor and Veldren. The same seed, packet bytes and declared versions produce the same complete collection bytes. The separate untimed base checkout supplies both baseline roles at the exact same merged revision. Its named default refusals precede the repeated complete head build. The formal trunk and parent clones remain untouched by dex until the frozen performance schedule starts.

The standard-library [artifact checker](../scripts/check_artifacts.py) imports no dex evaluator code. It reads all 708 Veldren public sources and their extraction hashes, native client and employee CSV rows, all 64 keys, nested identities, exact dates, waits, owner decisions, exact-change approvals, configurations and effects. Historical mistake IDs are exactly H008, H019, H031 and H044. Learning evidence is H006, H018 and H030; H042 remains exam evidence. Comparison controls reject changed bytes, changed paths, swapped membership and a missing required file.

Real CLI projections refuse before history adequacy. The confirmation is absent immediately before its October 1 delivery and present at 10:00, retaining its separate October 1, 2025 effective date. Saved views contain exactly H001 through H036 and reopen with the original collection and evaluator reads denied. Exam, future, evaluator and other-company evidence is absent. Prompts, diagnostics, caches, training tests, compiler recordings and library serialization obey the same boundary. [Projection readback](009-projection-readback.txt) and [audit readback](011-seed11-byte-proof.txt) retain the results. The separate isolation review also checks serialized rejection boundaries, every projected citation and imported authority.

The full seed-11 collection passes independent Veldren readback, and its Veldren subtree matches the separately generated seed-11 World 2 output byte for byte. Only permitted display-name data and dependent content identities vary. The separate [status](11-status.txt) and [changed-summary](12-summary.txt) fixture scenarios pass without claiming execution.

Fifteen named nonzero rejection probes preserve existing files, SQLite state, symlinks and exact path membership. They cover invalid selectors, invalid seeds, both worlds' missing packets, invalid inputs and existing or unsafe destinations. See the [driver](driver-refusals-v2.txt), [Veldren packet refusal](refusals-v2/refusal-world2-packet.txt), [state readback](016-refusal-readback.txt) and [exact path readback](022-refusal-exact-paths.txt). Setup failures do not count as rejection evidence.

The stream remains fixture requirements. Exact January 10 and final states, 19 and 40 touches, weekly totals and zero runtime model calls are expected schedules. Reference execution, compilation, learned-stream acceptance, trust execution, library acceptance, repairs and UI acceptance remain unavailable.

## Formal performance

All 110 frozen commands finish with valid Timer V2 clocks and expected exits. No sample is replaced or discarded. The recorder and Timer V2 are unchanged. The [freeze](formal/performance/freeze.json), [run](formal/020-performance-run.txt), [summary](formal/performance/summary.json) and [readback](formal/performance-artifacts.json) retain exact tools, source bytes, inputs, order and individual samples.

| Sample | Default build plus three checks, seconds | World 2 generation, seconds | Peak RSS for absolute probes, bytes |
| --- | ---: | ---: | ---: |
| 1 | 37.773037126 | 1.040326584 | 388235264 |
| 2 | 37.318307001 | 1.006840125 | 382337024 |
| 3 | 37.978600418 | 1.047055292 | 392036352 |
| 4 | 42.677628209 | 0.983636291 | 394805248 |
| 5 | 39.021094916 | 0.972470292 | 385466368 |

Every complete default build and all three public checks fit 60 seconds. Every complete World 2 generation fits 5 seconds. The maximum RSS across every supported command is 405078016 bytes, below 1 GiB.

Each supported comparison uses five alternating pairs per baseline. Build and check components use the same already scheduled three-command samples as the combined World 1 workload.

| Workload | Baseline | Baseline wall median, seconds | Head wall median, seconds | Wall change | RSS median change |
| --- | --- | ---: | ---: | ---: | ---: |
| Startup | trunk | 0.116872542 | 0.113691333 | -2.722% | -0.054% |
| Startup | actual dependency | 0.117165041 | 0.116142625 | -0.873% | +0.161% |
| World 1 build | trunk | 20.216069709 | 20.579881291 | +1.800% | -0.174% |
| World 1 build | actual dependency | 21.074208791 | 21.089898666 | +0.074% | +0.273% |
| Both World 1 checks | trunk | 16.452285709 | 16.601324250 | +0.906% | +0.122% |
| Both World 1 checks | actual dependency | 16.498083083 | 15.917477833 | -3.519% | -0.038% |
| World 1 build plus checks | trunk | 36.606577959 | 37.029347875 | +1.155% | -0.174% |
| World 1 build plus checks | actual dependency | 37.736667291 | 36.924618374 | -2.152% | +0.273% |

All wall and RSS median ratios fit 1.20. Individual samples and ranges remain in the summary. These comparisons establish the regression gate, not a World 1 optimization.

Cold trunk help is its formal checkout's first dex invocation and takes 0.462372959 seconds. The four unsupported default or World 2 baseline commands produce actual named refusals. They receive no generation comparison. Full CLI intervals include native writing, serialization and public validation; byte hashing occurs afterward. All 30 persisted outputs match independently checked bytes and all 55 public checks report exact declared cases, sources and deliveries.

The host has ten logical CPUs. Complete process snapshots and one-minute load range 7.52734375 through 25.98828125 remain in the samples. Root reports one 1.26-second read-only file inventory during the run. That activity is retained and no sample is excluded. All owned build, test and review jobs had stopped. An [excluded head profile](014-excluded-profile.txt) identifies native email/PDF extraction and file I/O as dominant work. It is not an acceptance measurement.

## Reproduction

Use fresh pinned checkouts named `trunk`, `parent`, `head` and a separate untimed baseline checkout. Use Python 3.13+, uv 0.11.31 and fresh output directories. Warm dependencies separately with `uv sync --frozen --all-groups --python 3.13`. Keep formal trunk and parent dex uninvoked until timing. The baseline and seed-7/seed-11 setup commands are preserved in the linked receipts.

The portable script directory is `docs/verification/m1-12/verifier/scripts`. The unchanged tools are `docs/verification/m1-10/scripts/record.py`, `measure.py`, and `docs/verification/m1-11/verifier/round2/scripts/sitecustomize.py`. [026-hook-reproduction-identity.txt](026-hook-reproduction-identity.txt) confirms the hook matches the tracked copy.

After creating `demo7-a` and `demo11` under a fresh evidence directory, run each live action with the same arguments:

```sh
python3.13 "$SCRIPTS/live.py" ACTION \
  --checkout "$CHECKOUTS/head" --evidence "$EVIDENCE" \
  --baseline "$BASELINE_WORLD1" --recorder "$RECORDER" \
  --cache "$CACHE" --hook "$HOOK"
```

Actions are `scenarios`, `repeat`, `admission`, `projections` and `refusals`. Each records its real CLI children separately. The artifacts checker accepts `WORLD --packets PACKET_ROOT --out SUMMARY --controls`. The projection checker accepts `--evidence EVIDENCE --world WORLD --out SUMMARY`; run it using the head virtual environment with the hook's original-root and evaluator-read denials enabled. The extra Veldren-packet launcher retains its complete argv in its receipt.

Use these identical arguments for `performance.py freeze`, `run` and `summarize`:

```sh
python3.13 "$SCRIPTS/performance.py" ACTION \
  --evidence "$EVIDENCE/formal" --checkouts "$CHECKOUTS" \
  --recorder "$RECORDER" --timer "$TIMER" --cache "$CACHE" \
  --hook "$HOOK" --input "$BASELINE_WORLD1" --baseline-revision "$BASE_SHA"
```

Only `run` receives `--cpu-idle-authorized`, after root releases the barrier. Freeze records the exact revision, inputs, script and tool hashes before cold trunk help. Preserve the same timer and all samples. After every timed command finishes:

```sh
python3.13 "$SCRIPTS/check_performance_artifacts.py" \
  --performance "$EVIDENCE/formal/performance" \
  --world1 "$BASELINE_WORLD1" --collection "$EVIDENCE/demo7-a" \
  --checkouts "$CHECKOUTS" --out "$EVIDENCE/performance-artifacts.json"
```

## Preserved failures and packaging

The first refusal-driver attempt omitted a required seed and stopped on setup; its [receipt](driver-refusals.txt) remains. The pre-launch summary-control shell quoting error, [sandbox-blocked freeze](017-performance-freeze.txt), [premature freeze readback](019-freeze-readback.txt) and [case-count readback error](formal/024-performance-artifacts.txt) remain separate from product outcomes. Corrected [synthetic controls](018b-summary-controls.txt) prove component and per-sample RSS failures are detected. No product fix-forward round or timing replacement was needed.

M1-11's 45.042089291-second result remains failed against 45 seconds. M1-10's 21.67-percent startup regression remains failed against 20 percent. Earlier limitations remain in their original reports. This milestone neither repeats nor waives those historical results.

Raw receipts, hashes, frozen inputs and all generated outputs remain unchanged in the durable local evidence tree. Reports and reproducible scripts are packaging candidates. The unchanged scanner rejects representative raw receipt hashes; no exemption or receipt rewrite is applied. Root owns final packaging, evidence-head applicability, CI, transcript review and release state. This verifier does not commit, push, merge or enable auto-merge.

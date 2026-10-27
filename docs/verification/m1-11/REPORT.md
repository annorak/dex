# M1-11 verification

This report records completed product, CLI, review and performance verification. The final evidence-only commit receives its own repository gate before pushing; its exact head, gate receipt, CI and release state are recorded afterward in the local [handoff](HANDOFF.json) and [final verifier report](verifier/final/report.md). [PR #10](https://github.com/annorak/dex/pull/10) is open against master. Product revision: 07747f2. Base and actual merged M1-10 dependency: 1015457. The owner must review transcripts before landing; this task will not merge or enable automatic merging.

## Delivered scope

`dex demo build --world world-1 --seed SEED --out OUTPUT` creates both Bramblewick and Fennor through the existing bundle writer. Seed, generator version and exact packet bytes determine every output byte, including XLSX metadata. Each company has 3,600 historical cases with a frozen 2,700/900 learning/exam split, 1,800 stream cases and ten separate shadow cases. The nineteen opening cases are members of the streams.

All seven source packets are tracked and copied exactly. Native company formats, named mistakes, duplicates, void-only matches, cancellations, snow cases, policy boundaries, deliveries and later-event fixture data are covered by the [exact specification checklist](specification-checklist.json). Independent decisions, effects and waits are constructed before any reference execution. Observed historical actions and planted mistakes are derived separately. Keys, response scripts, passage maps, recordings and later-operation schedules stay under reserved evaluator artifacts.

World 2 and all-world generation remain unavailable until M1-12. Reference execution, learned-stream results, library acceptance, repairs and UI acceptance remain unavailable. No golden fixtures, production adapters, authentication changes or live model calls were added.

## Verification and applicability

[Coverage](COVERAGE.md) retains fourteen separate outcomes. The independent [round-2 report](verifier/round2/report.md) records all ten live CLI lanes, thirteen explicit refusals, complete saved learning projections, 831 repository tests and 42 focused World 1 tests at 7377a3e. All generated scenarios were inspected against independent exact predicates. Refusals require the intended nonzero diagnostic and unchanged existing filesystem and SQLite state.

The final two-file change at 07747f2 affects only immutable snapshot validation and its tests. The verifier independently reran all 88 bundle tests, the requested 42 World 1 tests, both real public checks and both learning projections. Seed-7 and seed-11 outputs each match all 30,861 previous relative paths and bytes. Unchanged generator, evaluator, scenario, packet, startup and dependency blobs justify carrying the corresponding earlier evidence forward. The final evidence commit changes only verification documents and scripts. Its [committed-head repository gate](verifier/final/003-make-check.txt) runs before pushing. An empty product diff from 07747f2 and stable product patch ID establish final-head applicability.

Public validation reads no evaluator contents. Saved learning views retain exactly each company's 2,700 learning cases, preserve mixed-export row provenance and exclude exam, future and other-company evidence. Reopening the views succeeds with original bundles denied. Imported observations and recordings grant no authority. Core execution, replay, recovery, trust, grants, revocations, sampling, actor binding and expected-revision checks remain unchanged.

## Fix-forward rounds and preserved failures

The first correctness review failed five conditions: conflicting void-only history, business responses before requests, contradictory public posting times, missing certificate evidence for a resolved vendor, and incomplete approval payloads. The first fix closed all five. The independent [correctness validation](correctness/round2-validation.md) and [isolation validation](isolation/round2-validation/report.md) passed at 7377a3e. The original FAIL report and all receipts remain preserved.

At that revision, formal performance sample 4 failed: complete build plus both public checks took 45.042089291 seconds against the unchanged 45-second limit. All five samples remain in the round-2 report and raw evidence. Every build was under 30 seconds, peak RSS was below 1 GiB and supported median regressions were within 20%; those passing results do not cancel the combined-time failure.

The second and final fix removes redundant JSON parsing when a saved extraction is byte-identical to the canonical extraction freshly derived from source. Hash checks and section validation still run; different JSON encodings retain the original strict semantic comparison. Separate excluded profiles confirmed fewer parser calls, without serving as acceptance measurements. The final [correctness](correctness/round3-validation.md) and [isolation](isolation/round3-validation/report.md) reviews pass. The affected formal validation comparisons and all five full generation probes passed at the changed product revision, with unchanged inputs and limits. The [final product verifier report](verifier/round3/report.md) records each result and the exact carry-forward proof.

## Final performance

| Probe | First build, seconds | Repeat build, seconds | Build plus both checks, seconds | Peak RSS, bytes |
| --- | ---: | ---: | ---: | ---: |
| 1 | 22.980741458 | 22.895639833 | 41.737107500 | 359251968 |
| 2 | 22.783165000 | 22.774598833 | 41.151681417 | 348520448 |
| 3 | 22.720385542 | 23.205938709 | 40.890864167 | 348356608 |
| 4 | 23.225731667 | 24.872367542 | 41.782002916 | 355467264 |
| 5 | 24.521889875 | 23.533748667 | 42.945042000 | 353894400 |

All sixty final measurements have valid clocks and successful exits. Every build meets 30 seconds; every combined interval meets 45 seconds; every peak meets 1 GiB. Public-validation wall medians are 35.719% lower than trunk and 34.733% lower than the actual dependency on identical complete inputs; RSS changes are -0.304% and -0.566%. The unchanged startup path carries the original passing +2.604%/+6.443% wall and +0.162%/-0.054% RSS comparisons. Every supported ratio stays within 20%.

Outside timing, all ten complete worlds match every one of 30,861 relative paths and bytes. All fifty public-check readbacks report every declared case, source and delivery. No sample was discarded or repeated unchanged. The earlier failed sample remains a separate result.

## Evidence and reproduction

[Reproduction instructions](REPRODUCE.md) and the verifier scripts preserve the real CLI commands, deterministic refusal controls, exact readbacks and Timer V2 methodology. The original recorder and Timer V2 are reused unchanged. The first trunk invocation, actual unsupported baseline refusals, five-sample alternating pairs and host-load records remain separate evidence. No generation speedup is claimed against unsupported baselines.

Raw receipts preserve exact arguments, revisions, stdout, stderr and exit statuses. Completed receipts have been copied unchanged into `/Users/varunvis/workspace/dev/dex/docs/verification/m1-11/`. Complete generated artifacts and frozen inputs are retained there through same-filesystem directory moves, preserving their contents and metadata. The interrupted archive attempt and its partial file are retained; they are not a successful archive check. The unchanged scanner rejected all eleven selected principal success/refusal receipts for hash and environment-path strings, so the PR tracks suitable reports and reproducible scripts while retaining raw evidence locally. No receipt is rewritten, no scanner exemption is added and no failed sample is discarded. Raw links in these reports resolve in the local evidence tree; those files are deliberately absent from the public PR. Start with the successful [build transcript](verifier/round3/01-world1.txt), [public check](verifier/round3/03-admission.txt), [all-world refusal](verifier/round2/refusal-all.txt) and [complete refusal driver](verifier/round2/012-refusal-driver.txt).

## Inherited results

M1-10 was merged by the owner with its supported startup regression failed: 21.67% against the unchanged 20% limit. Its repository, projection, CLI, independent review and absolute projection gates passed. No cause is asserted, and that failure does not waive M1-11 limits.

Earlier recorded limitations remain: M1-01 lacked complete performance and independent review before landing; M1-06 exceeded its 15-second command threshold; M1-07 retains its documented failures and limits; M1-08 retained earlier failed attempts and revised probe history; M1-09 passed its final gates after preserved failed attempts. These milestones are not reverified here. See the existing M1-10 report and prior milestone reports.

# M1-13 evidence-driver packaging review

Verdict: PASS for static packaging at the eight SHA256 identities below. No material packaging blockers remain. Formal performance verdict: PENDING.

Product head: `b40c6beea0b66e1c40de8d641858f8c749a160ea`. Prior reviewed head: `4ea572c8486ef29ebe7dac824bdeb674490a04aa`. Actual merged base: `e990a3387fa2b1c8bce9e369e10c99db7079f89b`.

Scope: independent read-only review of the eight verifier drivers, their command arguments and paths, control invocation, frozen inputs and schedule, output readbacks, refusal preservation, and measurement publication. The reviewer read saved receipts and refreshed script hashes. The reviewer ran no tests, drivers, profiling, or performance workloads and made no product edits. The verifier owns execution evidence and the pending formal performance verdict.

## Methodology and findings

- The performance driver retains five alternating supported comparison pairs, separate cold and unsupported baseline records, every sample receipt, before/after host records, and explicit start records. Recorded tasks must exactly equal the frozen schedule. Scoring/report/combined limits remain 10/5/20 seconds, peak RSS remains 1 GiB, and the supported median regression ratio remains 1.20. Failed gates and samples remain visible in publication.
- Every large scoring sample checks the literal 10,000 case IDs, ten exact event IDs per case, completed status, integer decision 7, empty effects and waits, exact score rows, case membership and denominators, and saved artifact hashes. The small controls use the same verification helper and reject changed case IDs, event counts, decision values, pending status, and score errors.
- Every supported arithmetic sample checks the exact two artifact names, one observation, successful function result, and literal cents 1001, days 2, and due date 2028-03-01 in both saved actual and expected values. Changed-value and missing-artifact controls call the same summary code and reject the corruption.
- Live readbacks check exact case sets and differences, canonical waits including schema, frozen identities, historical versus current execution activity, distributions, acceptance coverage, immutable artifact hashes, and repeat reports. The persisted-readback controls explicitly invoke passing and corrupt-input cases.
- Refusal commands require exit 2, the named diagnostic, no traceback, absent output where applicable, and unchanged guarded files, symlinks, and SQLite state. The collection lane now also snapshots the original collection outside the guard. Its isolated current-head proof covers all 32,287 original files before and after the real refusal.
- The delta driver carries unchanged source, scenario, and dependency blobs, reasserts all ten prior live lanes, checks a fresh score and repeated report, and runs all ten preserved malformed evaluator copies through the public CLI with named rejections and complete guarded-state snapshots.
- The final publisher delta adds exact equality between recorded task lists and the frozen schedule. This strengthens publication admission without changing workload or limits. The publisher hash in this report includes that reviewed assertion and supersedes the earlier chat hash. Publication checks stable outcome artifacts and fresh-process report equality and retains recorded failures and exclusions.
- No material no-comments or deslop finding was identified in these evidence drivers.

## Reviewed identities

The refreshed hashes agree with the verifier's [final identity receipt](../../verifier/round2/016-final-driver-identities.txt).

| Driver | SHA256 |
| --- | --- |
| [delta_checks.py](../../verifier/scripts/delta_checks.py) | `9d30998b287b8f1387f533e3e04c0cf0b21f13fd96a892746f1c89d9f3374d8d` |
| [live.py](../../verifier/scripts/live.py) | `c46c853cca4c0384a2a969a09a219d9a2697d9dae2bfe946680709af9e8b4437` |
| [performance.py](../../verifier/scripts/performance.py) | `733bd6f9ea22186399145e9119f56d4f91532d0f5f0f817e6aec6c8ea0eeed80` |
| [performance_controls.py](../../verifier/scripts/performance_controls.py) | `1894699e4ab8b9a8cc10d4b05e0eff57c1f870f15cf99197ebd347b599860df8` |
| [prove_input_reuse.py](../../verifier/scripts/prove_input_reuse.py) | `3c9eebac16da0a292d18020e675bf8aa2c8b4bf0894e7ebde8811d2f51ecd91e` |
| [publish_measurements.py](../../verifier/scripts/publish_measurements.py) | `59f2de867bb9a57b8bcf271a57a58663b387246f243a30c657af2054b11e4036` |
| [readback_controls.py](../../verifier/scripts/readback_controls.py) | `275ad04512c4ed10cd4a8fc95bedc701119cfa257366a2e1748e1b92b9b885fd` |
| [refusals.py](../../verifier/scripts/refusals.py) | `9118ed7c9f96da8a5df40fa0fbb21586b95d6b68b06ee5f02ac70d2d63c05399` |

## Saved execution evidence read

- [009: delta carry and all ten preserved CLI refusals](../../verifier/round2/009-delta-checks.txt): PASS, exit 0 for the driver; each malformed CLI invocation exits 2.
- [011: complete performance controls](../../verifier/round2/011-performance-controls-complete.txt): PASS, including literal-work and changed/missing arithmetic controls. These synthetic controls validate the instrument; formal performance remains pending.
- [012: original collection preservation](../../verifier/round2/012-collection-preservation.txt): PASS at clean product head, named `reference_unavailable`, exit 2, output absent, and all 32,287 files unchanged.
- [050: persisted-readback controls](../../verifier/preflight/050-readback-controls-provenance.txt): all nine defined controls exercised; the reviewed live and readback-control bytes remain unchanged.

Applicability ends if any reviewed script changes. This report records a static packaging verdict and the cited verifier evidence; formal measurement results require the verifier's separate report.

# M1-13 verification report

M1-13 gives evaluators independent outcome scores and durable reports while stopping before the process reference implementations. This PR adds no M1-14 work.

Status: product verification PASS at the corrected head. Final evidence-head checks and CI are recorded separately in the durable HANDOFF.json. [PR 12](https://github.com/annorak/dex/pull/12) targets master. The operator must review the CLI transcripts before landing. Auto-merge and queue membership are checked again in the final HANDOFF.json. This agent never merges.

## Revisions and scope

The actual merged M1-12 dependency and GitHub master are e990a3387fa2b1c8bce9e369e10c99db7079f89b. GitHub PR 11 identifies the verified dependency head b7366b97a440f002f433a52b613337642ff5b05b. The implementation uses a fresh isolated worktree and branch from the fetched master. The original tracked checkout is preserved.

The initial reviewed head is 4ea572c8486ef29ebe7dac824bdeb674490a04aa. The corrected product head is b40c6beea0b66e1c40de8d641858f8c749a160ea. Final head, base, stable patch IDs, non-evidence blob equality, post-commit checks and CI are recorded in the durable final HANDOFF.json after the evidence commit. The final evidence commit does not redefine the engine.

The CLI adds bundle/collection reference evaluation and recorded reporting. Missing references explicitly fail. The existing scenario route and ordinary run behavior remain. Structural evaluator validation stays separate from public admission. It checks envelope/container types and identities; it does not claim complete process-payload or business-rule validation.

Keys, cohort, cutoff, sources and execution bytes are frozen before isolated checked execution. Complete canonical decisions, effects and waits are compared with independent values. Reports preserve historical mismatches, reference errors, required unresolved results, copied fields and all case identities. A valid recorded evaluation failure remains reportable. Invalid input cannot create a successful rejection artifact.

The ledger names supplied historical activity separately from work performed by the current evaluation. It preserves distinct calls, retries, human actions, shared activity, chronology and week/version intersections. Reporting reads saved artifacts without running programs, rebuilding keys, calling models, dispatching effects or changing outcomes.

## Fourteen independent outcomes

| Outcome | Result | Principal evidence |
| --- | --- | --- |
| Repository gate | PASS, 956 tests | verifier/round2/004-make-check.txt |
| 01. Correct result against mistaken history | PASS | verifier/round1/live/01-score.txt |
| 02. Copied historical mistake | PASS | verifier/round1/live/02-copied.txt |
| 03. One incorrect effect field | PASS | verifier/round1/live/03-effect.txt |
| 04. Expected wait and required unresolved result | PASS | verifier/round1/live/04-unresolved.txt |
| 05. Changed and missing frozen key | PASS | verifier/round1/live/05-key.txt |
| 06. Historical arrival context | PASS | verifier/round1/live/06-context.txt |
| 07. Calls, human actions and zero cases | PASS | verifier/round1/live/07-ledger.txt |
| 08. Event week and concerned version | PASS | verifier/round1/live/08-buckets.txt |
| 09. Absent history and unimplemented coverage | PASS | verifier/round1/live/09-coverage.txt |
| 10. Stable report in a fresh process | PASS | verifier/round1/live/10-report.txt |
| Performance | PASS, all 56 scheduled samples | [Verifier report](verifier/report.md); verifier/round2/019-performance-summary.txt |
| Correctness review | PASS after first fix round | [Review](correctness/fix-forward1/report.md) |
| Isolation review | PASS, including exact fix delta | [Review](isolation/round2/report.md) |

Each CLI evaluation has a separate report receipt. Lane 10 also has a fresh-process repeat. `verifier/round1/live/live-readback.json` checks exact case sets, field differences, ledger rows, buckets, denominators and identities. The first lane retains real trunk and merged-dependency refusals. Unsupported baseline commands are never reported as successful historical evaluations.

The exact focused command, `uv run pytest tests/eval/test_scoring.py tests/eval/test_report.py -q`, passed 78 tests at the corrected product head. Owner receipt 020 also records 154 relevant existing regressions. The independent committed-head gate is the pre-push gate for that same product revision. Later final-head gates are identified separately in HANDOFF.json.

## Rejections and independent review

The original 22 real CLI refusal probes cover malformed manifests, changed/missing keys and declarations, missing references, company/cohort/cutoff/case/fixture conflicts, unsafe paths, invalid selectors, destination files/directories/symlinks/missing parents and changed/missing recorded artifacts. Every rejection names its diagnostic and compares exact existing-state snapshots. Principal evidence is `verifier/round1/012-refusal-driver.txt` and `verifier/round1/refusals/refusal-readback.json`.

The first correctness review found a stale report CLI contract assertion and incomplete evaluator structural validation, including an unhandled list-valued decision. The first fix round corrects them. Both original evaluator bundles still admit. All ten preserved malformed evaluator copies now fail with named errors and unchanged input bytes. The original FAIL report and every failed attempt remain intact.

At the corrected product head, the verifier repeated all 22 refusal probes in `verifier/round2/008-refusal-driver.txt`. It also ran all ten preserved malformed evaluator copies through the real reference CLI in `verifier/round2/009-delta-checks.txt`. Every invocation returned its named diagnostic with exit 2, no traceback, no published output and unchanged guarded state. `verifier/round2/012-collection-preservation.txt` separately verifies all 32,287 original collection files before and after its missing-reference refusal. The [eight-driver packaging review](correctness/packaging/report.md) records the exact reviewed script hashes and literal output corruption controls.

The [isolation report](isolation/round1/report.md) proves real exam, evaluator, future and other-company exclusion at the projection/serialization boundary. It also proves engine/dependency identity sensitivity and two guarded fresh-process reports. The guards deny execution, network, writes and unrelated data reads. The same reviewer checked the admission delta separately.

## Evidence applicability and engine freeze

[ENGINE.md](ENGINE.md) preserves the full reusable content manifest, including core, workspace, adapters, ordinary boundaries, four shared evaluator execution files, runtime dependency content and versions. It is derived from `dex report`. Engine mutation controls prove reusable code and dependency changes alter identity, while evaluator, reference and external evidence additions cannot silently redefine it.

The admission fix changes only admission.py and two test files. Every other source blob and the complete engine/dependency manifest match the original reviewed head. The independent reviewers provide exact blob proofs. Thus earlier scoring, ledger, reporting, projection and engine probes are carried with identified applicability; they are not claimed as reruns at the corrected head. A fresh current-head identity readback is recorded by the verifier.

The preserved M1-12 seed-7 collection is reused only after exact generator, packet, admission and source-content proof across the prior verified product, actual merge and current implementation. The proof hashes 32,287 input files and 44 relevant implementation/source files. No M1-12 generation/performance matrix was repeated. The three generated companies still have no installed reference implementation.

## Performance

PASS. All five absolute-workload samples and all eight supported median wall-time/RSS comparisons meet the unchanged limits. The following values come from the published `dex report`, independently read back in `owner/057-published-metrics-readback.txt`. Each row summarizes five samples.

| Measurement | Median | Range | Limit |
| --- | --- | --- | --- |
| Scoring phase | 0.509455500 s | 0.484550833 to 0.534820291 s | 10 seconds |
| Complete evaluation command | 4.003230959 s | 3.820098375 to 4.155381750 s | Included in combined limit |
| Complete report command | 2.880336083 s | 2.775957000 to 3.096821708 s | 5 seconds |
| Combined command completion | 6.779187959 s | 6.697386583 to 7.252203458 s | 20 seconds |

Peak RSS across the measured workload is 492,945,408 bytes, below 1 GiB. The largest supported median ratio is 1.178968876 for startup wall time against the actual merged parent, below 1.20. The [verifier report](verifier/report.md) retains every comparison, sample and range.

The complete 56-command frozen schedule, including cold and unsupported baseline records, passed without replacement samples. Every host process snapshot succeeded. Independent readback checks literal case IDs, ten exact event IDs per case, completed decisions, score rows, all artifact hashes and identical supported arithmetic outputs.

The excluded profiles in `verifier/round2/020-profile-evaluation.txt` through `022-profile-readback.txt` identify JSON encoding and ledger validation as the main CPU costs. They retain full-work readback and zero network attempts. Profile timings are not gate samples.

`verifier/round2/023-publish-measurements.txt` publishes fifteen evaluation/report/combined measurement records through `dex report`. Two fresh reports are byte-identical. All eight original run artifacts, including recorded costs and the run manifest, remain unchanged. The report names exact workload, phase exclusions, frozen revisions, schedule, raw sample records and gate outcomes.

A prior launch waited for sandbox permission and was interrupted before any process or sample existed. That tool-level attempt is preserved separately and is not a measured failure or rejection. The single executed formal schedule remains intact.

The workload and limits are unchanged. The formal run uses exactly 10,000 cases and 100,000 distinct ledger events. Scoring is measured separately. Complete evaluation and report command intervals include persistence and serialization; combined completion is their sum. Byte readback, input freezing, dependency preparation and the separate profile are excluded. The measurement supplement is bound to the recorded run and published through `dex report` without altering scored artifacts.

The supported regression workloads are CLI help and language-arithmetic. They exercise the changed CLI dispatch and shared scenario boundary. Five alternating trunk/head and merged-parent/head pairs use identical frozen inputs. Formal trunk's first CLI invocation is measured cold after dependency-only preparation. The separate untimed baseline checkout does not warm it.

## Limits and preserved history

All process acceptance requirements remain visibly unimplemented because process references and learned-stream execution are unavailable. The report accounts for every non-heading acceptance source line in 52 blocks. Synthetic infrastructure checks do not claim Bramblewick, Fennor or Veldren acceptance, replay, exam or trust results. Fixture totals remain requirements until executed. No live model-network calls are used.

M1-12's final 877-test gate, ten CLI lanes, independent reviews, performance gates and final-head CI are historical dependency evidence. Its final evidence-only commit preserved all 355 non-evidence blobs. M1-11's earlier 45.042089291-second sample remains FAILED against 45 seconds before its final fix. M1-10's owner-merged startup regression remains FAILED at 21.67 percent against 20 percent. None waives any M1-13 threshold.

All development, instrumentation and formal failures remain in the local evidence tree. In particular, the initial M1-13 repository gate failed with 940 passing tests and one stale contract assertion. The corrected gate passed. Setup errors and absent outputs are never counted as rejection evidence. No unchanged measurement is repeated to obtain a passing sample.

## Reproduction and local-only evidence

[REPRODUCE.md](REPRODUCE.md) documents the drivers, cold-start preparation, negative controls, frozen inputs and exact measurement boundaries. Previously reviewed candidates passed the unchanged scanner. Final selected-file and committed-head scanner results are recorded in HANDOFF.json. Raw receipts contain hashes and path strings that the scanner rejects, as recorded in owner/049-raw-receipt-scanner.txt. They remain byte-for-byte intact locally. No receipt was rewritten and no exemption was added.

Resolve unlinked receipt paths above under `/Users/varunvis/workspace/dev/dex/docs/verification/m1-13/`. The raw results, failed attempts, frozen schedules and complete generated runs stay in that durable ignored tree. The final HANDOFF.json there records the exact final head and CI after the evidence commit. [CHECKLIST.md](CHECKLIST.md) maps requirements to assertions. [trail.tsv](trail.tsv) records decisions without backdating; the older decisions.tsv is preserved as a retrospective summary.

Attention: the written checklist and canonical trail were added after early integration. That sequencing shortfall is disclosed. Product review and owner-trail audit evidence are linked, with their exact scope. Transcript review by the repository owner remains required before landing.

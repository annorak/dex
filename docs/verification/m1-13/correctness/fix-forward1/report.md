# M1-13 correctness review, fix-forward 1

M1-13 adds independent scoring and recorded reports while stopping before the process references and M1-14.

Verdict: PASS at `b40c6beea0b66e1c40de8d641858f8c749a160ea`. C13-01, C13-02 and C13-03 are closed. No new correctness finding requires a fix.

- Actual base: `e990a3387fa2b1c8bce9e369e10c99db7079f89b`.
- Original reviewed head: `4ea572c8486ef29ebe7dac824bdeb674490a04aa`.
- Fix-forward head: `b40c6beea0b66e1c40de8d641858f8c749a160ea`.
- Worktree: `/private/tmp/dex-m1-13-20261103`, clean at the probes and [final readback](003-final-status.txt).
- This is the first fix-forward round. The user permits at most two.
- No product, test or scenario file was edited by this reviewer.

## Findings closed

| Finding | Independent closure evidence | Result |
| --- | --- | --- |
| C13-01, stale report CLI contract | Report without a run returns the required-argument diagnostic; report help succeeds. Both selected contract tests pass. [002](002-cli-and-invalid-input.txt). | Closed |
| C13-02, malformed evaluator artifacts accepted | Both original generated evaluators still admit. Every preserved invalid effect, wait, response-script JSON, actor and summary copy now raises its expected named BundleError. All input bytes remain unchanged. [001](001-probes.txt), [exact results](probes/results.json). | Closed |
| C13-03, list-valued decision raises TypeError | The exact preserved World 1 decision=[] copy now raises `answer.decision: expected nonempty text`. The CLI boundary tests return evaluator_invalid, preserve inputs and publish no run. [001](001-probes.txt), [002](002-cli-and-invalid-input.txt). | Closed |

The admission probe reuses all ten malformed evaluator copies from the [original round](../round1/boundaries), rather than regenerating them. Each expected diagnostic prefix is hand-written in the [delta driver](../probe_fix_forward.py). The original World 1 and World 2 evaluator artifacts also remain byte-for-byte unchanged after successful admission.

The five focused test cases cover report arguments, report help, and invalid response JSON, format and decision values at the normal reference CLI boundary. The three invalid-evaluator cases assert no destination exists after rejection and every original input byte is unchanged.

The fix adds structural envelope checks for effects, waits, World 2 record and branch containers, observation actors, and parseable object response scripts. It does not claim complete validation of every nested process payload, business-rule correctness, or reference execution. Those broader claims were not required to close the reproduced structural defects.

## Applicability of earlier evidence

The [blob proof](probes/results.json) shows the entire delta contains only:

- `src/dex/eval/admission.py`.
- `tests/eval/test_scoring.py`.
- `tests/contracts/test_checks.py`.

Every other source blob is identical to the original reviewed head. The current engine content and runtime dependency identity also matches the recorded original identity:

`6fd136fbe33a853a6c7b81d360264adc0efde29dc2b7dfb6f0f88b13ae75da36`.

The unaffected correctness evidence therefore remains applicable:

- [Exact outcome, wait, corruption and ledger contracts](../round1/002-contracts.txt).
- [Expected-free recording, human-action, approval and replay integrations](../round1/005-engine-corrected.txt).
- [Saved failed evaluations, fresh-process reports and invalid-input behavior](../round1/007-cli-cache-access.txt).
- [Recorded source coverage, current activity and identity readback](../round1/010-readback-corrected.txt).

The prior [isolation execution, projection, reporting and engine-identity evidence](../../isolation/round1/report.md) uses implementation blobs that are unchanged. The modified evaluator admission path was reviewed directly and re-exercised by the targeted checks above. This is an applicability assessment, not a replacement for the isolation reviewer's own verdict.

## Maintainability and trail audit

The exact delta contains no unrelated formatting or refactor. The validation stays at the evaluator boundary and reuses the existing object, text, timestamp and JSON parsers. No process semantics entered the core or ordinary execution path.

The no-comments and deslop passes found no new actionable issue. Token comparison found no added or removed comments and no new suppressions. There are no restored comments, HOLDs, encoding offers or unenforced comment constraints.

A practical independent spot audit of the [isolation decision log](../../isolation/decisions.tsv) passed. At audit time it contained 17 six-column rows, 33 resolving evidence pointers and 24 checked receipt timestamps. Each checked receipt finished before its logging timestamp. The audited trail SHA-256 was `8f5fdc3293edf93cc8aebfddb4b1bec563964a729d78ba5dea4d026cd7f0df25`.

This trail check covers format, evidence resolution and receipt chronology. It is not a complete transcript or model-family audit. No additional agent was spawned.

## Receipts and limits

| Receipt | Result |
| --- | --- |
| [001-probes.txt](001-probes.txt) | Exit 0. Valid admissions, ten named rejections, unchanged input bytes, exact source-blob applicability, engine identity, comment comparison and trail audit. |
| [002-cli-and-invalid-input.txt](002-cli-and-invalid-input.txt) | Exit 0. Five focused cases passed. |
| [003-final-status.txt](003-final-status.txt) | Exit 0. Clean committed tree retained. |

The [original FAIL report](../round1/report.md), malformed inputs and all earlier failed instrumentation or setup attempts remain preserved. No failed fix-forward probe was replaced.

The full suite, performance matrix, CI and overall milestone handoff belong to the root and designated verifier. They were not repeated here. Process references and M1-14 remain outside this change.

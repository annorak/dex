# M1-13 correctness review, round 1

M1-13 adds independent scoring and recorded reports while stopping before the process references and M1-14.

Verdict: FAIL. Three findings need a fix-forward change.

- Base: `e990a3387fa2b1c8bce9e369e10c99db7079f89b`.
- Head: `4ea572c8486ef29ebe7dac824bdeb674490a04aa`.
- Worktree: `/private/tmp/dex-m1-13-20261103`.
- The worktree was clean throughout the recorded product probes and at the [final readback](012-final-status.txt).
- No product, test or scenario file was edited by this reviewer.

## Findings

### C13-01. P1. The existing CLI contract test prevents repository checks from passing

`tests/contracts/test_checks.py:659` still expects `dex report` to fail with `invalid choice: 'report'`. The command now exists and correctly rejects its missing run argument instead. The focused test fails on that stale assertion.

Evidence: [011-stale-cli-test-corrected-target.txt](011-stale-cli-test-corrected-target.txt). Reproduce with `python -m pytest tests/contracts/test_checks.py::test_cli_unavailable_commands_fail -q` from the pinned checkout.

The owner identified this issue before this independent reproduction. Update the contract to the implemented command behavior and cover report help. No product behavior change is needed for this finding.

### C13-02. P2. Evaluator admission accepts structurally invalid expected evidence

`src/dex/eval/admission.py:validate_evaluator_answers` validates top-level fields and the existence of effect and wait arrays, but not their elements or several required nested values. `load_evaluator` does not parse the required response-script artifact.

Both original generated evaluators passed admission. Nine copied evaluator variants, with the altered artifact hash correctly declared in each manifest, were then incorrectly accepted:

| World | Altered artifact | Invalid value accepted |
| --- | --- | --- |
| World 1 and World 2 | answer-key.json | effects is [null] |
| World 1 and World 2 | answer-key.json | waits is [null] |
| World 1 and World 2 | response-scripts.json | Non-JSON bytes |
| World 1 and World 2 | answer-sheet.json | actor is [] |
| World 2 | answer-key.json | summary is null |

Evidence: [008-boundaries.txt](008-boundaries.txt), [boundary results](boundaries/results.json), and the complete copied evaluator directories beneath [boundaries](boundaries). The [probe](../probe_boundaries.py) reads each original public bundle with the ordinary loader and copies only evaluator bytes. It never modifies the originals.

Malformed expected evidence can therefore be frozen as valid evaluator input. The missing-reference guard currently prevents reference execution, but does not satisfy the independent admission contract.

Validate the existing generated envelope shapes before returning EvaluatorInputs. Required effect, wait, summary and observation records need their declared object and field types. Actor values must be nonempty text. Required JSON artifacts must parse and have their existing structural shape. These checks must not calculate correct business decisions, run a reference program, or introduce process semantics into the engine.

### C13-03. P2. A malformed World 1 decision escapes the actionable-error boundary

At `src/dex/eval/admission.py:299`, a World 1 decision is tested for membership in a set before being validated as text. Replacing one decision with [] raises `TypeError: unhashable type: 'list'`. It does not raise the expected admission error. The CLI wrapper catches OSError and BundleError, so this exception also escapes its normal diagnostic path.

Evidence: the world1-unhashable-decision check in [008-boundaries.txt](008-boundaries.txt). Its exact copied inputs remain in [world1-unhashable-decision](boundaries/world1-unhashable-decision).

Validate the decision type before selecting its structural variant. Preserve a named nonzero invalid-input diagnostic and publish no run.

## Passing checks

| Check | Independent evidence |
| --- | --- |
| Scalar types, list assignments, missing versus null, escaped pointers and exact field differences | [002-contracts.txt](002-contracts.txt) |
| Separate historical and reference mismatches, two copied fields, duplicate-pointer refusal and missing-case denominators | [002-contracts.txt](002-contracts.txt) |
| Legitimate waits, required unresolved results, complete output schemas and plain reviewed-work references | [002-contracts.txt](002-contracts.txt) |
| Scoped action deduplication, combined review tags, categories, Monday weeks, concerned versions, zero cases and zero denominators | [002-contracts.txt](002-contracts.txt) |
| Validated recordings, invalid-recording human fallback, redelivery, replay and one approval action reviewing one producing result | [005-engine-corrected.txt](005-engine-corrected.txt) |
| Saved failed evaluations remain reportable; fresh-process reports match; invalid input publishes nothing | [007-cli-cache-access.txt](007-cli-cache-access.txt), including its separate nested CLI receipts |
| Source coverage, saved outcome and engine identity | [010-readback-corrected.txt](010-readback-corrected.txt) |

The readback accounts for every non-heading source line across 52 recorded acceptance blocks. All remain explicitly unimplemented. The report preserves its failed result and zero current execution calls and touches. Static review confirms supplied historical activity has separate provenance and does not become runtime authority.

The recorded engine identity matches the current reusable content and dependency manifest: `6fd136fbe33a853a6c7b81d360264adc0efde29dc2b7dfb6f0f88b13ae75da36`. Scoring and reporting remain outside reference execution. No placeholder reference was added.

The primary human category and the retained descriptive tags follow the specified one-action model. A new nonexclusive tag-count feature is not required to close this review.

## Maintainability and comment review

The same independent reviewer performed the no-comments and deslop passes under the staffing constraint. Tokenization of every changed Python file found no added or removed comments and no suppressions. There are no restored comments, HOLDs, encoding offers, unenforced comment constraints, or comment-related fixes.

The actionable maintainability issue is the incomplete external validation described above. No unrelated refactor or cleanup is requested. The shared scenario change extracts an expected-free executor while retaining the existing core verifier, decider and reducer.

## Preserved failures and review limits

The original [probe version](../preparation/probe_contracts-v1.py) was preserved before the wait-schema update. Every executable product check uses the unchanged tracked recorder, with revision, command arguments, stdout, stderr and exit status.

- [003-engine.txt](003-engine.txt) preserves a probe error caused by omitting the verifier's required limits argument. The corrected probe passed in 005.
- [004-command-error.txt](004-command-error.txt) preserves an accidentally mistyped script path. It is labelled as transcribed tool output, not a product refusal.
- [006-cli.txt](006-cli.txt) and its nested receipts preserve uv cache sandbox failures before dex ran. The recorded cache-access retry passed in 007.
- [008-boundaries.txt](008-boundaries.txt) also preserves a readback-helper bytes-serialization error. The corrected audit passed in 010 without repeating admission.
- [009-stale-cli-test.txt](009-stale-cli-test.txt) preserves an absent pytest target. The real target was subsequently found and failed as recorded in 011.

These instrumentation and setup failures are not product findings or passing refusal evidence.

The designated verifier owns the repository suite, complete live matrix and performance measurements. This reviewer did not repeat them. This is formal correctness round 1, before any fix-forward changes. The user permits at most two fix-forward rounds.

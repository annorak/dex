# M1-13 isolation review: first fix-forward delta

**PASS.** No new isolation blocker was found in the exact delta. No further isolation fix is requested.

| Pin | Value |
| --- | --- |
| Reviewed head | `b40c6beea0b66e1c40de8d641858f8c749a160ea` |
| Prior reviewed head and direct parent | `4ea572c8486ef29ebe7dac824bdeb674490a04aa` |
| Actual merged predecessor/base | `e990a3387fa2b1c8bce9e369e10c99db7079f89b` |
| Engine identity at both reviewed heads | `6fd136fbe33a853a6c7b81d360264adc0efde29dc2b7dfb6f0f88b13ae75da36` |
| Reviewer | Same independent reviewer, `/root/isolation` |
| Checkout | `/private/tmp/dex-m1-13-20261103`, clean at all recorded checks and after the focused test |

## Delta reviewed

[Receipt 001](001-pin-delta.txt) records the complete diff: only `src/dex/eval/admission.py`, `tests/eval/test_scoring.py`, and `tests/contracts/test_checks.py` changed.

Admission now validates text discriminators before membership checks, parses the already-loaded response-script bytes, validates effect/wait members and World 2 object envelopes, and requires observed actors to be text. These checks stay within evaluator admission. They introduce no imports, learning selector, runtime command, model call, workspace access or publication path. The response-script read does not expand public bundle admission: it parses bytes already loaded by the evaluator-only reader. The CLI contract-test correction adds no product behavior.

## Current-head evidence

| Check | Result |
| --- | --- |
| Exact head, direct parent, clean tree and three-file delta | PASS, [001](001-pin-delta.txt). |
| Complete engine manifest equals the round-one baseline and saved run freeze | PASS, [002](002-boundary-identity.txt). All 31 engine/shared file hashes, runtime dependency content, versions and requirements are identical. |
| Evaluator identity discloses the change | PASS, [002](002-boundary-identity.txt). `admission.py` is the only changed evaluator-manifest entry. |
| Boundary blobs and imports | PASS, [002](002-boundary-identity.txt). CLI, report, ledger, persistence, scoring, fixtures, shared executor/parser/serializer, frozen-input bridge, identity code, `pyproject.toml` and `uv.lock` are byte-identical to the prior head. Admission imports are identical; AST checks of 26 ordinary files found no evaluator/demo imports. |
| Invalid input preserves source and destination | PASS, [003](003-admission-no-mutation.txt): three parameterized cases. Each admits a valid fixture first, then checks malformed response JSON, format or decision rejection; source files remain byte-identical and the destination remains absent. |
| Read review of added validation | PASS. Guards run before the existing missing-reference refusal, execution remains unavailable on this path, and evaluator data remains data. No later-milestone process implementation was added. |

## Earlier evidence carried forward

The following evidence was executed at `4ea572c8486ef29ebe7dac824bdeb674490a04aa`; it was **not rerun** for this delta. Receipt 002 establishes its applicability through identical implementation/dependency content, and receipt 001 establishes that no other product file changed.

| Earlier evidence | Applicability |
| --- | --- |
| [Identity mutations](../round1/002-identity.txt) | Identity implementation, all engine/shared files and runtime dependencies are unchanged. Code/dependency mutations still define engine identity separately from evaluator/reference/evidence additions. |
| [Real projection and frozen execution](../round1/003-projection.txt) | Public admission, learning view, cohort projection, serialization, business-date handling and executor are unchanged. The earlier exam/future/evaluator/root-path exclusions, substituted-view rejection and execution-without-file-opens proof apply. |
| [Guarded fresh-process reports](../round1/006-guarded-report.txt) | CLI report dispatch, report, ledger, run reader, identity helpers and dependencies are unchanged. Earlier guards denied evaluator execution/admission/fixture imports, network, writes and unrelated data reads. |
| [Focused authority and company boundaries](../round1/007-focused-boundaries.txt) | Public bundle, workspace, authority and frozen projection implementations are unchanged. Earlier six cases remain applicable. |
| [Ordinary implementation and generator comparison](../round1/008-structural-boundaries.txt) | The delta changes no ordinary engine, workspace, bundle, adapter, recording, verification or demo code. No generator or generated-byte matrix was repeated. |

The original [round-one report](../round1/report.md), all earlier failures and receipts remain intact. The [owner-trail follow-up audit](../round1/trail-audit.md) remains bound to the exact eight-entry trail hash `aa09ebd4df87f34a18b5fbe02da644c6cf823a5e7beb5ef5d8171a0e478f3d28`; this review makes no claim about later trail additions.

This was the first product fix-forward review. The reviewer changed no product file, ran no full suite or performance workload, and spawned no additional agent.

Attention: PASS covers this exact isolation delta. Overall correctness, repository gates, performance and final PR readiness remain separate reviewer/owner responsibilities.

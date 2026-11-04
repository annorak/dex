# M1-13 isolation review: round 1

**Product isolation verdict: PASS.** No blocking product finding at the reviewed head. The prepared identity, projection and guarded-report probes passed, and six focused boundary tests passed. No product fix-forward round is requested.

The owner decision-trail audit remains **pending an exact evidence delta**. The four-column committed decision summary does not satisfy the selected six-column trail format. The owner agreed to preserve that summary and add a canonical timestamped trail. This evidence follow-up is separate from the product verdict.

| Pin | Value |
| --- | --- |
| Reviewed head | `4ea572c8486ef29ebe7dac824bdeb674490a04aa` |
| Actual merged predecessor/base | `e990a3387fa2b1c8bce9e369e10c99db7079f89b` |
| Checkout | `/private/tmp/dex-m1-13-20261103` |
| Working tree | Clean at pin, each prepared probe, and final structural check |
| Reviewer | Independent isolation reviewer `/root/isolation` |
| Prepared driver SHA-256 | `2b2a73bb6e65e384e66fd7999f20ddbbfbbb285803dce6611f02e519a1537b64` |
| Observed engine identity | `6fd136fbe33a853a6c7b81d360264adc0efde29dc2b7dfb6f0f88b13ae75da36` |
| Fresh report-run identity | `33050d30fc7cd12e4c1cb43a7f222f0db799efb4c564e5b3691d1fd7a77004b5` |
| Guarded report SHA-256 | `2641f8868a4504237f52cc814f121fe7ac7626bd4eb2c47949729ccfc659d138` |

The review covered evaluator admission, expected-free execution, the bundle-to-frozen-input bridge, engine identity, ledger provenance, persistence and reporting. Source references below name files at the reviewed head. The reviewer made no product edits, ran no full suite or performance workload, and created no additional agents. Process references and learned-stream results remain unavailable; this verdict does not claim those later milestones or overall acceptance.

## Isolation checklist

| Boundary | Evidence and conclusion | Result |
| --- | --- | --- |
| Public admission never reads evaluator artifacts | `bundle/reader.py:57` still skips the top-level evaluator subtree. The instrumented unreadable-evaluator test observed zero accesses. Public bundle code is unchanged from base. [007](007-focused-boundaries.txt), [008](008-structural-boundaries.txt). | PASS |
| Ordinary code cannot select evaluator answers | The CLI imports evaluator entry points only in the explicit eval/report branches. AST inspection of 25 ordinary core, bundle, workspace, codec, recording, verification and adapter files found no evaluator/demo imports. Those files are unchanged. [008](008-structural-boundaries.txt); `cli.py:90`. | PASS |
| Expected answers do not enter execution | `eval/scenarios.py:76` takes only programs, commands and detail; `eval/score_execution.py:24` accepts only serialized programs/cases/cutoff. `score_scenarios.py:19` freezes separate answers before executing. Read review and [003](003-projection.txt). | PASS |
| Exam data reaches only frozen execution | The independent public bundle contains learning, exam and future cases, evaluator bytes and an imported approval-like observation. The learning view excludes every restricted marker. Frozen execution contains only the exam case and permitted catalog; it contains no original root path, evaluator bytes, future notice, future case value or imported observation. All six derived-learning destinations reject an exam evidence reference. [003](003-projection.txt). | PASS |
| Company, cutoff and exact projection remain bound | `score_execution.py:164` compares company/bundle, cutoff and exact materialized learning bytes. A same-ID substituted view was rejected. The focused test also rejected another company and another cutoff. `LearningView.catalog` is computed from validated content, not stored independently. [003](003-projection.txt), [007](007-focused-boundaries.txt); `bundle/projection.py:40`. | PASS |
| Business date and chronology stay distinct | The exam case opened July 1 with a June 30 business date; the dated rule returned 10. Changing only the business date to July 1 returned 20. Ledger validation separately parses occurrence, observation, receipt, availability and effective date, checks chronology and cutoff, and binds model rows to request identity and delivery. [003](003-projection.txt); `eval/ledger.py:80`, `eval/ledger.py:127`. | PASS |
| Imported evidence grants no authority | Frozen execution constructs only a sandbox opening with an empty membership/authority context; it does not turn observations or ledger rows into approvals, grants, responses or effect completions. The ledger is marked `supplied_history` and used only for validation/summary. The history/recording roundtrip rejected injected approval flags; forged-controller-grant tests left runtime state unchanged. [003](003-projection.txt), [007](007-focused-boundaries.txt); `score_execution.py:94`, `score_scenarios.py:163`. | PASS |
| Engine identity covers execution dependencies | The manifest includes 31 reusable and shared package files, including the four explicit execution/parser/serializer boundary files. Mutating copied core, workspace, command, codec, recording, verification, bundle, adapter and each shared execution file changed identity; a new ordinary module did too. Synthetic installed dependency content and version mutations changed identity for both current runtime dependencies. [002](002-identity.txt), [008](008-structural-boundaries.txt); `eval/identity.py:16`. | PASS |
| Evaluator, reference and evidence identities stay separate | Adding evaluator code changed evaluator identity without changing engine identity. Adding a separate reference artifact or external evidence did not change engine identity. The reference probe records its own artifact hash; it does not claim an installed reference implementation. [002](002-identity.txt). | PASS |
| Validation precedes publication | `admission.py:137` validates destination and every bundle/member before explicit reference refusal; it performs no execution, workspace mutation or publication. `run_store.py:27` prepares complete staged artifacts before publishing to a fresh destination. Failed collection admission has no output-publishing path. This row is a code review conclusion; the verifier owns the broader live refusal matrix. | PASS |
| Reports consume recorded outcomes only | Two fresh actual CLI processes had scoring, execution, admission, fixture and demo imports forbidden; socket creation and filesystem writes forbidden; non-code reads restricted to the saved run. Positive guard controls proved these restrictions active. Both reports were byte-identical and all eight saved files were unchanged. Only recorded run files were opened. [006](006-guarded-report.txt), [child read log](report/report-1.stderr); `eval/report.py:21`, `eval/run_store.py:52`. | PASS |
| Existing trust/recovery/generators remain intact | Core, workspace, ordinary bundle, adapters, codecs, recordings, verification and demo source blobs are unchanged from the actual base. The shared scenario change extracts execution from expectation comparison. No new process reference is present. [008](008-structural-boundaries.txt). Generator byte-reproduction and broad recovery gates belong to the verifier; this review does not claim to rerun them. | PASS |

## Receipts

Each receipt records exact argv, cwd, revision, working-tree status, stdout, stderr and exit status. Each output directory was fresh.

| Receipt | Outcome |
| --- | --- |
| [001 pin](001-pin.txt) | Exact head and clean tree confirmed; base-to-head file summary recorded. |
| [002 identity](002-identity.txt) | Exit 0; copied-code and dependency mutations affected engine identity as required. |
| [003 projection](003-projection.txt) | Exit 0; actual public admission/projection, exam release, no file opens during execution, business-date control and same-ID substitution rejection. |
| [004 setup failure](004-create-report-run.txt) | Exit 1; the attempted `python -m dex` entry point does not exist. No run was created. Retained as a reviewer invocation error, not a product defect. |
| [005 fresh run](005-create-report-run-cli.txt) | Exit 0; installed CLI created the current-schema three-case report-replay run. |
| [006 guarded report](006-guarded-report.txt) | Exit 0; two guarded child processes produced the same report and unchanged run files. Their separate command/stdout/stderr files are under [report/](report/). |
| [007 focused boundaries](007-focused-boundaries.txt) | Exit 0; six cases passed across four selected tests. No suite rerun. |
| [008 structural boundaries](008-structural-boundaries.txt) | Exit 0; unchanged ordinary implementation, import separation, shared-file membership and current dependency versions recorded. |

Earlier preflight failures remain under [../preflight/](../preflight/). They include a stale saved-run schema, an invalid handwritten CSV provenance fixture and a probe import-order check. They were corrected before the pinned review and are not counted as formal product fix-forward rounds.

## Decision-trail audit

The committed `docs/verification/m1-13/decisions.tsv` has four columns and day-only dates; it omits the selected trail's phase/result fields. The owner acknowledged this during review and will retain it byte-for-byte as a retrospective summary, then add a canonical six-column trail using actual logging timestamps and resolving evidence pointers. Audit of that exact evidence delta remains pending; no claim of a completed owner-trail audit is made here.

This reviewer's [decision log](../decisions.tsv) retains earlier failures and appends formal checkpoints, the corrected CLI invocation and the pending owner-trail follow-up. The reviewer checked its own claims against the visible tool transcript and receipts. Cross-review of this reviewer's trail will use the existing team, per the user's staffing constraint; no extra reviewer was spawned.

Attention: product isolation PASS is limited to the exact head above. Owner-trail evidence follow-up remains pending. No product fix-forward round has been consumed.

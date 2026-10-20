# Engine decisions and open questions

`docs/design/engine.md` defines product intent.
The world specifications supply concrete requirements for that engine.
They do not turn their process vocabulary or reference programs into engine architecture.

The retained decisions below preserve identifiers Q17 through Q53 from the earlier register.
The engine design supersedes prototype architectures, fixed step counts, and numerical baselines.
The representation decisions below record the approved architecture checkpoint.
Remaining design questions are identified explicitly.
Implementation and acceptance evidence are still pending.

## Decisions established by product intent

### Dex compiles operating procedures

The product accepts procedure documents, other business sources, historical cases, and employee answers.
Oak produces a cited procedure and an executable program.
Vendor invoices are World 1.
Payroll and benefits setup at an HR-services company is World 2.
A third process remains held out in a private repository.

The engine contains no process vocabulary.
World data, compiled programs, and tests own that vocabulary.

### Steps have three kinds

Every step is `code`, `ai`, or `human`.
There is no fixed ten-step pipeline and no separate untyped action kind.
Any step may stop for a person when its inputs do not resolve.
A human step names a role and a due time.

Code handles deterministic rules, lookups, arithmetic, recurring parsers, and templates.
AI handles a narrow unresolved input through a fixed schema.
Human steps provide required input, judgment, or authority.

### Models compile programs and handle explicit AI steps

Compile-time model calls are expected.
Their outputs are versioned, recorded, verified, and approved before activation.
At runtime, only AI steps call a model through the gateway.
Their checked outputs are recorded for replay.

Recurring email formats should become parsers.
Approval requests built from known facts are templates.
Demo mode uses recordings and makes no model-network calls.

### Trust and authority are separate

Clean reviews can qualify a step to skip routine review.
They do not grant authority to change another system.
An external change requires approval of that exact change or a valid standing grant within its limits.
The demo starts with per-change approval.
A named controller grants standing authority in dex only after the affected steps earn trust, within recorded limits.
A behavior change returns dependent changes to per-change approval until trust is earned again and a valid grant covers the change.
A verified repair that preserves behavior keeps the count.
Approval of an external change is engine authority over its writing step, not another process step.
Every step that changes another system is marked as a change.

A business-decision step can be marked never to automate.
Selecting the board as approver does not supply the board's decision.
Likewise, a successful onboarding check does not supply the service owner's authorization.

### The first world includes completion of the business process

World 1 reaches a scheduled payment in the AP application.
It includes invoice recording, approval requests, human decisions, and scheduling.
It has no bank transfer.

The AP web application is a process-world fixture.
Its existence does not turn a backend task into implementation of dex's product UI.
The product UI remains a separate client of the server API.

### Verification separates correctness from imitation

History can contain mistakes.
The newest quarter is held out from learning and compilation.
Reference programs, answer keys, planted mistakes, and pretend people remain evaluator-only.
Pretend people use the ordinary human interfaces.

Without usable history, verification begins with procedure-derived scenario tests and shadow mode.
Missing history does not prevent compilation.
It does prevent claims of historical verification.

### Repairs depend on whether behavior changes

A data repair preserves values and meaning and reruns every test.
An interface repair verifies the intended operation in a sandbox.
A behavior-preserving repair may apply with a log entry.
Unknown meaning requires a person.
Policy and procedure changes require dated or versioned behavior, verification, and approval.

### Results come from evaluation

Deterministic fixture gates use exact values computed from the manifest.
Bands belong only to generator calibration.
Reports distinguish historical agreement, reference correctness, model calls, and human touches.
Calls and touches are reported per case, by week, and by program version.
The evaluator derives exact trust dates and touch counts from its event schedule.
Published measured numbers come from `dex report`.

## Retained decisions

| ID | Decision |
| --- | --- |
| Q17 | Bramblewick exports ISO dates and integer cents. Fennor exports MM/DD/YYYY dates and decimal dollar strings. Parse at the boundary without binary-float money or silent rounding. Obtain column mappings through the normal interface rather than company identity. |
| Q18 | Use received business date in America/New_York. Closing day is inclusive. A closed invoice month advances to the earliest still-open month. Processing time cannot change it. Test long lateness and year boundaries. |
| Q19 | Terms are calendar days after invoice date, with no weekend adjustment. A hold preserves the contractual due date. |
| Q20 | Approval limits use strict greater-than comparisons. A community limit overrides the company limit. Otherwise use the manager. Fennor requires a distinct additional finance signer above $10,000, in addition to the board. Both decisions are required, with no signer order prescribed. Reject equally specific conflicting rules. |
| Q21 | At receipt, insurance is valid through its expiry date. Keep an authoritative certificate timeline across vendor aliases. Missing or expired insurance blocks payment but allows entry and business approval. A later replacement can release the hold without rewriting the original receipt-time check. |
| Q22 | Bramblewick reviews eligible snow invoices dated April through October. Fennor's own confirmed rule uses May through September. The flag requires a human decision and does not itself reject payment or alter another field. |
| Q23 | Trim only surrounding invoice-number whitespace. Match the company-specific key against records already posted at arrival. Exclude the current case and future events. Link duplicates to the prior entry and create no new entry, approval request, or schedule. A void-only match permits resubmission. Uncertain identity waits. |
| Q24 | Keep unresolved extracted text distinct from resolved IDs. A human event adds or links a workspace identity before resumption. An external vendor-master write is a separate change requiring authority. |
| Q25 | Employee answers and edits produce candidate rules or case-specific corrections. A permitted rule approver activates a verified general rule. Pretend people have explicit roles and use the same interfaces and authorization checks. |
| Q26 | Rules have scopes and effective intervals. Preserve historical expectations and human events. Test both sides of policy boundaries. Reset trust only for steps whose behavior changes. |
| Q27 | For the declared year of history, the exam is the final three calendar months, partitioned by receipt date or the world's case-opening date. Freeze the split before learning. Incomplete exports need an explicit interval and adequacy decision before any exam claim. |
| Q28 | Historical replay pins facts observed at each arrival, including ledger, insurance, and status state. Use earlier observed actions, not earlier candidate predictions, as historical context. Later postings or voids cannot alter arrival decisions. A separately identified operational simulation may evolve its own ledger. |
| Q29 | Separate permitted inputs and evaluator labels by construction. Check imports and serialized inputs, prompts, logs, tests, and library data. People deliver only answers to current questions through ordinary interfaces. Reference programs, planted labels, and exam details remain evaluator-only. |
| Q30 | Freeze a program before its exam. Exam diagnostics cannot create learning questions, rules, saved training tests, compiler recordings, or library entries. Development informed by public exam results needs a fresh private holdout before broader claims. |
| Q31 | Compare complete canonical decisions and effect payloads. Required unresolved results count as incorrect and also appear as unresolved. Distinguish historical agreement from reference correctness. Count copied corrupted fields individually. Deduplicate saved case-and-expectation pairs while reporting overlapping rule support. |
| Q32 | The earlier support totals and saved-test target are superseded. Keep every supporting or corrected example with provenance. Report membership, overlaps, and deduplication. Do not manufacture tests to meet a numerical target. |
| Q33 | The compiler is not limited to seven invoice rule families. Candidate behavior needs sources, evidence, restricted typed execution, and tests. Accept, reject, and edit answers are durable. Unsupported generalization cannot replace a question. Unexplained leftovers reach a person. Generated execution follows the bounds below. Compiler search limits and termination remain open for the compiler milestone. |
| Q34 | Public synthetic worlds establish fixture behavior. They do not establish performance on unseen companies or rule types. The private held-out world never enters this repository. |
| Q35 | Fixture constants are requirements. Measured results come from dex report. Expected values and prototype estimates are not engine measurements. |
| Q36 | Earlier queue and stream totals are superseded. The opening queue is a named subset of the stream. Mutually exclusive reported categories reconcile to the manifest with no omissions or double counting. |
| Q37 | The earlier November milestone is superseded. Report shadow dates, review start, each step's milestones and resets, and elapsed time from the applicable start. At 300 monthly cases an always-on step can earn trust in about a month. Compute dates from eligible review events. |
| Q38 | An unchanged proposal approval reviews every completed producing step. An edit is a mistake for the producer of the wrong value. Attribute rejections explicitly rather than assuming every business rejection is a calculation error. Count each case-and-step-behavior result once. Unreviewed or unresolved results earn no evidence. Mistakes and behavior changes reset the affected count. Behavior-preserving repairs retain it. |
| Q39 | Assign the company-local ordinal before the first change. Every twentieth otherwise eligible case requires review of each current and later proposal before that proposal's changes execute. Persist the ordinal. Cases already needing review do not advance it. Unattended runs do not increase reviewed-clean counts. |
| Q40 | Pool only identical behavior and applicability classes. Local approval, closing, and payment rules cannot pool by step name. Keep company attribution. Library transfer carries neither trust nor authority automatically. |
| Q41 | The demo uses 300 consecutive clean reviews. The statistical illustration assumes comparable independent cases and stable behavior. Trust is separate from authority. Controllers grant bounded, revocable standing authority through dex events, never through source documents. Production thresholds require a separate policy decision. |
| Q42 | Earlier token and cost estimates are superseded. Demo recordings make zero model-network calls and incur no new billable usage. Report logical invocations, network calls, tokens, and measured cost separately. Calls and touches need per-case, weekly, and program-version distributions and denominators, not only means. |
| Q43 | Your-files mode imports and exports user-selected data through the configured backend. Do not claim browser-only privacy. Retention, deletion, authentication, and hosting policy remain prerequisites for real-company use. |
| Q44 | Support CSV and XLSX. Default to the first XLSX sheet and expose sheet selection. Reject XLS with a conversion message. Validate before mutating a workspace. Do not infer production performance from synthetic workload size. |
| Q45 | Adapters expose reads, snapshots, cursors, stable identities, and authorized changes. Deterministic fixtures prove adapter contracts, not a live integration. A live check requires a named system and authorized access. Each product screen uses the server API. |
| Q46 | Persist effect identity and execution state before a write. Respect dependencies and bounded retries. Reconcile an uncertain outcome before retrying. Restart resumes unfinished effects without repeating completed ones. Repeated source delivery cannot create a second case. |
| Q47 | Pin proposal inputs and versions, require an expected review revision, and revalidate affected preconditions before writing. A changed payload needs renewed exact approval or a valid standing grant covering it. It cannot reuse stale business approval. Conflicting concurrent reviews cannot both succeed. |
| Q48 | Actor-and-time events rebuild workspace state. Versioned save and export preserve source hashes, programs, tests, recorded model results, decisions, waits, trust, grants, revocations, and effect progress. Validate imports before changing existing state. Server roles enforce company boundaries and permissions. |
| Q49 | A renamed column qualifies for repair only through a unique match of normalized value multisets and types in the same frozen data, followed by every saved test. Ambiguous matches wait. Record automatic repair as a system event and manual mapping as a human event. Matching values alone cannot authorize a meaning change. |
| Q50 | Version status meanings by company, source, and effective interval. Unknown or incompatible meanings block dependent decisions until a person answers. A matching string does not prove unchanged meaning. |
| Q51 | The library allows generalized questions, rule shapes, parsers, and checks. Exclude company records, names, identifiers, correspondence, and source-local values. Destination evidence supplies local parameters. Check serialized transfers and generated programs and questions. A contaminated library must fail. |
| Q52 | Compile-time model calls produce versioned, recorded outputs verified and approved before activation. Runtime calls occur only in AI steps through the gateway. Optional pasted-input actions require explicit user authorization. Validate schema and destination identities, record usage and failures, and replay checked outputs. Model text grants no authority. |
| Q53 | Keep demo acceptance separate from production readiness. A pilot needs a process owner, backup, system operator, gate approver, response expectations, retention policy, and measured shadow criteria. Golden changes require the repository owner's approval. Behavior changes declare expected golden diffs and do not regenerate fixtures in the same change. |

## Engine design status

The compile target, human waits, nested control flow, source boundary, and
engine ownership are approved design decisions.
No-history promotion, UI control repair, and evidence for changing a step's
kind remain open.

### What is the compile target?

The target is a versioned, typed program graph.
Its executable leaves are a discriminated union of code, AI, and human steps.
Each step retains its stable identity, behavior identity, plain-English intent,
citations, input and output types, and declared external-change contract.
An external change is a separate declaration, not a fourth step kind.

The procedure is a view of the same graph and metadata that the program executes.
The program also contains its schema, typed functions, dated rules, and tests.
There is no separately maintained English graph that can diverge from execution.

Schemas contain booleans, integers, text, dates, money in integer cents,
explicit optional values, tagged unions, named records, keyed collections,
and typed references.
Unresolved source text and resolved record identities have distinct types.
Untyped values do not enter checked execution.

Code uses one restricted instruction representation.
Python-like source is parsed through an AST allowlist, lowered into that
representation, type-checked, and interpreted.
Generated Python is never executed directly.
Imports, reflection, arbitrary attributes, recursion, ambient time,
randomness, and I/O are forbidden.
Calls between checked functions are acyclic.

Iteration operates over finite collections.
Limits cover source size, nesting, strings, collections, integer magnitude,
allocations, and operation cost, including the work performed by built-ins.
Every activation has a bounded execution budget.
Unsupported instructions and exhausted budgets produce visible failures.
They do not count as successful partial results or trigger an AI fallback.

Generic thresholds, scoped overrides, date windows, validity checks,
uniqueness keys, cutoffs, lookups, parsers, and templates use this same target.
Rules carry evidence, scope, and effective intervals.
Conflicting equally specific applicable rules fail verification.
The invoice reference program supplies process behavior, not language semantics.

The fallback path remains explicit graph wiring.
A code parser returns a recognized result, an unsupported format, or a need
for human input.
Unsupported formats may reach a declared AI step.
Missing or conflicting information reaches a human task.
AI outputs pass their fixed schema and company-record checks before use.
Invalid or unresolved outputs reach a person.
Adding a parser changes the verified code artifact without rewiring this path.

Runtime AI requests go through the gateway outside the core.
Their inputs, prompt and schema versions, results, usage, and failures are recorded.
Replay consumes recordings and makes no new model call.

The parser spike supplies prior evidence for allowlisted interpreted execution.
Its report does not establish the complete target's safety or runtime cost.
The implementation must exercise rejected syntax, resource bounds, and both
worlds' required behavior.
Per-case execution measurements must identify the workload and exclusions
and be published through `dex report`.

### How do human steps and waits execute?

Human tasks identify an exact request revision and work address.
Each task names its eligible role, current assignment, due time, response schema,
requested evidence or decision, and reviewed object revision.
Assignments, reassignments, cancellations, and responses are durable events.

A task can receive a response in dex or observe a decision in another system.
An external decision retains the actual actor, role, decision time, origin,
and reviewed revision. Observation time is recorded separately.
An adapter cannot invent the business actor or turn an absent response into approval.

The core validates response identity, scope, revision, schema, and authorization.
A matching late response may resolve a task that is still open.
Identical redelivery has no second effect, touch, or trust credit.
Wrong-scope, stale, conflicting, cancelled, or superseded responses fail visibly.

Time advances through supplied events.
An overdue notification supplies neither a response nor authority.
Waiting does not poll a model.
Save, restart, and replay preserve the task, its due time, and completed work.

A response resumes only the work that depends on that request.
A changed reviewed object requires a new decision.
The earlier decision remains in the event log but cannot cover the new revision.
Business decisions, program approval, and authority for external changes
remain distinct.

### How are branching and nested records represented?

Control wiring uses `Sequence`, `Choose`, `Each`, `Parallel`, and `Repeat`.
These constructs organize executable steps without adding step kinds.
Typed result references express dependencies across scopes.

A work address contains the case identity, scoped record keys, step identity,
and iteration.
Record keys are stable identities, never list positions.
Program schemas own the meaning of records and their relationships.

`Each` freezes the selected child identities for an activation.
A join completes only when all selected dependencies complete.
An unrequested branch has no instance.
Independent branches retain completed results while another branch waits.

`Repeat` has a finite bound or suspends for a new supplied event before repeating.
Internal execution cannot spin indefinitely.
Each resumed activation remains subject to its execution budget.

Results record the typed inputs and evidence revisions they consumed.
A correction can supersede dependent pending results, tasks, summaries,
and proposals while preserving unaffected work.
It cannot erase an external human decision or a confirmed effect.
Subsequent work records the new revision or proposes an explicit amendment.

Service, site, employee, invoice, and vendor concepts remain in program schemas.
Neither control wiring nor adapters acquire process-specific branching rules.

### How are sources ingested and cited?

[The company bundle contract](../bundle.md) defines the sole company-data boundary.
It specifies formats, immutable original bytes, deliveries, normalization,
historical observations, recordings, and evaluator ownership.

Citations identify the source revision, extraction identity and hash,
section, source locator, exact quote, and passage span.
A changed extraction cannot reinterpret an existing citation.
Exact quotation establishes passage identity, not semantic support.

Receipt, observation, availability, and policy effective time remain separate.
Missing, inaccessible, or contradictory evidence remains unresolved where
it prevents a decision.
Sources and model output remain data, never execution instructions.

Learning receives a materialized projection with no evaluator artifacts,
exam material, future deliveries, or capability to open the original bundle root.
The same exclusion applies to prompts, diagnostics, caches, training tests,
recordings, and library transfers.
Imports and serialized boundaries must reject intentional leaks.

### What verification is enough without history?

The starting path is fixed.
Use procedure-derived scenarios and shadow mode.
Do not manufacture a replay score or an exam.

Decide who approves the scenario coverage and what evidence permits review mode.
Define how branch coverage, rare failures, and human authority paths are exercised.
Choose promotion criteria that remain meaningful when cases are sparse or take days.
Keep these criteria separate from the later clean-review trust count.

### Where do UI adapters sit, and how are they verified?

The pure core cannot operate a browser or perform network I/O.
World 1 must nevertheless operate the AP application's interface.
Repairs must preserve intent, meaning, authority, and effect identity.

Adapters translate typed observations, authorized changes, and reconciliation results.
They cannot implement the program's branching, policy, or business decisions.
The effect protocol below governs uncertain writes.

Control description, rediscovery, and sandbox verification remain open.
Choose how a moved control is found and how the sandbox proves that the intended
operation occurred without changing behavior or meaning.
A repair cannot infer new business meaning from a successful click.

### What evidence permits promotion from human to AI to code?

The engine should reduce model calls and routine human work when evidence supports it.
A recurring input format can become a parser.
A rule-following human task may become code directly.
Promotion is not required to pass through every kind.

Define the evidence, tests, approval, monitoring, and rollback needed for a kind change.
Define how the engine proves that a repair preserves behavior.
A behavior change resets trust. A behavior-preserving repair keeps it.
Keep required customer input and permanent human authority outside automatic promotion.
Measure whether the change actually reduces calls or touches without changing correct outcomes.

### Where does the engine end and a program begin?

The core owns schemas, the checked representation, deterministic execution,
saved scenarios, events, trust, sampling, and authority enforcement.
It imports only itself and the standard library.
It performs no I/O and reads no ambient clock or randomness.
Dates, timestamps, observations, and any seed enter explicitly.

Programs own process vocabulary, schemas, rules, branch conditions, roles,
intent, and source-derived behavior.
Adapters translate observations and authorized effects.
Evaluation owns reference answers, reference programs, and pretend people.

The proposed module ownership is:

| Module | Responsibility |
| --- | --- |
| `dex.core.program` | Schemas, procedure and program types, citations, dated rules, scenarios, and verification contracts. |
| `dex.core.language` | Typed instructions, type checking, and bounded interpretation. |
| `dex.core.runtime` | Graph execution, work instances, transitions, and event rebuild. |
| `dex.core.events` | Versioned event variants and durable identities. |
| `dex.core.authority` | Exact approvals, grants, trust attribution, and sampling. |
| `dex.bundle` | Source ingestion, normalization, validation, and permitted projections. |
| `dex.workspace` | SQLite persistence, revision checks, dispatch, and recovery. |
| `dex.adapters` | External observations, authorized changes, and reconciliation. |
| `dex.demo` | Seeded generation of both worlds and their bundles. |
| `dex.eval` | Evaluator artifacts, isolated execution, and scoring. |
| `dex.cli` | Command dispatch. |

The core exposes these contracts:

```text
verify_program(draft: ProgramDraft, sources: SourceCatalog)
    -> VerificationResult

decide(state: WorkspaceState, command: Command, programs: ProgramCatalog)
    -> Accepted(events) | Refused

rebuild(events: tuple[Event, ...], programs: ProgramCatalog)
    -> WorkspaceState
```

One reducer owns cases, tasks, trust, sampling, grants, and effect progress.
The shell atomically appends accepted events against the expected workspace
revision before dispatching work.
Concurrent conflicting commands cannot both succeed.
Projections and snapshots are rebuildable from the durable event sequence.

Every event identifies its format and relevant program, policy, and evidence
versions. Replay retains the complete referenced artifact catalog.
Unknown versions fail loading rather than being interpreted under current rules.
Rebuild performs no I/O and dispatches no external work.

A case pins its arrival facts, business date, program, and rule bindings.
A later-effective policy preserves older cases' bindings.
New evidence of a missed already-effective policy holds affected pending work
until an approved version rebinds it.
Migration records retained work and superseded pending revisions.
Historical decisions and completed effects remain facts.

An effect key contains company, case, scope, operation, and occurrence.
Occurrence identifies intended repeated work, not a transport retry.
Payload, behavior, program, and adapter versions do not change the key.
Immutable effect revisions bind the exact payload, producing results,
business decisions, preconditions, and authority.

The shell revalidates the revision, preconditions, business decisions,
and current authority before dispatch.
It records the attempt before contacting the adapter.
Confirmation and reconciliation identify the same operation and payload revision.

An adapter must provide atomic deduplication by operation identity, or equivalent
fencing and conclusive reconciliation.
An absent lookup does not permit retry while an earlier attempt can still commit.
Unknown outcomes remain uncertain.
A superseded uncertain attempt must still be reconciled before replacement work.
Retries are bounded and retain the operation identity.

A changed pending payload needs renewed applicable authority.
A correction after confirmation is an explicit amendment.
Revocation blocks new dispatch under that grant.
Reconciliation can still record what already happened.
Program approval, business approval, and trust alone never authorize a write.

Trust evidence is attributed to its producing step behavior and deduplicated
by company and case.
Unreviewed and unresolved results earn no credit.
A writing step receives credit only after correct execution is confirmed
or reconciled.
Behavior changes and mistakes reset affected counts.
Verified behavior-preserving repairs retain them.
Sampling state and grant revocations survive restart.

Compiler, normal runtime, gateway, and adapter code cannot import `dex.demo`
or `dex.eval`.
The CLI can route to their entry points.
Only `dex eval` loads reference programs and keys, then invokes the same pure
engine through isolated simulation.
The generator's evaluator access is limited to fixture construction.

The first milestone uses Python 3.13 or newer, uv, and one `src/dex` package.
`make check` runs Ruff, strict Pyright, pytest with Hypothesis, import-linter,
and the purity and isolation contracts on every pull request.
Contract checks must fail on intentional violations.

Before compiler work, each world's reference program must reproduce its
independently frozen answer key on every historical case.
The same engine build must execute both worlds.
Reference correctness does not claim successful source compilation.

Initial behavioral checks cover typed execution, dated rules, nested work,
human waits, event rebuild, authority, uncertain writes, and trust.
Trust checks include attribution, deduplication, confirmation-dependent credit,
the demo's 299/300 boundary, resets, and persistent twentieth-case sampling.
Full learned streams, library comparison, repairs, and UI integration remain later.

`dex report` lists implemented acceptance checks and their evidence.
It identifies the engine, bundle, program versions, cohort, and cutoff.
Unimplemented requirements remain visibly unimplemented.

## Review boundary

The representation decisions record the approved architecture checkpoint.
They are design contracts, not implemented guarantees or acceptance results.
The remaining questions require their own evidence and review.
Implementation still follows the repository's per-file diff and approval process.

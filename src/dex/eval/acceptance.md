# Acceptance

This document defines required behavior and its evidence.
It does not choose the engine's implementation.
`docs/design/engine.md` governs conflicts.
The world documents define fixture requirements, not measured product results.

## Evidence and isolation

Every deterministic fixture has a versioned evaluator manifest.
It names sources, companies, cases, event chronology, effective policies, and reference behavior.
It identifies expected decisions, effects, waits, and historical mistakes.
Expected values are established independently of the candidate program.
The evaluator cannot revise them to accommodate a candidate's output.

Reference programs, answer keys, mistake labels, response scripts, and exam material remain evaluator-only.
Import checks cover direct and indirect dependencies.
Input-boundary checks prevent answer-bearing artifacts from entering compilation through serialized data.
The checks must fail when an intentional violation is introduced.

Pretend employees, reviewers, and clients use the interface available to real people.
Their responses expose only the answer to the current task.
They do not supply their scripts, the manifest, or future responses.

## Compile the process from its sources

For both worlds, oak drafts a procedure and a program from the permitted sources.
Every step has exactly one kind, `code`, `ai`, or `human`.
Every step cites a specific passage, delivered employee answer, or reviewer correction.
Citations resolve to immutable company file versions and numbered sections.
Ingestion reads exactly the packet files listed by each world.
No specification, evaluator passage map, answer label, or embedded reference program can enter that packet.
Initial sources are ordinary company documents written before adoption of dex, with their own unresolved gaps and dated evidence.
They contain no mention of dex or a demonstration and no editorial explanation that another section is obsolete or contradictory.

The evaluator checks coverage of each reference program's required operations and paths.
The kinds must be correct.
Acceptance does not require a fixed step count, fixed names, or identical decomposition.
A candidate cannot hide a required human business decision inside a code or AI step.
Every operation that changes another system is marked as a change, independently of its kind.
Approving an external change is engine authority over its writing step, not a process step.
The reference programs contain no approve-the-change rows.

Rules, lookups, arithmetic, recurring parsers, and messages assembled from known facts use code.
Unfamiliar inputs may use a narrow AI step with a fixed schema.
The output is checked against the schema and company records.
Invalid or unresolved output stops for a person.
Human steps name a role and a due time.

Every compile question identifies a real gap or contradiction and the decision it prevents.
It cites the relevant source passages or historical observations.
A question already answered by the available source packet fails this check.
Questions may differ in wording while resolving the same evidenced gap.

Confirmed rules and corrections produce saved scenario tests.
Compile-time outputs, generated tests, and approvals are versioned and recorded.
Candidates may run in a sandbox for verification.
They cannot become active or change an external system before verification and program approval.

## Complete World 1

Both companies complete the reference workflow against their AP application instances.
The trace distinguishes extraction, validation, routing, business approval, and external effects.
The successful path reaches a scheduled payment with the exact expected payload.
A correct invoice extraction or sent approval request alone does not pass.

The first-screen opening queue contains the nineteen named cases within the stream totals.
Its saved event prefix includes all required paths and counts earlier human actions once.
C1-S0001 retains the worked invoice's exact amount, dates, board route, posting month, and eventual schedule.
The Rillhaven Rise correction creates a dated rule and saved test and resets only changed behavior.

The evaluator checks these cases explicitly:

- Duplicate matching follows each company's identity rules.
- Voids do not satisfy the posted-record duplicate check, including C2-H0500 and C2-S0005 with status X.
- C1-H2128 and C1-H3208 arrive as explicit cancellations. A later void cannot change an earlier arrival decision.
- True resends include originals posted during history.
- A later posting is unavailable to an earlier duplicate decision.
- Insurance holds and unresolved questions prevent payment scheduling.
- Managers, boards, and second signers decide in the AP application. Dex observes their actor, time, role, and reviewed revision.
- Business decisions remain distinct from operator review and engine authority.
- Rejections and unanswered requests do not become approvals.
- The designated C1 snow sets and counts match the manifest exactly.

Recurring email formats run without runtime model calls.
Approval requests use templates.
The first three F4 cases use their recorded, validated AI fallback.
After the approved parser becomes active, later F4 cases use code.
Malformed or unresolved extraction scenarios produce the exact expected human tasks and no unauthorized effects.

The library may transfer questions, rule shapes, parsers, and checks that generalize.
It cannot transfer company records, identifiers, local rule values, or authority grants.
Each reused rule receives evidence for the receiving company.
Run Fennor in fresh workspaces with and without the same dated library, using identical local inputs.
Report upfront questions, questions after replay, compile and runtime calls, and first-replay agreement for each run.
The first replay occurs after source and library questions and before questions derived from its misses.
The library run asks about the rule absent from Fennor's packet and learning history and records Fennor's own answer.
Fennor's January F4 deliveries use the transferred parser with zero runtime model calls.
The later parser update cannot enter the initial compile before its December 4 release.
Reject Bramblewick names, identifiers, records, and source-local values in Fennor's program or questions.
Validate parameter provenance as well as scanning identifiers. Independently evidenced shared constants are permitted.
Planted leaks of a name, record, and local rule value must each cause failure.
The no-library control's misses remain visible and separate from the passing program's correctness gate.

## Complete World 2 without changing the engine

Freeze the engine build used to pass World 1.
Compile and run World 2 using that same build.
Record and compare the engine identity throughout the run.

World 2 may supply source material, records, compiled artifacts, and boundary adapters.
It cannot add onboarding behavior to the engine or change engine configuration semantics.
Adapters map observations and authorized effects.
They cannot implement the world's branching, policy, or authority decisions.

The evaluator checks nested identities, selected branches, joins, and independent progress.
An unrequested service branch remains absent.
A missing response holds the affected work without erasing completed sibling work.
Responses match their exact requests.
Save, restart, and replay preserve pending tasks, due times, and completed work.

Payroll and benefits setup use synthetic records without SSNs, bank details, or medical data.
The hidden shared-cutover rule comes from learning history and a delivered confirmation, never from the source files or exam.
The owner's activation decision stays human after any number of clean cases.
A changed summary requires renewed authorization.
Each end-of-day cutoff produces its exact completed, pending, and not-started sets.
January 10 includes S004, S006, and S009, giving eight complete, two pending, and six not started.
January 23 has sixteen complete cases and sixteen authorized activation writes.
The exact stream touch counts are 19 at January 10 and 40 at January 23.

## Keep the core independent of either process

`dex.core` contains no process vocabulary or world-specific policy.
Vocabulary checks cover the process-specific symbols and concepts introduced by both worlds.
Generic engine concepts such as cases, steps, events, and authority remain permitted.
The check must fail on a planted process-specific core symbol.

The core imports only itself and the standard library.
Checks reject I/O, ambient clocks, and ambient randomness.
Seeds, dates, and external observations enter explicitly.
Money is integer cents, and dates are `datetime.date`.

Generated code obeys the engine's restricted pure form and runs with its verified tests.
Source documents, emails, and model output remain data.
Adversarial text in those inputs cannot alter execution instructions or escape the compile target.

## Verify history without copying its mistakes

Partition history before learning.
The newest quarter is the final exam.
Exam inputs and outcomes never reach learning or compilation.
The evaluator releases exam inputs only to the isolated execution path being evaluated.

Replay preserves case chronology and historical observations.
A later AP posting or document receipt cannot appear in an earlier case's input.
Later employee answers may establish rules that applied during learning history.
Answer time and policy effective time are separate facts.
A future-effective policy cannot change the expected result of an older case.

Every evaluated stage distinguishes two comparisons:

- Historical mismatches compare the candidate with observed human behavior.
- Reference errors compare the candidate with the evaluator's correct behavior.

Compare normalized decisions and effect payloads, not incidental prose.
Where a fixture determines the result, require the exact evaluator-computed value and case-ID set.
Do not accept a percentage band instead.

At the fully learned version, copied planted mistakes equal zero.
Every planted learning-mistake ID remains in the historical mismatch set.
Leftovers cannot be fewer than the planted learning mistakes.
For each fully learned passing program, the complete mismatch set equals the planted-mistake set.
The Fennor no-library comparison reports its additional errors separately.
An earlier incomplete version may have additional mismatches, which remain visible.

Do not prescribe a universal number of compile questions or intermediate drafts.
Report their actual counts.
When a recorded compile fixture fixes their semantic outcomes, compare those outcomes exactly.

## Check each change

Every event declares its input change, affected cases, expected versions, and expected effects.
Test cases immediately before and on effective boundaries, plus older cases still waiting.

| Event | Required check |
| --- | --- |
| W1-D1, renamed column | Read the October 15 08:00 C1 invoice-register export before arrivals. Repair amount_cents to gross_cents through a unique value-and-type match, run every test, log the repair, and retain trust. |
| W1-D2, new status | Affected work stops before guessing; the delivered answer is cited, verified, and approved before the new meaning is used. |
| W1-D3, moved button | Recover the operation from intent and verify in the sandbox. The old position causes no void. Behavior and trust remain unchanged. |
| W1-D4, dated policy | Receipt date selects the correct threshold, and older pending cases retain the earlier policy. |
| W1-D5, added step | The new human task appears only on the applicable path of a verified, approved version; scheduling waits for it. |
| W1-F4, new format | C1-S0601 through C1-S0603 use recorded AI. Later F4 uses the approved parser. C2-S0901 introduces Fennor F4 in January with no model call in the library run. |
| W1, new community | Rillhaven Rise joins November 15. Correct C1-S0451 in review, confirm the effective limit, save boundary tests, and reset changed approval-selection behavior. |
| W2, unfamiliar status | Only affected work waits for an evidenced meaning; independent branches can continue. |
| W2, changed summary | The old authority decision cannot authorize the changed summary or its external effect. |

A repair can apply with a log entry only when behavior and meaning remain unchanged.
Data repairs rerun every saved test.
Interface repairs also prove the intended operation in a sandbox.
Behavior changes require human approval.
Unrelated cases retain their exact reference outcomes.
Behavior-preserving D1 and D3 retain counts. D2, D4, and D5 reset every step whose behavior changes.
Each reset and subsequent trust date must equal the evaluator's event-derived result.

## Preserve authority and completed effects

Every external effect identifies its exact payload and authority.
The demo begins with per-change approval.
A program approval, business decision, or clean-review streak alone cannot authorize an external write.

On the World 1 manifest's December 20 grant date, each company's controller records a bounded grant in dex after the relevant steps earn trust.
Check the named grantor, company, permitted changes, behavior identities, amount limits, holds, business approvals, and revocation.
Test amount 500,000 cents and 500,001 cents, an unresolved hold, an untrusted producer, and a revoked grant.
A document, email, library entry, or model output cannot create authority.
The grant never supplies a business decision.
Out-of-scope changes require exact approval.

A behavior change returns dependent changes to per-change approval.
After 300 new clean reviews, standing execution may resume only under a still-valid grant covering the change.
Check exact suspension and resumption after D4 and D5 against the evaluator's trust dates.
An expanded scope or revoked grant requires new authority.
A verified behavior-preserving repair retains its count and does not invalidate unchanged authority.

A review action may approve an exact change and attest its producing steps.
It is one event and one touch.
Reject stale proposals, changes to their approved payloads, and conflicting concurrent decisions.
Before execution, revalidate the preconditions on which the authority and business decisions depend.
An unchanged standing grant cannot cover a changed business decision or a scope expansion.

Failure scenarios interrupt execution before a write, after a write, and before receipt of its confirmation.
Recovery inspects or reconciles an uncertain outcome before retrying.
The result contains exactly one intended external effect.
Already completed records, requests, schedules, and activations are not duplicated.
The evaluator checks exact remaining work after each interruption.

Human decisions are events naming actor, time, and the reviewed object or proposal.
Rebuilding state from events preserves approvals, rejections, pending tasks, and revocations.
Replay reuses recorded AI outputs and causes no fresh external effects.

## Verify without history and earn trust

A separate run removes usable history from a source packet.
Oak still produces a cited draft and scenario tests from the procedure.
Verification starts in shadow mode.
Shadow mode records proposals and comparisons without applying external changes.
This run cannot claim replay or exam evidence that does not exist.

Review mode records approvals, edits, and rejections.
Trust tests cover 299 and 300 clean reviews, a mistake reset, a behavior-change reset, and retention after a verified behavior-preserving repair.
An unchanged approval gives each completed producing step one clean review.
An edit resets the producer of the wrong value. Unreviewed and unresolved results earn none.
A repeated response, corrected rerun, or replay cannot duplicate credit.
A writing step earns its reviewed credit only after correct execution is confirmed or reconciled. Pending approval or an uncertain write alone cannot advance it.
A business rejection is not automatically a computation error.
Never-automate business decisions stay human.
The fixture fixes the exact sampled cases for repeatability.
Review opportunities, applicability, and sampling are visible in the report.
Assign sampling before the first change. Every twentieth otherwise review-free case needs review of each current and later proposal before its own changes execute.
The company-local counter survives restart. Cases already requiring review do not advance it.
A sampled mistake resets the affected step and suspends dependent standing execution.
Check exact sampled IDs, resets, first trust dates, and re-earned dates against the evaluator.
World 1's shadow run ends October 1 and review starts October 2.
Always-on steps have enough reviewed cases to reach 300 within 35 days of their initial or changed behavior starting.
Rare and conditional steps report their actual opportunity count rather than borrowing an always-on step's date.

The evidence needed to promote a no-history process from shadow mode remains an explicit engine question.
The implementation cannot silently substitute a fabricated historical score.

## Measure calls and human touches

`dex report` identifies the engine build, fixture manifest, program versions, cohort, and observation cutoff.
It reports compile-time and runtime model calls separately.
Runtime calls are attributed to an AI step and a case.
Retries count as additional calls.

Logical model invocations and actual network calls are separate measures.
A demo recording represents a logical invocation but makes no model-network call.
Waiting, time advancement, and replay do not create new model invocations.

A human touch is a distinct recorded human action.
Retries and event replay do not count the action again.
Each touch has one primary category and can have additional descriptive tags.
Categories distinguish compile clarification, program approval, case review, requested input, business authority, external-change approval, and authority administration.
Reminders, polling, and elapsed waiting time are not human touches.

Report an event ledger and model calls and human touches for each case, including zero-call and zero-touch cases.
Group those case records by Monday-starting week, program version, and their intersection.
Attribute each call or touch to its event week and the version whose work it concerns, not the version active when the report runs.
A case spanning weeks or versions retains all its rows without duplicating events.
Show frequency distributions, zero shares, totals, means, medians, and maxima with explicit denominators.
Show started, completed, and pending cohorts separately.
Separate business decisions, case review, requested input, and exact-change approval without counting a combined review-and-approval action twice.
Never infer touch reduction from skipped case review while omitting continuing business decisions.
Shared compile questions, program approvals, grants, and revocations are reported separately from case execution.
Their weekly and program-version totals remain visible.
Any amortized compile cost names its cohort and denominator.

For fixture-determined counts, observed values must equal the evaluator's exact expected values.
Compute the oracle from the frozen manifest's responses, review attributions, behavior changes, grants, and sampling policy before comparing candidate outputs.
Compare every case's calls and touches, every week-and-version bucket, the sampled case sets, and every step's trust and reset dates.
For World 2, weekly touches are exactly 2, 17, 14, and 7 for weeks starting December 28, January 4, January 11, and January 18.
Its runtime calls are zero in every bucket, not only on average.
Model-dependent compile effort is measured directly without invented expected counts.
Generator calibration may use declared bands across named seeds and sample sizes.
Those bands cannot replace exact fixture gates.

Every numerical product claim published in documentation comes from `dex report`.
Proposed fixture constants remain labelled as requirements until an actual run exists.

## Product behavior through the server API

These requirements restore the product capabilities of the earlier acceptance document.
They require backend behavior. They do not implement the product UI.

| Capability | Required evidence |
| --- | --- |
| Your-files mode | Import CSV and XLSX source records and history for a process, with example files. Confirm or correct mappings and status meanings through the normal interfaces. Default to the first XLSX sheet, expose sheet selection, and reject XLS with a conversion message. |
| Boundary validation | Invalid money, fractional cents, dates, references, or schemas return actionable errors before workspace mutation. Equivalent source encodings produce identical canonical decisions. |
| Learning and review | Start from company sources, inspect replay misses, answer or edit questions, review leftovers, approve or correct proposals, and inspect every version and saved test. No fixed ten-step pipeline or seven-family finder is required. |
| Optional model actions | A requested pasted-input reader is an explicit AI step with schema and identity checks. Optional text rewriting requires user authorization and preserves established facts, roles, and holds. Routine approval requests remain code templates. |
| Source ingestion | Preserve source identity and version, immutable snapshots, and durable cursors. Duplicate delivery and restart create no duplicate cases. A live integration requires a named target and authorized test; the fixture adapter alone does not pass it. |
| Workspace save and reopen | Preserve sources, hashes, decisions, evidence, programs, tests, waits, trust, sampling counters, grants, revocations, recorded AI outputs, and completed-effect identities. Event rebuild, save, reopen, and restart yield the same state. |
| Workspace and decision export | Export a versioned workspace and decisions as CSV with stable case IDs and provenance. Validate archive version, source hashes, recorded outputs, and permissions before import. Invalid imports leave the current workspace intact. Import cannot duplicate effects or enlarge authority. |
| Roles | Server-side checks isolate companies. Employees answer and review within assigned scope. Controllers approve rules and grant or revoke external authority. Engineers connect sources and run diagnostics without implicitly acquiring controller powers. Business approvers decide through their company's application. |
| Concurrency | Stale revisions and unauthorized decisions fail visibly. Two users cannot accept conflicting reviews or create duplicate writes. Pending work survives interruption. |
| Gateway log | Record purpose, compile or runtime phase, company, input identity, model, prompt and schema versions, validated result, usage, and failures. Runtime entries name the case and AI step. Recorded replay adds no network call. Company access controls apply to the log. |
| Golden fixtures | Once fixtures exist, CI compares the declared expected golden diff with actual behavior. A behavior change cannot regenerate goldens in the same change. Only the repository owner approves fixture changes. |
| Repeatable checks | One repository command runs the relevant contracts and behavior checks. Reports identify the seed, manifest, engine, programs, sources, recorded outputs, and event cutoff. The clean demo reproduces its results without model-network calls. |

The API supports every screen's information and actions:

| Screen | Required API behavior |
| --- | --- |
| Overview | Learning summary, lifecycle and gate evidence, current attention cases, and weekly process volumes. |
| Review | Queue, company source evidence, step trace, proposed effects, questions, and approve, edit, reject, or resolve actions. |
| Replay | Historical runs, misses, questions, leftovers, and isolated frozen exams. |
| Procedure | Source-cited steps and kinds, change markers, effective rules, tests, and every program version. |
| Trust | Per-step streaks and reset reasons, trust dates, sampled cases, company and eligible pooled views, grants, and weekly calls and touches. |
| Tests | Saved cases, expected decisions, provenance, current results, and test execution. |
| Library | Inspect generalized knowledge and compare Fennor with and without it. |
| Data | Sources, imports, mappings, status meanings, validation results, gateway records, and drift exercises. |

Long-running API operations expose durable progress, completion, and failure.
Source evidence, model text, and emails cannot execute instructions or bypass permissions.
Real-company retention, deletion, hosting, integration access, and pilot gates remain explicit decisions before production use.

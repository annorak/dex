# M1-09 verification

M1-09 reads and writes company evidence and runs current cases through the existing workspace. All fourteen independent outcomes pass at 0d1575242d01b75035af158def47cc8030eb1215 against master at 9d66353dd4136abccda85ee4d1b49fb88d7fae3c. The stable product patch ID is 47edd7cc1d10ec842d894803a307d56085079342. [PR #8](https://github.com/annorak/dex/pull/8) covers only this milestone.

## Behavior and limits

Company and collection manifests keep company identity separate from session authority. Admission preserves original bytes, source hashes, origins, deliveries, cases, observations, history and recordings. Occurrence, observation, receipt, availability and effective times remain distinct. Later evidence can remain in a valid bundle but cannot become an earlier arrival fact. Future deliveries cannot execute now.

Markdown, text, plain and HTML email, attachments, selectable PDF text, CSV and XLSX retain record, cell, message-part and page provenance. XLSX defaults to its first sheet and supports explicit selection. XLS is rejected with conversion guidance. Unreadable and image-only extraction remains unresolved. Exact decimal arithmetic produces integer cents; fractional cents and invalid dates fail. Confirmed mappings supply meanings and date formats. Company names never select a mapping.

Each extraction has immutable identity, a separately retained extractor version, exact text and Unicode code-point citation spans. Supplied extraction snapshots must match. Deterministic directory and ZIP writers preserve original bytes, stable paths, serialization and archive metadata. Public directory, ZIP and collection admission never opens or traverses eval/. Unreadable-subtree and access-tripwire checks prove that boundary.

All bundle validation precedes workspace mutation. Unsafe paths, symlinks, undeclared or missing files, unsupported versions, hash failures, identity conflicts and invalid chronology fail with context. Delivery retries admit once. Per-record membership prevents aliases, reordered inputs and overlapping groups from creating new arrivals. Distinct records in one delivery and equal-byte resends with new delivery identities remain valid.

Ordinary run requires the exact registered artifact hash and persisted program approval. A real two-source code program passes ordinary registration, saves an explicit approval and produces 7. Unapproved and changed artifacts fail with named errors and unchanged workspace bytes. The existing reducer owns runtime, authority and admission decisions; batch admission appends only after every case is accepted. Source approval flags, imported actions and recordings cannot approve programs, grant authority or complete effects. Replay does no I/O, interpretation or dispatch. M1-07 recovery and M1-08 trust, grants, revocations, sampling, actor binding and expected revisions remain covered by the repository gate.

The existing verifier supports a narrow code-only program with saved scenarios, complete node coverage and replay checks. Programs containing rules, AI or human steps, writes, references or unresolved values retain missing checks and cannot activate. M1-09 does not implement those missing verification capabilities. Learning projection, later milestones, UI, production authentication, production adapters and OCR remain unavailable. No fixtures/golden/ or live model-network calls were introduced.

## Fourteen independent outcomes

Root alone implemented the change. One independent verifier ran repository gates, ten live CLI scenarios and performance. Separate correctness and isolation reviewers audited the pinned revision. Each outcome has its own exact raw transcript in the durable evidence directory. The [verifier report](verifier/round2/report.md) identifies the commands, predicates and receipts.

| Outcome | Result | Evidence |
| --- | --- | --- |
| Repository gates | PASS, 741 tests, Ruff, strict Pyright, import/core contracts, unchanged scanner and help | [Verifier report](verifier/round2/report.md) |
| bundle-roundtrip | PASS, originals, identities, provenance and deterministic directory/ZIP output | [Result](verifier/round2/live/bundle-roundtrip/actual.json) |
| bundle-money-dates | PASS, equivalent cents/dollar and ISO/US representations | [Result](verifier/round2/live/bundle-money-dates/actual.json) |
| bundle-fractional-invalid | PASS, fractional cents, invalid dates and conflicting mappings rejected with context | [Result](verifier/round2/live/bundle-fractional-invalid/actual.json) |
| bundle-email-attachments | PASS, text, HTML, selectable text and part/page provenance | [Result](verifier/round2/live/bundle-email-attachments/actual.json) |
| bundle-xlsx-sheets | PASS, first and selected sheet, XLS guidance, unresolved unreadable/image-only content | [Result](verifier/round2/live/bundle-xlsx-sheets/actual.json) |
| bundle-path-hash | PASS, all named path/file/hash/identity/version refusals precede mutation | [Result](verifier/round2/live/bundle-path-hash/actual.json) |
| bundle-delivery-identities | PASS, retry once and distinct legitimate resends | [Result](verifier/round2/live/bundle-delivery-identities/actual.json) |
| bundle-chronology | PASS, legitimate late evidence preserved without earlier arrival facts | [Result](verifier/round2/live/bundle-chronology/actual.json) |
| bundle-eval-unreadable | PASS, unreadable eval subtree and open/traversal tripwires | [Result](verifier/round2/live/bundle-eval-unreadable/actual.json) |
| bundle-ordinary-run | PASS, real verification, explicit approval, exact artifact, success and refusals | [Result](verifier/round2/live/bundle-ordinary-run/actual.json) |
| Performance | PASS, all five absolute budgets and supported startup comparisons | [Verifier report](verifier/round2/report.md) |
| Correctness | PASS, three initial findings closed | [Final review](correctness/final-validation.md) |
| Isolation | PASS, two initial findings closed and evaluator/runtime/replay boundaries retained | [Final review](isolation/final-validation.md) |

The exact focused command passes 38 tests. All 31 emitted bundle-check commands run at head, including all five roundtrip checks. Rejection tests assert the named reason and unchanged database bytes. Deterministic barriers cover concurrent expected revisions; no timing sleeps are used. Independent readback confirms persisted state and replay.

## Performance

The unchanged historical Timer V2 and recorder passed control checks. Revisions, input bytes, environment, methodology and the 46-step schedule were frozen before measurement. Dependencies were warmed separately. The first trunk CLI invocation was measured cold, before five alternating trunk/head startup pairs and five alternating dependency-parent/head startup pairs. Measurements ran serially after CPU-heavy gates and reviews.

Each size sample reads and validates 10,000 tabular rows and a 10 MiB packet, normalizes every row, writes a deterministic directory and ZIP, and serializes the result to disk and stdout. Processing timing includes output serialization; full-command timing also includes process startup and timing metadata. All 26 measured child processes exited zero with valid clocks.

| Sample | Processing seconds | Full command seconds | Peak RSS bytes |
| --- | ---: | ---: | ---: |
| 1 | 1.213906417 | 1.481322750 | 244432896 |
| 2 | 1.199410583 | 1.461512000 | 245923840 |
| 3 | 1.217870375 | 1.493649917 | 246480896 |
| 4 | 1.191838625 | 1.458699250 | 246333440 |
| 5 | 1.183176750 | 1.452599125 | 244170752 |
| Median | 1.199410583 | 1.461512000 | 245923840 |
| Unchanged limit | 10 | 20 | 536870912 |

Cold trunk help took 0.594203834 seconds and 30441472 bytes. Trunk/head startup medians were 0.085279208 and 0.089322667 seconds, a 4.74 percent increase. Parent/head medians were 0.084499000 and 0.093924000 seconds, an 11.15 percent increase. Median RSS increased about 0.11 percent in each comparison. All supported comparisons stay below the unchanged 20 percent limit. Individual samples and ranges are in the verifier report. No speedup is claimed.

Trunk and the actual dependency parent are the same M1-08 commit in separate pinned checkouts. Both received identical frozen regression and size inputs. Both actually refuse the new scenario and bundle commands as unsupported. Those refusals are neither successful bundle runs nor performance comparisons. No intermediate implementation commit substitutes for the dependency parent.

Outside timing, the verifier reloads every directory and ZIP, counts 10,000 normalized rows, checks their 50005000-cent sum and the exact 10485760-byte packet, and compares original bytes, evidence and deterministic archives. Readback leaves all outputs unchanged. A separate excluded profile identifies extraction snapshot serialization as the largest measured component. It is evidence about the limiter, not an additional performance sample.

## Review applicability and retained failures

Both reviewers passed the exact code head and base above. The first review at b509d09 found future deliveries executing early, mutable case selectors allowing duplicate arrivals, and shared extractor-version identities preventing multi-source catalogs. Isolation found malformed mapping shapes escaping validation and unsupported XLSX compression escaping unresolved handling. Owner regressions failed before the fix. The focused fix closes those findings without weakening catalog or authority checks. The original [correctness FAIL](correctness/report.md) and [isolation FAIL](isolation/report.md) remain unchanged.

The first independent repository gate failed one stale CLI availability test. Its 730 passing tests did not make that gate pass. Earlier owner typing, lint, CLI invocation and test failures remain in their original receipts. A verifier setup probe used the wrong event-revision field and failed before correction. The first excluded profiling command failed because dex has no module entry point; the corrected profile uses the installed CLI script. Setup failures and crashes never count as successful rejection tests or measurements.

This evidence-only packaging commit changes no product, tests, dependencies or commands. Final applicability requires an empty code delta from the reviewed head and an identical product patch ID. The final committed-head make check, push protocol, current base, CI, comments and merge-state readback are recorded in the durable HANDOFF.json after publication. Earlier executions are carried forward by exact unchanged-code evidence, not described as final-head reruns.

PR #1 passed CI and 173 tests, but performance and the full independent reviewer round were incomplete before merge. PR #5 passed CI, 638 tests, twenty CLI lanes and applicable reviews. Its formal M1-06 performance gate failed at 15.030444625 seconds against the unchanged 15-second limit; the owner merged it. M1-07's documented failures, evidence limitations and final applicability remain unchanged. M1-08 passed its final gates, but its earlier correctness findings, typing failure and failed development performance attempt remain historical failures. Its revised probe is not a product speedup.

## Evidence and operator review

Exact raw transcripts, input bytes, databases, profiles, schedules, failed attempts and proposed diffs remain unchanged under /Users/varunvis/workspace/dev/dex/docs/verification/m1-09/. The unchanged scanner rejects hash-bearing raw receipts, schedules and some size results. They remain durable local evidence; no receipt was rewritten, no exemption was added and scanning was not weakened. This commit includes suitable exact reports, scenario results, expected answers and processing-time files. Relative raw-transcript links in copied reports resolve in the full local evidence directory, not the smaller GitHub package.

Review these exact ordinary CLI receipts in the local evidence directory before landing:

- [Registration](verifier/round2/live/bundle-ordinary-run/register.txt) and [explicit approval](verifier/round2/live/bundle-ordinary-run/approve.txt).
- [Approved success](verifier/round2/live/bundle-ordinary-run/success-run.txt).
- [Unapproved rejection](verifier/round2/live/bundle-ordinary-run/rejection-unapproved.txt).
- [Changed-program rejection](verifier/round2/live/bundle-ordinary-run/rejection-tampered.txt).
- [Unsafe-path rejection](verifier/round2/live/bundle-path-hash/rejection-traversal.txt) and [fractional-cent rejection](verifier/round2/live/bundle-fractional-invalid/rejection-fractional.txt).

Model the Domain kept durable arrival identity in the existing reducer. Boundary Discipline kept parsing and chronology checks ahead of mutation. The [decision trail](decisions.tsv) records the choices and findings. Only the operator lands this PR after transcript review. No merge or auto-merge is authorized. Stop after M1-09.

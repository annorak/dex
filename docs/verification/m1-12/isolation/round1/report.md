# M1-12 isolation review, round 1

The goal is to add Veldren and complete the default three-company demo collection without giving learning or runtime access to evaluator answers or source-supplied authority.

Verdict: PASS for isolation at the pinned product head. No severity/file:line product finding in the assigned scope. This is not an overall M1-12 acceptance verdict.

Head: 499198ca10a2a7c3bb69aa5c34b3ceaab71427e6.
Base and merged M1-11 dependency: 5a6faaa69b4644a12593a719c42a9752bdfbb4f9.
Stable patch ID: 274aa5d21338095dc47b05f6f9b7eb65b04e7a1e.
Checkout: /private/tmp/dex-m1-12-20261103.
Evidence: /Users/varunvis/workspace/dev/dex/docs/verification/m1-12/isolation/round1.

## Scope and review

Read AGENTS.md, the full bundle and World 2 contracts, the shared and M1-12 plan, canonical specification-checklist.json, and relevant M1-11 handoff and isolation reports. Inspected the changed generator, evaluator, scenario, CLI, packet, and test code. Traced the actual public command, reader, collection, writer, learning projection, serialization, import, workspace authority and recovery boundaries.

The parent owns all product edits. This reviewer made no product, test or scenario edits, spawned no agents, and ran no full suite or performance measurement. The staffing override keeps the no-comments and deslop review in this independent reviewer. Those lenses found no actionable boundary issue. Changed product Python contains no comment tokens or suppression comments. No comments were deleted or restored; there are no HOLDs, encoding offers or reshape findings.

The Prove It Works principle changed the verification choice: the review uses a freshly generated Veldren bundle, guards real file opens and import resolution, checks actual citations, and reopens the saved view with original access denied. It does not accept the scenario's self_contained boolean as sufficient proof.

## Boundaries proved

- dex.demo.fixtures remains the sole demo-to-evaluator import bridge. It writes the World 2 evaluator outputs only beneath the target eval directory. Public bundle construction completes through admit_bundle and the existing writer before evaluator construction.
- The actual check_bundle route and collection check succeed in a fresh process while imports of dex.demo and dex.eval are forbidden. os.open, builtins.open and io.open reject evaluator paths. The separate guarded admission and projection probe made zero evaluator reads.
- The learning view contains exactly H001 through H036. Every H037 through H048 marker, evaluator passage label, answer-key or response-script marker, World 1 company prefix and original-root path is absent. H006, H018 and H030 response evidence is present. H042 and all future stream responses are absent.
- Shared-date confirmation is excluded at 2026-10-01T09:59:59-04:00 and admitted at 10:00. Its rule effective date remains 2025-10-01. Case inputs and late observations retain separate declared chronology. The probe checks actor, original record values, occurrence, observation, receipt and availability against their source and delivery descriptors for every historical observation.
- All 3,817 projected passage spans independently match their admitted original extraction and projected extraction. Every historical response names an existing earlier request, the same request revision and client, and an exact requested site/field.
- Prompts, diagnostics, caches, saved training tests and compiler recordings reject explicit exam, cross-company and not-yet-available confirmation references. Library serialization rejects company evidence.
- Saved view bytes and the reconstructed source catalog reopen identically with os.open, builtins.open and io.open rejecting the entire original-world directory, including descriptor-relative access. A deterministic write and read of the admitted Bundle yields exact object equality.
- Independent evaluator key reconstruction succeeds with verify_program, runtime decide/rebuild and checked language execution blocked. Altering an observed activation changes no key bytes. Expected answers remain evaluator data; no reference or candidate execution creates them.
- Core, workspace, workspace commands, verification, recordings, all bundle modules, import contracts and core lint are byte-unchanged from base. Ordinary run gained no reference selector. Imported owner decisions, exact-change approvals and activation confirmations remain CSV observations, not authenticated engine commands.
- Focused existing tests prove imported history and recordings confer no authority, ordinary run still requires real verification and persisted approval, source grants cannot borrow controller permission, source actors cannot borrow stored authority, and concurrent import obeys expected revision.
- Focused new tests prove failed Veldren construction after both World 1 bundles have staged publishes nothing. Invalid selectors, seeds, packets, parents and existing directory/file/symlink destinations preserve existing state. A deterministic publication barrier preserves one complete World 2 winner and refuses the other contender.

The nested records retain invented client/site/employee identities. Benefits-only sites receive no payroll fields by construction. Source packets contain no hidden shared-date rule. No new process vocabulary, model polling, ambient runtime I/O, authorization shortcuts, recovery semantics, trust credit, grants, revocations or sampling behavior enters the unchanged engine. These last semantics are an unchanged-code and focused-boundary conclusion, not a claim that the Veldren reference or learned stream has executed.

## Receipts

All recorded commands use docs/verification/m1-10/scripts/record.py unchanged from base. Its SHA-256 is f2b7a2f1ace973c1e03d3e03e912503b9fdfde57dfc09a0da4bb535e5a460486. Receipts preserve exact argv, cwd, pinned revision, initial clean worktree status, stdout, stderr and exit status.

| Receipt | Result |
| --- | --- |
| 001-boundary-probe.txt | Instrumentation FAIL. macOS readlink on /dev/fd returned Invalid argument in the review guard before admission. Preserved; no product inference. |
| 002-focused-tests.txt | PASS, exit 0. All 25 publication, refusal, imported-authority, persisted-approval and revision tests passed. |
| 003-boundary-probe-corrected.txt | Instrumentation FAIL. The guard worked, but the citation check omitted the existing dex-typed-1 value envelope. Preserved; no product inference. |
| 004-patch-identity.txt | PASS, exit 0. Exact head/base, stable patch ID, unchanged recorder hash and clean checkout recorded. |
| 005-boundary-probe-typed-citations.txt | PASS, exit 0. Fresh network-blocked fixture; guarded admission/projection; exact cohorts, chronology and citations; serialized exclusions; original-denied reopen; exact Bundle roundtrip; execution-denied key independence; unchanged protected paths and zero product comment tokens. |
| 006-public-command-import-denial.txt | PASS, exit 0. Actual public bundle and collection command functions run with evaluator opens and generator/evaluator imports forbidden. Public result reports all 64 cases, 708 sources, 408 deliveries and no unresolved source. |

probe.py is the final rerunnable independent probe. Each instrumentation correction was shown before applying. Fresh artifact directories preserve all three attempts. The two probe errors do not consume product fix-forward rounds and are not counted as product rejection evidence.

## Decision-trail audit

Read the owner's decision trail and its cited early integration, byte/key independence, first failing test and later passing test receipts. The recorded early failure is real and preserved: the pre-adequacy projection correctly raises history_adequacy_unavailable. The cited later receipt reports 39 passing tests.

Found one evidence chronology issue. The 19:31:54Z fixtures/cutoff rows named that passing result, but owner/009 finished at 19:32:53Z. The owner appended a 20:17:36Z correction declaring those rows retrospective summaries and receipt times authoritative. Original rows and receipts remain unchanged. The correction closes this report issue without product changes. No unsupported isolation success remains in the inspected trail. Forge and watcher setup are outside this product-isolation verdict.

All review subprocesses have finished. No performance workload was run and no historical milestone was reverified or relabeled. Full repository checks, ten CLI lanes, performance, CI, business correctness and final release applicability remain their assigned gates. M1-12 still stops before merge and before M1-13.

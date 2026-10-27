# M1-11 correctness review, round 1

Verdict: FAIL.

Head: 3ba4b840c192f54f5e1d167b68e7383ef4f69dd8.
Base: 10154578ecaab14d68e1de42fc00c931978b3acd.
Checkout: /private/tmp/dex-m1-11-20261027.

## Scope and evidence

Read-only review of all changed implementation modules, source packets, scenario definitions, tests, and AGENTS.md against the World 1 specification, bundle contract, engine intent, open questions, M1 shared rules and M1-11 plan, and the exact specification-checklist.json. The authoritative design documents were read from /Users/varunvis/workspace/dev/dex because ignored design documents are absent from the pinned worktree.

Inspected src/dex/demo/{world_1,build,native,fixtures}.py; src/dex/eval/{world_1,world_1_schedule,world_1_checks,world_1_scenarios,scenarios}.py; src/dex/bundle/{formats,provenance}.py; src/dex/cli.py; tests/demo/test_world_1.py; all seven tests/scenarios/world1-*.json; all seven docs/sources packet files.

Focused seed-7 in-memory probes, each exit 0:
- /private/tmp/dex-m1-11-correctness/chronology.txt
- /private/tmp/dex-m1-11-correctness/public-chronology.txt

Each receipt preserves exact argv, pinned revision, working-tree status, stdout, stderr, and exit status using the existing record.py. These probes enumerate existing fixture values; exit 0 means the probe completed, not that the fixture passed. No full suite, build, broad fuzzing, or performance timing was duplicated. No implementation files were changed.

## Blockers

### C1. P1: historical postings invalidate later void-only keys

Location: src/dex/demo/world_1.py:237, :277, :335, :370; src/dex/demo/build.py:650.

C1-H0898 and C2-H0500 become posted new invoices with OPEN-003, vendor C1-C02-V01 / C2-V01 and community C1-C02 / C2-C02. Their observed historical actions have posted C/A status. C1-S0004 and C2-S0005 then use the identical duplicate keys, as do each company's SH03, but the independent key calls them eligible void-only invoices. There is no intervening void of the new historical posting. Stream exports initialize from prehistory opening records alone and omit the historical posted ledger.

Correction: give the required stream/shadow void-only paths distinct matching void records, or supply explicit valid intervening void observations. Reconstruct duplicate context from the complete relevant chronology. Assert at every named void-only receipt that no earlier still-posted record shares its applicable duplicate key. Keep the specified historical and stream case IDs and required paths.

### C2. P1: four business decisions precede their requests

Location: src/dex/eval/world_1.py:64 and :129; src/dex/eval/world_1_schedule.py:54 and :128.

The schedule delays review until clerk resolution plus ten seconds, but business responses retain the same timestamp as the clerk response. On October 5, C1-S0005 responds at 09:04:00 and authorizes its approval request at 09:04:12; S0006 is 09:05:00 versus 09:05:12; S0007 is 09:06:00 versus 09:06:12; S0010 is 09:09:00 versus 09:09:12. All have offset -04:00. Request confirmation follows authorization by another microsecond. A real AP decision cannot be recorded for a request that has not yet been submitted.

Correction: freeze a causally ordered case timeline: required resolution, invoice entry confirmation, request submission confirmation, business response, observed response, schedule authorization and confirmation. Assert response time is after its own request confirmation for every role and case, not merely before a due time. Keep the opening prefix and stated resolution deadlines.

### C3. P1: public posting timestamps contradict confirmed execution

Location: src/dex/demo/build.py:721 and :751; src/dex/eval/world_1_schedule.py:175.

The native AP export derives posting time separately as receipt plus one hour, while the evaluator confirms the write shortly after review. For C1-S0002, the October 3 export says posted_at = 2026-10-02T10:01:00-04:00. The operation schedule confirms the same invoice at 09:01:31.000001 and its payment schedule at 09:12:20.000001. Thus the required completed opening case has a payment schedule before its source AP record says the invoice was posted. Resolved cases similarly use another independent formula.

Correction: establish one frozen external occurrence timeline, then independently serialize public observations and evaluator expectations from that chronology. Posting occurrence must precede its successful confirmation, request, and schedule; preserve separate observation/availability times. Cross-check every exported posting against the corresponding external record identity and execution event.

### C4. P1: unknown vendors receive valid insurance without evidence

Location: src/dex/eval/world_1.py:136, :161, :261; src/dex/demo/build.py:502 and :573.

Unknown-vendor resolution creates V11 with a name and identity only. The vendor exports contain V01..V10, and the replacement certificate export only V09/V10. Neither the resolution nor any source supplies a certificate for V11. Nevertheless C1-S0005 and each company's SH04 are declared insurance-valid, have no payment hold, and schedule payment. The policy requires an actual certificate covering receipt; a resolved vendor identity does not establish coverage.

Correction: deliver certificate evidence with the identity resolution or through a separate dated resolution, or link the vendor to an existing identity with valid evidenced coverage. Preserve a missing-insurance hold until that evidence arrives. Verify no successful scheduled case claims valid or replaced coverage without a matching available source or delivered answer.

### C5. P2: approval effects omit required reviewed business context

Location: src/dex/eval/world_1.py:212.

The expected request_approval payload contains identity, amount, roles and response due_at, but omits work, contractual invoice due date, and payment holds. Bramblewick procedure 4.1 and Fennor checklist 4 explicitly require those fields in approval requests. The response deadline is not the contractual due date. As the independent exact effects key, this would reject a faithful request or encourage an incomplete one.

Correction: include the specified work, contractual due date and current hold information in each request payload and its reviewed fields, preserving the distinct task due time. Check held opening cases as well as ordinary requests.

## Other conclusions

The daily-postings-and-opening export name makes incremental content explicit. Retaining prior immutable versions can satisfy the specification without rewriting a full cumulative snapshot every day; a delta format alone is not a blocker. It does not cure C1's missing historical posted context or C3's contradictory occurrence timestamps.

The named history counts, receipt formulas, mistake membership, snow sets, policy boundaries, later-event dates and F4 membership are represented directly. Historical action exports contain native route, posting-month, due-date, signer and snow-review observations, giving evidence for W1-A1 through W1-A8 while withholding Fennor's seasonal answer. The answer key is constructed without executing a reference or candidate; mistakes remain separate observations. Public arrivals are raw email/attachment references with empty facts. These are sound structural choices.

The operation schedule is explicitly logical-operation data, not executable engine commands. Deferring actual step mapping, reference execution, learned streams, library acceptance and UI acceptance is appropriate for M1-11. Review qualification and twentieth-case sampling are chronologically computed at the logical-operation level, with writing credit after confirmation. The timeline blockers above must be corrected before treating their derived touch/trust dates as frozen expected evidence.

The MIME change and immutable one-entry PDF cache were inspected. No additional correctness blocker was established in this bounded pass. Full gates, live CLI verification, isolation review and performance verdicts belong to their assigned reviewers.

M1-10's owner-merged startup regression of 21.67% against the 20% limit remains a historical failure. This review neither reruns nor relabels that result.

Final disposition: FAIL at the pinned head. Recheck the five corrective conditions against the owner's next pinned revision.

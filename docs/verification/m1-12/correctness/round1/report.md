# M1-12 correctness review, round 1

Verdict: PASS.

The reviewed change adds the Veldren fixture world and complete default demo collection. This review covers fixture correctness, specification fidelity, publication failure behavior, and maintainability. It does not claim reference execution or learned-stream acceptance.

- Base: `5a6faaa69b4644a12593a719c42a9752bdfbb4f9`.
- Head: `499198ca10a2a7c3bb69aa5c34b3ceaab71427e6`.
- Stable patch ID: `274aa5d21338095dc47b05f6f9b7eb65b04e7a1e`.
- Worktree: `/private/tmp/dex-m1-12-20261103`, clean and pinned during the recorded probes.
- Recorder: unchanged tracked `docs/verification/m1-10/scripts/record.py` from that worktree.

## Evidence

| Receipt | Independent check | Result |
| --- | --- | --- |
| [01-build.txt](01-build.txt) | Fresh real CLI World 2 build with seed 7. | Exit 0. |
| [02-native-probe.txt](02-native-probe.txt) | Reconstruct requirements from native CSV inputs and observations, then compare all 64 cases with evaluator keys. | Exit 0. |
| [03-boundaries.txt](03-boundaries.txt) | Packet bytes, separate change fixtures, key independence, late publication failure, revision identity and comment audit. | Exit 0. |

The [native probe](probe_native.py) and [boundary probe](probe_boundaries.py) are independent review scripts. Their complete proposed diffs were displayed and saved before creation as [proposed-native.patch](proposed-native.patch) and [proposed-boundaries.patch](proposed-boundaries.patch). The recorder preserves command arguments, pinned revision, working-tree state, stdout, stderr and exit status.

## Findings

No proven defect requires a fix.

The native probe independently checked H001 through H048 and S001 through S016. Historical opening dates, the 36/12 split, service selection, branch readiness and nested identities matched the specification. Exact overlapping historical memberships produced 32 multi-site cases, 16 both-service cases and 24 waits, divided into twelve three-day and twelve five-day waits.

Native client responses named the matching request, revision, client, site and sponsor. Requests contained field names without future answer values. Benefits exports contained no payroll fields. The four hidden cases preserved distinct initial dates and later shared dates. H006, H018 and H030 supplied the learning question; H042 did not appear in it. The confirmation kept its October 1, 2025 effective date separate from October 1, 2026 at 10:00 delivery.

Observed early activations were exactly H008, H019, H031 and H044. All configurations matched their independently constructed expected payloads. Correct keys retained owner authorization, exact-change approval and activation ordering. Removing the observed-action collection did not change the key. Key reconstruction succeeded with verification, execution, replay and function entry points replaced by failures.

All stream case schedules matched the required dates. The native event rows independently produced 40 final touches, 19 through January 10, and weekly totals 2, 17, 14 and 7. The exact January 10 completed set matched the specification. The separate status fixture retained affected and independent branches, exact request identity, a one-day due time, delivered evidence and subsequent verification and approval requirements. The changed-summary fixture ordered the new summary after the first decision and before the renewed decision, exact approval and activation.

Both required packet files matched the original source bytes. Neither contains the hidden rule or evaluator labels. Static review confirmed the existing World 1 generation path and version remain unchanged. The added default path uses the existing staging and writer boundary. A targeted failure injected after the real Veldren public bundle was written left no published destination, removed temporary staging and preserved an existing sentinel.

## Maintainability and scope

The no-comments and deslop reviews ran in this reviewer under the staffing override. Tokenizing every changed Python file found zero comments. There are zero comment deletions, restored comments, HOLDs, suppressions, encoding offers or unenforced comment constraints. No separate subagent was created. No out-of-scope refactor is requested.

The diff changes no core, workspace or bundle implementation. The fixture generation and evaluator construction remain separate. The answer-bearing artifacts and separate change requirements remain under `eval/`. Generated schedules explicitly remain requirements; this review did not execute a candidate program.

The designated verifier owns full suites, CLI lanes, repeatability, complete collection byte comparisons and performance. The isolation reviewer owns projection and import-boundary probes. This reviewer did not duplicate those runs or repeat historical M1-11 verification. The historical M1-11 45.042089291-second result above its 45-second limit and M1-10 21.67% result above its 20% limit remain failures; this verdict does not replace them.

An initial read-only lookup used the original documentation directory for the historical recorder and received a missing-file error. The tracked unchanged worktree copy was then used for every executable probe. That lookup was not treated as a product refusal or a passing test.

No product, test or scenario file was edited by this reviewer.

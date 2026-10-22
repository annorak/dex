# M1-08 independent correctness review

Verdict: ISSUES. Two P1 correctness blockers.

Head: 6f5d88335b5e1b0066283c9ab8de29cf5899366e.
Base: f36d484d25aa7e1eda50841bd55d1e6a995c4689.
Checkout: /private/tmp/dex-m1-08-20261022.

## Blockers

1. P1: sampled mistakes in unattended cases do not reset trust.
   src/dex/core/runtime.py:933 returns before the mistake branch whenever
   review_mode is unattended. Receipt 007.txt trains 300 clean cases, grants
   authority, starts 20 unattended cases, verifies ordinal 20 is sampled, and
   records an explicit reviewer mistake. The count remains 300 and the next
   case's BeginEffectAttempt is accepted. Expected: zero clean count and
   dependent standing execution refused. Replay preserves the wrong state.
   This violates acceptance.md's sampled-mistake reset requirement.

2. P1: one confirmed instance prematurely credits a repeated writing behavior.
   src/dex/core/runtime.py:962-972 deduplicates by case and behavior after
   recording only the first WorkRevision's effects. Receipt 011.txt creates
   an Each with two actual writing instances. Approving and confirming the
   first produces clean count 1 while the second effect remains Proposed
   and unreviewed. At count 299 this can qualify behavior before the case's
   other writes are reviewed and confirmed. A subsequent mistake on the
   second instance resets the count, but cannot undo standing execution
   admitted in the intervening period. Expected: one case credit only after
   all relevant instances and writes are correctly reviewed and confirmed.
   Include later-created instances in the regression coverage.

## Reviewed contracts and evidence limits

Read the shared plan and M1-08 requirements, engine intent, trust/authority
specifications, M1-07 final report and handoff, recovery verifier report,
the changed trust reducer, authority types, events, workspace binding,
scenario driver and fixtures, and focused trust tests.

The code separates qualification from grants, pins company and applicability,
checks all producing code/AI dependencies, bounds amount and scope, checks
preconditions, and rechecks current grants at dispatch. Existing reservation,
attempt identity, reconciliation and retry paths remain in place. Source
review found no additional blocker in those paths. This is not a fresh
execution of all inherited recovery tests or the formal verifier's gates.

Both successful adversarial probes rebuild the event stream while patched
interpretation and file opening raise, proving replay equality for those
probes. No model-network calls or product edits were made.

Scenario expected JSON is used only after execution for comparison. However,
TrustFixture.train approves every proposal without an independent result
comparison. These scenarios establish accounting and protocol behavior,
not independent correctness of every approved value. Regression fixtures
should explicitly check the values they claim to review.

## Comment and trail audit

No added comment or suppression requiring removal was identified in the
reviewed new trust sources. Deletions, restorations and encodings: zero.
No additional reviewer panel was spawned, per the explicit staffing override.

The decision trail preserves the failed first performance probe and the
foreign-grant fixture correction. No audit blocker was found in that log.
The formal verifier owns performance, repository gates and ten live lanes;
none is represented as independently rerun here.

Receipt 009.txt retains a probe fixture field-name error, corrected in 011.
Receipt 012.txt retains a shell quoting error, corrected in 013. The initial
instruction search was broader than needed and completed without edits.
The initial pwd and a receipt read preceded use of the recorder. Those are
read-only bootstrap audit gaps, not substantive passing checks.

The two findings were sent to the owner immediately. Heavy probes are
finished. This reviewer remains available to validate the fixes.

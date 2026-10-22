# M1-08 isolation fix validation

Isolation review: PASS at `f3ba616d28e08a5b9bcb7e61a7bf72774c46f22e`,
against base `f36d484d25aa7e1eda50841bd55d1e6a995c4689`.
This is the same independent review outcome continued from `report.md`.
The initial report and its failed setup receipts remain unchanged.

The reviewed fix delta is `6f5d883..f3ba616`. It moves mistake handling ahead of
positive-credit exclusions and records reviewed work instances before credit.
The original review's authorization findings remain applicable to unchanged
actor binding, local policy enforcement, expected revisions and dispatch code.
The initial CLI matrix and codec/import probes ran at the earlier head only.

No additional isolation, replay or compatibility blocker was found.
The new behavior-work and case-review indexes are populated by the reducer from
events and included in immutable state. They introduce no external input or
alternate authority path. Completion checks current instance revisions and
confirmed effect identities. Historical results still earn no credit.
ReviewEvidence is derived projection data, not a persisted event payload.
Existing typed events rebuild the added indexes without a stored format change.
No new I/O, ambient time/randomness, model/network call or evaluator import was
introduced. Ordinary command binding, codec and workspace code are unchanged.

`009-fix-diff.txt` and `010-fix-types.txt` record the inspected delta.
`011-fix-focused-tests.txt` passed four tests: sampled unattended mistake,
both repeated-writing-instance outcomes, and legacy StartSandbox decoding.
Their replay assertions verify equality after rebuilding the new projections.
`012-fix-replay-trail.txt` confirms the clean exact head and the appended decision
trail, including both reproduced regressions and the fix rationale.

This PASS covers the isolation review only. Fresh final-head repository gates,
all ten CLI lanes and serial performance results belong to the verifier.
No production authentication, adapter integration or live model call is claimed.

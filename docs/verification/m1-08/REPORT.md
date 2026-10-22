# M1-08 verification

This PR adds company-local trust attribution, bounded standing grants and persistent twentieth-case sampling to the existing reducer. Trust qualifies after 300 consecutive eligible clean reviews. It does not grant authority. Writing credit waits for confirmed or reconciled execution. Mistakes reset the affected applicability; changed behavior has a new applicability. Checked repairs with identical normalized behavior retain credit.

Current local session membership, grant scope, amount, holds, trust and revocation are checked again at dispatch. Reconciliation can record work completed before revocation. Permanent business decisions remain human. Programs with missing verification checks still cannot activate. Production adapters, authentication, bundle/run expansion, UI and M1-09 remain unavailable.

Independent repository, scenario, review and performance gates are pending on the frozen commit. No STACK-READY claim is made yet.

The first independent correctness review found two blockers at 6f5d883. A sampled unattended mistake did not reset trust, and a repeated writing behavior received credit after only its first instance was reviewed and confirmed. Regressions reproduced both mismatches before the fix. Credit now waits for the case to finish, all current instances of the behavior to receive clean review, and all their writes to be confirmed. Sampled mistakes reset trust in unattended mode without awarding positive credit. Root's 63 focused tests and updated live sampling scenario passed; independent fix validation is pending.

Fix validation closed both original findings and exposed a third reset case at f3ba616. Two wrong applicability classes sharing one behavior ID reset only the first class. A new regression failed with counts [0, 1] instead of [0, 0]. Review evidence now records each reset applicability so both reset once, while redelivered mistakes preserve later clean streaks. All 24 trust tests pass locally. Final independent validation remains pending.

The size workload contains 10,000 review events. It trains 300 writing cases through ordinary workspace commands, then batches 9,700 evaluator-owned checked case traces and review events for reduction. A final ordinary reopen validates saved events, counts, sampling and grants. This measures event reduction and persistence, not 10,000 ordinary transaction admissions.

Raw receipts and complete proposed diffs are retained at /Users/varunvis/workspace/dev/dex/docs/verification/m1-08. The first size development attempt took 18.716883416 seconds and failed the unchanged 15-second command limit. Removing a redundant middle reopen, while keeping the final full reopen, produced a valid development sample of 11.857747209 seconds. This is a probe correction, not a product speedup claim. Formal cold-start and five-sample evidence is still required.

PR #1 passed CI and 173 tests, but performance and the full independent reviewer round were incomplete before merge. PR #5 passed CI, 638 tests, twenty CLI lanes and applicable reviews; its formal M1-06 sample took 15.030444625 seconds and failed the 15-second limit before the owner merged it. M1-07's documented failed attempts, raw-evidence limitations and final verification applicability remain unchanged in its historical reports.

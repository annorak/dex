# M1-08 verification

M1-08 adds company-local trust, bounded standing grants and persistent twentieth-case sampling. The independent code gates pass at `f3e326b3d2dc4be376e2447034e10d1b8d7d46e3`, against `f36d484d25aa7e1eda50841bd55d1e6a995c4689` on master. The final packaging commit changes only this evidence directory. Its committed-head check and GitHub status are recorded in the PR and the durable handoff after publication.

## Behavior and limits

A behavior qualifies after 300 consecutive eligible clean reviews, counted once per company, case and behavior. Credit belongs to the producing behavior and its applicability. Unreviewed, unresolved, historical and unattended results earn no positive credit. Writing credit waits for the case to finish, every current instance to receive clean review, and every associated write to be confirmed or reconciled. Mistakes reset each affected applicability once. Changed behavior gets a new applicability. Verified repairs with identical normalized behavior retain credit.

Trust never authorizes a write. A named person grants bounded authority separately. Dispatch rechecks company, current behavior, amount, holds, required decisions, trust, grant scope, current role and revocation. Revocation blocks new dispatch while reconciliation can record prior completed work. The company-local ordinal is saved before the first change. Every twentieth otherwise review-free case requires review of its first and later proposals. Already-review-required cases do not advance it.

One deterministic reducer owns these decisions. Local sessions still bind actors, roles and scopes; expected revisions reject stale commands. Source data cannot grant authority. M1-07 operation identity, fencing, deduplication, bounded retries and reconciliation remain covered. Replay does no I/O, interpretation or dispatch. Permanent business decisions remain human. Missing verification checks still block activation. Production adapters and authentication, UI, bundle/run expansion and M1-09 remain unavailable.

## Fourteen independent coverage outcomes

The user authorized one verifier for twelve outcomes and two separate reviewers. Root alone wrote product code. Each row has a separate raw receipt. Saved results and independent reports are linked below; the raw receipt paths are listed in the verifier report.

| Outcome | Result | Receipt |
| --- | --- | --- |
| Repository gates | PASS, 703 tests; Ruff, strict Pyright, import/core contracts and unchanged secret scanner | [Verifier report](verifier/round4/report.md) |
| trust-299-300 | PASS, 299 is unqualified, 300 qualifies after write confirmation | [Saved result](verifier/round4/live/trust-299-300/actual.json) |
| trust-no-grant | PASS, qualification does not authorize; ordinary approval binds actor; stale command fails | [Saved result](verifier/round4/live/trust-no-grant/actual.json) |
| trust-credit-attribution | PASS, producing behavior receives credit; mistakes reset affected credit | [Saved result](verifier/round4/live/trust-credit-attribution/actual.json) |
| trust-pending-write | PASS, no credit before confirmation or reconciliation | [Saved result](verifier/round4/live/trust-pending-write/actual.json) |
| trust-redelivery-replay | PASS, duplicate events do not add credit; replay matches | [Saved result](verifier/round4/live/trust-redelivery-replay/actual.json) |
| trust-change-repair | PASS, behavior change resets applicability; checked preserving repair retains credit | [Saved result](verifier/round4/live/trust-change-repair/actual.json) |
| trust-grant-boundaries | PASS, 500,000 cents allowed within all limits; 500,001, holds and untrusted producers refused | [Saved result](verifier/round4/live/trust-grant-boundaries/actual.json) |
| trust-revocation | PASS, new dispatch refused; prior-effect reconciliation retained | [Saved result](verifier/round4/live/trust-revocation/actual.json) |
| trust-twentieth-restart | PASS, persisted twentieth case and later proposals require review; unattended mistake resets trust | [Saved result](verifier/round4/live/trust-twentieth-restart/actual.json) |
| trust-human-and-pooling | PASS, permanent decisions stay human and incompatible companies cannot pool credit or grants | [Saved result](verifier/round4/live/trust-human-and-pooling/actual.json) |
| Performance | PASS, all five absolute budgets and supported startup comparisons | [Verifier report](verifier/round4/report.md) |
| Correctness | PASS, all three earlier P1 findings closed | [Final review](correctness/final-report.md) |
| Isolation | PASS, current-session authority, evaluator boundary, codec and replay reviewed | [Final review](isolation/final-validation.md) |

The required [24 trust tests](verifier/round4/report.md) pass. Deterministic barriers exercise revocation after reservation and concurrent expected-revision checks. No timing sleeps or live model calls were used. Independent post-run checks reopened all ten live databases and blocked interpretation, dispatch, sockets, subprocesses and file opening during core replay.

## Performance

The unchanged historical Timer V2 measures a fresh child process with monotonic nanoseconds, adjacent UTC clock validation and Darwin child peak RSS. Revisions, identical input bytes, methodology and alternating schedule were frozen before measurement. The first trunk help invocation was measured cold, followed by five alternating trunk/head help pairs. Heavy repository checks and reviews finished before serial measurement.

| Sample | Core accounting seconds | Full command seconds | Peak RSS bytes |
| --- | ---: | ---: | ---: |
| [1](verifier/round4/trust-size-1/actual.json) | 0.993452666 | 12.525088750 | 228048896 |
| [2](verifier/round4/trust-size-2/actual.json) | 1.020638583 | 12.617542459 | 228261888 |
| [3](verifier/round4/trust-size-3/actual.json) | 0.990577459 | 12.523398125 | 228442112 |
| [4](verifier/round4/trust-size-4/actual.json) | 1.007569707 | 12.714207708 | 227901440 |
| [5](verifier/round4/trust-size-5/actual.json) | 1.017659001 | 12.901290125 | 227164160 |
| Median | 1.007569707 | 12.617542459 | 228048896 |
| Unchanged limit | 5 | 15 | 536870912 |

Every sample completed successfully with a valid clock and matching results. Cold trunk help took 0.611511041 seconds and 30703616 bytes. Startup median wall time was 0.090349167 seconds on trunk and 0.081996750 at head. Median RSS was 30490624 and 30523392 bytes. Both ratios remain within the 20 percent regression limit. Trunk and dependency parent are the same M1-07 revision in separate pinned checkouts. Both actually refuse the new trust scenario and size workload with exit 2. These are unsupported baselines, not passes or trust performance comparisons.

The size workload contains 10,000 distinct reviewed cases. It trains 300 writing cases through ordinary commands, then batches 9,700 evaluator-owned checked traces and review events for reduction and persistence. It includes resulting grant checks, sampling, revocation and one ordinary final reopen. It measures accounting and event persistence, not 10,000 ordinary transaction admissions. Core accounting includes full-history reduction plus grant and sampling work; full-command timing also includes fixture construction, codec, SQL save, reopen and final checks.

Outside timing, independent ordinary reopen confirmed all five databases contain 76,307 contiguous events, 10,000 reviewed cases, calculation credit 10,000, writing credit 300, ordinal 20, preserved revocation and 301 unique completed remote operations. Database bytes were unchanged by readback. The measured command performs the stated work. Earlier profiling identifies typed event decoding during full reopen as the dominant cost. That profile is qualitative evidence only and is excluded from formal timing statistics.

## Review applicability and retained failures

Correctness and isolation reviewed `8c4484018ca2ffc8e0c80c91e534be1c6a87e02c`. The only later product change is an explicit type argument on an empty immutable set. The verifier checked that delta, then ran the final repository gates, ten CLI scenarios and performance at `f3e326b`. Earlier boundary probes remain applicable where their code is unchanged; they are not described as final-head reruns. The final packaging commit carries these executions forward only if product and test bytes remain identical, with a fresh committed-head `make check` before push.

The first correctness review found two P1 bugs at `6f5d883`. Sampled unattended mistakes retained trust, and repeated writing instances received premature credit. Regressions failed before the fix. The next review closed both and found a third bug at `f3ba616`: two mistaken applicability classes sharing one behavior reset only the first. The failing counts were [0, 1] instead of [0, 0]. The second fix records each reset applicability and preserves later streaks when old mistakes are redelivered. Both reviewers closed all findings at `8c44840`.

The final gate at `8c44840` failed strict Pyright on an untyped empty set. The typing-only commit fixed it; the final 703-test gate passed. Original ISSUES reports, failing tests, setup errors, prior gate receipts and all earlier revisions remain available. No failed attempt is counted as a pass.

The first size development attempt took 18.716883416 seconds and failed the unchanged 15-second limit. Removing a redundant middle reopen, while retaining the final full reopen and persisted-event checks, produced an 11.857747209-second development sample. This changed the probe, not product performance. Neither sample is part of the formal five-sample result.

PR #1 passed CI and 173 tests, but performance and the full independent reviewer round were incomplete before merge. PR #5 passed CI, 638 tests, twenty CLI lanes and applicable reviews. Its formal M1-06 gate failed at 15.030444625 seconds against the unchanged 15-second limit; the owner merged it. M1-07's documented failed attempts, evidence limitations and final verification applicability remain unchanged in its historical reports.

## Evidence and decisions

Exact raw evidence, databases, inputs, timing schedule, failed attempts and complete proposed diffs remain unchanged under `/Users/varunvis/workspace/dev/dex/docs/verification/m1-08/`. This commit includes concise reports and suitable exact receipts after preflight with the unchanged scanner. All final raw .txt transcripts and the hash-bearing schedule and coverage JSON are scanner-rejected and remain local. They were not edited, allowlisted or reclassified to make packaging pass.

For the exact ordinary command success and refusal, read `verifier/round4/live/trust-no-grant/success-approval.txt` and `verifier/round4/live/trust-no-grant/rejection-stale.txt` under that raw evidence directory. The tracked lane-02 receipt records the enclosing successful scenario and its assertions. Relative .txt links in copied independent reports resolve in the full raw evidence tree, not this tracked subset. Local raw files are not claimed to be downloadable from GitHub.

The Model the Domain principle kept trust, grant and sampling state in the existing reducer. Explain the Number required independent persisted-work checks, a named timing boundary and honest unsupported baselines. The [decision trail](decisions.tsv) records these choices and the accepted fixes. No merge or auto-merge is authorized. The operator lands this single PR.

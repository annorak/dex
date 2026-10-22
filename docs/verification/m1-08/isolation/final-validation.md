# M1-08 final isolation validation

Isolation review: PASS at `8c4484018ca2ffc8e0c80c91e534be1c6a87e02c`,
against base `f36d484d25aa7e1eda50841bd55d1e6a995c4689`.
This continues the same independent review recorded in report.md and
fix-validation.md. Both earlier reports remain unchanged.

No additional isolation, codec or replay blocker was found in the final delta
`f3ba616..8c44840`. ReviewEvidence now remembers reset BehaviorKeys so different
applicability classes sharing a behavior ID reset independently and only once.
This field is derived projection data rebuilt by the reducer. No stored event,
command format, actor binding, policy, dispatch or ordinary CLI path changed.
The unchanged boundary code retains the earlier static review and probe evidence.
Those probes are earlier-head executions, not reruns at this head.

`013-applicability-diff.txt` records the complete reviewed delta.
`014-applicability-tests.txt` passed five tests covering mixed applicability,
sampled unattended mistakes, both repeated-instance outcomes and legacy decoding.
The regression tests also assert equal event replay after the reset sequences.

This PASS is the isolation coverage outcome only. Repository gates, ten live
lanes and performance remain the verifier's responsibility. No live model,
production authentication or production adapter verification is claimed.

# M1-08 fix validation

Verdict: ISSUES at f3ba616d28e08a5b9bcb7e61a7bf72774c46f22e.
Base: f36d484d25aa7e1eda50841bd55d1e6a995c4689.
Reviewed delta: 6f5d88335b5e1b0066283c9ab8de29cf5899366e..f3ba616.

Both original P1 findings are closed. Receipt 017 reruns the exact original
probe commands. Unattended sampled mistakes reset to zero and block the
next attempt. The repeated writer earns zero while its second instance
remains Proposed. Receipt 018 passes all 23 focused trust tests.

Receipt 021 independently exercises an event-suspended Repeat with two
writing iterations. Credit remains zero after first confirmation, rebuild,
resumption, second review, and until second confirmation. It then becomes
exactly one. Literal result assertions and replay equality pass.

Deferring positive credit until the case succeeds is conservative and
consistent with the requirement to cover later-created instances. Mixed
applicability within one case conservatively earns no shared positive
credit. The fixture now checks literal expected values before training
approvals, closing the earlier evidence limitation for training.

A related P1 reset blocker remains. In src/dex/core/runtime.py,
review_result returns when the prior case/behavior evidence is a mistake,
without comparing the prior applicability class to the current one.
Receipt 023 trains two admitted pure programs with distinct node behavior
signatures and the same behavior ID. Both counts are one. A third admitted
Sequence combines those same nodes. Recording a mistake for each yields
[0, 1], not [0, 0]. Replay reproduces the state. At the trust threshold,
the second wrong applicability class would retain qualification.

Deduplicating case credit must not suppress negative evidence for another
affected applicability class. Retain once-per-class mistake deduplication
while resetting every explicitly reviewed wrong class.

Receipt 022 retains a failed search for a nonexistent verify.py; it is
not treated as a product failure. Initial report and all original failures
remain intact. No product edits, extra agents, or model-network calls.
CPU probes are finished. Formal gates and performance remain owned by
the designated verifier. This report does not authorize landing.

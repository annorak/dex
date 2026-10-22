# M1-08 final independent correctness review

PASS within the reviewed scope at
8c4484018ca2ffc8e0c80c91e534be1c6a87e02c.
Base: f36d484d25aa7e1eda50841bd55d1e6a995c4689.
Checkout: /private/tmp/dex-m1-08-20261022.

All three reported P1 findings are closed. Receipt 026-final-probes.txt
reruns the exact recorded probes against this head:

- A sampled unattended mistake resets the affected count to zero and
  refuses the next dependent standing-authority attempt.
- Confirming one of two writing instances gives zero credit while the
  second remains unreviewed.
- An event-suspended Repeat retains zero credit across rebuild and later
  instance creation. Credit becomes exactly one only after every instance
  is reviewed and its writes are confirmed.
- Two wrong applicability classes sharing one behavior ID both reset.
  Counts move from [1, 1] to [0, 1] to [0, 0].

Receipt 027-final-tests.txt passes all 24 focused trust tests. The added
mixed-applicability regression also earns new clean streaks and redelivers
both old mistakes, proving those duplicates do not reset the new streaks.
Every independent probe verifies replay equality without interpretation
or file opening through the core replay path.

Reviewed both fix deltas in full. Case completion is a conservative
credit boundary that prevents future instances from qualifying a behavior
prematurely. Mixed applicability in a case does not pool positive credit.
Negative evidence now records each affected applicability independently.
Generation checks still prevent late confirmations from crossing resets.
The evaluator training fixture now compares literal expected results and
payloads before approval.

No further blocking correctness issue was found in the reviewed trust,
sampling, authority, current-policy dispatch, replay or recovery changes.
The initial report describes the broader contract review and its limits.
This is not an independent rerun of repository gates, all ten live lanes,
performance, or every inherited recovery test. Those remain the designated
verifier's responsibility. Production adapters and activation remain
outside the implemented scope.

The comment and decision-trail audit found no additional blocker.
No product edits, commits, pushes, extra agents, or model-network calls
were made. All initial failures and the two earlier ISSUES reports remain
preserved. CPU probes are complete. This verdict does not authorize merge.

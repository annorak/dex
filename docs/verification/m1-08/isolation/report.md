# M1-08 isolation review

Head: `6f5d88335b5e1b0066283c9ab8de29cf5899366e`.
Base: `f36d484d25aa7e1eda50841bd55d1e6a995c4689`.
Disposition: no additional isolation finding. Overall PASS withheld pending the
correctness review's trust-reset fix and review of the resulting head.

## Findings

No additional blocker found in this review's assigned boundary scope.
The owner reported a separate P1: a sampled unattended mistake can escape the
trust reset because positive-credit exclusions run before mistake handling.
This report does not claim that finding is fixed or independently reproduced here.

## Reviewed boundaries

- The ordinary workspace binds actor and company policy outside source data.
  New trust commands pass current local role/scope checks before reducer mutation.
  Expected revision is checked inside the SQLite transaction and in the reducer.
- Grant admission requires earned company-local behavior, a named controller,
  bounded operation/scope/amount/conditions and an aware validity interval.
  Dispatch checks current controller membership and revocation separately from
  the historical case policy. Sampling remains a separate exact-review barrier.
- Trust commands use the existing event reducer and persistence. New core code
  imports only standard-library and core modules. No new I/O, ambient clock,
  randomness, network, model call, or replay interpreter was found in the diff.
- Ordinary commands have no evaluator adapter selector. Registration still
  reports missing verification checks, and activation remains unavailable.
- Scenario expectations are compared after fixture execution. They do not feed
  trust reduction or authority decisions. The new fixture modules stay in eval.
- M1-07 attempt identity, reservations, fencing, bounded retry and reconciliation
  remain in their existing owners. The dispatch change substitutes the common
  authority validator; reconciliation can still observe earlier execution.
- The changed code adds no explanatory comment blocks. The reducer remains the
  single owner of trust/grants/sampling; no additional abstraction is warranted.

## Independent probes and receipts

- `006-cli-authority-matrix.txt`, exit 0: all nine ordinary CLI requests reject
  forged source authority with exit 1 and `session_authority`. Grant, revocation
  and result review were each tested with a missing local actor, role and scope.
  Every attempt preserved the complete reopened state at revision 15.
- `005-codec-import-probe.txt`, exit 0: old StartSandbox bytes default to review;
  invalid string, null and integer modes fail with `typed_field_type`.
  Importing the ordinary workspace command module loads no evaluator modules.
- `004-pinned-source-diff.txt` records the complete reviewed boundary diff.
- `007-requirements-trail-audit.txt` records requirements and the decision trail.
  The trail preserves the failed first performance probe and revised workload
  rationale. It still needs the current review/fix outcomes before handoff.

## Limits and failed attempts

Receipts 001, 002 and 003 are failed probe setup attempts, not passes. 001 lost
the virtualenv interpreter while resolving a symlink. 002 proved the CLI refusal
and unchanged state, then addressed the wrong codec envelope level. 003 omitted
the codec expected-type argument. 005 and 006 are the corrected passing probes.
Initial source/rule reads were retained in the conversation without recorder
wrapping. Subsequent pinned diff and requirement reads are recorded above.
No product files, commits or pushes were changed by this reviewer. The full
suite, ten scenario lanes and serial performance probes belong to the verifier.
This review made no live model call and does not prove production authentication,
production adapters, held-out evaluation, or the correctness review's fixes.

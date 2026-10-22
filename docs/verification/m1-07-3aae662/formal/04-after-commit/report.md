# M1-07 lane 04: PASS

Head: e7eabc89ac47e6abb870e4e4f4306dc891b53217
Base, parent, frozen trunk: 80e60aac6ab78017020e5fce4c625c5fcb169ac1
Stable patch ID: 98794acdc178e34957554428ff611fd4825b926d
Worktree: /private/tmp/dex-m1-07-lane04
Scenario SHA-256: d2a6708bc7e18eeb16e790fe3e578290c65694d8f2a61f121c03b7de8f5f53c5
uv.lock SHA-256: 80663649dc0d95981af2122c4e86ec3b795313875263ea8bdc00dbb39d077950
Environment: Python 3.13.11, uv 0.11.31, detect-secrets 1.5.0, macOS arm64.

Principal command: env UV_CACHE_DIR=/private/tmp/dex-m1-07-audit/formal/04-after-commit/uv-cache DEX_MODEL_NETWORK=disabled uv run dex eval --scenario tests/scenarios/recovery-after-remote-commit.json --out /private/tmp/dex-m1-07-audit/formal/04-after-commit/run-01
Principal receipt: principal04-after-write.txt, exit 0.

Predicate: a remote commit followed by lost local confirmation reopens and reconciles the original receipt without a second applied write.
Observed: interrupted=true; writes_before_reopen=1; unresolved_before_reopen=1; replay_equal=true; remote_writes=1; confirmed_effects=1; unresolved_attempts=0. All five emitted expected matches are true.

Independent SQLite assertions in 10-independent-bindings.txt passed. Event prefix through revision 17 rebuilds one unresolved attempt and zero confirmed effects. Final revision 21 has one confirmed effect, no unresolved attempts, and the same single reservation. The log contains one BeginEffectAttempt transition, one applied ReconcileEffect transition, and zero ConfirmEffect transitions. Remote attempts contains one row total and one applied row.
Operation: eaf1a76a0fb63761dcbdb3f50cef4b339a75ddf934e11923a9becfd4fe884d90
Attempt: eaf1a76a0fb63761dcbdb3f50cef4b339a75ddf934e11923a9becfd4fe884d90/12
Receipt adapter: fixture-adapter-1. Receipt evidence: 2beb225de747c5103631e02149067f085b9e43f5d2fcc45ea1ac273f13cf89af.
Assertions bind receipt external ID to remote operation, adapter revision to remote version, evidence to SHA-256 of remote payload, payload to original effect revision, and attempt/effect identities across begin and reconciliation.

Source inspection in 07-code.txt and 09-db-source.txt confirms the fault occurs after remote COMMIT and before returning its outcome. Recovery calls reconcile; the adapter reads the existing matching row and does not insert another row. Expected values are checked separately after execution.
Limits: this is the evaluator-owned deterministic adapter and SandboxWorkspace. It overrides normal activation eligibility for protocol testing; normal activation remains blocked by missing checks. No live integration, production authentication, standing authority dispatch, UI, or model-network verification is established. The environment flag is not a network firewall; the exercised fixture code makes no model calls. No baseline run, fuzzing, performance campaign, or broader correctness verdict is claimed.
Failures: initial unrecorded worktree creation hit sandbox denial; 01-worktree-escalated.txt succeeded. 02-pin.txt failed because gitleaks was unavailable; 08-env-hashes.txt pins the actual installed scanner. 05-sync.txt hit shared uv-cache denial; 06-sync-escalated.txt succeeded. supplemental-pre-helper.txt records the initial unwrapped commands.
All evidence concerns this head. 11-final-requirements-clean.txt verifies empty git status and clean staged/unstaged diffs. Product sources unchanged; no commit or push. Other lane verdicts and preserved earlier milestone limitations remain the root's responsibility.

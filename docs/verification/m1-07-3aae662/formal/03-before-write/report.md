# Lane 03: recovery before write

PASS for the assigned deterministic recovery contract. No product defect proved.

Head: e7eabc89ac47e6abb870e4e4f4306dc891b53217.
Parent and frozen base/trunk: 80e60aac6ab78017020e5fce4c625c5fcb169ac1.
Stable patch ID: 98794acdc178e34957554428ff611fd4825b926d.
Detached worktree: /private/tmp/dex-m1-07-lane03.
All paths below are relative to this report's directory.

## Predicate and observations

The persisted attempt survives reopen with its operation identity intact. Recovery reconciles it conclusively before retry. Every adapter contact has a matching committed dispatch reservation. Exactly one effect applies remotely and is confirmed locally.

The actual command was `env UV_CACHE_DIR=/private/tmp/dex-m1-07-audit/formal/03-before-write/uv-cache UV_OFFLINE=1 uv run dex eval --scenario tests/scenarios/recovery-before-write.json --out /private/tmp/dex-m1-07-audit/formal/03-before-write/run-01`.
It exited 0. See principal03-before-write.txt.
run-01/actual.json reports interrupted=true, writes_before_reopen=0, unresolved_before_reopen=1, replay_equal=true, operation_count=1, remote_writes=1, confirmed_effects=1, unresolved_attempts=0, revision=30.
run-01/expected.json records all four expected matches as true. The broader predicate above was checked independently.

The injected fault is reservation_durable, workspace.py line 284, after atomic append of the BeginEffectAttempt and ReserveDispatch events, before adapter.execute at line 311.
The workspace uses synchronous=FULL, BEGIN IMMEDIATE and COMMIT for accepted event batches.
In the principal database, attempt /12 begins at revision 13 and has a durable reservation at 17. Reconciliation records its atomic fence at 18-21. Retry /21 begins at 22, reserves at 26, and confirms at 27-30.
The remote database has exactly two attempt rows, /12 fenced and /21 applied. Their operation, payload and adapter version are identical. Both databases pass integrity_check.
See 09-mechanism.txt and 10-database-facts.txt for source and raw durable facts.

Same operation identity means the unchanged EffectKey, including company, case, scope, operation and occurrence, hashes to the same adapter operation ID:
eaf1a76a0fb63761dcbdb3f50cef4b339a75ddf934e11923a9becfd4fe884d90.
Attempt IDs differ intentionally, with /12 and /21 suffixes derived from workspace revisions. Recovery does not resend the fenced attempt. It obtains a conclusive fence before starting a new attempt for the same operation.

The independent restart_probe.py ran in two separate Python processes using fresh run-03 databases.
15-fresh-before.txt proves one persisted unresolved reservation, zero remote rows, zero writes and zero adapter contacts at interruption.
16-fresh-after.txt proves exact state-hash equality on fresh-process reopen, then one reconcile contact for /12 and one execute contact for /21.
Each contact independently opens the SQLite event database read-only and checks the committed reservation, effect reference, adapter revision and operation-key hash before calling the deterministic adapter.
The final remote rows are fenced/applied with one shared operation/payload/version and exactly one confirmed local effect. No unresolved attempt remains.
Socket connect and create_connection are replaced with assertions in this independent probe; no socket connection was attempted.
This proves no unrecorded adapter contact in the observed path. It is not a model gateway or live integration test.

## Inputs and environment

SHA-256:

| Input | Hash |
| --- | --- |
| tests/scenarios/recovery-before-write.json | 40af1d5f5b6938c5b0405655492a5749aa30ee2bd1cef28409dc8f92143d03d0 |
| uv.lock | 80663649dc0d95981af2122c4e86ec3b795313875263ea8bdc00dbb39d077950 |
| pyproject.toml | 291bb13bbe19e42757261ecaf50b82ec8c7c9f5e6c39d1f0d80bf8fe469362f1 |
| src/dex/workspace.py | 1de193f10887a0a5da851f78bc592e50ff025011749e1e0655b3e2830ac1ac88 |
| src/dex/eval/recovery.py | 0cc48810656fb16256a8ab4366687aaa1a4a80a0fbe4ec9b75a0d15dc3c5c774 |
| src/dex/eval/recovery_fixture.py | c8c38f2671fe525f91a7eb897073235f227872c3297aae5b3935ef44cd046786 |
| restart_probe.py, final | 0d3435227a48f6a9f591f55ee28a74a816e3331e0e1d4925b95bcf60bc672374 |
| formal-brief.md | 6b6e32c5c9238d92e3e662dc26d0758d68ffc377512af2f149cb3aa1a2838915 |
| record.py | f2b7a2f1ace973c1e03d3e03e912503b9fdfde57dfc09a0da4bb535e5a460486 |

Python 3.13.11, uv 0.11.31, detect-secrets 1.5.0. Frozen all-groups installation succeeded in 07-sync-escalated.txt. Full installed versions appear there.
The principal command uses uv offline mode. Its synthetic program is a restricted identity code step, with evaluator-owned deterministic SQLite adapter and no AI step or model call path.

## Command evidence and failed attempts

Every receipt contains exact argv, cwd, revision where available, dirty state, stdout, stderr, exit and elapsed time.
00-bootstrap-reconstructed.txt honestly reconstructs the successful initial brief read from the tool transcript. The full brief is durably reread in 17-final-evidence.txt.
01-context.txt records instructions and skill reads before worktree creation. Its repository revision is the original checkout, not the tested head.
02-worktree.txt failed exit 128 because sandbox denied Git metadata writes. 03-sync.txt failed exit 127 because that worktree was absent. Neither is a product result.
04-worktree-escalated.txt successfully creates the exact detached head.
05-sync.txt failed exit 2 on uv cache sandbox access. 07-sync-escalated.txt succeeds after the required escalation.
06-discovery.txt, 08-source-docs.txt and 09-mechanism.txt record requirements and implementation inspection.
principal03-before-write.txt and 10-database-facts.txt record the actual live run and independent database inspection.
11-fresh-before.txt passed the original fresh-process setup. 12-fresh-after.txt failed an incorrect audit assertion expecting Approved after a fence. The contract is Reconciled(FencedNotApplied), as 13-fence-state.txt shows. This is an audit-script mistake, not a product failure or expected rejection.
14-probe-v1-and-requirements.txt preserves the full original probe before its two-assertion correction. run-02 remains untouched after that failed assertion.
15-fresh-before.txt and 16-fresh-after.txt pass the corrected probe on fresh run-03.
17-final-evidence.txt records final input hashes and clean source status.

## Limits and source integrity

Effect recovery uses SandboxWorkspace and the evaluator-owned deterministic adapter. That subclass bypasses normal program dispatch eligibility only for deterministic adapters. The registered effect program still lists missing verification checks; this lane does not establish normal activation, standing authority, production authentication, a live integration, UI, model-gateway behavior or later milestones.
The principal scenario closes/reopens within one process. The independent run-03 probe adds actual fresh-process recovery but uses an injected exception and clean process exit, not power-loss or filesystem failure.
No baseline workload was executed in this lane. Pre-worktree setup receipts identify their original revision; all actual recovery evidence is on the exact head.
Source files remained unchanged. Final git status is empty and git diff --exit-code succeeds in 17-final-evidence.txt.
No source edits, fuzz campaign, performance claim, commit or push occurred. This lane does not declare the PR STACK-READY.
The brief's historical limits remain unchanged, including the failed M1-06 15-second sample and incomplete PR #1 independent/performance evidence.

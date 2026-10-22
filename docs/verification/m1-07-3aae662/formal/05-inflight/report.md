# Lane 05: PASS

Head: e7eabc89ac47e6abb870e4e4f4306dc891b53217
Parent/base/frozen trunk: 80e60aac6ab78017020e5fce4c625c5fcb169ac1
Stable patch ID: 98794acdc178e34957554428ff611fd4825b926d
Worktree: /private/tmp/dex-m1-07-lane05
Evidence directory: /private/tmp/dex-m1-07-audit/formal/05-inflight

Verified the added M1-07 absent-lookup/in-flight recovery contract on the exact head.
No source files were changed. Final git status and diff were empty in receipt 15.
No commit, push, mutation/fuzz campaign, performance run, or child agent.

## Method and observations

Principal command, receipt 10-principal05-inflight.txt:
env UV_CACHE_DIR=/private/tmp/dex-m1-07-audit/formal/05-inflight/uv-cache UV_OFFLINE=1 PYTHONHASHSEED=0 uv run dex eval --scenario tests/scenarios/recovery-lookup-absent-inflight.json --out /private/tmp/dex-m1-07-audit/formal/05-inflight/run-cli

Exit 0. Read actual.json and expected.json directly in receipt 14. All six matches
are true: lookup absent, zero applied writes, uncertainty after recovery, one
reservation, one unresolved attempt, and replay equality. Local revision is 21.
The remote SQLite row is pending, not absent. The scenario alone does not release
the pending attempt or exercise retry/replacement; the independent probe covers these.

Independent command, receipt 13-independent.txt:
env PYTHONHASHSEED=0 UV_OFFLINE=1 .venv/bin/python /private/tmp/dex-m1-07-audit/formal/05-inflight/probe.py

Exit 0. Fresh run-independent databases. Two threading.Barrier instances order the
completion worker, with bounded waits and no sleeps. After reopening and recovery,
lookup is absent and the original remains uncertain. While completion is held,
retry and a corrected, separately approved replacement each return Accepted
reconciliation, with no new dispatch admission. Assertions check one reservation,
one original unresolved reference, zero applied writes, and one pending remote row.
Releasing the barrier makes the original attempt commit. Recovery reconciles that
original revision, clears uncertainty, and preserves its confirmed identity.
Replacement then returns Refused(code='amendment_required'). Reopen equals the
saved state at revision 34, with exactly one reservation and one applied remote row.
Full local events and remote rows are in independent-observations.json.
Both local and remote databases in both runs report PRAGMA integrity_check = ok.

Operation ID:
eaf1a76a0fb63761dcbdb3f50cef4b339a75ddf934e11923a9becfd4fe884d90
Attempt ID:
eaf1a76a0fb63761dcbdb3f50cef4b339a75ddf934e11923a9becfd4fe884d90/12
Adapter revision: fixture-adapter-1
Original effect revision: 1. Replacement revision: 2. Both retain the same key.
The probe compares the remote payload bytes to codec.dumps(original EffectRevision).
The local reservation and final ReconcileEffect retain the same operation/attempt,
original revision, adapter revision and original payload receipt.

## Protocol inspection

Receipts 09, 11 and 15 contain fixture, shell and adapter source. Workspace.dispatch
first reconciles unresolved_attempts[key], before starting/reserving a new attempt.
Reservation is durable before adapter admission. A transaction refreshes and checks
session and exact dispatch authority before adapter.execute. Pending becomes
MarkEffectUncertain; recovery calls adapter.reconcile on the original durable request.
The fixture atomically binds attempt identity to operation, payload and adapter
version in SQLite. Reconcile leaves an existing pending row pending. lookup selects
only applied rows, so its absence is insufficient evidence of non-application.
finish transitions that same pending row to applied. Atomic per-operation admission
also rejects a second unresolved/applied revision. These are fixture protocol proofs.

## Versions and hashes

Frozen sync succeeded with CPython 3.13.11 and uv 0.11.31. detect-secrets is 1.5.0.
Initial host python3 is 3.11.6; verification used the synced 3.13.11 interpreter.
UV_OFFLINE=1 prevents uv network use. The evaluated code uses only the deterministic
SQLite fixture and makes no model calls; this lane does not test network enforcement.

SHA-256:
- scenario: 175c0658dd3e59b0d9b2c9162a571c538c799dd0cc558a1e1c641c0dc327e92e
- uv.lock: 80663649dc0d95981af2122c4e86ec3b795313875263ea8bdc00dbb39d077950
- probe.py: bdd9f040fe71dbeba7178e5e9d23582192e231a9eb33a110262a5bfa53f384a6
- independent-observations.json: 3c60298d7f6c2b8743c0747392cc19bc9b91ff08fa4f0891b49b57ec370a2174
- actual.json: c2fdeb2a6544e4af0b7d2664b01f2eb6649aaac96251d381bd990552192f7413
- expected.json: 5bb32474c4f027eb66f821caa68136e90212440b7c3ed785ccb68ed0cfb18511

## Receipt inventory and failed attempts

Every numbered command receipt stores argv, cwd, revision, dirty status, stdout,
stderr, exit and elapsed time. No receipt was overwritten.
01 worktree: exit 128, sandbox denied .git/worktrees creation.
02 instructions: exit 127, dependent read failed because worktree did not exist.
03 escalated worktree: exit 0, exact detached head installed.
04 instructions and boot rules: exit 0.
05 engine/spec/scenario contract: exit 0.
06 versions: exit 127 because gitleaks is absent. This repository uses detect-secrets,
not gitleaks. Correct scanner version recorded successfully in 11 and 15.
07 sync: exit 2, sandbox denied uv cache access.
08 escalated frozen all-groups Python 3.13 sync: exit 0.
09 source: overall exit 0, but cat src/dex/workspace/recovery.py failed because the
implementation is src/dex/workspace.py. Correct source read in 11 and 15.
10 required CLI: exit 0.
11 source/versions: overall exit 0, but sed src/dex/adapters.py failed because adapters
is a package. Correct src/dex/adapters/__init__.py read in 15.
12 focused boot/M1-07/spec reads: exit 0.
13 independent barrier proof: exit 0.
14 actual/expected, SQLite integrity/identities and hashes: exit 0.
15 final protocol/source, exact revision, clean status/diff and versions: exit 0.
16 local event inspection: exit 0. Durable receipt contains 21 CLI and 34 independent
events, including original-attempt reconciliation.

Pre-helper commands, preserved here from tool output:
1. cat /private/tmp/dex-m1-07-audit/formal-brief.md: exit 0, full brief read.
2. cat installed swarm/SKILL.md and /Users/varunvis/.agents/skills/unslop/SKILL.md:
exit 0, both read.
3. ls /private/tmp/dex-m1-07-audit/formal/05-inflight /private/tmp/dex-m1-07-lane05:
exit 1; both paths reported No such file or directory.
4. mkdir -p /private/tmp/dex-m1-07-audit/formal/05-inflight: exit 0, no output.
The full probe and report diffs were shown before writing them. Only temporary
audit artifacts and the isolated worktree/environment were created.

## Limits

All successful behavior evidence is on the supplied head, not a different revision.
No baseline capability claim. No independently proven defect in this lane.
The evaluator-owned SandboxWorkspace bypasses normal dispatch eligibility only
for DeterministicAdapter. Normal activation remains unavailable. This proof does
not cover production authentication, live adapters, standing authority, UI, model
network enforcement, later milestones, or the full repository/performance gates.
Earlier PR #1's incomplete performance/reviewer round and PR #5's failed M1-06
15-second sample remain as recorded in the formal brief. This lane does not declare
the PR STACK-READY.


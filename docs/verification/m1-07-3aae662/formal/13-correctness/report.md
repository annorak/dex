# M1-07 lane 13 correctness audit

Verdict: PASS within this lane's correctness scope. No proof-backed new finding.

## Identity

- Head: `e7eabc89ac47e6abb870e4e4f4306dc891b53217`.
- Parent, base, frozen trunk: `80e60aac6ab78017020e5fce4c625c5fcb169ac1`.
- Stable patch ID: `98794acdc178e34957554428ff611fd4825b926d`.
- Detached worktree: `/private/tmp/dex-m1-07-lane13`.
- Output directory: `/private/tmp/dex-m1-07-audit/formal/13-correctness`.
- Python used for verification: 3.13.11. uv: 0.11.31. Repository scanner: detect-secrets 1.5.0.
- `final-identity.txt` independently records these identities and an empty working-tree status. Product sources remained unchanged.

## Method and receipts

Every listed receipt is relative to this report's directory. The recorder preserves exact argv, cwd, revision, dirty status, stdout, stderr, exit status, and elapsed time. Review covered the introduced workspace persistence, core workspace transitions and dispatch admission, generic adapter contract, codec, verification boundary, command handling, recovery evaluator and tests. Requirements were read from engine.md, M1 shared boot rules and M1-07, open-questions.md, and acceptance.md. The installed swarm and Codex mapping instructions were read. No child agents were used.

| Evidence | Command or inspected material | Predicate and result |
| --- | --- | --- |
| `setup-sync-retry.txt` | `uv sync --frozen --all-groups --python 3.13` | Exit 0; pinned environment installed. |
| `tests.txt` | `.venv/bin/pytest tests/workspace/test_recovery.py tests/core/test_effects.py tests/core/test_authority.py -q -p no:cacheprovider` | Exit 0; 77 passed. |
| `probe-run.txt` | `.venv/bin/python probe.py probe-run`, using absolute assigned output paths | Exit 0; all five deterministic checks below passed. |
| `live-complete-retry.txt` | `uv run dex eval --scenario tests/scenarios/recovery-complete.json --out .../live-complete-retry` | Exit 0; verified registration, persisted approval, stale refusal, one confirmed effect and one remote write. |
| `live-recovery-lookup-absent-inflight.txt` | Corresponding `uv run dex eval` scenario and fresh output | Exit 0; absent applied lookup, one reservation, one uncertain attempt, zero writes. |
| `live-recovery-delayed-old-revision.txt` | Corresponding `uv run dex eval` scenario and fresh output | Exit 0; replacement waited; old effect reconciled; replacement refused with `amendment_required`; one write. |
| `live-recovery-retry-bound.txt` | Corresponding `uv run dex eval` scenario and fresh output | Exit 0; three reservations, `retry_exhausted`, zero writes. |
| `live-recovery-rebuild.txt` | Corresponding `uv run dex eval` scenario and fresh output | Exit 0; fresh-process state equal; one business decision, two completed work items, one open task due 2026-01-02 UTC. |
| `live-recovery-invalid-import.txt` | Corresponding `uv run dex eval` scenario and fresh output | Exit 0; intended corruption refusals and unchanged bytes. |
| `readback.txt` | Complete/rebuild/invalid nested CLI transcripts | Register and approve exit 0 at revisions 1 and 2; stale approval exit 1 with `stale_revision`; corruption commands exit 2 with `artifact_corrupt`, `event_version`, `workspace_version`. Fresh-process rebuild exit 0. |
| `predicates-and-state.txt` | Independent JSON and SQLite inspection with exact code in argv | Exit 0; nonempty expected maps, all expected/matches checked against actual and input scenario; contiguous event rows; independent core rebuild; receipt checks below. |
| `final-identity.txt` | Git identity/status/patch ID and tool versions | Exit 0; exact frozen head/base and clean source checkout. |

Read receipts are `setup-read.txt`, `contracts.txt`, `source1.txt`, `source2.txt`, `focused-source.txt`, `transition-source.txt`, `probe-planning-source.txt`, and `readback.txt`. The complete proposed verifier-script diff is in `proposed-probe-diff.txt`; the script is `probe.py`.

## Checked contracts

SQLite append uses BEGIN IMMEDIATE, refreshes durable state, compares expected revision, decides through the core, and writes artifact and events in one transaction. In-memory state updates only after commit. The focused tests exercise deterministic conflicting reviews, crash points before/after append and around dispatch/commit/confirmation, no-reservation absence racing admission, recovery, restart retry exhaustion, and corrupt stored data. The direct registration probe raised after SQL inserts and observed zero artifacts and zero events after reopen; retry registered once and replayed identically.

Dispatch persists attempt and reservation before adapter contact, then refreshes and checks core admission under the SQLite write transaction. Core admission checks current effect and producer dependencies, preconditions, business-decision linkage, exact approval, revocation, current executor scope, reservation identity, adapter revision, and current-policy approver authority. Correcting producer evidence after reservation but before admission returned `stale_effect` with zero adapter calls and zero writes.

The custom receipt mismatch probe returned `adapter_revision`, retained the unresolved attempt, and recorded no confirmed effect. Successful live receipts were independently checked against the deterministic remote SQLite row: external ID equals the stable operation-key hash, payload equals the exact serialized effect revision, receipt evidence equals its SHA-256, and adapter versions match the reservation/remote version. This is a property of the evaluator adapter's receipt format; the generic adapter API's external IDs and evidence remain adapter-owned strings.

The absent-inflight live database contains one pending remote attempt and one unresolved local attempt. Recovery does not turn absence into permission to retry. The delayed-old-revision database confirms revision 1 while revision 2 remains current; no second write occurs and amendment remains necessary. Retry-bound has exactly three fenced remote attempts, three reservations, and one operation identity. Fencing and delayed-finish ordering are also exercised by the focused tests. Revocation before admission blocks new writes; completed delayed effects remain reconcilable after revocation.

## Precommit fixes independently verified

The reports under `audit/precommit/astra`, `sol`, and `luna` concern a frozen uncommitted snapshot, not this Git head. They are historical evidence, not current passing receipts.

1. Removed approver membership: the current company policy now reaches `authorize_dispatch`. The probe removed only the approver role while retaining executor authority. Dispatch returned exactly `effect_authority`; the patched execute method was never called, and remote writes stayed zero. The persisted attempt remains unresolved and recoverable.
2. Unauthorized reconciliation: `Workspace.reconcile` now calls canonical session authorization before adapter contact. With no current memberships, it returned exactly `session_authority`. A patched reconcile method was never called. Both local and remote database bytes were unchanged.

Both focused regression tests passed at the frozen head. Their historical snapshot Git-metadata failures do not recur in this detached Git worktree.

## Input identities

| Input | SHA-256 |
| --- | --- |
| recovery-complete.json | `3792599f24134e37e43bc3f7ebfb7874d378ddc60842c4213b6c8489be6f0095` |
| recovery-lookup-absent-inflight.json | `175c0658dd3e59b0d9b2c9162a571c538c799dd0cc558a1e1c641c0dc327e92e` |
| recovery-delayed-old-revision.json | `3fb2e006c7374415cdc5130575c24952d9a27abfe5565bbf25924bd3e5a80b55` |
| recovery-retry-bound.json | `1ab4539ba838c0cc0dc93fedceab98fed97a905d45d19f5f53766c60924fa14d` |
| recovery-rebuild.json | `b1745fa89018b736bd36844421dacdb64608b96820830fec376a0fd625d30027` |
| recovery-invalid-import.json | `a18fdb726d6bcc53933fd6f0b5919a364a5aa235936a810b6898c1275f7e29cd` |
| probe.py | `d9e79d2cbec4c8f8be13e637b7999d801a6692e72a7ad96676492ea5ba79fb0e` |

## Failed attempts and disposition

- `setup-read.txt`: exit 128 after reading instructions because sandbox permissions blocked repository Git worktree metadata. `setup-worktree-retry.txt` used approved escalation and succeeded at the assigned head.
- `contracts.txt`: exit 127 because an exploratory `gitleaks version` lookup found no gitleaks executable. The system python3 was 3.11.6. Neither was used as the verification environment. Repository scanner discovery showed detect-secrets, and `probe-planning-source.txt`/`final-identity.txt` record Python 3.13.11 and detect-secrets 1.5.0.
- `setup-sync.txt`: exit 2 because sandbox permissions blocked the uv cache. `setup-sync-retry.txt` used approved escalation and succeeded.
- `live-complete.txt`: exit 2 for the same uv cache restriction before the scenario ran. It is not a successful rejection or scenario pass. `live-complete-retry.txt` used approved escalation and a new output path; it succeeded.
- No failed tests or failed deterministic probes at this Git head.

## Limits and historical context

Effect recovery uses the evaluator-owned deterministic adapter and SandboxWorkspace eligibility override. The normal verified pure-program registration/approval boundary is independently exercised. Ordinary effect activation remains unavailable: missing verification checks reject approval/dispatch and ActivateProgram returns unsupported_activation. This audit does not claim production effect activation, standing-authority dispatch, production authentication, live integration, UI, or model-network verification.

No model calls were needed by the inspected deterministic recovery path. No performance workload, mutation/fuzz campaign, full make check, commit, push, merge, or source modification was performed. Scenario-generated timing fields were not treated as performance evidence. Trunk/parent workloads were not executed by this correctness lane, and no comparative claim is made.

Preserve the supplied historical limitations: PR #1 had incomplete performance and independent review before merge; M1-06's valid 15.030444625-second sample failed its unchanged 15-second gate despite later merge. Neither limitation is cleared by this audit.

This lane does not declare the PR STACK-READY.

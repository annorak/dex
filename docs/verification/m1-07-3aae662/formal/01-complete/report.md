# Lane 01: PASS with unsupported baseline limitation

Head: e7eabc89ac47e6abb870e4e4f4306dc891b53217
Base, trunk, and parent: 80e60aac6ab78017020e5fce4c625c5fcb169ac1
Stable patch ID: 98794acdc178e34957554428ff611fd4825b926d

Only the head live-lane predicate passes. Trunk and parent lack the recovery format and workspace command. Their refusals are limitations, not passes or valid behavioral comparisons. This lane makes no stack-readiness or performance claim.

## Inputs and setup

Frozen input: recovery-complete.json in this directory, outside all worktrees.
SHA-256: 3792599f24134e37e43bc3f7ebfb7874d378ddc60842c4213b6c8489be6f0095
All revisions received these identical bytes. The final-*.txt receipts recheck the hash and clean Git status.
Detached worktrees: /private/tmp/dex-m1-07-lane01-{trunk,parent,head}.
Each used uv sync --frozen --all-groups --python 3.13.
Versions: Python 3.13.11; uv 0.11.31; repository secret scanner detect-secrets 1.5.0.

## Commands and evidence

The exact argv, revision, timestamps, status, stdout, and stderr are in each receipt.
Canonical scenario command: env UV_CACHE_DIR=<this directory>/uv-cache UV_OFFLINE=1 OPENAI_API_KEY= ANTHROPIC_API_KEY= uv run dex eval --scenario <this directory>/recovery-complete.json --out <fresh output directory>.
The strict serial sequence is trunk-refusal-serial.txt, parent-refusal-serial.txt, principal01-recovery-serial.txt, with fresh run-trunk-02, run-parent-02, and run-head-02 outputs.
Trunk and parent each returned exit 2, scenario_error, requiring the older format fields. Neither produced a completed recovery result.
trunk-workspace-unsupported.txt and parent-workspace-unsupported.txt each returned exit 2, invalid command workspace.
Head returned exit 0. Its actual.json and expected.json show all seven requested matches true.

## Independently checked observations

Read source-read.txt, artifacts-read.txt, db-schema.txt, and serial-nested-and-activation.txt for scenario, command-boundary, persistence, and fixture source.
Normal CLI registration succeeded at revision 1 with no missing checks. Approval succeeded at revision 2. The request claimed source-impostor, while the stored RegisterProgram and ApproveProgram events name session actor operator.
independent-db-probe.txt checks the actual SQLite catalog after reopen: one artifact, one registration, no missing checks, one persisted approval, exactly the registration and approval events.
The same probe repeats the normal stale CLI approval and observes exit 1, failure stale_revision, revision 2, and byte-identical catalog data. Catalog SHA-256: 1f5b19d073f3e6c69df843c62ec41d7289e750d66c1887f3f7be500ca681394c.
The effect workspace reopens at revision 21 with one confirmed effect and zero unresolved attempts. Its remote database contains exactly one applied attempt at fixture-adapter-1. Reopen leaves effect database bytes unchanged.
The scenario itself compares pre-close and rebuilt state and reports replay_equal=true. The independent probe checks the rebuilt persistent result separately.
Effect recovery uses evaluator-owned SandboxWorkspace and DeterministicAdapter. It is separate from the normally registered pure artifact. The effect artifact has missing checks and zero program approvals. Normal dispatch retains authorize_program, so normal activation remains unavailable. This lane proves local persistence and deterministic adapter protocol behavior, not production authentication, integrations, or model-network verification.

## Preserved attempts and disposition

Initial git worktree creation failed with Operation not permitted for repository Git metadata; the tool transcript is preserved in the session. The authorized escalated retry created all three detached checkouts.
setup-trunk.txt, setup-parent.txt, and setup-head.txt each failed with uv cache access denied. The corresponding setup-*-retry.txt receipts show successful authorized installs. These failures are not passes.
metadata.txt attempted gitleaks, which is absent. The repository actually uses detect-secrets; artifacts-read.txt and final-*.txt record its installed version 1.5.0.
The first trunk and parent commands overlapped. Their trunk-refusal.txt and parent-refusal.txt receipts, principal01-recovery.txt, and run-head-01 output remain preserved. The strict serial rerun supersedes that ordering attempt.

Product sources remained unchanged in all three worktrees. No commit, push, source edit, fuzz campaign, package change, or performance measurement was performed.
Handoff success receipts: run-head-02/register.txt and run-head-02/approve.txt.
Handoff rejection receipt: run-head-02/stale-approval.txt. Independent preservation proof: independent-db-probe.txt.

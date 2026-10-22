# Lane02: interruption before durable intent

Verdict: PASS for the lane02 predicate. No stack readiness verdict.

Head: e7eabc89ac47e6abb870e4e4f4306dc891b53217
Parent, frozen base, and supplied trunk: 80e60aac6ab78017020e5fce4c625c5fcb169ac1
Stable patch ID independently computed: 98794acdc178e34957554428ff611fd4825b926d
Worktree: /private/tmp/dex-m1-07-lane02
Input: tests/scenarios/recovery-before-attempt.json
Input SHA256: 72f3109c3ea2913c1e58ab78eafa9c693c88277d8422ab2380f0d119f178268e

## Environment and principal command

uv 0.11.31, CPython 3.13.11, detect-secrets 1.5.0.
Pinned setup: uv sync --frozen --all-groups --python 3.13.
Principal command, with a temporary writable cache:
env UV_CACHE_DIR=/private/tmp/dex-m1-07-lane02/.uv-cache uv run dex eval --scenario tests/scenarios/recovery-before-attempt.json --out /private/tmp/dex-m1-07-audit/formal/02-before-attempt/run-01

The command exited 0. Receipt: principal02-before-attempt.txt.
The run directory was fresh. No baseline execution was requested or performed in this lane. All successful verification receipts identify the exact head above.

## Predicate and independent observations

Pass requires an interruption before durable intent and zero external writes. Expected JSON is not the sole evidence.

The evaluator maps recovery-before-attempt to before_append after setup and approval. Workspace.dispatch first calls _append(BeginEffectAttempt). _append invokes before_append after pure decision computation and before INSERT events. The exception therefore occurs before persisted attempt identity, ReserveDispatch, and adapter.execute. The transaction rolls back and dispatch does not continue. Receipts 18-recovery.txt and 22-dispatch-lines.txt record this ordering.

The actual output reports interrupted=true, writes_before_reopen=0, remote_writes=0, unresolved_before_reopen=0, unresolved_attempts=0, confirmed_effects=0, replay_equal=true, revision=12. Every emitted expected match is true. Actual state SHA256 is 7263026161ae913eac410aaa78e86b162450ecf67011c40c4ee503ae3d58312f.

Independent read-only SQL inspection found:
- workspace.db integrity_check=ok, one artifact, and 12 events at revisions 1 through 12.
- Events comprise registration, sandbox start/computation/proposal, and exact effect approval. Revision 10 is EffectTransitioned carrying ApproveEffect.
- Recursive inspection of stored event payloads finds no BeginEffectAttempt, ReserveDispatch, ConfirmEffect, ReconcileEffect, or MarkEffectUncertain.
- remote.db integrity_check=ok and attempts has zero rows, including zero applied rows.
- Explicit assertions over stored events, remote rows, and actual output pass.

Receipts 23-independent-db.txt and 26-independent-assertions.txt contain the SQL, full stored event rows, and independent assertions. The adapter schema and implementation are in 20-fixture.txt. The empty remote attempts table proves no adapter admission or external write in this deterministic fixture, independently of the evaluator's writes counter. Reopen and recover produce no attempt because none was durable.

## Scope and limitations

This exercises the evaluator-owned deterministic adapter and SandboxWorkspace. It is protocol evidence, not a live integration or production activation test. The stored effect-capable artifact retains missing verification checks. Ordinary activation remains unavailable. The scenario contains no AI steps or model calls; its inspected execution path uses local SQLite and deterministic computation. This lane did not measure or independently monitor model-network access, run performance tests, fuzz, or inspect later milestones.

No source files were modified. git status --porcelain was empty in 24-patch-id.txt. The final clean-state receipt is 28-final-clean.txt. No commit, push, or merge occurred.

## Every failed attempt and disposition

- 01-worktree.txt, exit 128: sandbox denied creation of repository worktree metadata. 04-worktree-retry.txt succeeded with required escalation.
- 02-context.txt and 03-design.txt, exit 127: commands attempted the not-yet-created worktree after the failed worktree setup. No read succeeded. Retried successfully in 05-context.txt, 06-plan.txt, and 07-design.txt, with focused excerpts in 17-plan-excerpts.txt and 25-policy-excerpts.txt.
- 08-sync.txt, exit 2: sandbox denied uv cache access. 16-sync-retry.txt succeeded with required escalation and installed the pinned environment.
- 14-python.txt, exit 127: metadata probe preceded successful environment creation. Correct Python metadata is in 21-env.txt.
- 15-gitleaks.txt, exit 127: gitleaks is absent. The repository's installed scanner is detect-secrets 1.5.0, independently read from installed package metadata in 21-env.txt. No scanner gate was run by this live lane.

None of these setup or metadata failures counts as the expected scenario interruption or as a passing check.

## Bootstrap provenance

Before helper use, tool-level commands read the brief, read the unslop skill, and printed cwd, all with exit 0. The tool outputs were chunk 37168c for cat /private/tmp/dex-m1-07-audit/formal-brief.md, chunk 3e363a for cat /Users/varunvis/.agents/skills/unslop/SKILL.md, and chunk 69047e for pwd. mkdir -p /private/tmp/dex-m1-07-audit/formal/02-before-attempt also exited 0, chunk b453be. These were genuine tool-level bootstrap calls, not helper receipts. There were no pre-helper failures. They do not establish a product verdict.

Every subsequent read, setup, verification, and report-write command has its own never-overwritten .txt receipt in this directory. 27-write-report.txt records report creation after its complete proposed diff was displayed. 28-final-clean.txt reads back this report and records final revision, patch ID, and clean worktree state.

# Lane 14 isolation audit

Verdict: PASS for the assigned isolation scope. No proof-backed introduced finding. This lane does not declare the stack ready.

Head: e7eabc89ac47e6abb870e4e4f4306dc891b53217
Parent: 80e60aac6ab78017020e5fce4c625c5fcb169ac1
Base and frozen trunk: 80e60aac6ab78017020e5fce4c625c5fcb169ac1
Stable patch ID: 98794acdc178e34957554428ff611fd4825b926d
Detached worktree: /private/tmp/dex-m1-07-lane14
Evidence root: /private/tmp/dex-m1-07-audit/formal/14-isolation
Python: 3.13.11. uv: 0.11.31. detect-secrets: 1.5.0.
All executed behavior evidence is on the exact head above. No baseline behavior is claimed.

## Verified predicates

- The real normal CLI registers a code-only artifact with no missing checks, records approval from local actor operator despite source-impostor metadata, and rejects replay at a stale revision. Nested register/approve/stale-approval transcripts were inspected. The approval persists at revision 2.
- Independent normal CLI probes rejected unprivileged catalog inspection, forged source actor approval, removed current roles, foreign company access, stale inspection, an injected approved flag, incomplete program approval, and an internal ReserveDispatch command. Every refusal against an existing database preserved its exact bytes. Each nested probe records argv, stdout, stderr, exit status, and before/after database hashes under probe-run/.
- A saved scenario with a wrong expected result registers as incomplete and cannot be approved. Existing focused tests additionally prove pending effect programs cannot dispatch normally and activation returns unsupported_activation.
- The local session supplies actor and company policy. Normal command metadata replaces source identity, time, and expected revision; action binding replaces actor, company, and origin. The command boundary has a fixed allowlist and supplies no adapter.
- Scoped memberships do not confer global catalog access. Workspace authorization checks current role/scope/time and company before the append. Existing focused tests prove stored actor authority cannot substitute for current policy and unauthorized reconciliation never contacts an adapter.
- Codec probes reject unknown format versions, wrong field types, duplicate fields, and extra approved fields with their exact errors. Persistence rejects artifact corruption, event version 99, and workspace version 99 with structured nonzero CLI errors while preserving damaged bytes. Artifact loading checks the payload hash, recomputed artifact identity, and verifier version.
- Reopen reconstructs projections without calling decide, execute_function, or adapter execution. The focused replay test patches these calls to fail. The fresh-process rebuild retains one pending task, due time 2026-01-02T00:00:00+00:00, one business decision, two completed work items, and identical state.
- The actual import contract passes: 42 files and 153 dependencies, one contract kept. The normal workspace command was also executed in a fresh Python process and loaded no dex.eval modules. Evaluator SandboxWorkspace is confined to dex.eval.recovery_fixture and only bypasses dispatch eligibility with DeterministicAdapter instances. The ordinary CLI cannot select this subclass or import it from encoded data.
- Complete recovery emits one remote write and one confirmed effect, with replay equality and zero unresolved attempts. This effect recovery uses the evaluator-owned deterministic adapter. It does not prove production dispatch.
- All actual values named in the three scenario expected maps were independently compared. Every emitted matches entry is true. These maps reside in expected.json, not a separate matches.json.

## Commands and receipts

Each numbered transcript contains the receipt helper's exact argv, cwd, revision, dirty status, output, status, and elapsed time unless otherwise stated below.

| Receipt | Command or purpose | Observation |
| --- | --- | --- |
| 01-worktree.txt | git worktree add --detach at exact head | Permission failure, exit 128; not a pass. |
| 03-worktree-retry.txt | Same worktree creation with approved escalation | Exit 0. |
| 04-rules-plan.txt | Read AGENTS, swarm, unslop, and M1 plan | Exit 0; required source intent read. |
| 05-sync.txt | uv sync --frozen --all-groups --python 3.13 | Restricted uv cache failure, exit 2; not a pass. |
| 06-metadata.txt | Revision, parent, diff, stable patch ID, uv version and source inventory | Assigned identities match. |
| 07-sync-retry.txt | Same uv sync with approved escalation | Exit 0. |
| 08-boundaries.txt | Read workspace command, codec, verifier, workspace, adapters and CLI | Exit 0. |
| 09-source-intent.txt | Read engine intent, relevant open questions/acceptance, boot and M1-07 plan | Exit 0. |
| 10-workspace.txt | Numbered workspace implementation | Exit 0. |
| 11-runtime-diff.txt | Full changed core runtime/events/CLI diff | Exit 0. |
| 12-evaluator-tests.txt | Read recovery tests, evaluator, configuration and adapters | Exit 0. |
| 13-focused-tests.txt | .venv/bin/python -m pytest tests/workspace/test_recovery.py tests/contracts/test_checks.py -q | 211 passed, exit 0. |
| 14-contract-check.txt | .venv/bin/lint-imports | Contract kept, exit 0. |
| 15-recovery-boundary.txt | Evaluator bypass, authority and import enforcement inspection | Exit 0. |
| 16-recovery-complete.txt | .venv/bin/dex eval --scenario tests/scenarios/recovery-complete.json --out EVIDENCE/run-recovery-complete | Exit 0; actual and nested CLI evidence inspected. |
| 17-recovery-rebuild.txt | .venv/bin/dex eval --scenario tests/scenarios/recovery-rebuild.json --out EVIDENCE/run-recovery-rebuild | Exit 0; fresh-process checkpoint equal. |
| 18-recovery-invalid-import.txt | .venv/bin/dex eval --scenario tests/scenarios/recovery-invalid-import.json --out EVIDENCE/run-recovery-invalid-import | Exit 0; exact rejection errors and byte preservation. |
| 19-details.txt | Replay/bypass/corruption implementation, Python/scanner versions and Codex skill mapping | Exit 0. |
| 20-boundary-probes.txt | .venv/bin/python EVIDENCE/probe.py | All nine normal CLI probe assertions passed, exit 0. |
| 21-emitted-evidence.txt | Read actual/expected and nested CLI transcripts | Reads also attempted absent matches.json; stderr preserved, not a pass predicate. |
| 22-final-status-hashes.txt | Source status/diff, input hashes, actual/expected files | Exit 1 solely for absent matches.json lookups. Actual expected maps were read; no source changes. |
| 23-readonly-boundary-predicates.txt | Read-only independent Python assertions for comparison maps, scope, codec, normal loaded modules | Exit 0. Corrected evidence lookup passes. |
| 24-final-source-status.txt | git status --porcelain | Empty output, exit 0. |

An initial dependent read attempted the nonexistent worktree after receipt 01 failed. The receipt helper itself failed before creating 02-rules-plan.txt with FileNotFoundError for /private/tmp/dex-m1-07-lane14. [02-wrapper-failure-reconstructed.txt](02-wrapper-failure-reconstructed.txt) durably transcribes the exact wrapper argv, intended cwd, original traceback and wrapper exit status 1 from the tool context. Revision and child status are unavailable because the child command never ran. Receipt 04 records the subsequent successful read. One other setup command lacked a separate receipt: mkdir -p /private/tmp/dex-m1-07-audit/formal/14-isolation, launched in the inherited session cwd /Users/varunvis/workspace/dev/dex/docs with no workdir argument. Its original tool result was exit 0, empty stdout/stderr, chunk_id 835bdd, wall_time_seconds 0.000006625; no revision was captured. This paragraph preserves that session-level result durably. All other executed shell commands have numbered durable receipts. No other failed test or setup attempt is omitted.

EVIDENCE in the table means the evidence root above. Scenario output directories are fresh. The temporary probe diff was shown before its write. No product file was modified, and no commits, pushes, mutation campaign, fuzz campaign, performance run, or live model call occurred.

## Input hashes

SHA-256:
- tests/scenarios/recovery-complete.json: 3792599f24134e37e43bc3f7ebfb7874d378ddc60842c4213b6c8489be6f0095
- tests/scenarios/recovery-rebuild.json: b1745fa89018b736bd36844421dacdb64608b96820830fec376a0fd625d30027
- tests/scenarios/recovery-invalid-import.json: a18fdb726d6bcc53933fd6f0b5919a364a5aa235936a810b6898c1275f7e29cd
- probe.py: c0fed9fd26f5655a1c14a197f991f662570891fcfea3598becc066355229f063

## Limits and inherited history

DEX_SESSION is trusted local configuration, not production authentication. An operator who controls that configuration can name actors and policy; M1 explicitly leaves production authentication outside scope. Local SQLite is not an adversarially signed event store. Hash checks detect corruption, not a malicious writer who can replace the database and recompute hashes.

Normal activation remains unavailable. Standing-authority dispatch, live integrations, UI and model-network verification are not implemented by this change. Normal workspace commands cannot load evaluator adapters. Complete recovery proves the protocol with a deterministic fixture adapter only.

This lane did not measure performance or rerun unsupported parent/trunk workloads. PR #1's independent review/performance incompleteness and PR #5's preserved 15.030444625-second M1-06 performance failure remain unchanged. This PASS does not clear those historical limitations.

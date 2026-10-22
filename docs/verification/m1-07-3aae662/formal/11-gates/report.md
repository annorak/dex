# M1-07 lane 11

PASS for repository gates and focused recovery tests.

Head: e7eabc89ac47e6abb870e4e4f4306dc891b53217
Parent and frozen base: 80e60aac6ab78017020e5fce4c625c5fcb169ac1
Stable patch ID: 98794acdc178e34957554428ff611fd4825b926d
Worktree: /private/tmp/dex-m1-07-lane11
All relative evidence paths below are in this report's directory.

Environment: uv 0.11.31, Python 3.13.11, detect-secrets 1.5.0, pytest 9.1.1.
Pinned setup: uv sync --frozen --all-groups --python 3.13 succeeded in 11-sync-escalated.txt.

17-make-check.txt records env UV_NO_CACHE=1 UV_OFFLINE=1 make check, exit 0.
Ruff passed. Strict Pyright reported zero errors and warnings.
Import analysis examined 42 files and 153 dependencies, with one contract kept and none broken.
Core checker and secret scanner exited 0. Full pytest passed 671 tests in 65.89 seconds.
The final dex --help completed successfully and advertised eval and workspace.

28-focused-recovery.txt separately records uv run pytest tests/workspace/test_recovery.py -q, exit 0.
The environment set UV_NO_CACHE=1, UV_OFFLINE=1 and PYTEST_ADDOPTS=--basetemp=/private/tmp/dex-m1-07-audit/formal/11-gates/focused-run.
All 33 focused tests passed in 1.75 seconds. Artifacts remain in focused-run.
29-artifact-inspection.txt records all ten emitted actual/expected comparisons and nested transcripts.
Every recorded match was true. Matches are stored inside expected.json, not a separate matches.json.
Registration and authorized approval exited 0; stale approval exited 1 with stale_revision.
Corrupt artifact, event version and workspace version each exited 2 for its intended reason.
The corruption predicates also checked unchanged database bytes.

I read Makefile, checker predicates, recovery assertions, driver and fixture source.
Coverage includes eight crash boundaries, authority checks, durable retry exhaustion, concurrent stale-revision rejection, replay without dispatch or interpretation, and corrupt-state refusal.
The driver derives observations from workspace state and SQLite adapter counts before comparing expected values.
The fixture adapter uses local SQLite, and the driver uses local subprocesses. No model transport appears in the inspected recovery path.
UV_OFFLINE disables uv downloads. This lane did not trace network traffic or exercise a live model gateway.
Recovery effects use the evaluator-owned deterministic adapter. Normal activation remains unsupported; pending verification blocks dispatch.
This is not performance verification, production authentication verification, or a full PR verdict. No baseline workload was run in this lane.

Input SHA-256 hashes are recorded in 22-lock-input-hashes.txt for Makefile, pyproject.toml, uv.lock, the recovery tests, driver and fixture.
Failed attempts remain preserved: 00-early-failures.txt records missing-worktree status and sandbox worktree creation failure; approved creation then succeeded.
10-sync.txt records sandbox cache denial; 11-sync-escalated.txt succeeded. 21-network-imports.txt includes a nonexistent gateway.py read; 23 corrected it.
26-process-inspection.txt records sandbox ps denial; 27-process-inspection-escalated.txt succeeded.
30-clean-worktree.txt has empty git status --porcelain; 31-source-diff.txt has empty git diff --exit-code, exit 0. Sources remained unchanged. No commit or push occurred.

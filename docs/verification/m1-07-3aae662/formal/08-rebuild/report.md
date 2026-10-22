# Lane 08: PASS

Head: e7eabc89ac47e6abb870e4e4f4306dc891b53217.
Parent, base, frozen trunk: 80e60aac6ab78017020e5fce4c625c5fcb169ac1.
Stable patch ID: 98794acdc178e34957554428ff611fd4825b926d.
Worktree: /private/tmp/dex-m1-07-lane08.
No evidence from another revision is used.

The principal command was `uv run dex eval --scenario tests/scenarios/recovery-rebuild.json --out /private/tmp/dex-m1-07-audit/formal/08-rebuild/run-01`.
Its exact argv and environment override are recorded in principal08-reopen.txt; exit 0.
The scenario has six expected predicates and all six emitted matches are true.
The driver builds actual state independently from request.expected; expected values are used only in the final comparison.

## Observed behavior

- SQLite contains revisions 1 through 24 with no gaps, including HumanActed at revision 19 and TaskOpened at revisions 11 and 22.
- The nested transcript run-01/fresh-process-rebuild.txt records actual Python executable, inline code, database argument, session, pinned revision, stdout, empty stderr, and exit 0.
- That code instantiates ordinary Workspace in a new interpreter with no adapters. It does not reuse the evaluator's in-memory object.
- Nested stdout retains answered review and open followup tasks, both due exactly 2026-01-02T00:00:00+00:00, one business decision, and two completed work records.
- The independent probe process also opens ordinary Workspace with no adapters. It traps r.decide, lang.execute_function, dispatch, reconcile, and recover.
- It asserts operator/reviewer decision at 2026-01-01T00:00:00+00:00, response value 7, answered review, open followup, and completed review/write values 7.
- It reconstructs all projections directly from real SQLite events and catalog, with file, socket, process, and SQLite I/O trapped during r.rebuild. Full dataclass equality and repr equality pass.
- Reopen preserves database bytes. Full state digest matches the live evaluator and nested process: ca286dd17962d6fa1ecd998724732f83893849b95a9651a442de555ecf9b7cdf.
- Source tree remains clean; git diff --exit-code and git status checks are in 09-final-identity.txt.

## Hashes and environment

Scenario SHA256: b1745fa89018b736bd36844421dacdb64608b96820830fec376a0fd625d30027.
Session SHA256: 7b25da9aeb36855ea928635e15a3d3d809b296ee0346fc1f6728bd2eb6745561.
Database SHA256: c15e38644094ac7e152f4fff87918ad6dc949f730648cafba4b0bd72a6a52415.
Ordered SQLite event rows JSON SHA256: 770b6d12c8404893c88a644d9956839f98413957b05edf735a7c0d7a93520adb.
Probe SHA256: 3d933629e18801ee07d4a89fb6dad8ec4ec7a9a370e8d815d84845978573cc60.
Python 3.13.11; uv 0.11.31; detect-secrets 1.5.0. Initial shell python3 was 3.11.6 and only ran the receipt helper.

## Receipts and failed attempts

01-inspect.txt records identity, applicable AGENTS, design/spec/plan and scenario reads. 02-sync.txt failed on sandbox access to uv cache; 03-sync-retry.txt records approved frozen installation success. 04-code.txt records source reads and versions; its compound read includes an absent src/dex/persistence.py diagnostic, with shell exit 0, and is not treated as a clean individual file read. 05-evidence.txt records emitted actual/expected/matches, nested subprocess transcript, fixture code and replay implementation. 06-independent-probe.txt failed because the verifier used HumanAction.at rather than decided_at; 07-action-type.txt identifies the correct field. 08-independent-probe-retry.txt passes after that one-line probe correction. 09-final-identity.txt records final hashes and clean status.

The initial worktree creation failed with Operation not permitted creating .git/worktrees/dex-m1-07-lane08. The approved escalated retry created the detached worktree. These first setup calls precede receipt-helper adoption; their exact tool outputs remain in the lane conversation. The first brief read and skill read also preceded receipt adoption. No failed attempt is counted as a pass.

## Limits

This lane verifies the rebuild slice only. Reopen necessarily reads SQLite; the pure replay phase performs no I/O, interpretation or dispatch. The evaluator owns the deterministic adapter; it made zero remote writes here. No runtime model call is present in this path. This is no claim about live integrations, production authentication, standing authority, ordinary activation, performance, or the whole PR. Ordinary activation remains unavailable. Source files were not edited; no fuzzing, performance campaign, commit, push, or child agent was used.

# M1-07 lane 07: PASS

Head: e7eabc89ac47e6abb870e4e4f4306dc891b53217
Parent/base/frozen trunk: 80e60aac6ab78017020e5fce4c625c5fcb169ac1
Stable patch ID: 98794acdc178e34957554428ff611fd4825b926d
Worktree: /private/tmp/dex-m1-07-lane07
Runtime: CPython 3.13.11, uv 0.11.31, detect-secrets 1.5.0.

## Observed behavior

The required live CLI scenario exited 0. actual.json reports reviews ["accepted", "stale_revision"], remote_writes 0, replay_equal true, revision 12, confirmed_effects 0, and unresolved_attempts 0. expected.json contains the separate expected values and three true matches.

Source inspection confirms Barrier(2), two independent SQLite connections, identical expected revision 8, distinct review command/action IDs, and no sleeps. Workspace._append uses BEGIN IMMEDIATE, refreshes state, checks expected revision before decision or insertion, and inserts artifacts and the whole event batch inside that transaction.

Independent SQLite inspection found contiguous event revisions 1 through 12. Only review-2 persisted, as a complete batch at 9 through 12 with ordinals 0 through 3 and BatchCompleted count 4. review-1 has no event. Rebuilt state has one exact approval action, one approved effect, one artifact, and no tasks. SQLite integrity_check returned ok. No partial artifact or event batch was observed.

An additional bounded task probe synchronized competing integer answers 7 and 8 against the same task and expected revision 13. Answer 8 was accepted; answer 7 returned stale_revision. The seven appended events all belong to answer-8, have contiguous ordinals and a matching BatchCompleted count. Exactly one RespondTask action remains, with value 8; the original task is answered and the follow-up remains open. Artifact rows are byte-for-byte unchanged. Reopen reconstructed equal state.

## Inputs and evidence

Scenario SHA256: 1c9cbf45f6da07b5b70e4a56aa3634b6773f9ce00f8d11b4887881b241953302
actual.json SHA256: 1fea6ca3236d1da1006c06cf291317a82a3293561fb5383869e0c262825301a1
expected.json SHA256: 98be078983cd8b998a93fa1e638303bc6dc729736d6d16d1bba4c1c36088939c
Task probe receipt SHA256: f8725c5fe90b8c540a622ffa77351b65f6ae392a7a96ae210d551db0c1ed347c

All receipt paths are relative to this report directory. principal07-concurrency.txt records the actual uv run dex eval command and environment. 15-evidence.txt preserves all event rows, output files, schema, integrity and reconstructed actions/tasks. 18-task-probe.txt contains the exact inline probe and assertions. 19-assertions.txt records corrected scenario assertions and hashes. 20-final-state.txt confirms head, parent, versions, empty git status, and empty git diff. Other numbered receipts preserve instruction, specification, and implementation reads.

## Failed attempts and limits

Initial brief read and existence check ran before the receipt directory existed and remain only in the tool transcript; the existence check exited 1 because the worktree and evidence directory were absent. 00-worktree.txt records sandbox denial creating Git metadata; 01-worktree-escalated.txt succeeded. 05-env.txt exited 1 because system Python was 3.11.6 and scanner executables were absent from PATH; the installed virtualenv versions were subsequently recorded. 06-sync.txt records sandbox denial accessing uv cache; 11-sync-escalated.txt succeeded. 08-store.txt records an incorrect guessed store path; 12-workspace-source.txt and 16-boundary.txt read the actual workspace.py. 15-evidence.txt ended with AttributeError for nonexistent state.approvals after printing evidence; 19-assertions.txt correctly inspected state.effects and passed.

These probes use two concurrent connections under the same local operator identity, not two authenticated production users. The required scenario races two approval commands; the extra probe covers conflicting task values. Stale refusal is a typed workspace result inside the successful evaluator, not a separate nonzero CLI invocation. No fuzzing, performance claim, live integrations, model-network verification, production authentication, or standing-authority dispatch was tested. The evaluator adapter proves protocol behavior only; normal activation remains blocked by missing program checks. uv ran offline and the exercised code contains no model call.

Product sources remained unchanged, with a clean final worktree. No commits or pushes occurred. All product execution evidence is at the exact head; no baseline capability is claimed. This lane does not declare the stack ready.

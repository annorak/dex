# Lane10: PASS

Head e7eabc89ac47e6abb870e4e4f4306dc891b53217.
Parent, base and supplied trunk 80e60aac6ab78017020e5fce4c625c5fcb169ac1.
Stable patch ID 98794acdc178e34957554428ff611fd4825b926d.
Input tests/scenarios/recovery-invalid-import.json SHA256
a18fdb726d6bcc53933fd6f0b5919a364a5aa235936a810b6898c1275f7e29cd.

Principal command was uv run dex eval --scenario
tests/scenarios/recovery-invalid-import.json --out
/private/tmp/dex-m1-07-audit/formal/10-invalid-import/run-01.
Receipt principal10-invalid-state.txt records exit 0. actual.json and expected.json
show all six expected predicates matched, with revision 12, 12 stored events,
one artifact, zero remote writes, and replay equality. Matches are embedded in
expected.json; there is no matches.json.

Inspected nested reject-artifact.txt, reject-event.txt and reject-version.txt.
Each starts the normal workspace CLI in a fresh process at this head, returns
exit 2, and reports respectively artifact_corrupt, event_version and
workspace_version. The scenario compares damaged SQLite bytes before and after.
Its invalid draft check alone would not establish the lane predicate.

Independent verification used probe.py, executed in independent-probe.txt.
Every normal CLI invocation has a separate receipt under independent/.
The clean control exits 0 at revision 12. Eight rejection cases each exit 2:

| Case | Intended error |
| --- | --- |
| artifact-content | artifact_corrupt |
| artifact-identity | artifact_identity |
| artifact-verifier-version | artifact_version |
| artifact-wire-version | format_version |
| event-wire-version | format_version |
| event-format-version | event_version |
| workspace-format-version | workspace_version |
| command-wire-version | format_version |

Each database starts as a separate copy of the populated scenario workspace.
Verifier-version alteration recomputes both content hash and artifact pin so
artifact_version is reached rather than an earlier hash or identity check.
Artifact wire-version alteration recomputes its content hash to reach decoding.
The command wire-version case reaches codec format rejection before decoding
its deliberately incomplete command body. It does not prove body validity.

independent/results.json retains every before/after byte SHA256, SQL dump
SHA256, user_version and row count. Every pair is identical. Baseline byte hash
c07df53f4e97e838d6ee89f9b8ab4cd6840a44027fcaf598f93bde56a15c214f;
baseline SQL dump hash
8c622df5f877b243daae33f08d807ae6985fea45b6aa82c2abacb5141ab565a2.
final-inspection.txt independently records SQL mutation samples and clean
git status. Probe SHA256
444ba7e79116510ac55cddd534f624a18c625fbe7d795adb6f23e123a14c5116.

Environment: Python 3.13.11, uv 0.11.31, detect-secrets 1.5.0.
sync.txt failed because the sandbox denied the default uv cache.
sync-escalated.txt records successful authorized frozen all-groups installation.
read-01.txt exited 127 because gitleaks is absent and an initial source glob
was wrong. The configured scanner is detect-secrets, confirmed in read-04.txt
and final-inspection.txt. read-05.txt preserves a missing matches.json read;
expected.json supplies those matches. These are setup/read errors, not product
rejections or passing checks.

Source files stayed unchanged. No commits, pushes, product edits, fuzz or
performance campaign. All execution evidence is at the supplied head.
The bounded corruption cases prove rejection of the implemented stored formats,
not arbitrary archive import/export or adversarial corruption recovery.
Recovery uses an evaluator-owned deterministic fixture, with no live adapter
or model invocation. Model networking was not independently packet-monitored.
Normal activation, standing-authority dispatch, production authentication,
live integrations, UI and later milestones remain unavailable.
Preserved upstream limitations remain: PR1 lacked full independent/performance
verification; PR5's 15.030444625-second sample failed its unchanged 15-second gate.
This lane does not declare the stack ready.

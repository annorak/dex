# M1-11 coverage

Product revision: 07747f2. All product, CLI, performance and independent review results below apply to that revision or have exact carry-forward evidence. The final evidence-only commit receives the separate repository gate linked below. Its exact final status is recorded in local HANDOFF.json after CI; earlier failed samples remain preserved.

| Outcome | Assigned owner | Status | Evidence |
| --- | --- | --- | --- |
| Repository gate | verifier | Final committed-head result in separate receipt; earlier 831-test gate PASS | [final gate](verifier/final/003-make-check.txt) |
| 01 build on trunk, dependency parent and head | verifier | PASS; final head rebuild and unchanged baseline refusals | verifier/round3/01-world1.txt |
| 02 deterministic repeated seed 7 | verifier | PASS | verifier/round2/02-repeat.txt |
| 03 both public bundle checks, evaluator unread | verifier | PASS | verifier/round2/03-admission.txt |
| 04 exact packet bytes | verifier | PASS | verifier/round2/04-packets.txt |
| 05 history and split membership | verifier | PASS | verifier/round2/05-membership.txt |
| 06 exact mistake sets | verifier | PASS | verifier/round2/06-mistakes.txt |
| 07 duplicates, void-only, cancellations, snow | verifier | PASS | verifier/round2/07-paths.txt |
| 08 stream opening and later dates | verifier | PASS | verifier/round2/08-stream.txt |
| 09 independent frozen keys | verifier | PASS | verifier/round2/09-key.txt |
| 10 seed 11 deterministic variation | verifier | PASS | verifier/round2/10-seed.txt |
| Performance | verifier | PASS at 07747f2; earlier failure retained | [final results](verifier/round3/report.md) |
| Correctness review | correctness | PASS at 07747f2; original FAIL retained | correctness/round3-validation.md |
| Isolation review | isolation | PASS at 07747f2, original plus bounded deltas | isolation/round3-validation/report.md |

Supplemental refusal receipts must identify the intended violation, nonzero exit, and unchanged existing state. Setup failures remain failures. Every command keeps its own exact receipt; raw evidence is not rewritten for scanning.

[Carry-forward proof](verifier/round3/006-carry-forward-proof.txt) identifies exactly two changed product/test files and 313 unchanged files. Final seed-7 and seed-11 builds match the prior worlds byte for byte; public checks and saved learning projections were rerun. The final evidence commit must have an empty product diff from 07747f2.

# M1-11 first fix-forward validation

Verdict: PASS for the focused correctness delta.

Validated head: 7377a3e02c9aed2706314dcb05f2e263e3fc5319.
Previous reviewed head: 3ba4b840c192f54f5e1d167b68e7383ef4f69dd8.
Milestone base: 10154578ecaab14d68e1de42fc00c931978b3acd.
Checkout: /private/tmp/dex-m1-11-20261027.

Read the complete seven-file delta: demo/build.py, demo/world_1.py, eval/world_1.py, eval/world_1_schedule.py, eval/world_1_checks.py, tests/demo/test_world_1.py, and tests/contracts/test_checks.py. Reviewed the five original corrective conditions and risks introduced by shared chronology, added native identity fields, and final-day export handling.

Independent recorded probe: /private/tmp/dex-m1-11-correctness/fix1-validation.txt. It records exact argv, head, working-tree status, stdout, stderr and exit status. Exit status 0; both companies passed. The probe constructs seed-7 cases, expectations, schedules and native exports in memory. It does not run a reference, candidate, full build, full suite or performance measurement.

| Finding | Result | Evidence |
| --- | --- | --- |
| C1, void-only identity collision | Closed | Historical OPEN-003 remains unchanged; stream and shadow use distinct void OPEN-005. Checked every void-only key against prior postings, including history, with company-local C1 qualification and company-wide C2 qualification. Four C1 and three C2 cases passed. Shadow does not execute writes. |
| C2, response before request | Closed | Checked each delivered stream business response against its role's confirmed request, observation, due time and later schedule. 1,808 C1 and 1,806 C2 business responses passed. |
| C3, contradictory posting chronology | Closed | Public posted_at now derives from raw fixture chronology, with authorization before occurrence, occurrence before confirmation, and confirmation before request. All 1,798 C1 and 1,799 C2 stream postings passed, including final-day records. |
| C4, unsupported vendor insurance | Closed | V11 resolutions deliver attributed certificate data naming the vendor, coverage interval and availability. Receipt-time missing insurance remains recorded; evidence arrives before eligibility. Two C1 and one C2 unknown-vendor cases passed. |
| C5, incomplete approval context | Closed | Every stream request includes work, contractual due date and payment holds, separately from the task response deadline. Held opening requests retain their holds. |

The added native history identity columns preserve a reconstructable historical posted context without requiring cumulative daily exports. Final-day exports retain S1800 for both companies, and all scheduled operation events remain within the March 31 cutoff. Shared raw occurrence data does not execute reference decisions or import evaluator answers into public source construction.

No new blocker was found in this bounded delta review. The strengthened owner checks exercise causal ordering; the independent probe checks the same contracts without calling those check functions. Full repository gates, CLI lanes, isolation and performance remain separate reviewer responsibilities.

The original round-1 FAIL remains valid at 3ba4b84. This PASS applies only to the fix delta and the five corrected conditions at 7377a3e. M1-10's owner-merged 21.67% startup regression against its 20% limit remains an unreverified historical failure.

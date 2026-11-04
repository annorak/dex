# M1-13 specification to assertion checklist

This is the single working checklist. Current evidence is provisional until independently repeated at the committed head. The first integration path preceded this written checklist; that sequencing shortfall is recorded rather than backdated.

| Requirement | Exact assertion or gate | State |
| --- | --- | --- |
| Fresh origin/master worktree contains merged M1-12 | GitHub PR 11, fetched ancestry, isolated branch; checkpoint base | Verified at setup |
| Preserve original checkout and historical failures | original tracked state unchanged; failed owner/verifier receipts retained | Ongoing |
| Separate evaluator admission | admission.load_evaluator; real bundle/collection refusal driver; public eval-denied audit | Pending final |
| Freeze keys before execution | test_key_tamper_records_real_integrity_failure_without_execution; 05-key | Focused passed |
| Full canonical decisions/effects/waits | test_effect_field_is_compared_in_full; incomplete outcome parameterization; 03-effect | Focused passed |
| Separate history, reference, unresolved, copied errors | first four scoring tests; 01-score through 04-unresolved | Focused passed |
| Missing required results remain in denominator | test_missing_case_stays_in_denominator; test_expected_wait_and_missing_required_result | Focused passed |
| Exact case sets and field differences | live.py literal readback assertions; deliberate field controls | Pending final |
| Historical arrival context never uses predictions | test_arrival_inputs_ignore_candidate_predictions_and_later_observations; 06-context | Focused passed |
| Never execute to construct expected answers | expected-free executor signature; independent literal key tests; correctness review | Pending review |
| Report all artifact identities | freeze engine/evaluator/program/source/key/history/execution/cohort/cutoff maps; 10-report | Pending final |
| Zero cases and explicit distributions | test_week_version_counts_and_zero_denominators; 07-ledger | Focused passed |
| Calls, network, retries, compile, runtime distinct | test_invalid_ledger_rejected; provenance assertions; 07-ledger | Focused passed |
| Distinct combined human action counted once | test_distinct_action_origin_identity_and_combined_review; exact ledger rows | Focused passed |
| Business/review/input/exact-change/admin categories visible | ledger category and tag assertions; correctness engine integration probes | Pending final |
| Monday event week/version intersections | test_week_version_counts_and_zero_denominators; 08-buckets | Focused passed |
| Started/completed/pending cohorts separate | test_failed_evaluations_keep_all_cases_reportable; test_cutoff_preserves_not_started_case | Focused passed |
| Shared activity separate and no unnamed amortization | shared buckets, phases, amortization null; 07/08 | Pending final |
| Every acceptance requirement evidenced or unimplemented | exact acceptance source-line coverage; 09-coverage | Pending final |
| Absent history does not fabricate replay/exam result | test_absent_history_stays_unimplemented; 09-coverage | Focused passed |
| Measured costs include workload/exclusions | external measurement binding test; formal supplement reported by dex report | Pending formal |
| Read-only stable fresh-process reports | test_report_fresh_process_cannot_execute_or_write; 10-report; isolation guard | Focused passed |
| Explicit missing-reference refusal | real generated bundle and collection commands; no placeholder implementations | Early refusal passed |
| Reusable engine/dependency content freeze | engine identity mutation parameterization; independent dependency probes | Pending review |
| Evidence/reference additions do not redefine engine | test_engine_identity_separates_evaluator_reference_and_evidence | Focused passed |
| Exam/evaluator/future/company projection exclusion | real projection test; existing 154 regression tests; independent isolation probes | Focused passed |
| Receipt/occurrence/observation/availability/effective/business times preserved | ledger chronology fields; business-date rule test; projection regressions | Focused passed |
| Responses name exact request and require delivery | model request registry checks; continuation regressions and isolation review | Pending review |
| Source data cannot confer authority or completion | no engine semantics changed; effect/continuation regressions; import contracts | Pending final gate |
| Verification/program/owner/exact-change authority distinct | unchanged core/workspace blobs; relevant existing tests; full gate | Pending final gate |
| Recovery/trust/grants/revocation/sampling/actors/revisions preserved | unchanged engine implementation; full repository gate | Pending final gate |
| Replay performs no I/O/interpretation/dispatch | unchanged core replay; guarded report and existing replay regressions | Pending final gate |
| Validate before mutation and no partial collection publication | refusal snapshots; concurrent publication barrier test; missing artifact tests | Pending final |
| Demo packet/generator/generated bytes unchanged | independent seed7 applicability proof across verified product, merge and current source | Preflight passed |
| Exact focused command | uv run pytest tests/eval/test_scoring.py tests/eval/test_report.py -q | 64 passed, owner019 |
| Relevant regressions and final repository gate | 154 selected regression tests; committed-head make check | Regression passed; final pending |
| Ten real CLI lanes and fourteen separate outcomes | verifier repository + lanes01-10 + performance; correctness; isolation | Pending |
| Negative controls identify diagnostic and unchanged state | refusals.py; before/after hashes; no crash credited | Pending final |
| Formal 10k/100k thresholds and supported regressions | frozen performance.py schedule; five samples; alternating pairs; cold trunk first | Pending |
| All failures retained, no rerun for a pass | immutable receipts and sample list; host-contention records | Ongoing |
| One PR, no M1-14, no merge/auto-merge | PR title/base/scope, final GitHub readback | Pending |
| Pre-push gate and merge-safety protocol | committed-head make check each push; cancellation/readback on existing PR | Pending |
| Green CI, exact head/base/patch IDs and comment triage | final HANDOFF.json after committed-head gates and CI | Pending |
| Owner reviews transcripts before landing | handoff at STACK-READY only; never merge | Pending |

# M1-13 specification to assertion checklist

This is the single working checklist. The corrected product head is b40c6be. REPORT.md and the independent reports distinguish direct checks from evidence carried through exact unchanged blobs. Final committed-head checks and GitHub state are recorded separately in the durable HANDOFF.json. The first integration path preceded this written checklist; that sequencing shortfall is recorded rather than backdated.

| Requirement | Exact assertion or gate | State |
| --- | --- | --- |
| Fresh origin/master worktree contains merged M1-12 | GitHub PR 11, fetched ancestry, isolated branch; checkpoint base | Verified at setup |
| Preserve original checkout and historical failures | original tracked state unchanged; failed owner/verifier receipts retained | Preserved; original tracked checkout unchanged |
| Separate evaluator admission | admission.load_evaluator; real bundle/collection refusal driver; public eval-denied audit | PASS; current-head refusal driver, ten preserved malformed inputs, collection snapshot and publication barrier |
| Freeze keys before execution | test_key_tamper_records_real_integrity_failure_without_execution; 05-key | PASS; 78 focused tests at b40c6be and applicable independent lane/review |
| Full canonical decisions/effects/waits | test_effect_field_is_compared_in_full; incomplete outcome parameterization; 03-effect | PASS; 78 focused tests at b40c6be and applicable independent lane/review |
| Separate history, reference, unresolved, copied errors | first four scoring tests; 01-score through 04-unresolved | PASS; 78 focused tests at b40c6be and applicable independent lane/review |
| Missing required results remain in denominator | test_missing_case_stays_in_denominator; test_expected_wait_and_missing_required_result | PASS; 78 focused tests at b40c6be and applicable independent lane/review |
| Exact case sets and field differences | live.py literal readback assertions; deliberate field controls | PASS; independent live readback, reviews and b40c6be repository gate |
| Historical arrival context never uses predictions | test_arrival_inputs_ignore_candidate_predictions_and_later_observations; 06-context | PASS; 78 focused tests at b40c6be and applicable independent lane/review |
| Never execute to construct expected answers | expected-free executor signature; independent literal key tests; correctness review | PASS; independent live readback, reviews and b40c6be repository gate |
| Report all artifact identities | freeze engine/evaluator/program/source/key/history/execution/cohort/cutoff maps; 10-report | PASS; independent live readback, reviews and b40c6be repository gate |
| Zero cases and explicit distributions | test_week_version_counts_and_zero_denominators; 07-ledger | PASS; 78 focused tests at b40c6be and applicable independent lane/review |
| Calls, network, retries, compile, runtime distinct | test_invalid_ledger_rejected; provenance assertions; 07-ledger | PASS; 78 focused tests at b40c6be and applicable independent lane/review |
| Distinct combined human action counted once | test_distinct_action_origin_identity_and_combined_review; exact ledger rows | PASS; 78 focused tests at b40c6be and applicable independent lane/review |
| Business/review/input/exact-change/admin categories visible | ledger category and tag assertions; correctness engine integration probes | PASS; independent live readback, reviews and b40c6be repository gate |
| Monday event week/version intersections | test_week_version_counts_and_zero_denominators; 08-buckets | PASS; 78 focused tests at b40c6be and applicable independent lane/review |
| Started/completed/pending cohorts separate | test_failed_evaluations_keep_all_cases_reportable; test_cutoff_preserves_not_started_case | PASS; 78 focused tests at b40c6be and applicable independent lane/review |
| Shared activity separate and no unnamed amortization | shared buckets, phases, amortization null; 07/08 | PASS; independent live readback, reviews and b40c6be repository gate |
| Every acceptance requirement evidenced or unimplemented | exact acceptance source-line coverage; 09-coverage | PASS; independent live readback, reviews and b40c6be repository gate |
| Absent history does not fabricate replay/exam result | test_absent_history_stays_unimplemented; 09-coverage | PASS; 78 focused tests at b40c6be and applicable independent lane/review |
| Measured costs include workload/exclusions | external measurement binding test; formal supplement reported by dex report | PASS; 56 formal samples, exact readback and published report; verifier/round2/019 and 023 |
| Read-only stable fresh-process reports | test_report_fresh_process_cannot_execute_or_write; 10-report; isolation guard | PASS; 78 focused tests at b40c6be and applicable independent lane/review |
| Explicit missing-reference refusal | real generated bundle and collection commands; no placeholder implementations | PASS; real bundle and full collection refusal; no reference installed |
| Reusable engine/dependency content freeze | engine identity mutation parameterization; independent dependency probes | PASS; independent live readback, reviews and b40c6be repository gate |
| Evidence/reference additions do not redefine engine | test_engine_identity_separates_evaluator_reference_and_evidence | PASS; 78 focused tests at b40c6be and applicable independent lane/review |
| Exam/evaluator/future/company projection exclusion | real projection test; existing 154 regression tests; independent isolation probes | PASS; 78 focused tests at b40c6be and applicable independent lane/review |
| Receipt/occurrence/observation/availability/effective/business times preserved | ledger chronology fields; business-date rule test; projection regressions | PASS; 78 focused tests at b40c6be and applicable independent lane/review |
| Responses name exact request and require delivery | model request registry checks; continuation regressions and isolation review | PASS; independent live readback, reviews and b40c6be repository gate |
| Source data cannot confer authority or completion | no engine semantics changed; effect/continuation regressions; import contracts | PASS; independent live readback, reviews and b40c6be repository gate |
| Verification/program/owner/exact-change authority distinct | unchanged core/workspace blobs; relevant existing tests; full gate | PASS; independent live readback, reviews and b40c6be repository gate |
| Recovery/trust/grants/revocation/sampling/actors/revisions preserved | unchanged engine implementation; full repository gate | PASS; independent live readback, reviews and b40c6be repository gate |
| Replay performs no I/O/interpretation/dispatch | unchanged core replay; guarded report and existing replay regressions | PASS; independent live readback, reviews and b40c6be repository gate |
| Validate before mutation and no partial collection publication | refusal snapshots; concurrent publication barrier test; missing artifact tests | PASS; current-head refusal driver, ten preserved malformed inputs, collection snapshot and publication barrier |
| Demo packet/generator/generated bytes unchanged | independent seed7 applicability proof across verified product, merge and current source | Preflight passed |
| Exact focused command | uv run pytest tests/eval/test_scoring.py tests/eval/test_report.py -q | PASS, 78 tests at b40c6be; verifier/round2/005-focused.txt |
| Relevant regressions and final repository gate | 154 selected regression tests; committed-head make check | PASS, 154 regressions; 956-test b40c6be gate; final head in HANDOFF.json |
| Ten real CLI lanes and fourteen separate outcomes | verifier repository + lanes01-10 + performance; correctness; isolation | PASS; all fourteen outcomes in REPORT.md; exact unchanged-code carry proof retained |
| Negative controls identify diagnostic and unchanged state | refusals.py; before/after hashes; no crash credited | PASS; current-head refusal driver, ten preserved malformed inputs, collection snapshot and publication barrier |
| Formal 10k/100k thresholds and supported regressions | frozen performance.py schedule; five samples; alternating pairs; cold trunk first | PASS; 56 formal samples, exact readback and published report; verifier/round2/019 and 023 |
| All failures retained, no rerun for a pass | immutable receipts and sample list; host-contention records | Preserved; no thresholds weakened or failed samples discarded |
| One PR, no M1-14, no merge/auto-merge | PR title/base/scope, final GitHub readback | PR 12 against master; final GitHub state in HANDOFF.json |
| Pre-push gate and merge-safety protocol | committed-head make check each push; cancellation/readback on existing PR | Product gate and push PASS; final push protocol in HANDOFF.json |
| Green CI, exact head/base/patch IDs and comment triage | final HANDOFF.json after committed-head gates and CI | Product CI PASS; final evidence-head status in HANDOFF.json |
| Owner reviews transcripts before landing | handoff at STACK-READY only; never merge | Required before landing; agent never merges |

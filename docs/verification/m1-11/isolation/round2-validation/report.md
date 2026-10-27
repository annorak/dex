# M1-11 isolation delta validation

Verdict: PASS for the first-fix isolation delta.

Head: 7377a3e02c9aed2706314dcb05f2e263e3fc5319.
Previously reviewed head: 3ba4b840c192f54f5e1d167b68e7383ef4f69dd8.
Original base: 10154578ecaab14d68e1de42fc00c931978b3acd.
Checkout: /private/tmp/dex-m1-11-20261027.

## Applicability

Reviewed the complete seven-file diff from the previous head. Changes cover native chronology, historical identity columns, a separate unused void opening identity, final-day posting exports, evaluator causality/certificate/request context checks and tests. No product files were edited by this reviewer.

The core, importer, projection, MIME/cache, workspace command admission, CLI, fixture bridge, import contracts and scanner are byte-for-byte unchanged from the previously reviewed head. The original report and completed receipts 001 through 005 therefore continue to support their unchanged guarantees. They are preserved rather than rerun.

Full business correctness, repository checks, ten CLI lanes and performance are owned by the other reviewers. This PASS does not replace those verdicts or assert whole-M1-11 acceptance.

## Focused proof

Receipt /private/tmp/dex-m1-11-isolation/007-first-fix-delta-corrected.txt records the exact clean head, argv, probe source, output and exit 0 using the required recorder and UV_CACHE_DIR. The probe admits small real company bundles through the existing admission path. Each includes H0001, the H2700/H2701 cohort boundary, S0001 and S1800.

Both companies pass:

- The public historical community, vendor and invoice-number columns survive permitted row projection with normal source and record provenance.
- The reconciled mixed export retains learning record:2 and excludes exam record:3. H2701 remains excluded even at the final stream cutoff.
- Final-postings is an export from the company-local AP source system, available at 2027-03-31T23:59:59-04:00. It contains the final stream case in original native bytes, is absent from the earlier learning view, and retains export provenance when its cutoff arrives.
- Native daily and final exports remain unresolved pending mapping confirmation. The change does not silently manufacture normalized facts.
- Public case facts remain empty. values_reviewed_at and the chronology dictionary remain in the evaluator fixture specification, not the public manifest or source bytes. Public posting occurrence timestamps are permitted AP observations.
- The reserved evaluator import remains confined to demo.fixtures. The common chronology helper imports no evaluator and supplies occurrence facts before key construction. It is not an answer-key loader or reference executor.

Receipt 006-first-fix-delta.txt is an honest failed probe. It incorrectly required normalized records in final-postings, which deliberately has no confirmed mapping. Receipt 007 changes only that assertion to require unresolved status and preserved provenance. The failure did not identify a product defect and is not counted as a passing receipt.

No new severity/file:line isolation finding. No broad suites, repeated full projections, fuzzing, formal timing or extra agents were used. The full original projections remain the evidence for unchanged self-contained citations, saved views and consumer serialization.

M1-10's historical 21.67% startup regression against the 20% limit remains a failure. No historical reverification or relabeling occurred.

Review commands are complete. No owner-worktree process remains active from this reviewer.

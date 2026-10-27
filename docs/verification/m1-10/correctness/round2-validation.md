# M1-10 correctness validation, second fix

PASS at head ecd4b9a against milestone base c7c1976. The focused delta starts at b9d6794. Exact full revisions are recorded in the command receipts.

The saved nested-alias input that failed the first fix now passes through the real projection CLI. Both raw aliases are absent, the parent email contains only headers and its permitted body, and the permitted CSV row remains. Receipt 11-round2-reproduction.txt records the command, revision, output and readback assertions.

Receipt 12-round2-depth-order.txt records eight passing checks: attachment alias depths zero, one and two in both source orders, plus whole-row and cell-only observation scope. The depth-two fixture tests another email wrapper and its raw text alias. These tests assert source absence and exact retained sections, so MIME encoding cannot hide a surviving raw alias from the assertion.

Reviewed the complete two-file delta. Every iteration fully propagates the current ambiguous restrictions before discovering newly affected original hashes. Each original hash is processed once, bounding termination. Exact selector restrictions remain separate from ambiguity, and processing the primary hash once avoids feeding ambiguity back into its known permitted rows. The newly affected parent hashes now propagate to their different-extractor aliases. No remaining concrete correctness finding was found in this bounded review.

Both initial findings are closed at this head. P2's original confirmed-cell reproduction passed at b9d6794, and its focused row/cell tests pass again here. The earlier recording-lineage validation remains applicable because this delta changes only restriction propagation and its regression tests.

The initial report and first focused FAIL report remain unchanged. Receipts 11 and 12 append evidence; no earlier receipt was rewritten. No product files were changed by this reviewer. No full suite, performance measurement, broad review or historical verification was repeated. Repository gates, isolation, live lanes and performance remain their assigned verifiers' responsibility.

CPU-heavy correctness work is finished.

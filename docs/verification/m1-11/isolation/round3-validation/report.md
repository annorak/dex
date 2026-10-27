# M1-11 final isolation delta validation

Verdict: PASS for the extraction-validation fix.

Head: 07747f22416ebf6673aeb577c5014c391eba9042.
Previous head: 7377a3e02c9aed2706314dcb05f2e263e3fc5319.
Checkout: /private/tmp/dex-m1-11-20261027.

Reviewed the complete two-file diff in src/dex/bundle/evidence.py and tests/bundle/test_admission.py. No product edits, extra agents, broad suite or formal timing were performed.

## Integrity and boundaries

No new severity/file:line finding.

At evidence.py:56, the original read and SHA-256 check still precede equality. The expected bytes come from the freshly derived admitted Source through extraction_bytes, not from a saved cache or evaluator. Canonical serialization cannot introduce duplicate JSON keys or nonfinite values.

At evidence.py:58, byte equality proves the saved file is the exact derived extraction and skips only redundant parsing. Unequal bytes still use the existing strict parse_json semantic comparison, retaining accepted JSON reordering and whitespace behavior and rejecting duplicate fields.

At evidence.py:62, section uniqueness and span bounds still execute after either branch. The code returns the actual saved bytes, preserving admission and later deterministic writer behavior. Source-specific pins, record values, extractor versions and unresolved state remain part of the compared extraction. No global cache, source resolver, evaluator capability or live-network path was added.

The generator, raw chronology, reserved evaluator bridge, key construction, core, actor/revision/authority/recovery/trust paths, learning projection, MIME/PDF cache and scanner are unchanged by this two-file delta. Earlier isolation reports and receipts remain applicable to those unchanged paths.

## Receipts

Exact raw receipts are under /private/tmp/dex-m1-11-isolation. Both use the required recorder and UV_CACHE_DIR=/private/tmp/dex-m1-10-verifier-cache and record this clean pinned head.

- 008-snapshot-fastpath.txt: PASS, exit 0. Independent direct probe proves byte-equal snapshots never invoke parse_json after their hash check; reordered Unicode JSON is accepted unchanged. Wrong hashes, duplicate JSON fields, altered quotes, malformed JSON and another source pin are refused. Duplicate section names, negative starts and overflowing ends fail on both the canonical fast path and parsed fallback. Evaluator/unsafe/non-extraction paths fail before read.
- 009-snapshot-admission-tests.txt: PASS, exit 0. Five focused integration tests exercise reordered/duplicate/hash contracts, quote rewriting and public admission with instrumented unreadable evaluator data.

This is an isolation verdict, not the final correctness, CI or performance gate. The preserved 7377a3e performance sample 4 failed at 45.042089291 seconds against 45 seconds. No passing performance claim is made for the new head here. M1-10's historical 21.67% startup regression against 20% also remains a failure.

All review processes are finished. CPU-idle for the serial performance run.

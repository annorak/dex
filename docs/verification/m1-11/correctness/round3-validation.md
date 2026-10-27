# M1-11 second and final fix-forward validation

Verdict: PASS for the focused correctness delta.

Head: 07747f22416ebf6673aeb577c5014c391eba9042.
Previous head: 7377a3e02c9aed2706314dcb05f2e263e3fc5319.
Milestone base: 10154578ecaab14d68e1de42fc00c931978b3acd.

Read the complete two-file delta in src/dex/bundle/evidence.py and tests/bundle/test_admission.py. The change compares supplied extraction bytes with freshly generated canonical expected bytes before falling back to the existing semantic JSON comparison.

The shortcut preserves validation. Paths, descriptors and content hashes are checked before byte comparison. Equal bytes are the output of the canonical serializer, so they cannot introduce duplicate JSON fields, malformed syntax or non-finite numbers. Differently encoded bytes still undergo the original strict parser and semantic comparison. Extraction-section validation remains after both branches and is not skipped.

Independent receipt: /private/tmp/dex-m1-11-correctness/fix2-validation.txt. It contains exact argv, revision, working-tree status, stdout, stderr and exit status. Exit 0, nine focused cases passed:

- Canonical extraction accepted.
- Reordered, indented, ASCII-escaped equivalent extraction accepted.
- Incorrect hash rejected even for exact canonical bytes.
- Duplicate field rejected even when its repeated value is identical.
- Malformed JSON rejected.
- Changed extracted text rejected with a correctly updated content hash.
- Duplicate section names rejected even for exact expected bytes.
- Out-of-range sections rejected even for exact expected bytes.
- Canonical unresolved extraction accepted.

No production files were changed and no full suite, bundle generation or formal performance work was duplicated. The reviewer reported CPU-idle after the probe. No new correctness blocker was found.

The round-1 FAIL at 3ba4b84 and first fix-forward PASS at 7377a3e remain separate historical verdicts. This PASS applies to the exact two-file delta ending at 07747f2. The reported 45.042089291-second sample at 7377a3e exceeded its 45-second budget and remains a failure. This correctness receipt makes no speed claim or performance waiver. M1-10's owner-merged 21.67% startup regression also remains unchanged.

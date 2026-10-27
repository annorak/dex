# M1-11 isolation review, round 1

Verdict: PASS for isolation at the pinned head. This is not an overall M1-11 acceptance verdict.

Head: 3ba4b840c192f54f5e1d167b68e7383ef4f69dd8.
Base: 10154578ecaab14d68e1de42fc00c931978b3acd.
Checkout: /private/tmp/dex-m1-11-20261027.
Outputs: /private/tmp/dex-m1-11-isolation.

## Scope

Read AGENTS.md, the M1 shared and M1-11 plan, engine intent, acceptance, World 1 specification, bundle contract, open questions and specification-checklist.json. Ignored design documents came from /Users/varunvis/workspace/dev/dex.

Inspected the changed-file inventory and the generator, native serializers, fixture bridge, evaluator artifact construction and schedule, scenario dispatch, CLI routing, MIME/PDF changes and focused tests. Traced existing public admission, extraction provenance, learning projection, serialized consumer inputs, workspace commands and bundle execution. Business-key correctness and full repository, ten CLI and performance gates belong to their separate reviewers.

No product edits, extra agents, broad suite, fuzzing or timing gate were run. The deslop, comment and code-quality lenses found no additional actionable isolation defect. New demo/evaluator Python contains no comment tokens or suppression comments. The review did not introduce abstractions or request unrelated cleanup.

## Findings

No additional severity/file:line finding in the assigned isolation scope.

- src/dex/demo/fixtures.py:6 is the only demo-to-evaluator import. Its writes stay under eval/. build.py:791 uses the existing bundle writer before constructing those reserved artifacts.
- Ordinary consumers do not import demo/evaluator modules; CLI routes only explicit commands. Core, workspace, workspace command admission, bundle run, projection, import contracts and secret-scanner files are unchanged from base.
- reader.py:64 skips eval/ before traversal. Generated public manifests contain company evidence, not evaluator descriptors. Guarded actual admission and projection performed no evaluator reads.
- build.py:325 leaves native arrival facts empty. Original email/PDF evidence remains the input; historical actions remain separately mapped observations.
- build.py:429 assigns mixed reconciled rows to their cases. Existing projection removes the exam row while preserving the learning row, original locator, source identity and exact original/projected citation spans.
- Source metadata and imported observations never become authenticated workspace commands. Existing actor, expected-revision, artifact approval, recovery and trust admission remain unchanged. No reference selector or key loader was added to ordinary run.
- build.py:756 validates world, seed, destination, parent and packets before staging. Both companies are staged before destination reservation/publication. Focused refusal and synchronized race tests passed.
- formats.py:76 caches one immutable tuple by exact PDF bytes. Source pins are built separately from source/revision/hash, preventing cached text from borrowing provenance. compat32 is used consistently in extraction and attachment validation; focused comparison preserved the prior native MIME results.

## Exact receipts

All commands use the required round3 record.py wrapper and UV_CACHE_DIR=/private/tmp/dex-m1-10-verifier-cache. Receipts preserve exact argv, code, cwd, revision, initial worktree status, stdout, stderr and exit status.

| Receipt in /private/tmp/dex-m1-11-isolation | Result |
| --- | --- |
| 001-network-blocked-build.txt | PASS. Full seed-7 two-company build with socket connect and create_connection blocked. |
| 002-boundary-projection.txt | PASS. Both public bundles admitted with os.open, builtin open and io.open guarded against eval. Exact H0001..H2700 learning membership; no exam, future notice, evaluator label, other-company prefix or bundle path. Mixed reconciled export retains record:2 and excludes record:3. Citation spans independently compared with admitted originals. Saved views reopened with original bundle access blocked. Five consumer destinations reject exam and cross-company references; library rejects local evidence. |
| 003-mime-cache-provenance.txt | PASS. Twelve native MIME cases match default-policy extraction; attachment byte substitution fails; cache holds one immutable entry; identical bytes keep different source pins; invalid PDF remains unresolved. |
| 004-publication-refusal.txt | PASS. Ten targeted tests cover synchronized destination conflict, second-company failure, missing packet, unsupported world/seed and existing directory/file/symlink preservation. |
| 005-static-snapshot-boundaries.txt | PASS. Protected implementations/scanner unchanged; restricted import edges checked; no added comment tokens. All 182 daily sources per company have local record keys and posted/void timestamps earlier than the snapshot; future notices retain delivery times. |

The snapshot probe proves availability isolation, not agreement between AP occurrence timestamps and evaluator confirmations. The separate correctness report identifies that chronology gap and four other findings. Its FAIL verdict is not overridden here.

The head was clean when the recorded probes began. Owner edits made after this review started are outside this original verdict and require a separately pinned delta review.

M1-10's historical startup regression of 21.67% against the 20% limit remains a failure. This review did not rerun or relabel it.

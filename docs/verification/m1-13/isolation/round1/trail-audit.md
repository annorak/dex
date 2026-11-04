# M1-13 owner-trail follow-up audit

**PASS** for the exact eight-entry canonical trail proposed in `proposals/20-canonical-trail.patch`. This closes the pending trail-format follow-up in [the round-one isolation report](report.md).

| Artifact | SHA-256 |
| --- | --- |
| `trail.tsv` | `aa09ebd4df87f34a18b5fbe02da644c6cf823a5e7beb5ef5d8171a0e478f3d28` |
| `proposals/20-canonical-trail.patch` | `c0afaf394046c87576647c3dcd50a427aa26f4a7ce9d28d963bbd31d741b8dbc` |
| Preserved committed `decisions.tsv` | `8ca9a1bfdaafa0678aa6671d3ea8b249016f9726658f88c3a15f276934d47f50` |

[Audit receipt 010](010-owner-trail-audit.txt) records exact commands, input hashes, revision, status and results. The owner checkout was clean at `4ea572c8486ef29ebe7dac824bdeb674490a04aa`, with base `e990a3387fa2b1c8bce9e369e10c99db7079f89b`.

All entries have the required six fields and timezone-bearing logging timestamps. Earlier decisions are explicitly retrospective. The applied file exactly matches the proposal, every evidence pointer resolves, every referenced receipt finished before its entry was logged, and the original committed summary is byte-for-byte unchanged. The complete product proposal also exactly matches the base-to-head committed diff.

The cited receipts support the stated pins, named reference refusals, 64 precommit focused-test passes, input-reuse proof, independent isolation result, failed repository gate and pending evaluator-admission corrections. The correctness receipt separately retains a probe serialization error; the trail does not present it as a product finding. No unsupported pass claim or blocking trail flag was found in this delta.

The original isolation report remains unchanged as historical evidence. This follow-up used the same reviewer, changed no product files, ran no product tests and spawned no additional agent.

Attention: this is a trail-audit PASS, not an overall milestone verdict. The repository-gate correction and correctness admission findings remain pending as recorded by the owner.

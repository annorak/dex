# Independent final-fix verification at 07747f2

Product head: 07747f2. Trunk and actual merged dependency parent: 1015457.
Independent affected verification and formal performance PASS. The final committed-head
repository gate remains pending; this report alone does not declare STACK-READY.
The verifier made no product changes.

## Fourteen separate coverage outcomes

| Outcome | Result | Receipt |
| --- | --- | --- |
| Repository gate | Pending final evidence commit; prior head passed 831 tests | [prior gate](../round2/003-make-check.txt); reserved [final gate](../final/003-make-check.txt) |
| Lane 1: ordered trunk, parent, head build | PASS; exact baseline refusals carried | [head](01-world1.txt), [trunk](../round2/performance/transcripts/01-world1-trunk.txt), [parent](../round2/performance/transcripts/01-world1-parent.txt) |
| Lane 2: seed-7 repeat | PASS; ten formal worlds match every byte | [repeat](02-repeat.txt), [readback](019-performance-artifact-readback.txt) |
| Lane 3: both public bundle checks | PASS; evaluator reads denied | [Bramblewick](03-admission.txt), [Fennor](03-admission-fennor.txt) |
| Lane 4: seven exact packets | PASS, carried with unchanged code and byte proof | [packets](../round2/04-packets.txt) |
| Lane 5: exact history and split | PASS, same proof | [membership](../round2/05-membership.txt) |
| Lane 6: specified mistake IDs | PASS, same proof | [mistakes](../round2/06-mistakes.txt) |
| Lane 7: duplicate, snow, void and cancellation sets | PASS, same proof | [paths](../round2/07-paths.txt) |
| Lane 8: openings and later schedule | PASS, same proof | [stream](../round2/08-stream.txt) |
| Lane 9: independent evaluator keys | PASS, same proof | [key](../round2/09-key.txt) |
| Lane 10: seed variation | PASS; both seeds match prior complete repeats | [scenario](../round2/10-seed.txt), [new seed 11](10-seed-build.txt), [byte proof](008-seed11-manifest.txt) |
| Performance | PASS; all five absolute probes and supported comparisons | [summary](018-performance-summary.txt), [readback](019-performance-artifact-readback.txt) |
| Correctness review | Separate reviewer PASS at this product head, reported by root | Root's correctness report |
| Isolation review | Separate reviewer PASS at this product head, reported by root | Root's isolation report |

[003-bundle-tests.txt](003-bundle-tests.txt) passes 88 affected bundle tests.
The exact requested World 1 command passes all 42 tests in [004-focused.txt](004-focused.txt).

## Applicability and boundaries

[006-carry-forward-proof.txt](006-carry-forward-proof.txt) proves the delta from 7377a3e
contains only the snapshot-comparison optimization and its three admission tests:
two changed files, 313 unchanged tracked files. The CLI startup path, dependencies,
generator, evaluator, scenarios, packets and early refusal paths are byte-identical.
Startup exits before importing the changed bundle code. The original cold-start receipt,
five startup pairs per baseline and actual unsupported baseline refusals therefore remain applicable.

[007-seed7-manifest.txt](007-seed7-manifest.txt) and
[008-seed11-manifest.txt](008-seed11-manifest.txt) independently recheck all required
fixture predicates and prove every one of the 30,861 paths and bytes for each seed matches
its prior complete world. This also carries the original scenario result readbacks,
seed-repeat evidence and 13 unchanged-state refusal outcomes, including
[all-world refusal](../round2/refusal-all.txt) and [refusal driver](../round2/012-refusal-driver.txt).

Both real learning projections rerun on this head:
[Bramblewick](009-projection-bramblewick.txt), [Fennor](0010-projection-fennor.txt).
[013-projection-readback.txt](013-projection-readback.txt) proves self-contained saved views,
2,700 learning cases per company, exact mixed-export row selection and provenance,
and exclusion of exam, evaluator, future and other-company evidence across all five
company-evidence destinations. Original bundles and network access are denied during readback.
[016-audit-readback-complete.txt](016-audit-readback-complete.txt) confirms zero denied-operation
attempts in all seven successful audited commands. The earlier aggregation attempt
[015-audit-readback.txt](015-audit-readback.txt) ran before the last audit file existed;
its setup failure remains preserved and is not counted as a product result.

Each company still has 3,600 history cases, a frozen 2,700/900 split, 1,800 stream cases
and ten separate shadows. The nineteen openings belong to the streams. Final cutoff exports
retain all 1,798 and 1,799 stream postings. Fixture verification claims no learned-stream,
library, repair or UI acceptance.

## Formal performance

All 60 frozen commands completed serially after other owned CPU-heavy work stopped.
All exits and Timer V2 clocks are valid. The unchanged 30-second build, 45-second combined,
1-GiB RSS and 20-percent supported-regression limits apply.

| Sample | First build, seconds | Second build, seconds | Build plus both checks, seconds | Peak RSS, bytes |
| --- | ---: | ---: | ---: | ---: |
| 1 | 22.980741458 | 22.895639833 | 41.737107500 | 359251968 |
| 2 | 22.783165000 | 22.774598833 | 41.151681417 | 348520448 |
| 3 | 22.720385542 | 23.205938709 | 40.890864167 | 348356608 |
| 4 | 23.225731667 | 24.872367542 | 41.782002916 | 355467264 |
| 5 | 24.521889875 | 23.533748667 | 42.945042000 | 353894400 |

| Supported identical workload | Baseline | Wall median change | RSS median change |
| --- | --- | ---: | ---: |
| Both public validations | trunk | -35.719% | -0.304% |
| Both public validations | actual dependency | -34.733% | -0.566% |
| CLI startup, carried unchanged | trunk | +2.604% | +0.162% |
| CLI startup, carried unchanged | actual dependency | +6.443% | -0.054% |

The [freeze](performance/freeze.json) preserves the same 30,868 input hashes and exact
original validation input path. Five alternating validation pairs per baseline and five
two-build/two-check probes use the unchanged recorder and Timer V2. Byte comparisons,
dependency warming and excluded profiling remain outside measured intervals.
The host has ten logical CPUs; recorded one-minute load ranges from 16.111 to 21.162.
No generation speedup is claimed against the unsupported baselines.

Post-timing readback confirms ten complete persisted worlds, each with 30,861 identical files,
and all fifty public checks with exactly 5,400 cases and 7,704/7,714 sources.
Both final-posting exports are present. Input and product bytes remain unchanged.
Register mappings stay unconfirmed; public validation grants no authority.

## Preserved failures and packaging

Round 2 remains FAILED: sample 4 took 45.042089291 seconds against 45.
Every sample and receipt remains unchanged; no unchanged workload was rerun to seek a pass.
The final fix changes snapshot validation, and only affected workloads were remeasured.
Round 1's stale CLI-test failure and missing-parent setup failure also remain preserved.

M1-10's supported startup regression remains FAILED at 21.67 percent against 20 percent,
despite its subsequent owner merge. No earlier failure is waived.

The single unchanged scanner run [021-principal-receipts-scan.txt](021-principal-receipts-scan.txt)
rejects all ten selected principal success receipts and the explicit all-world refusal.
The acceptable raw-receipt tracking list is empty. Raw receipts, frozen inputs and generated
artifacts remain unchanged in the durable local archive managed by root; reports and
reproducible scripts are tracked. No receipt edits, scanner exemptions or threshold changes
were made. Linked raw paths are local evidence, not claims that those files are committed.

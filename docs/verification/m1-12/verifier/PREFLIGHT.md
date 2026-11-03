# M1-12 independent verifier preflight

The goal is one PR for Veldren and the deterministic three-company demo collection.
This verifier owns twelve outcomes and stops at M1-12 without merging.
Head verification and formal performance remain pending.

## Prepared environment

Python 3.13.11, uv 0.11.31, and detect-secrets 1.5.0 are available.
The shell default is Python 3.11.6, so verification uses explicit Python 3.13.
Root, trunk, parent, and the untimed baseline have initialized virtual environments.
The cache is `/private/tmp/dex-m1-10-verifier-cache`.
Offline setup failures remain in `preflight/005-*-sync.txt`.
Network setup then succeeded in `preflight/007-*-sync-network.txt`.

Trunk and the actual merged dependency both name `5a6faaa69b4644a12593a719c42a9752bdfbb4f9`.
Their separate clones are `/private/tmp/dex-m1-12-verifier/trunk` and `/private/tmp/dex-m1-12-verifier/parent`.
Both remain clean and neither has invoked dex.
The independent head clone is not created until root supplies its pinned revision.

The unchanged M1-10 recorder and Timer V2 match the tracked copies byte for byte.
Their success, failure, allocation, clock-jump, and failing-child controls pass once.
The unchanged M1-11 audit hook denies evaluator reads, original-root reads, and socket network.
Each denial has its own receipt and exact hook-attempt readback.

## Early World 1 integration fixture

The separate `untimed-base` clone builds World 1 from the actual merged dependency.
`baseline-world1` retains the complete seed-7 output.
`baseline-world1-manifest.json` records all 30,861 relative file paths and hashes.
The hook loaded and recorded zero network attempts.
Receipts are `preflight/013-baseline-world1-build.txt` and `preflight/015-baseline-manifest.txt`.
This is untimed setup evidence and does not replace any head outcome.

## Pending outcomes

| Outcome | State | Principal receipt |
| --- | --- | --- |
| Repository gate | PENDING | committed-head make check |
| CLI lane 1 | PENDING | 01-demo.txt |
| CLI lane 2 | PENDING | 02-repeat.txt |
| CLI lane 3 | PENDING | 03-admission.txt |
| CLI lane 4 | PENDING | 04-packets.txt |
| CLI lane 5 | PENDING | 05-history.txt |
| CLI lane 6 | PENDING | 06-nesting.txt |
| CLI lane 7 | PENDING | 07-waits.txt |
| CLI lane 8 | PENDING | 08-keys.txt |
| CLI lane 9 | PENDING | 09-stream.txt |
| CLI lane 10 | PENDING | 10-isolation.txt |
| Performance | PENDING | frozen schedule and all samples |

## Timing conditions

Root supplies the pinned code-ready head and specification checklist before functional verification.
Formal timing waits until functional checks and both reviews settle and root releases the CPU barrier.
The frozen schedule starts with cold trunk help, then five alternating startup pairs per baseline.
Supported World 1 build plus public validation uses five alternating pairs per baseline on identical inputs.
Actual unsupported default and World 2 baseline refusals remain separate from supported comparisons.
Five head default builds include all native writes and serialization plus three public checks.
World 2 generation is measured separately. Limits are 60 seconds combined, 5 seconds World 2, 1 GiB RSS, and 20 percent supported median regression.
Complete byte comparisons and artifact readback occur outside timing. Every sample, failure, and contention record remains.

M1-11's 45.042089291-second result remains failed against 45 seconds.
M1-10's 21.67-percent startup regression remains failed against 20 percent.

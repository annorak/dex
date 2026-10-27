# M1-11 verifier preflight

Preflight is complete. Product verification and formal performance have not run.
The verifier did not change product sources or invoke dex.

## Environment and controls

Python 3.13.11, uv 0.11.31, GitHub CLI 2.102.0 and detect-secrets 1.5.0 are available.
Both baseline checkouts have warm dependencies from the preserved M1-10 cache.
The shell's default python3 is 3.11.6, so product and measurement commands use the explicit Python 3.13 environment.

The separate trunk and actual dependency checkouts are pinned to the M1-10 merge.
Their full revisions and checkout status are in the raw setup receipts.
Neither baseline has invoked dex.
Their paths are /private/tmp/dex-m1-11-verifier/trunk and /private/tmp/dex-m1-11-verifier/parent.

Bun is absent from PATH.
The preserved /private/tmp/dex-m1-08-tools/bun-darwin-aarch64/bun is version 1.4.4.
The installed pstack watch-pr help command succeeds with that executable.
Root owns authenticated forge state and merge-safety checks.

The preserved recorder and Timer V2 are reused unchanged from M1-10 verifier/round3/scripts.
Recorder controls retain exact argv, revision, stdout, stderr and exit status for success and nonzero results.
Timer controls pass success, nonzero, 64 MiB allocation, forward-clock invalidation, backward-clock invalidation and preservation of a failing child's exit status.
Every control has a separate receipt.
The one-time control script is /private/tmp/dex-m1-11-verifier/preflight_controls.py.
Its complete proposed diff is retained beside it.

## Proposed formal schedule

The final freeze will name head, trunk, dependency, exact source and input bytes, tool hashes and every sample before measurement.
Root will release the CPU barrier after untimed verification and both reviews finish.
The verifier will retain host load and process context before and after the schedule.
The first observed preflight load was 38.86, 24.92 and 18.00 on ten logical CPUs.
This is environment evidence, not grounds to discard a later sample.

1. Measure cold trunk help as that checkout's first product invocation after dependency setup.
2. Run five alternating trunk/head startup pairs and five alternating dependency/head startup pairs.
3. Run the exact seed-7 world build command on trunk, dependency and head in that order. Record actual unsupported baseline refusals.
4. Compare supported public validation on identical frozen seed-7 bundles with five alternating trunk/head pairs and five alternating dependency/head pairs.
5. Run five head size samples. Each sample creates two complete fresh seed-7 builds and checks both public company bundles from the first build.
6. Compare complete path-and-byte manifests outside generation timing. Validate every declared case, native export and packet outside timing.
7. Preserve all samples, failures, outputs, clocks and error classifications.

Each complete build must stay at or below 30 seconds.
A complete build plus both public checks must stay at or below 45 seconds.
Peak RSS must stay at or below 1 GiB.
Each supported identical-workload median wall-time and RSS ratio must stay at or below 1.20.
The second build supplies the byte-identical comparison and has its own complete-build budget.
Generation refusals do not count as speedups.
Profiling, if needed to answer a concrete risk, runs separately and is excluded from formal samples.
No unchanged measurement will be repeated to obtain a pass.

## Evidence packaging

The unchanged scanner accepts the portable control script.
It rejects representative raw receipts because they contain full revision and tool hashes.
Receipt 018-receipt-scan.txt preserves those findings.
Raw receipts remain unchanged.
No scanner exemption, allowlist or receipt rewriting is planned.
The tracked package will contain scanner-compatible scripts, coverage and concise reports.
The complete raw tree remains separately available for the owner's transcript review.

All raw preflight receipts currently live under /private/tmp/dex-m1-11-verifier/preflight.
Root must preserve that tree in the durable milestone archive before cleanup.

## Historical status

M1-10 was merged by the owner after its supported startup wall-time regression failed.
Its recorded increase was 21.67 percent against the unchanged 20 percent limit.
Its 788-test repository gate, 47 focused tests, ten CLI outcomes, both reviews and five absolute projection samples passed.
This preflight does not repair or relabel M1-10 or earlier milestones' failures and limitations.

## Pending

The verifier is waiting for the pinned code-ready head and root's single specification-to-assertion checklist.
Repository gates, ten live lanes, performance, generated-bundle admission and projection checks remain unrun.
The twelve verifier outcomes remain PENDING.
Correctness and isolation belong to the two independent reviewers.

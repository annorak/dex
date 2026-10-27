# Reproduce M1-10 verification

The product revision is ecd4b9a. The actual M1-09 dependency and the measured trunk revision are both c7c1976. Use separate pinned checkouts for trunk, dependency parent and head. Do not substitute an intermediate M1-10 commit for the dependency parent.

The checked-in scripts are byte-for-byte copies of the executed scripts. record.py and Timer V2 measure.py also match the preserved M1-09 versions. The evaluator fixture generator and scenario inputs live in src/dex/eval/projection_fixture.py and tests/scenarios/projection-*.json.

Use Python 3.13 or newer and uv 0.11.31. Install pinned dependencies in each checkout before measurement with uv sync --frozen --all-groups. Do not invoke the trunk CLI during setup. Dependency warming and the first CLI invocation are separate steps.

Create a fresh evidence directory. Run the following from the checkout containing these scripts, supplying absolute paths for each placeholder. The prepare command creates frozen learning and 10,000-case bundles once, hashes their bytes, and writes the revision, tool, input and schedule freeze.

```sh
python3 docs/verification/m1-10/scripts/verify_projection.py prepare \
  --root EVIDENCE_DIRECTORY \
  --checkout HEAD_CHECKOUT \
  --trunk TRUNK_CHECKOUT \
  --parent DEPENDENCY_CHECKOUT \
  --base FULL_DEPENDENCY_REVISION \
  --head FULL_PRODUCT_REVISION \
  --cache UV_CACHE_DIRECTORY \
  --history ABSOLUTE_PATH_TO_THIS_SCRIPTS_DIRECTORY \
  --uv ABSOLUTE_UV_EXECUTABLE \
  --python ABSOLUTE_PYTHON_EXECUTABLE

python3 docs/verification/m1-10/scripts/verify_projection.py live \
  --root EVIDENCE_DIRECTORY --first-lane 2 --last-lane 10

python3 docs/verification/m1-10/scripts/verify_projection.py performance \
  --root EVIDENCE_DIRECTORY
```

Run performance only after all CPU-heavy checks and independent reviews finish. The schedule measures trunk's first CLI invocation, five alternating trunk/head help pairs and five alternating actual-parent/head help pairs. It then records actual unsupported projection refusals on trunk and parent, runs the ordered learning scenario on head, and measures five complete 10,000-case commands. Each sample uses a fresh output directory and database. Emitted projection commands are also executed and checked outside the measured samples.

All five size samples must meet 10 seconds of projection work, 20 seconds of full command completion and 512 MiB peak RSS. Supported identical-workload median wall time and RSS must stay within 20 percent of each baseline. The projection workload is unsupported on the dependency and trunk, so there is no projection speedup comparison.

The driver checks every declared input case, every retained row and the persisted view outside timing. It checks unchanged source, workspace and destination state for named CLI refusals. The live scenarios plant evaluator, exam, future and root-capability leaks, then inspect serialized output and denied-root behavior. Independent reviewers' probes add nested MIME aliases, exact cell observations and excluded recording producers.

The original run reused frozen inputs across focused fixes. Its final config is verifier/round3/frozen-config.json in the local evidence directory. Earlier configs, failures and receipts are unchanged. The complete local evidence directory is docs/verification/m1-10 under the original checkout. It includes raw command transcripts, frozen inputs, independent probes, saved views, databases and full hashes.

The unchanged scanner flags hashes in raw receipts. Those files were not rewritten, redacted or exempted. The PR includes suitable reports, results and scripts; the raw evidence remains local for the owner's transcript review. The reproduction commands create new evidence and must not overwrite the original run.

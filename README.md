# dex

Python 3.12 CLI scaffold for dex.

Install uv 0.11.31, then set up the locked development environment:

```sh
uv sync --locked
uv run --locked python -m dex --help
```

`run`, `measure`, and `verify-package <package>` are unimplemented command stubs.
They print an error to stderr and exit with status 1. Help exits successfully.

See [AGENTS.md](AGENTS.md) for the development and verification commands.

## Generate the demo fixtures

Build step 1 creates the three invented companies, hidden answer keys and employee
sheets, HOA checklist v1, and Pallet HOA's reviewed package. Generate all artifacts
with one command:

```sh
uv run --locked python scripts/generate_demo.py
```

Use `--output <directory>` to generate a separate tree. The generator overwrites
its named artifacts and preserves other files. It does not update the reviewed
hash baseline. An interrupted run can leave an incomplete tree; rerun the same
command to restore all named artifacts.

`demo/companies/` contains the approved sources for each company. It includes
source inventories with fixed snapshot dates. Keep `demo/keys/`, this repository's
build scripts, tests, and the design document outside oak's allowed folders.
Cerulean and Vermilion reference SQL is in `demo/keys/` for future plain-code checks.
The employee-only facts remain in the separate `*.employee.yaml` files.

`demo/packages/pallet/` is a prepared example with simulated employee and engineer
approvals. Its evidence, saved SQL, three executed checks, and internal hashes are
self-contained. The application `verify-package` command remains an unimplemented
stub in this build step.

The specification does not enumerate Pallet's rows. This fixture chooses Pallet
Grove P01, Lavender Grove P02 with no invoices, and company-wide vendor V1, Eevee
Maintenance. P100 is open with a 15000-cent balance on a 20000-cent invoice. P101
is closed with a zero balance on a 10000-cent invoice. Its snapshot date is
September 30, 2026. Cerulean's unspecified single-line invoice descriptions are
`Invoice total`; the two I100 descriptions match the design exactly. The old
workbook tab names are `Open Invoices` and `Trips`.

Run the independent readback and hash checks:

```sh
uv run --locked pytest tests/test_demo.py -v
```

The tests read both the checked-in and freshly generated fixtures. They compare
all Cerulean and Vermilion rows, source documents, employee answers, checklist,
keys, and Pallet package contents. They exercise changed, added, and removed keys
against the hash guard, then show that an explicit hash update permits the guard.
Independent semantic checks still reject incorrect expected answers.

Fresh runs produce identical file hashes in the same locked environment and
SQLite runtime. Workbook document properties and ZIP timestamps are fixed.
SQLite files record the SQLite writer version, so byte identity across different
SQLite runtimes is not promised. The checked-in artifacts always match the exact
reviewed hashes in `tests/demo.sha256`.

After approving an intentional fixture change, regenerate it, review its data and
complete diff, and explicitly record its hashes:

```sh
uv run --locked python scripts/generate_demo.py --hashes > tests/demo.sha256
uv run --locked pytest tests/test_demo.py -v
```

Review `tests/demo.sha256` with the changed fixtures. The test also rejects an
unrecorded extra or missing file anywhere in `demo/`.

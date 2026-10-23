import json
import os
import sys
from copy import deepcopy
from datetime import UTC, date, datetime
from email.message import EmailMessage
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Any, cast
from unittest.mock import patch

from dex import codec
from dex.bundle.collection import Collection, load_collection, write_collection
from dex.bundle.formats import XLSX
from dex.bundle.model import BundleError
from dex.bundle.reader import load_bundle
from dex.bundle.validation import canonical, fields, object_value, parse_json
from dex.bundle.writer import bundle_files, write_bundle
from dex.core import events as e
from dex.core import program as p
from dex.core import runtime as r
from dex.eval.bundle_fixture import (
    AT,
    add_source,
    cli,
    make_bundle,
    mapping,
    ordinary_run,
    pdf,
    save_manifest,
    session_file,
    supported_program,
    workbook,
)
from dex.workspace import Workspace


def _check(path: Path, reason: str | None = None) -> dict[str, object]:
    return {
        "argv": ["uv", "run", "dex", "bundle", "check", str(path)],
        "exit_status": 0 if reason is None else 2,
        "reason": reason,
    }


def _guard(out: Path) -> tuple[Path, Path, Path]:
    source = out / "guard-bundle"
    make_bundle(source)
    draft, catalog = supported_program(source)
    session_path = out / "session.json"
    session = session_file(session_path)
    database = out / "workspace.sqlite"
    now = datetime.now(UTC)
    with Workspace(database, session, {}) as workspace:
        assert isinstance(
            workspace.register(
                e.CommandMeta("register", session.actor, now, now, 0), draft, catalog
            ),
            r.Accepted,
        )
        pin, artifact = next(iter(workspace.catalog.artifacts.items()))
        assert not workspace.state.registrations[pin].missing_checks
        assert isinstance(
            workspace.execute(
                e.ApproveProgram(
                    e.CommandMeta(
                        "approve", session.actor, now, now, workspace.state.revision
                    ),
                    pin,
                    session.company,
                )
            ),
            r.Accepted,
        )
    program_path = out / "program.json"
    program_path.write_text(codec.dumps(artifact))
    return database, session_path, program_path


def _reject(
    out: Path, label: str, path: Path, reason: str, guard: tuple[Path, Path, Path]
) -> None:
    database, session, program = guard
    before = database.read_bytes()
    result = cli(
        out,
        "rejection-" + label,
        [
            "run",
            str(path),
            "--program",
            str(program),
            "--workspace",
            str(database),
            "--out",
            str(out / ("rejected-" + label)),
        ],
        session,
    )
    assert result.returncode == 2 and reason in result.stderr, (
        result.stdout,
        result.stderr,
    )
    assert database.read_bytes() == before
    assert not (out / ("rejected-" + label)).exists()


def roundtrip(out: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    source = out / "input"
    manifest = make_bundle(source)
    add_source(
        source,
        manifest,
        "table.csv",
        b"Amount,Date,Status\n1234,2026-01-02,P\n",
        "text/csv",
        mapping=mapping(),
    )
    bundle = load_bundle(source)
    first, second, archive = out / "first", out / "second", out / "bundle.zip"
    write_bundle(bundle, first)
    reloaded = load_bundle(first)
    assert bundle.originals == reloaded.originals
    assert (
        bundle.sources == reloaded.sources
        and bundle.cases == reloaded.cases
        and bundle.deliveries == reloaded.deliveries
    )
    write_bundle(reloaded, second)
    assert bundle_files(reloaded) == bundle_files(load_bundle(second))
    write_bundle(bundle, archive, archive=True)
    write_bundle(reloaded, out / "again.zip", archive=True)
    assert archive.read_bytes() == (out / "again.zip").read_bytes()
    assert load_bundle(archive) == reloaded
    other = out / "other-input"
    other_manifest = make_bundle(other)
    other_manifest.update(company_id="company-2", bundle_id="packet-2")
    save_manifest(other, other_manifest)
    collection = Collection(
        "two-companies", b"", (("one", bundle), ("two", load_bundle(other)))
    )
    write_collection(collection, out / "collection")
    combined = load_collection(out / "collection/collection.json")
    assert [item.company_id for _, item in combined.bundles] == [
        "company-1",
        "company-2",
    ]
    return {
        "original_bytes": True,
        "evidence_equal": True,
        "deterministic_archive": True,
        "companies": 2,
    }, [
        _check(path)
        for path in (source, first, second, archive, out / "collection/collection.json")
    ]


def money_dates(out: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    values: list[tuple[p.NamedValue, ...]] = []
    checks: list[dict[str, object]] = []
    for label, row, money, dates in (
        ("iso", "1234,2026-01-02,P", "cents", "iso"),
        ("us", "12.34,01/02/2026,P", "decimal-dollars", "us"),
    ):
        path = out / label
        manifest = make_bundle(path)
        add_source(
            path,
            manifest,
            "table.csv",
            ("Amount,Date,Status\n" + row + "\n").encode(),
            "text/csv",
            mapping=mapping(money, dates),
        )
        source = load_bundle(path).sources[1]
        values.append(source.records[0].values)
        checks.append(_check(path))
    expected = (
        p.NamedValue("amount", p.MoneyValue(1234)),
        p.NamedValue("date", p.DateValue(date(2026, 1, 2))),
        p.NamedValue("status", p.TextValue("posted")),
    )
    assert values == [expected, expected]
    return {
        "equal": True,
        "amount_cents": 1234,
        "date": "2026-01-02",
        "status": "posted",
    }, checks


def invalid_values(out: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    guard = _guard(out)
    checks: list[dict[str, object]] = []
    for label, row, reason in (
        ("fractional", "0.001,2026-01-02,P", "fractional cents"),
        ("date", "1.00,2026-02-30,P", "invalid business date"),
        ("mapping", "1.00,2026-01-02,P", "conflicting mapping"),
        ("status", "1.00,2026-01-02,NEW", "unresolved status meaning"),
    ):
        path = out / label
        manifest = make_bundle(path)
        columns = mapping("decimal-dollars")
        if label == "mapping":
            columns["columns"].append(deepcopy(columns["columns"][0]))
        add_source(
            path,
            manifest,
            "table.csv",
            ("Amount,Date,Status\n" + row + "\n").encode(),
            "text/csv",
            mapping=columns,
        )
        _reject(out, label, path, reason, guard)
        checks.append(_check(path, reason))
    return {
        "fractional_rejected": True,
        "date_rejected": True,
        "mapping_rejected": True,
        "status_rejected": True,
        "workspace_unchanged": True,
    }, checks


def email_attachments(out: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    path = out / "bundle"
    manifest = make_bundle(path)
    attachment = pdf()
    message = EmailMessage()
    message["From"] = "clerk@example.invalid"
    message["To"] = "office@example.invalid"
    message["Subject"] = "Preserve evidence"
    message.set_content("Plain message body.")
    message.add_alternative(
        "<p>HTML message café.</p><script>untrusted data</script>", subtype="html"
    )
    message.set_boundary("fixed-alternative")
    message.add_attachment(
        attachment, maintype="application", subtype="pdf", filename="attachment.pdf"
    )
    message.set_boundary("fixed-mixed")
    add_source(path, manifest, "message.eml", message.as_bytes(), "message/rfc822")
    add_source(
        path,
        manifest,
        "attachment.pdf",
        attachment,
        "application/pdf",
        origin={
            "kind": "attachment",
            "message": {"source_id": "message.eml", "revision_id": "r1"},
            "part": "part:2",
            "attachment_id": "attachment.pdf",
        },
    )
    add_source(path, manifest, "body.html", b"<p>Standalone HTML.</p>", "text/html")
    add_source(
        path,
        manifest,
        "note.md",
        b"# 1. A numbered note\nKeep the original.\n",
        "text/markdown",
    )
    plain = EmailMessage()
    plain["Subject"] = "Plain email"
    plain.set_content("Plain email text.")
    add_source(path, manifest, "plain.eml", plain.as_bytes(), "message/rfc822")
    bundle = load_bundle(path)
    extracted = bundle.sources[1].extraction
    assert extracted is not None and bundle.sources[1].unresolved is None
    assert all(
        value in extracted.text
        for value in (
            "Plain message body.",
            "HTML message café.",
            "Selectable attachment text.",
        )
    )
    assert {"headers", "part:1:1", "part:1:2", "part:2/page:1"} <= {
        section.locator for section in extracted.sections
    }
    write_bundle(bundle, out / "roundtrip")
    assert bundle.originals == load_bundle(out / "roundtrip").originals
    return {
        "plain": True,
        "html": True,
        "attachment": True,
        "part_provenance": True,
        "page_provenance": True,
        "original_bytes": True,
    }, [_check(path), _check(out / "roundtrip")]


def xlsx_sheets(out: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    checks: list[dict[str, object]] = []
    amounts: list[int] = []
    for label, sheet in (("first", None), ("second", "Second")):
        path = out / label
        manifest = make_bundle(path)
        options: dict[str, object] = {} if sheet is None else {"sheet": sheet}
        add_source(
            path,
            manifest,
            "table.xlsx",
            workbook(),
            XLSX,
            mapping=mapping("decimal-dollars", "us"),
            **options,
        )
        value = load_bundle(path).sources[1].records[0].values[0].value
        assert isinstance(value, p.MoneyValue)
        amounts.append(value.cents)
        checks.append(_check(path))
    assert amounts == [1234, 5678]
    xls = out / "xls"
    manifest = make_bundle(xls)
    add_source(xls, manifest, "table.xls", b"legacy", "application/vnd.ms-excel")
    try:
        load_bundle(xls)
    except BundleError as error:
        assert "convert to XLSX or CSV" in str(error)
    else:
        raise AssertionError("XLS accepted")
    checks.append(_check(xls, "convert to XLSX or CSV"))
    unresolved = out / "unresolved"
    manifest = make_bundle(unresolved)
    add_source(unresolved, manifest, "bad.xlsx", b"not a workbook", XLSX)
    add_source(
        unresolved, manifest, "image.pdf", pdf(image_only=True), "application/pdf"
    )
    parsed = load_bundle(unresolved)
    assert all(
        source.unresolved and source.extraction is None for source in parsed.sources[1:]
    )
    checks.append(_check(unresolved))
    return {
        "first_cents": 1234,
        "second_cents": 5678,
        "xls_rejected": True,
        "unreadable_unresolved": True,
        "image_unresolved": True,
    }, checks


def paths_hashes(out: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    guard = _guard(out)
    checks: list[dict[str, object]] = []
    for label, reason in (
        ("traversal", "unsafe path"),
        ("absolute", "unsafe path"),
        ("symlink", "symlink"),
        ("missing", "missing"),
        ("undeclared", "undeclared"),
        ("hash", "hash mismatch"),
        ("version", "unsupported version"),
        ("identity", "conflicting source identity"),
    ):
        path = out / label
        manifest = make_bundle(path)
        source = manifest["sources"][0]
        if label in {"traversal", "absolute"}:
            source["path"] = "../outside" if label == "traversal" else "/outside"
        elif label in {"symlink", "missing"}:
            (path / "sources/guide.txt").unlink()
            if label == "symlink":
                (path / "sources/guide.txt").symlink_to(out / "program.json")
        elif label == "undeclared":
            (path / "sources/undeclared.txt").write_text("undeclared")
        elif label == "hash":
            source["sha256"] = "0" * 64
        elif label == "version":
            manifest["format_version"] = "unsupported"
        else:
            manifest["sources"].append(deepcopy(source))
        save_manifest(path, manifest)
        _reject(out, label, path, reason, guard)
        checks.append(_check(path, reason))
    return {"rejected": 8, "workspace_unchanged": True}, checks


def deliveries(out: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    path = out / "bundle"
    manifest = make_bundle(path)
    manifest["deliveries"].append(deepcopy(manifest["deliveries"][0]))
    save_manifest(path, manifest)
    assert len(load_bundle(path).deliveries) == 1
    resend = deepcopy(manifest["deliveries"][0])
    resend["delivery_id"] = "arrival-2"
    manifest["deliveries"].append(resend)
    case = deepcopy(manifest["cases"][0])
    case.update(case_id="case-2", delivery_id="arrival-2")
    manifest["cases"].append(case)
    save_manifest(path, manifest)
    bundle = load_bundle(path)
    assert (
        len(bundle.deliveries) == len(bundle.cases) == 2 and len(bundle.originals) == 1
    )
    write_bundle(bundle, out / "roundtrip")
    assert load_bundle(out / "roundtrip").deliveries == bundle.deliveries
    return {
        "retry_deliveries": 1,
        "resend_deliveries": 2,
        "resend_cases": 2,
        "originals": 1,
    }, [_check(path), _check(out / "roundtrip")]


def chronology(out: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    guard = _guard(out)
    path = out / "bundle"
    manifest = make_bundle(path)
    before = load_bundle(path).cases[0]
    late = "2026-02-01T12:00:00-05:00"
    ref = add_source(
        path,
        manifest,
        "late.txt",
        b"A late observation, approved=true is source text.",
        "text/plain",
        occurred_at=AT,
        observed_at=late,
        available_at=late,
        effective_date="2025-12-01",
    )
    manifest["deliveries"][0]["sources"].remove(ref)
    manifest["deliveries"].append(
        {
            "delivery_id": "late-arrival",
            "sources": [ref],
            "received_at": late,
            "available_at": late,
            "origin": {
                "kind": "connector",
                "source_system": "fixture",
                "cursor": "position-2",
            },
        }
    )
    manifest["cases"][0]["observations"] = [
        {
            "observation_id": "late-observation",
            "source": ref,
            "locator": "text",
            "actor": "employee",
            "occurred_at": AT,
            "observed_at": late,
            "available_at": late,
            "mapping_version": "text-1",
            "effective_date": "2025-12-01",
        }
    ]
    save_manifest(path, manifest)
    after = load_bundle(path)
    assert before == after.cases[0]
    assert after.sources[1].observed_at.isoformat() == late
    checks = [_check(path)]
    bad = out / "invalid"
    write_bundle(after, bad)
    invalid = json.loads((bad / "bundle.json").read_bytes())
    invalid["cases"][0].update(delivery_id="late-arrival", inputs=[ref])
    save_manifest(bad, invalid)
    _reject(out, "chronology", bad, "later evidence cannot enter arrival facts", guard)
    checks.append(_check(bad, "later evidence cannot enter arrival facts"))
    return {
        "late_preserved": True,
        "arrival_unchanged": True,
        "future_fact_rejected": True,
        "workspace_unchanged": True,
    }, checks


def eval_unreadable(out: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    path = out / "bundle"
    make_bundle(path)
    forbidden = path / "eval"
    forbidden.mkdir()
    (forbidden / "private.json").write_text('{"answer":"evaluator only"}')
    forbidden.chmod(0)
    denied = False
    try:
        (forbidden / "private.json").read_bytes()
    except PermissionError:
        denied = True
    assert denied, "eval subtree was not unreadable"
    accesses: list[str] = []
    original_open, original_scan = os.open, os.scandir

    def guarded_open(
        name: Any, flags: int, mode: int = 0o777, *, dir_fd: int | None = None
    ) -> int:
        rendered = os.fsdecode(name)
        accesses.append("open " + rendered)
        assert "eval" not in Path(rendered).parts, rendered
        return original_open(name, flags, mode, dir_fd=dir_fd)

    def guarded_scan(name: Any) -> Any:
        accesses.append("scandir " + str(name))
        assert isinstance(name, int), (
            "public loader must use admitted directory descriptors"
        )
        return original_scan(name)

    with (
        patch.object(os, "open", guarded_open),
        patch.object(os, "scandir", guarded_scan),
    ):
        bundle = load_bundle(path)
    assert len(bundle.sources) == 1
    (out / "accesses.json").write_bytes(canonical(accesses))
    return {"unreadable": True, "eval_accesses": 0, "public_valid": True}, [
        _check(path)
    ]


def prepare_size(path: Path) -> None:
    manifest = make_bundle(path)
    packet = (b"Evidence packet.\n" * (10485760 // 17 + 1))[:10485760]
    assert len(packet) == 10485760
    add_source(path, manifest, "packet.txt", packet, "text/plain")
    rows = "Amount,Date,Status\n" + "".join(
        f"{index},2026-01-02,P\n" for index in range(1, 10001)
    )
    add_source(
        path, manifest, "table.csv", rows.encode(), "text/csv", mapping=mapping()
    )


def size(out: Path, source: Path) -> dict[str, object]:
    bundle = load_bundle(source)
    records = bundle.sources[2].records
    assert len(records) == 10000
    amounts = [record.values[0].value for record in records]
    assert all(isinstance(value, p.MoneyValue) for value in amounts)
    total = sum(cast(p.MoneyValue, value).cents for value in amounts)
    assert total == 50005000
    packet = next(
        original
        for original in bundle.originals
        if original.path == "sources/packet.txt"
    )
    assert len(packet.content) == 10485760
    write_bundle(bundle, out / "written")
    write_bundle(bundle, out / "written.zip", archive=True)
    return {
        "rows": len(records),
        "source_packet_bytes": len(packet.content),
        "total_cents": total,
        "original_bytes": sum(len(original.content) for original in bundle.originals),
        "output": "written",
        "archive": "written.zip",
        "source_packet_sha256": sha256(packet.content).hexdigest(),
    }


def run_bundle_scenario(raw: bytes, out: Path) -> int:
    try:
        specification = parse_json(raw, "scenario")
        fields(
            specification,
            {"format", "scenario_id", "case", "expected"},
            {"input_bundle"},
            "scenario",
        )
        name = specification["case"]
        cases = {
            "bundle-roundtrip": roundtrip,
            "bundle-money-dates": money_dates,
            "bundle-fractional-invalid": invalid_values,
            "bundle-email-attachments": email_attachments,
            "bundle-xlsx-sheets": xlsx_sheets,
            "bundle-path-hash": paths_hashes,
            "bundle-delivery-identities": deliveries,
            "bundle-chronology": chronology,
            "bundle-eval-unreadable": eval_unreadable,
        }
        if name not in {*cases, "bundle-ordinary-run", "bundle-size-10000"}:
            raise BundleError("unknown bundle scenario")
        out.mkdir(parents=True, exist_ok=False)
        checks: list[dict[str, object]] = []
        started = None
        if name == "bundle-size-10000":
            source = (
                Path(specification["input_bundle"])
                if "input_bundle" in specification
                else out / "input"
            )
            if "input_bundle" not in specification:
                prepare_size(source)
            started = perf_counter()
            actual = size(out, source)
        elif name == "bundle-ordinary-run":
            actual = ordinary_run(out)
            checks = [_check(out / "bundle")]
        else:
            actual, checks = cases[name](out)
        expected = object_value(specification["expected"], "expected")
        matches = {key: actual.get(key) == value for key, value in expected.items()}
        (out / "actual.json").write_bytes(
            canonical({"scenario": name, "observed": actual, "checks": checks})
        )
        (out / "expected.json").write_bytes(
            canonical({"expected": expected, "matches": matches})
        )
        output = canonical(
            {"scenario": name, "observed": actual, "matches": matches, "checks": checks}
        ).decode()
        print(output, end="", flush=True)
        processing_seconds = None if started is None else perf_counter() - started
        if processing_seconds is not None:
            (out / "timing.json").write_bytes(
                canonical({"processing_seconds": processing_seconds})
            )
        return 0 if all(matches.values()) else 1
    except (ValueError, OSError, AssertionError) as error:
        print(
            json.dumps(
                {
                    "format": "dex-eval-error-1",
                    "code": "bundle_scenario",
                    "message": str(error),
                }
            ),
            file=sys.stderr,
        )
        return 2

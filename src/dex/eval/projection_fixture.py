from pathlib import Path
from typing import Any

from dex.eval.bundle_fixture import add_source, make_bundle, save_manifest

CUTOFF = "2026-10-01T00:00:00+00:00"
MIXED = "Value\nCafé 🦉 learning\nexam-only payload\nfuture-only payload\n".encode()


def projection_bundle(path: Path) -> dict[str, Any]:
    manifest = make_bundle(path)
    manifest["cases"] = []
    ref = add_source(
        path,
        manifest,
        "mixed.csv",
        MIXED,
        "text/csv",
        mapping={
            "version": "mapping-1",
            "confirmed_by": "employee",
            "confirmed_at": "2026-01-01T00:00:00+00:00",
            "effective_from": "2020-01-01",
            "effective_until": None,
            "columns": [{"source": "Value", "target": "value", "kind": "text"}],
        },
    )
    cases = [
        {
            "case_id": identity,
            "delivery_id": "arrival-1",
            "opened_at": opened,
            "business_date": opened[:10],
            "inputs": [ref],
            "facts": [
                {
                    "name": "value",
                    "source": ref,
                    "record": f"record:{record}",
                    "column": "value",
                }
            ],
            "observations": [],
        }
        for identity, opened, record in (
            ("learning-case", "2026-06-30T23:59:59+00:00", 2),
            ("exam-case", "2026-07-01T00:00:00+00:00", 3),
            ("future-case", "2027-01-01T00:00:00+00:00", 4),
        )
    ]
    manifest["history"] = {
        "kind": "interval",
        "start": "2025-10-01T00:00:00+00:00",
        "end": "2026-10-01T00:00:00+00:00",
        "opening_event": "received",
        "adequacy": {
            "decision": "usable",
            "actor": "employee",
            "decided_at": "2026-01-01T00:00:00+00:00",
        },
        "cases": cases[:2],
    }
    manifest["cases"] = cases[2:]
    future = add_source(
        path,
        manifest,
        "future.txt",
        b"future notice",
        "text/plain",
        occurred_at="2025-01-01T00:00:00+00:00",
        observed_at="2026-01-01T00:00:00+00:00",
        available_at="2027-01-01T00:00:00+00:00",
        effective_date="2025-01-01",
    )
    manifest["deliveries"][0]["sources"].remove(future)
    manifest["deliveries"].append(
        {
            "delivery_id": "future-delivery",
            "sources": [future],
            "received_at": "2026-01-01T00:00:00+00:00",
            "available_at": "2027-01-01T00:00:00+00:00",
            "origin": {"kind": "file", "snapshot": "later"},
        }
    )
    (path / "eval").mkdir()
    (path / "eval/manifest.json").write_text('{"label":"evaluator-only key"}')
    save_manifest(path, manifest)
    return manifest


def add_observation(
    path: Path,
    manifest: dict[str, Any],
    case_index: int,
    identity: str,
    available: str,
    content: bytes,
) -> None:
    ref = add_source(path, manifest, identity + ".txt", content, "text/plain")
    manifest["history"]["cases"][case_index]["observations"].append(
        {
            "observation_id": identity,
            "source": ref,
            "locator": "text",
            "actor": "employee",
            "occurred_at": "2026-06-30T12:00:00+00:00",
            "observed_at": "2026-07-02T00:00:00+00:00",
            "available_at": available,
            "effective_date": "2025-10-01",
            "mapping_version": "text-1",
        }
    )
    save_manifest(path, manifest)


def add_recording(
    path: Path,
    manifest: dict[str, Any],
    identity: str,
    case_id: str,
    refs: list[dict[str, str]],
    *,
    phase: str = "runtime",
    available: str = "2026-08-01T00:00:00+00:00",
    producer_case: str | None = None,
) -> None:
    import json
    from hashlib import sha256

    from dex import codec
    from dex.bundle.validation import canonical
    from dex.core import events as e
    from dex.core import program as p
    from dex.recordings import request_digest

    request = e.RecordingRequest(
        e.WorkRevision(e.WorkAddress(case_id, "read"), 1),
        manifest["company_id"],
        e.ArtifactPin("program", "r1", "a" * 64),
        ()
        if producer_case is None
        else (
            e.ConsumedInput(
                ("upstream",),
                p.ResultRef("prior"),
                p.TextValue("derived input"),
                e.WorkAddress(producer_case, "prior"),
                producer_revision=1,
            ),
        ),
        "prompt-1",
        p.Scalar.TEXT,
        "records-1",
    )
    content = canonical(
        {
            "format": "dex-recording-1",
            "request_digest": request_digest(request),
            "recording_id": identity,
            "model": "recorded",
            "input_tokens": 1,
            "output_tokens": 1,
            "value": identity + " output",
            "failure": None,
        }
    )
    (path / "recordings").mkdir(exist_ok=True)
    relative = "recordings/" + identity + ".json"
    (path / relative).write_bytes(content)
    descriptor = {
        "recording_id": identity,
        "path": relative,
        "sha256": sha256(content).hexdigest(),
        "phase": phase,
        "input_identity": request_digest(request),
        "prompt_version": "prompt-1",
        "schema_version": "text-1",
        "request": json.loads(codec.dumps(request)),
        "sources": refs,
        "observed_at": available,
        "available_at": available,
    }
    if phase == "runtime":
        descriptor.update(case_id=case_id, ai_step="read", program_version="r1")
    manifest["recordings"].append(descriptor)
    save_manifest(path, manifest)


def prepare_size(path: Path) -> None:
    from hashlib import sha256

    manifest = projection_bundle(path)
    source = manifest["sources"][1]
    content = (
        "Value\n" + "".join(f"record-{number:05d}\n" for number in range(10000))
    ).encode()
    (path / source["path"]).write_bytes(content)
    source["sha256"] = sha256(content).hexdigest()
    ref = {"source_id": source["source_id"], "revision_id": source["revision_id"]}
    manifest["history"]["cases"] = [
        {
            "case_id": f"case-{number:05d}",
            "delivery_id": "arrival-1",
            "opened_at": "2026-06-30T23:59:59+00:00"
            if number < 8000
            else "2026-07-01T00:00:00+00:00",
            "business_date": "2026-06-30" if number < 8000 else "2026-07-01",
            "inputs": [ref],
            "facts": [
                {
                    "name": "value",
                    "source": ref,
                    "record": f"record:{number + 2}",
                    "column": "value",
                }
            ],
            "observations": [],
        }
        for number in range(10000)
    ]
    manifest["cases"] = []
    save_manifest(path, manifest)


def add_native_evidence(path: Path, manifest: dict[str, Any]) -> None:
    import io
    import zipfile
    from email.message import EmailMessage

    from dex.bundle.formats import XLSX
    from dex.eval.bundle_fixture import mapping, pdf, workbook

    output = io.BytesIO()
    with (
        zipfile.ZipFile(io.BytesIO(workbook())) as original,
        zipfile.ZipFile(output, "w") as projected,
    ):
        for entry in original.infolist():
            content = original.read(entry)
            if entry.filename == "xl/worksheets/sheet1.xml":
                content = content.replace(
                    b"</sheetData>",
                    b'<row r="3"><c r="A3" t="inlineStr"><is><t>98.76</t></is></c><c r="B3" t="inlineStr"><is><t>07/01/2026</t></is></c><c r="C3" t="inlineStr"><is><t>X</t></is></c></row></sheetData>',
                )
            projected.writestr(entry, content)
    ref = add_source(
        path,
        manifest,
        "mixed.xlsx",
        output.getvalue(),
        XLSX,
        mapping=mapping("decimal-dollars", "us"),
    )
    for index, case in enumerate(manifest["history"]["cases"]):
        case["inputs"].append(ref)
        case["facts"].append(
            {
                "name": "amount",
                "source": ref,
                "record": f"record:{index + 2}",
                "column": "amount",
            }
        )
    message = EmailMessage()
    message["From"] = "employee@example.test"
    message["To"] = "operator@example.test"
    message["Subject"] = "Archived evidence"
    message.set_content("permitted message body")
    message.add_attachment(
        pdf(), maintype="application", subtype="pdf", filename="page.pdf"
    )
    message.add_attachment(
        b"exam attachment secret",
        maintype="text",
        subtype="plain",
        filename="restricted.txt",
    )
    message.set_boundary("projection-boundary")
    parent = add_source(
        path, manifest, "message.eml", message.as_bytes(), "message/rfc822"
    )
    child = add_source(
        path,
        manifest,
        "restricted.txt",
        b"exam attachment secret",
        "text/plain",
        origin={
            "kind": "attachment",
            "message": parent,
            "part": "part:3",
            "attachment_id": "attachment-3",
        },
    )
    manifest["history"]["cases"][1]["observations"].append(
        {
            "observation_id": "restricted-attachment",
            "source": child,
            "locator": "text",
            "actor": "employee",
            "occurred_at": "2026-07-01T00:00:00+00:00",
            "observed_at": "2026-07-02T00:00:00+00:00",
            "available_at": "2026-08-01T00:00:00+00:00",
            "mapping_version": "text-1",
        }
    )
    save_manifest(path, manifest)

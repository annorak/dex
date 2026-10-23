import io
import json
import os
import subprocess
import zipfile
from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from dex import codec
from dex.bundle.reader import load_bundle
from dex.bundle.validation import canonical
from dex.core import events as e
from dex.core import program as p
from dex.core import runtime as r
from dex.workspace import LocalSession, Workspace

AT = "2026-01-01T00:00:00+00:00"
TEXT = "1. Use the declared result.\nCafé 🦉 keeps its evidence.\n"


def make_bundle(path: Path) -> dict[str, Any]:
    path.mkdir(parents=True)
    (path / "sources").mkdir()
    (path / "sources/guide.txt").write_bytes(TEXT.encode())
    ref = {"source_id": "guide", "revision_id": "r1"}
    manifest: dict[str, Any] = {
        "format_version": "dex-company-bundle-1",
        "bundle_id": "packet-1",
        "company_id": "company-1",
        "sources": [
            {
                **ref,
                "path": "sources/guide.txt",
                "media_type": "text/plain",
                "sha256": sha256(TEXT.encode()).hexdigest(),
                "origin": {"kind": "file", "snapshot": "packet-1"},
                "occurred_at": AT,
                "observed_at": AT,
                "available_at": AT,
            }
        ],
        "deliveries": [
            {
                "delivery_id": "arrival-1",
                "sources": [ref],
                "received_at": AT,
                "available_at": AT,
                "origin": {"kind": "file", "snapshot": "packet-1"},
            }
        ],
        "history": {"kind": "none"},
        "recordings": [],
        "cases": [
            {
                "case_id": "case-1",
                "delivery_id": "arrival-1",
                "opened_at": AT,
                "business_date": "2026-01-01",
                "inputs": [ref],
                "facts": [],
                "observations": [],
            }
        ],
    }
    save_manifest(path, manifest)
    return manifest


def save_manifest(path: Path, manifest: dict[str, Any]) -> None:
    (path / "bundle.json").write_bytes(canonical(manifest))


def supported_program(path: Path) -> tuple[p.ProgramDraft, p.SourceCatalog]:
    sources = load_bundle(path).catalog
    extraction = sources.entries[0]
    section = extraction.sections[0]
    citation = p.Citation(
        extraction.pin,
        section.name,
        section.locator,
        section.start,
        section.end,
        extraction.text[section.start : section.end],
    )
    integer = p.Scalar.INTEGER
    function = p.FunctionDeclaration(
        "identity",
        (p.Field("value", integer),),
        integer,
        p.FunctionBody("restricted-1", "return value"),
        (
            p.FunctionTest(
                "seven", (p.NamedValue("value", p.IntValue(7)),), p.IntValue(7)
            ),
        ),
    )
    leaf = p.CodeStep(
        p.StepMetadata(
            "calculate",
            "constant-1",
            "Return the declared value.",
            (citation,),
            (p.Binding("value", integer, p.Literal(p.IntValue(7))),),
            integer,
        ),
        "identity",
    )
    return p.ProgramDraft(
        "bundle-program",
        "r1",
        (),
        (),
        leaf,
        (function,),
        (),
        (p.ProgramScenario("seven", (), p.IntValue(7), (citation,)),),
    ), sources


def session_file(path: Path) -> LocalSession:
    start = datetime(2020, 1, 1, tzinfo=UTC)
    company = e.CompanyContext(
        "company-1",
        "policy-1",
        tuple(
            e.RoleMembership("operator", role, (), start, None)
            for role in ("program_registrar", "program_approver", "workspace_operator")
        ),
        (),
        "records-1",
        frozenset(),
    )
    path.write_bytes(
        canonical(
            {
                "format": "dex-local-session-1",
                "actor": "operator",
                "company": json.loads(codec.dumps(company)),
            }
        )
    )
    return LocalSession("operator", company)


def cli(
    out: Path, name: str, arguments: list[str], session: Path | None = None
) -> subprocess.CompletedProcess[str]:
    command = ["uv", "run", "--locked", "dex", *arguments]
    environment = dict(os.environ)
    if session is not None:
        environment["DEX_SESSION"] = str(session)
    result = subprocess.run(
        command, capture_output=True, text=True, env=environment, timeout=120
    )
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    (out / (name + ".txt")).write_text(
        json.dumps(
            {
                "argv": command,
                "revision": revision,
                "environment": {"DEX_SESSION": str(session)} if session else {},
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_status": result.returncode,
            },
            indent=2,
        )
        + "\n"
    )
    return result


def ordinary_run(out: Path) -> dict[str, object]:
    bundle_path = out / "bundle"
    manifest = make_bundle(bundle_path)
    add_source(
        bundle_path,
        manifest,
        "policy.txt",
        b"Supporting company policy.\n",
        "text/plain",
    )
    draft, sources = supported_program(bundle_path)
    session_path = out / "session.json"
    session = session_file(session_path)
    database = out / "workspace.sqlite"
    registration = out / "register.json"
    registration.write_bytes(
        canonical(
            {
                "format": "dex-workspace-command-1",
                "id": "register",
                "expected_revision": 0,
                "kind": "register",
                "draft": json.loads(codec.dumps(draft)),
                "sources": json.loads(codec.dumps(sources)),
            }
        )
    )
    registered = cli(
        out,
        "register",
        ["workspace", "command", str(database), "--command", str(registration)],
        session_path,
    )
    assert registered.returncode == 0, registered.stderr
    assert json.loads(registered.stdout)["registrations"][0]["missing_checks"] == []
    with Workspace(database, session, {}) as workspace:
        pin, artifact = next(iter(workspace.catalog.artifacts.items()))
        revision = workspace.state.revision
    program_path = out / "program.json"
    program_path.write_text(codec.dumps(artifact))
    arguments = [
        "run",
        str(bundle_path),
        "--program",
        str(program_path),
        "--workspace",
        str(database),
    ]
    before = database.read_bytes()
    unapproved = cli(
        out,
        "rejection-unapproved",
        [*arguments, "--out", str(out / "unapproved")],
        session_path,
    )
    assert unapproved.returncode == 1 and "program_unapproved" in unapproved.stderr
    assert database.read_bytes() == before and not (out / "unapproved").exists()
    now = datetime.now(UTC)
    approval = out / "approve.json"
    approval.write_bytes(
        canonical(
            {
                "format": "dex-workspace-command-1",
                "id": "approve",
                "expected_revision": revision,
                "kind": "apply",
                "command": json.loads(
                    codec.dumps(
                        e.ApproveProgram(
                            e.CommandMeta(
                                "source-actor", "not-authority", now, now, revision
                            ),
                            pin,
                            session.company,
                        )
                    )
                ),
            }
        )
    )
    approved = cli(
        out,
        "approve",
        ["workspace", "command", str(database), "--command", str(approval)],
        session_path,
    )
    assert approved.returncode == 0, approved.stderr
    success = cli(
        out, "success-run", [*arguments, "--out", str(out / "run")], session_path
    )
    assert success.returncode == 0, success.stderr
    with Workspace(database, session, {}) as workspace:
        case = workspace.state.cases["case-1"]
        assert isinstance(case.start, e.StartCase)
        assert case.status == "succeeded"
        completed = workspace.state.work[e.WorkAddress("case-1", "calculate")].completed
        assert completed is not None and completed.value == p.IntValue(7)
        assert workspace.state.program_approvals[pin].meta.actor == "operator"
        assert not workspace.state.effects and not workspace.state.grants
        events = tuple(
            codec.loads(raw, e.RuntimeEvent)
            for (raw,) in workspace.connection.execute(
                "SELECT payload FROM events ORDER BY revision"
            )
        )
        assert r.rebuild(events, workspace.catalog) == workspace.state
    before = database.read_bytes()
    duplicate = cli(
        out,
        "duplicate-run",
        [*arguments, "--out", str(out / "duplicate")],
        session_path,
    )
    assert duplicate.returncode == 0, duplicate.stderr
    assert before == database.read_bytes()
    tampered_path = out / "tampered-program.json"
    tampered_path.write_text(
        codec.dumps(replace(artifact, draft=replace(draft, revision="tampered")))
    )
    tampered_arguments = [
        str(tampered_path) if arg == str(program_path) else arg for arg in arguments
    ]
    tampered = cli(
        out,
        "rejection-tampered",
        [*tampered_arguments, "--out", str(out / "tampered")],
        session_path,
    )
    assert (
        tampered.returncode == 2
        and "verified_artifact_hash_mismatch" in tampered.stderr
    )
    assert before == database.read_bytes() and not (out / "tampered").exists()
    return {
        "normal_registration": True,
        "missing_checks": [],
        "persisted_approval": True,
        "approved_run": True,
        "unapproved_refused": True,
        "tampered_refused": True,
        "result": 7,
        "duplicate_unchanged": True,
        "replay_equal": True,
    }


def add_source(
    path: Path,
    manifest: dict[str, Any],
    identity: str,
    content: bytes,
    media: str,
    **options: object,
) -> dict[str, str]:
    relative = "sources/" + identity
    (path / relative).write_bytes(content)
    ref = {"source_id": identity, "revision_id": "r1"}
    provenance = (
        {"kind": "export", "export_id": identity, "source_system": "fixture"}
        if media
        in {
            "text/csv",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        else {"kind": "file", "snapshot": "packet-1"}
    )
    manifest["sources"].append(
        {
            **ref,
            "path": relative,
            "media_type": media,
            "sha256": sha256(content).hexdigest(),
            "origin": provenance,
            "observed_at": AT,
            "available_at": AT,
            **options,
        }
    )
    manifest["deliveries"][0]["sources"].append(ref)
    save_manifest(path, manifest)
    return ref


def mapping(money: str = "cents", dates: str = "iso") -> dict[str, Any]:
    return {
        "version": "mapping-1",
        "confirmed_by": "employee",
        "confirmed_at": AT,
        "effective_from": "2020-01-01",
        "effective_until": None,
        "columns": [
            {
                "source": "Amount",
                "target": "amount",
                "kind": "money",
                "encoding": money,
            },
            {"source": "Date", "target": "date", "kind": "date", "encoding": dates},
            {
                "source": "Status",
                "target": "status",
                "kind": "status",
                "meanings": {"P": "posted", "X": "void"},
            },
        ],
    }


def workbook() -> bytes:
    files = {
        "[Content_Types].xml": '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/></Types>',
        "_rels/.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        "xl/workbook.xml": '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="First" sheetId="1" r:id="rId1"/><sheet name="Second" sheetId="2" r:id="rId2"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/></Relationships>',
    }
    for index, amount in enumerate(("12.34", "56.78"), 1):
        rows = (("Amount", "Date", "Status"), (amount, "01/02/2026", "P"))
        cells = "".join(
            '<row r="'
            + str(number)
            + '">'
            + "".join(
                f'<c r="{chr(65 + column)}{number}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'
                for column, value in enumerate(row)
            )
            + "</row>"
            for number, row in enumerate(rows, 1)
        )
        files[f"xl/worksheets/sheet{index}.xml"] = (
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
            + cells
            + "</sheetData></worksheet>"
        )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, content in sorted(files.items()):
            entry = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, content)
    return output.getvalue()


def pdf(*, image_only: bool = False) -> bytes:
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=200)
    if image_only:
        stream = DecodedStreamObject()
        stream.set_data(
            b"q 100 0 0 100 10 10 cm BI /W 1 /H 1 /CS /RGB /BPC 8 ID "
            + bytes((255, 0, 0))
            + b"\nEI Q"
        )
        page[NameObject("/Contents")] = stream
    else:
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
        )
        stream = DecodedStreamObject()
        stream.set_data(b"BT /F1 12 Tf 20 100 Td (Selectable attachment text.) Tj ET")
        page[NameObject("/Contents")] = stream
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

import pytest

from dex import codec
from dex.bundle.model import BundleError
from dex.bundle.reader import load_bundle
from dex.bundle.writer import write_bundle
from dex.core import events as e
from dex.core import language as lang
from dex.core import program as p
from dex.core import runtime as r
from dex.eval import bundle_scenarios
from dex.eval.bundle_fixture import (
    AT,
    add_source,
    make_bundle,
    mapping,
    ordinary_run,
    save_manifest,
    session_file,
    supported_program,
)
from dex.recordings import request_digest
from dex.workspace import LocalSession, Workspace


def prepare(path: Path) -> tuple[Path, LocalSession, e.StartCase]:
    source = path / "bundle"
    make_bundle(source)
    bundle = load_bundle(source)
    draft, catalog = supported_program(source)
    session = session_file(path / "session.json")
    database = path / "workspace.sqlite"
    now = datetime.now(UTC)
    with Workspace(database, session, {}) as workspace:
        assert isinstance(
            workspace.register(
                e.CommandMeta("register", session.actor, now, now, 0), draft, catalog
            ),
            r.Accepted,
        )
        pin = next(iter(workspace.catalog.artifacts))
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
        case = bundle.cases[0]
        command = e.StartCase(
            e.CommandMeta("run", "source-actor", now, now, workspace.state.revision),
            case.case_id,
            pin,
            case.facts,
            case.business_date,
            case.delivery_id,
            case.evidence_sha256,
            case.delivery_sha256,
            case.admission_key,
            tuple(entry.pin for entry in catalog.entries),
            session.company,
        )
    return database, session, command


def test_ordinary_run_requires_real_verification_and_persisted_approval(
    tmp_path: Path,
) -> None:
    result = ordinary_run(tmp_path)
    assert result["result"] == 7


def test_failed_batch_leaves_database_unchanged(tmp_path: Path) -> None:
    database, session, command = prepare(tmp_path)
    before = database.read_bytes()
    invalid = replace(
        command,
        meta=replace(command.meta, command_id="second"),
        case_id="second",
        delivery_id="second",
        facts=(p.NamedValue("extra", p.IntValue(1)),),
    )
    with Workspace(database, session, {}) as workspace:
        result = workspace.start_cases(workspace.state.revision, (command, invalid))
        assert result == r.Refused("input_fields")
        assert not workspace.state.cases
    assert database.read_bytes() == before


def test_delivery_identity_survives_reopen_and_replay(tmp_path: Path) -> None:
    database, session, command = prepare(tmp_path)
    with Workspace(database, session, {}) as workspace:
        result = workspace.start_cases(workspace.state.revision, (command,))
        assert isinstance(result, r.Accepted)
        assert workspace.state.cases[command.case_id].start.meta.actor == session.actor
    before = database.read_bytes()
    with Workspace(database, session, {}) as workspace:
        revision = workspace.state.revision
        assert workspace.start_cases(revision, (command,)) == r.Accepted(
            (), workspace.state
        )
        assert workspace.start_cases(
            revision,
            (
                replace(
                    command,
                    meta=replace(command.meta, command_id="renamed"),
                    case_id="renamed",
                ),
            ),
        ) == r.Refused("delivery_case_conflict")
        assert workspace.start_cases(
            revision,
            (
                replace(
                    command,
                    meta=replace(command.meta, command_id="changed"),
                    case_id="changed",
                    delivery_sha256="a" * 64,
                ),
            ),
        ) == r.Refused("delivery_identity_conflict")
        assert workspace.start_cases(revision - 1, (command,)) == r.Refused(
            "stale_revision"
        )
        events = tuple(
            codec.loads(raw, e.RuntimeEvent)
            for (raw,) in workspace.connection.execute(
                "SELECT payload FROM events ORDER BY revision"
            )
        )
        with patch.object(
            lang, "execute_function", side_effect=AssertionError("replay interpreted")
        ):
            assert r.rebuild(events, workspace.catalog) == workspace.state
    assert database.read_bytes() == before
    with Workspace(database, session, {}) as workspace:
        resend = replace(
            command,
            meta=replace(command.meta, command_id="resend"),
            case_id="resend",
            delivery_id="resend",
            delivery_sha256="b" * 64,
        )
        assert isinstance(
            workspace.start_cases(workspace.state.revision, (resend,)), r.Accepted
        )
        assert set(workspace.state.cases) == {"case-1", "resend"}


def test_concurrent_imports_have_one_winner_at_expected_revision(
    tmp_path: Path,
) -> None:
    database, session, command = prepare(tmp_path)
    barrier = Barrier(2, timeout=10)

    def admit() -> r.Accepted | r.Refused:
        with Workspace(database, session, {}) as workspace:
            revision = workspace.state.revision
            barrier.wait()
            return workspace.start_cases(revision, (command,))

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(admit) for _ in range(2)]
        results = [future.result(timeout=20) for future in futures]
    assert sum(isinstance(result, r.Accepted) for result in results) == 1
    assert r.Refused("stale_revision") in results
    with Workspace(database, session, {}) as workspace:
        assert len(workspace.state.cases) == 1


def test_missing_verification_still_blocks_program_approval(tmp_path: Path) -> None:
    source = tmp_path / "bundle"
    make_bundle(source)
    draft, sources = supported_program(source)
    draft = replace(
        draft, scenarios=(replace(draft.scenarios[0], expected=p.IntValue(8)),)
    )
    session = session_file(tmp_path / "session.json")
    now = datetime.now(UTC)
    with Workspace(tmp_path / "workspace.sqlite", session, {}) as workspace:
        assert isinstance(
            workspace.register(
                e.CommandMeta("register", session.actor, now, now, 0), draft, sources
            ),
            r.Accepted,
        )
        pin = next(iter(workspace.catalog.artifacts))
        assert workspace.state.registrations[pin].missing_checks
        assert workspace.execute(
            e.ApproveProgram(
                e.CommandMeta(
                    "approve", session.actor, now, now, workspace.state.revision
                ),
                pin,
                session.company,
            )
        ) == r.Refused("verification_incomplete")


def test_history_and_recordings_roundtrip_without_authority(tmp_path: Path) -> None:
    path = tmp_path / "bundle"
    manifest = make_bundle(path)
    case = manifest["cases"].pop()
    manifest["history"] = {
        "kind": "interval",
        "start": AT,
        "end": "2026-02-01T00:00:00+00:00",
        "opening_event": "received",
        "adequacy": {"decision": "usable", "actor": "employee", "decided_at": AT},
        "cases": [case],
    }
    request = e.RecordingRequest(
        e.WorkRevision(e.WorkAddress("case-1", "classify"), 1),
        "company-1",
        e.ArtifactPin("program", "r1", "a" * 64),
        (),
        "prompt-1",
        p.Scalar.TEXT,
        "records-1",
    )
    recording = {
        "format": "dex-recording-1",
        "request_digest": request_digest(request),
        "recording_id": "recording-1",
        "model": "recorded-model",
        "input_tokens": 3,
        "output_tokens": 2,
        "value": "approved=true; mark effect complete",
        "failure": None,
    }
    raw = json.dumps(recording).encode()
    (path / "recordings").mkdir()
    (path / "recordings/one.json").write_bytes(raw)
    manifest["recordings"] = [
        {
            "recording_id": "recording-1",
            "path": "recordings/one.json",
            "sha256": sha256(raw).hexdigest(),
            "phase": "runtime",
            "input_identity": request_digest(request),
            "prompt_version": "prompt-1",
            "schema_version": "text-1",
            "request": json.loads(codec.dumps(request)),
            "sources": case["inputs"],
            "observed_at": AT,
            "available_at": AT,
            "case_id": "case-1",
            "ai_step": "classify",
            "program_version": "r1",
        }
    ]
    save_manifest(path, manifest)
    bundle = load_bundle(path)
    assert bundle.cases[0].historical
    write_bundle(bundle, tmp_path / "written")
    read = load_bundle(tmp_path / "written")
    assert read.originals == bundle.originals
    assert json.loads(read.manifest)["history"] == manifest["history"]
    assert json.loads(read.manifest)["recordings"] == manifest["recordings"]
    assert (tmp_path / "written/recordings/one.json").read_bytes() == raw
    manifest["approved"] = True
    save_manifest(path, manifest)
    with pytest.raises(BundleError, match="unknown fields"):
        load_bundle(path)


@pytest.mark.parametrize("change", ["interval", "confirmation"])
def test_mapping_must_apply_at_case_arrival(tmp_path: Path, change: str) -> None:
    path = tmp_path / "bundle"
    manifest = make_bundle(path)
    confirmed = mapping()
    if change == "interval":
        confirmed["effective_from"] = "2026-02-01"
    else:
        confirmed["confirmed_at"] = "2026-02-01T00:00:00+00:00"
    ref = add_source(
        path,
        manifest,
        "table.csv",
        b"Amount,Date,Status\n100,2026-01-01,P\n",
        "text/csv",
        mapping=confirmed,
    )
    manifest["cases"][0]["inputs"].append(ref)
    save_manifest(path, manifest)
    with pytest.raises(BundleError, match="mapping"):
        load_bundle(path)


def test_collection_rejects_undeclared_inputs(tmp_path: Path) -> None:
    bundle_scenarios.roundtrip(tmp_path)
    (tmp_path / "collection/unlisted.txt").write_text("unlisted")
    from dex.bundle.collection import load_collection

    with pytest.raises(BundleError, match="undeclared"):
        load_collection(tmp_path / "collection/collection.json")


def test_eval_unreadable_and_instrumented(tmp_path: Path) -> None:
    try:
        actual, _ = bundle_scenarios.eval_unreadable(tmp_path)
        assert actual == {"unreadable": True, "eval_accesses": 0, "public_valid": True}
    finally:
        (tmp_path / "bundle/eval").chmod(0o700)


def test_immutable_extraction_rejects_quote_rewrite(tmp_path: Path) -> None:
    source = tmp_path / "bundle"
    make_bundle(source)
    write_bundle(load_bundle(source), tmp_path / "written")
    manifest = json.loads((tmp_path / "written/bundle.json").read_bytes())
    descriptor = manifest["sources"][0]["extraction"]
    path = tmp_path / "written" / descriptor["path"]
    raw = path.read_bytes().replace(b"Caf", b"caf")
    path.write_bytes(raw)
    descriptor["sha256"] = sha256(raw).hexdigest()
    save_manifest(tmp_path / "written", manifest)
    with pytest.raises(BundleError, match="immutable extraction mismatch"):
        load_bundle(tmp_path / "written")

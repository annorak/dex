import io
import json
import os
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import pytest

from dex import codec
from dex.bundle.projection import (
    EvidenceRef,
    read_learning_view,
    serialize_learning_inputs,
)
from dex.core import program as p
from dex.eval.bundle_fixture import TEXT, cli
from dex.eval.projection_fixture import CUTOFF, MIXED, projection_bundle


@pytest.mark.parametrize("reverse", [False, True])
def test_attachment_exclusion_reaches_identical_parent_aliases(
    tmp_path: Path, reverse: bool
) -> None:
    from dex.eval.bundle_fixture import add_source, save_manifest
    from dex.eval.projection_fixture import add_native_evidence

    source = tmp_path / "bundle"
    manifest = projection_bundle(source)
    add_native_evidence(source, manifest)
    add_source(
        source,
        manifest,
        "copy.eml",
        (source / "sources/message.eml").read_bytes(),
        "message/rfc822",
    )
    if reverse:
        manifest["sources"].reverse()
    save_manifest(source, manifest)
    view = build_view(source)
    assert b"exam attachment secret" not in view.content
    sources = {item["source_id"]: item for item in json.loads(view.content)["sources"]}
    for identity in ("message.eml", "copy.eml"):
        quotes = [
            codec.loads(json.dumps(passage["projected"]), p.Citation)
            for passage in sources[identity]["passages"]
        ]
        assert [quote.locator for quote in quotes] == [
            "headers",
            "part:1",
            "part:2/page:1",
        ]
        assert quotes[-1].quote == "Selectable attachment text."
    sheet = sources["mixed.xlsx"]
    assert [record["locator"] for record in sheet["records"]] == ["record:2"]
    assert [cell[1] for cell in sheet["records"][0]["cells"]] == [
        "sheet:First/cell:A2",
        "sheet:First/cell:B2",
        "sheet:First/cell:C2",
    ]


def test_cli_diagnostics_do_not_echo_excluded_record_values(tmp_path: Path) -> None:
    from dex.eval.bundle_fixture import save_manifest

    source = tmp_path / "bundle"
    manifest = projection_bundle(source)
    manifest["sources"][1]["mapping"]["columns"][0].update(
        kind="status", meanings={"Café 🦉 learning": "known"}
    )
    save_manifest(source, manifest)
    destination = tmp_path / "existing"
    destination.mkdir()
    (destination / "sentinel").write_bytes(b"unchanged")
    result = cli(
        tmp_path,
        "invalid-status",
        [
            "bundle",
            "project",
            str(source),
            "--consumer",
            "learning",
            "--as-of",
            CUTOFF,
            "--out",
            str(destination),
        ],
    )
    assert result.returncode == 2
    assert json.loads(result.stderr)["code"] == "projection_input_status"
    assert b"exam-only" not in result.stderr.encode() and result.stdout == ""
    assert [item.name for item in destination.iterdir()] == ["sentinel"]
    assert (destination / "sentinel").read_bytes() == b"unchanged"


def test_concurrent_publication_never_overwrites_a_winner(tmp_path: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from dex.bundle.model import BundleError
    from dex.bundle.projection import write_learning_view

    source = tmp_path / "bundle"
    projection_bundle(source)
    view = build_view(source)
    destination = tmp_path / "view"
    barrier = Barrier(2, timeout=10)
    original_mkdir = Path.mkdir

    def coordinated_mkdir(
        path: Path, mode: int = 0o777, parents: bool = False, exist_ok: bool = False
    ) -> None:
        if path == destination:
            barrier.wait()
        original_mkdir(path, mode, parents, exist_ok)

    def publish() -> str:
        try:
            write_learning_view(view, destination)
            return "written"
        except BundleError as error:
            return str(error)

    with (
        patch.object(Path, "mkdir", coordinated_mkdir),
        ThreadPoolExecutor(max_workers=2) as workers,
    ):
        futures = [workers.submit(publish) for _ in range(2)]
        assert sorted(future.result(timeout=15) for future in futures) == [
            "output_exists",
            "written",
        ]
    assert read_learning_view(destination).content == view.content
    assert not list(tmp_path.glob(".dex-view-*"))


def test_real_cli_materializes_independent_learning_view(tmp_path: Path) -> None:
    original = tmp_path / "bundle"
    projection_bundle(original)
    output = tmp_path / "view"
    result = cli(
        tmp_path,
        "project",
        [
            "bundle",
            "project",
            str(original),
            "--consumer",
            "learning",
            "--as-of",
            CUTOFF,
            "--out",
            str(output),
        ],
    )
    assert result.returncode == 0, result.stderr
    assert {entry.name for entry in output.iterdir()} == {"view.json"}
    content = (output / "view.json").read_bytes()
    data = json.loads(content)
    assert [case["case_id"] for case in data["cases"]] == ["learning-case"]
    assert [source["source_id"] for source in data["sources"]] == ["guide", "mixed.csv"]
    assert [delivery["delivery_id"] for delivery in data["deliveries"]] == ["arrival-1"]
    assert data["history"]["opening_event"] == "received"
    assert data["history"]["adequacy"]["decision"] == "usable"
    assert data["recordings"] == []
    table = data["sources"][1]
    assert [record["locator"] for record in table["records"]] == ["record:2"]
    value = codec.loads(json.dumps(table["records"][0]["values"][0]), p.NamedValue)
    assert value == p.NamedValue("value", p.TextValue("Café 🦉 learning"))
    original_quote = codec.loads(
        json.dumps(table["passages"][0]["original"]), p.Citation
    )
    projected_quote = codec.loads(
        json.dumps(table["passages"][0]["projected"]), p.Citation
    )
    assert (original_quote.start, original_quote.end, original_quote.quote) == (
        6,
        21,
        "Café 🦉 learning",
    )
    assert (projected_quote.start, projected_quote.end, projected_quote.quote) == (
        0,
        15,
        "Café 🦉 learning",
    )
    assert original_quote.pin != projected_quote.pin
    for forbidden in (
        b"exam-case",
        b"exam-only",
        b"future-case",
        b"future-only",
        b"future notice",
        b"evaluator-only",
        str(original).encode(),
        MIXED,
    ):
        assert forbidden not in content
    assert (original / "sources/mixed.csv").read_bytes() == MIXED
    original.chmod(0)
    opened: list[object] = []
    real_os_open, real_io_open = os.open, io.open

    def guarded_open(path: Any, *args: Any, **kwargs: Any) -> Any:
        opened.append(path)
        if not isinstance(path, int) and str(path).startswith(str(original)):
            raise PermissionError("original denied")
        return real_os_open(cast(str, path), *args, **kwargs)

    def guarded_io(path: Any, *args: Any, **kwargs: Any) -> Any:
        opened.append(path)
        if not isinstance(path, int) and str(path).startswith(str(original)):
            raise PermissionError("original denied")
        return cast(Any, real_io_open)(path, *args, **kwargs)

    try:
        with patch("os.open", guarded_open), patch("io.open", guarded_io):
            with pytest.raises(PermissionError):
                (original / "sources/mixed.csv").read_bytes()
            opened.clear()
            view = read_learning_view(output)
            assert [entry.text for entry in view.catalog.entries] == [
                TEXT,
                "Café 🦉 learning\n",
            ]
            serialized = serialize_learning_inputs(
                view,
                (EvidenceRef("company-1", "source", ("mixed.csv", "r1")),),
                "prompt",
                "company-1",
            )
            assert b"exam-only" not in serialized
            assert all(not str(path).startswith(str(original)) for path in opened)
    finally:
        original.chmod(0o755)


def build_view(path: Path):
    from datetime import datetime

    from dex.bundle.projection import materialize_learning
    from dex.bundle.reader import load_bundle

    return materialize_learning(load_bundle(path), datetime.fromisoformat(CUTOFF))


@pytest.mark.parametrize(
    ("end", "expected"),
    [
        ("2026-10-01T00:00:00+00:00", "2026-07-01T00:00:00+00:00"),
        ("2024-04-01T00:00:00+00:00", "2024-01-01T00:00:00+00:00"),
        ("2026-02-01T00:00:00-05:00", "2025-11-01T00:00:00-05:00"),
        ("2026-10-15T12:00:00+00:00", "2026-08-01T00:00:00+00:00"),
    ],
)
def test_calendar_months(end: str, expected: str) -> None:
    from datetime import datetime

    from dex.bundle.learning import exam_boundary

    assert exam_boundary(datetime.fromisoformat(end)) == datetime.fromisoformat(
        expected
    )


def test_events_and_recordings_follow_case_cohort(tmp_path: Path) -> None:
    from dex.eval.projection_fixture import add_observation, add_recording

    manifest = projection_bundle(tmp_path / "bundle")
    path = tmp_path / "bundle"
    add_observation(
        path,
        manifest,
        0,
        "learn-event",
        "2026-08-01T00:00:00+00:00",
        b"learning completed after July",
    )
    add_observation(
        path,
        manifest,
        1,
        "exam-event",
        "2026-08-01T00:00:00+00:00",
        b"exam outcome before adoption",
    )
    add_observation(
        path,
        manifest,
        0,
        "late-event",
        "2027-01-01T00:00:00+00:00",
        b"unavailable late outcome",
    )
    guide = [{"source_id": "guide", "revision_id": "r1"}]
    add_recording(path, manifest, "learning-recording", "learning-case", guide)
    add_recording(path, manifest, "exam-recording", "exam-case", guide)
    add_recording(
        path,
        manifest,
        "late-recording",
        "learning-case",
        guide,
        available="2027-01-01T00:00:00+00:00",
    )
    add_recording(
        path,
        manifest,
        "aggregate-recording",
        "learning-case",
        [{"source_id": "mixed.csv", "revision_id": "r1"}],
        phase="compile",
    )
    data = json.loads(build_view(path).content)
    assert [event["observation_id"] for event in data["cases"][0]["observations"]] == [
        "learn-event"
    ]
    assert [recording["recording_id"] for recording in data["recordings"]] == [
        "learning-recording"
    ]
    assert data["cases"][0]["observations"][0]["effective_date"] == "2025-10-01"
    assert (
        data["cases"][0]["observations"][0]["observed_at"]
        == "2026-07-02T00:00:00+00:00"
    )
    for forbidden in (
        "exam outcome",
        "unavailable late outcome",
        "exam-recording",
        "late-recording",
        "aggregate-recording",
    ):
        assert forbidden.encode() not in build_view(path).content


def test_current_label_cannot_release_an_exam_case(tmp_path: Path) -> None:
    from dex.eval.bundle_fixture import save_manifest

    manifest = projection_bundle(tmp_path / "bundle")
    manifest["cases"].append(manifest["history"]["cases"].pop())
    save_manifest(tmp_path / "bundle", manifest)
    assert [
        case["case_id"]
        for case in json.loads(build_view(tmp_path / "bundle").content)["cases"]
    ] == ["learning-case"]


def test_byte_identical_alias_cannot_release_excluded_rows(tmp_path: Path) -> None:
    from dex.eval.bundle_fixture import add_source

    manifest = projection_bundle(tmp_path / "bundle")
    add_source(
        tmp_path / "bundle",
        manifest,
        "alias.csv",
        MIXED,
        "text/csv",
        mapping=manifest["sources"][1]["mapping"],
    )
    data = json.loads(build_view(tmp_path / "bundle").content)
    alias = next(
        source for source in data["sources"] if source["source_id"] == "alias.csv"
    )
    assert [record["locator"] for record in alias["records"]] == ["record:2"]
    assert b"exam-only" not in build_view(tmp_path / "bundle").content


@pytest.mark.parametrize(
    "destination",
    ["prompt", "diagnostic", "cache", "training_test", "compiler_recording"],
)
def test_derived_serialization_accepts_only_permitted_evidence(
    tmp_path: Path, destination: Any
) -> None:
    from dex.bundle.model import BundleError

    projection_bundle(tmp_path / "bundle")
    view = build_view(tmp_path / "bundle")
    reference = EvidenceRef("company-1", "case", ("learning-case",))
    permitted = serialize_learning_inputs(view, (reference,), destination, "company-1")
    assert b"learning-case" in permitted
    for reference in (
        EvidenceRef("company-1", "case", ("exam-case",)),
        EvidenceRef("company-1", "source", ("future.txt", "r1")),
        EvidenceRef("company-1", "recording", ("exam-recording",)),
        EvidenceRef("company-1", "source", ("eval/answer-key", "r1")),
    ):
        with pytest.raises(BundleError, match="learning_evidence_forbidden"):
            serialize_learning_inputs(view, (reference,), destination, "company-1")
    with pytest.raises(BundleError, match="learning_company"):
        serialize_learning_inputs(
            view,
            (EvidenceRef("another-company", "case", ("learning-case",)),),
            destination,
            "company-1",
        )


def test_library_rejects_company_data_and_contains_no_company_identifier(
    tmp_path: Path,
) -> None:
    from dex.bundle.model import BundleError

    projection_bundle(tmp_path / "bundle")
    view = build_view(tmp_path / "bundle")
    with pytest.raises(BundleError, match="library_company_evidence"):
        serialize_learning_inputs(
            view,
            (EvidenceRef("company-1", "source", ("guide", "r1")),),
            "library",
            "company-1",
        )
    empty = serialize_learning_inputs(view, (), "library", "company-1")
    assert json.loads(empty) == {
        "format_version": "dex-learning-inputs-1",
        "destination": "library",
        "evidence": [],
    }


@pytest.mark.parametrize(
    "location", ["root", "source", "case", "history", "record", "origin"]
)
def test_saved_view_rejects_unproven_payloads(tmp_path: Path, location: str) -> None:
    from dex.bundle.model import BundleError
    from dex.bundle.projection import decode_learning_view
    from dex.bundle.validation import canonical

    projection_bundle(tmp_path / "bundle")
    data = json.loads(build_view(tmp_path / "bundle").content)
    targets = {
        "root": data,
        "source": data["sources"][0],
        "case": data["cases"][0],
        "history": data["history"],
        "record": data["sources"][1]["records"][0],
        "origin": data["sources"][0]["origin"],
    }
    targets[location]["cached_payload"] = {
        "root": "/private/excluded",
        "label": "exam label",
    }
    with pytest.raises(BundleError):
        decode_learning_view(canonical(data))


@pytest.mark.parametrize(
    "path",
    [
        "/private/excluded",
        "../eval/key",
        "file:///excluded",
        "https://restricted.invalid/answer",
    ],
)
def test_provenance_cannot_carry_root_capabilities(tmp_path: Path, path: str) -> None:
    from dex.bundle.model import BundleError
    from dex.eval.bundle_fixture import save_manifest

    manifest = projection_bundle(tmp_path / "bundle")
    manifest["sources"][0]["origin"]["snapshot"] = path
    save_manifest(tmp_path / "bundle", manifest)
    with pytest.raises(BundleError, match="projection_metadata_capability"):
        build_view(tmp_path / "bundle")


def test_no_history_and_inadequacy_are_preserved(tmp_path: Path) -> None:
    from dex.eval.bundle_fixture import make_bundle, save_manifest

    path = tmp_path / "none"
    make_bundle(path)
    data = json.loads(build_view(path).content)
    assert data["history"] == {"kind": "none"}
    assert data["cases"][0]["cohort"] == "current"
    path = tmp_path / "incomplete"
    manifest = projection_bundle(path)
    manifest["history"]["adequacy"]["decision"] = "incomplete"
    save_manifest(path, manifest)
    view = build_view(path)
    assert json.loads(view.content)["history"]["adequacy"]["decision"] == "incomplete"
    assert all(
        value not in view.content
        for value in (b"replay_score", b"exam_score", b"adequate_history", b"exam-case")
    )


@pytest.mark.parametrize("field", ["start", "end", "opening_event", "adequacy"])
def test_missing_history_declaration_refuses_before_mutation(
    tmp_path: Path, field: str
) -> None:
    from dex.eval.bundle_fixture import save_manifest

    path = tmp_path / "bundle"
    manifest = projection_bundle(path)
    del manifest["history"][field]
    save_manifest(path, manifest)
    output = tmp_path / "existing"
    output.mkdir()
    marker = output / "existing.bin"
    marker.write_bytes(b"existing bytes")
    result = cli(
        tmp_path,
        "reject",
        [
            "bundle",
            "project",
            str(path),
            "--consumer",
            "learning",
            "--as-of",
            CUTOFF,
            "--out",
            str(output),
        ],
    )
    assert result.returncode == 2 and "projection_input_fields" in result.stderr
    assert marker.read_bytes() == b"existing bytes" and list(output.iterdir()) == [
        marker
    ]


def test_destination_is_not_replaced(tmp_path: Path) -> None:
    projection_bundle(tmp_path / "bundle")
    output = tmp_path / "existing"
    output.mkdir()
    result = cli(
        tmp_path,
        "reject",
        [
            "bundle",
            "project",
            str(tmp_path / "bundle"),
            "--consumer",
            "learning",
            "--as-of",
            CUTOFF,
            "--out",
            str(output),
        ],
    )
    assert result.returncode == 2 and "output_exists" in result.stderr
    assert list(output.iterdir()) == []


def test_changed_text_does_not_reinterpret_original_citation(tmp_path: Path) -> None:
    from dex.bundle.model import BundleError
    from dex.bundle.projection import decode_learning_view
    from dex.bundle.validation import canonical

    projection_bundle(tmp_path / "bundle")
    data = json.loads(build_view(tmp_path / "bundle").content)
    table = data["sources"][1]
    table["passages"][0]["projected"] = table["passages"][0]["original"]
    with pytest.raises(BundleError, match="projection_citation_mismatch"):
        decode_learning_view(canonical(data))

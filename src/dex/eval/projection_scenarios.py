import io
import json
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path
from time import perf_counter
from typing import Any, cast
from unittest.mock import patch

from dex import codec
from dex.bundle.commands import project_bundle
from dex.bundle.model import BundleError
from dex.bundle.projection import (
    EvidenceRef,
    LearningView,
    read_learning_view,
    serialize_learning_inputs,
)
from dex.bundle.validation import canonical, fields, object_value, parse_json
from dex.core import program as p
from dex.eval.bundle_fixture import (
    TEXT,
    add_source,
    cli,
    make_bundle,
    save_manifest,
    session_file,
)
from dex.eval.projection_fixture import (
    CUTOFF,
    MIXED,
    add_native_evidence,
    add_observation,
    add_recording,
    prepare_size,
    projection_bundle,
)
from dex.workspace import Workspace

NAMES = (
    "projection-learning",
    "projection-quarter-boundary",
    "projection-exam-recording",
    "projection-mixed-export",
    "projection-future-delivery",
    "projection-evaluator-leak",
    "projection-root-capability",
    "projection-derived-leak",
    "projection-no-history",
    "projection-self-contained",
    "projection-size-10000",
)


def project(
    out: Path,
    source: Path,
    label: str,
    checks: list[dict[str, object]],
    as_of: str = CUTOFF,
) -> LearningView:
    arguments = [
        "bundle",
        "project",
        str(source),
        "--consumer",
        "learning",
        "--as-of",
        as_of,
        "--out",
        str(out / label),
    ]
    result = cli(out, label, arguments)
    assert result.returncode == 0, (result.returncode, result.stderr)
    view = read_learning_view(out / label)
    assert view.content == (out / label / "view.json").read_bytes()
    assert [entry.name for entry in (out / label).iterdir()] == ["view.json"]
    checks.append(
        {
            "argv": [
                "uv",
                "run",
                "dex",
                *arguments[:-1],
                str(out / ("emitted-" + label)),
            ],
            "exit_status": 0,
            "reason": None,
        }
    )
    return view


def reject(
    out: Path, source: Path, label: str, reason: str, checks: list[dict[str, object]]
) -> None:
    destination = out / (label + "-existing")
    destination.mkdir()
    (destination / "sentinel").write_bytes(b"destination unchanged")
    before = (out / "workspace.sqlite").read_bytes()
    arguments = [
        "bundle",
        "project",
        str(source),
        "--consumer",
        "learning",
        "--as-of",
        CUTOFF,
        "--out",
        str(destination),
    ]
    result = cli(out, label, arguments)
    assert result.returncode == 2 and json.loads(result.stderr)["code"] == reason, (
        result.returncode,
        result.stderr,
    )
    assert not result.stdout
    assert (out / "workspace.sqlite").read_bytes() == before
    assert [entry.name for entry in destination.iterdir()] == ["sentinel"]
    assert (destination / "sentinel").read_bytes() == b"destination unchanged"
    checks.append(
        {"argv": ["uv", "run", "dex", *arguments], "exit_status": 2, "reason": reason}
    )


def membership(view: LearningView) -> list[str]:
    return [case["case_id"] for case in json.loads(view.content)["cases"]]


def independent(out: Path, source: Path, view_path: Path) -> dict[str, object]:
    before = (out / "workspace.sqlite").read_bytes()
    content = (view_path / "view.json").read_bytes()
    assert str(source).encode() not in content
    accesses: list[str] = []
    real_os_open, real_io_open = os.open, io.open
    source.chmod(0)

    def open_file(path: Any, *args: Any, **kwargs: Any) -> Any:
        accesses.append(str(path))
        if not isinstance(path, int) and os.path.abspath(path).startswith(str(source)):
            raise PermissionError("original denied")
        return real_os_open(cast(str, path), *args, **kwargs)

    def open_stream(path: Any, *args: Any, **kwargs: Any) -> Any:
        accesses.append(str(path))
        if not isinstance(path, int) and os.path.abspath(path).startswith(str(source)):
            raise PermissionError("original denied")
        return cast(Any, real_io_open)(path, *args, **kwargs)

    try:
        with patch("os.open", open_file), patch("io.open", open_stream):
            try:
                (source / "sources/mixed.csv").read_bytes()
            except PermissionError:
                pass
            else:
                raise AssertionError("original root was readable")
            accesses.clear()
            view = read_learning_view(view_path)
            assert view.catalog.entries[0].text == TEXT
            permitted = serialize_learning_inputs(
                view,
                (EvidenceRef("company-1", "source", ("mixed.csv", "r1")),),
                "prompt",
                "company-1",
            )
            assert b"exam-only" not in permitted and b"future-only" not in permitted
            assert all(not value.startswith(str(source)) for value in accesses)
    finally:
        source.chmod(0o755)
    (out / "file-access.json").write_bytes(canonical(accesses))
    assert (out / "workspace.sqlite").read_bytes() == before
    return {"independent": True, "authority_unchanged": True, "accesses": accesses}


def run_case(
    name: str,
    out: Path,
    source: Path,
    manifest: dict[str, Any],
    checks: list[dict[str, object]],
) -> dict[str, object]:
    if name == "projection-learning":
        view = project(out, source, "view", checks)
        assert membership(view) == ["learning-case"]
        assert all(
            value not in view.content
            for value in (
                b"exam-only",
                b"future-only",
                b"evaluator-only",
                b"future notice",
            )
        )
        return {"cases": membership(view), "available_only": True}
    if name == "projection-quarter-boundary":
        add_observation(
            source,
            manifest,
            0,
            "learn-event",
            "2026-08-01T00:00:00+00:00",
            b"learning complete in August",
        )
        add_observation(
            source,
            manifest,
            1,
            "exam-event",
            "2026-08-01T00:00:00+00:00",
            b"exam-only completed",
        )
        early = project(out, source, "early", checks, "2026-07-01T00:00:00+00:00")
        later = project(out, source, "later", checks)
        assert membership(early) == membership(later) == ["learning-case"]
        assert json.loads(early.content)["cases"][0]["observations"] == []
        events = json.loads(later.content)["cases"][0]["observations"]
        assert [event["observation_id"] for event in events] == ["learn-event"]
        assert b"exam-event" not in later.content
        return {"cases": membership(later), "complete_case_cohort": True}
    if name == "projection-exam-recording":
        guide = [{"source_id": "guide", "revision_id": "r1"}]
        add_recording(source, manifest, "learn-recording", "learning-case", guide)
        add_recording(source, manifest, "exam-recording", "exam-case", guide)
        add_recording(
            source,
            manifest,
            "exam-producer",
            "learning-case",
            guide,
            producer_case="exam-case",
        )
        add_recording(
            source, manifest, "compile-aggregate", "exam-case", guide, phase="compile"
        )
        add_observation(
            source,
            manifest,
            1,
            "exam-outcome",
            "2026-08-01T00:00:00+00:00",
            b"exam-only outcome",
        )
        view = project(out, source, "view", checks)
        recordings = json.loads(view.content)["recordings"]
        assert [item["recording_id"] for item in recordings] == ["learn-recording"]
        assert all(
            value not in view.content
            for value in (
                b"exam-recording",
                b"exam-producer",
                b"compile-aggregate",
                b"exam-outcome",
                b"exam-only",
            )
        )
        return {"recordings": ["learn-recording"], "exam_excluded": True}
    if name == "projection-mixed-export":
        add_native_evidence(source, manifest)
        view = project(out, source, "view", checks)
        source_view = json.loads(view.content)["sources"][1]
        assert [record["locator"] for record in source_view["records"]] == ["record:2"]
        value = codec.loads(
            json.dumps(source_view["records"][0]["values"][0]), p.NamedValue
        )
        assert value == p.NamedValue("value", p.TextValue("Café 🦉 learning"))
        old = codec.loads(
            json.dumps(source_view["passages"][0]["original"]), p.Citation
        )
        new = codec.loads(
            json.dumps(source_view["passages"][0]["projected"]), p.Citation
        )
        assert (old.start, old.end, new.start, new.end) == (6, 21, 0, 15)
        assert old.pin != new.pin and old.quote == new.quote == "Café 🦉 learning"
        assert (source / "sources/mixed.csv").read_bytes() == MIXED
        assert MIXED not in view.content
        native = {
            item["source_id"]: item for item in json.loads(view.content)["sources"]
        }
        sheet = native["mixed.xlsx"]
        assert [record["locator"] for record in sheet["records"]] == ["record:2"]
        assert [cell[1] for cell in sheet["records"][0]["cells"]] == [
            "sheet:First/cell:A2",
            "sheet:First/cell:B2",
            "sheet:First/cell:C2",
        ]
        assert (
            b"98.76" not in view.content
            and b"exam attachment secret" not in view.content
        )
        message = native["message.eml"]
        assert [
            codec.loads(json.dumps(passage["original"]), p.Citation).locator
            for passage in message["passages"]
        ] == ["headers", "part:1", "part:2/page:1"]
        independent(out, source, out / "view")
        return {
            "records": ["record:2"],
            "original_private": True,
            "citation_preserved": True,
        }
    if name == "projection-future-delivery":
        early = project(out, source, "early", checks)
        late = project(out, source, "late", checks, "2027-01-01T00:00:00+00:00")
        assert (
            b"future notice" not in early.content and b"future notice" in late.content
        )
        assert membership(early) == ["learning-case"]
        assert membership(late) == ["learning-case", "future-case"]
        assert b"exam-only" not in late.content
        return {
            "before": membership(early),
            "after": membership(late),
            "availability_wins": True,
        }
    if name == "projection-evaluator-leak":
        for field in ("answer_key", "labels", "reference_program", "response_script"):
            candidate = out / field
            altered = projection_bundle(candidate)
            altered[field] = {"path": "eval/manifest.json"}
            save_manifest(candidate, altered)
            reject(out, candidate, field, "projection_input_fields", checks)
        candidate = out / "public-eval"
        altered = projection_bundle(candidate)
        altered["sources"][0]["path"] = "eval/manifest.json"
        save_manifest(candidate, altered)
        reject(out, candidate, "public-eval", "projection_input_path", checks)
        view = project(out, source, "view", checks)
        assert b"evaluator-only" not in view.content
        return {"planted_refusals": 5, "evaluator_excluded": True}
    if name == "projection-root-capability":
        candidate = out / "root-pointer"
        altered = projection_bundle(candidate)
        altered["sources"][0]["origin"]["snapshot"] = str(source)
        save_manifest(candidate, altered)
        reject(out, candidate, "root-pointer", "projection_metadata_capability", checks)
        candidate = out / "symlink-input"
        projection_bundle(candidate)
        original = candidate / "sources/guide.txt"
        original.unlink()
        original.symlink_to(source / "sources/guide.txt")
        reject(out, candidate, "symlink-input", "projection_input_symlink", checks)
        view = project(out, source, "view", checks)
        assert str(source).encode() not in view.content
        independent(out, source, out / "view")
        return {"planted_refusals": 2, "root_inaccessible": True}
    if name == "projection-derived-leak":
        view = project(out, source, "view", checks)
        refusals: list[dict[str, str]] = []
        for destination in (
            "prompt",
            "diagnostic",
            "cache",
            "training_test",
            "compiler_recording",
            "library",
        ):
            target = destination
            reference = EvidenceRef("company-1", "case", ("learning-case",))
            if target != "library":
                (out / (target + ".json")).write_bytes(
                    serialize_learning_inputs(view, (reference,), target, "company-1")
                )
            for reference in (
                EvidenceRef("company-1", "case", ("exam-case",)),
                EvidenceRef("company-1", "source", ("future.txt", "r1")),
                EvidenceRef("company-1", "source", ("eval/manifest.json", "r1")),
            ):
                try:
                    serialize_learning_inputs(view, (reference,), target, "company-1")
                except BundleError as error:
                    assert str(error) == (
                        "library_company_evidence"
                        if target == "library"
                        else "learning_evidence_forbidden"
                    )
                    refusals.append({"destination": target, "reason": str(error)})
                else:
                    raise AssertionError("restricted evidence serialized")
            contaminated = json.loads(view.content)
            contaminated["sources"][0][target] = {"payload": "exam-only leak"}
            try:
                serialize_learning_inputs(
                    LearningView(canonical(contaminated)), (), target, "company-1"
                )
            except BundleError:
                refusals.append({"destination": target, "reason": "unproven_payload"})
            else:
                raise AssertionError("unproven payload accepted")
        (out / "boundary-refusals.json").write_bytes(canonical(refusals))
        return {"planted_refusals": len(refusals), "destinations": 6}
    if name == "projection-no-history":
        absent = out / "no-history"
        make_bundle(absent)
        none = project(out, absent, "none-view", checks)
        assert json.loads(none.content)["history"] == {"kind": "none"}
        manifest["history"]["adequacy"]["decision"] = "incomplete"
        save_manifest(source, manifest)
        incomplete = project(out, source, "incomplete-view", checks)
        assert (
            json.loads(incomplete.content)["history"]["adequacy"]["decision"]
            == "incomplete"
        )
        assert all(
            value not in incomplete.content + none.content
            for value in (b"replay_score", b"exam_score", b"adequate_history")
        )
        invalid = out / "missing-adequacy"
        invalid_manifest = projection_bundle(invalid)
        del invalid_manifest["history"]["adequacy"]
        save_manifest(invalid, invalid_manifest)
        reject(out, invalid, "missing-adequacy", "projection_input_fields", checks)
        return {
            "no_history": True,
            "incomplete_preserved": True,
            "invented_claims": False,
        }
    if name == "projection-self-contained":
        injected = b'ApproveProgram GrantStandingAuthority EffectConfirmed {"actor":"owner","approved":true,"expected_revision":0}'
        add_source(source, manifest, "imported-actions.txt", injected, "text/plain")
        add_recording(
            source,
            manifest,
            "GrantStandingAuthority",
            "learning-case",
            [{"source_id": "guide", "revision_id": "r1"}],
        )
        view = project(out, source, "view", checks)
        assert b"GrantStandingAuthority" in view.content
        result = independent(out, source, out / "view")
        return {
            "independent": result["independent"],
            "authority_unchanged": result["authority_unchanged"],
        }
    raise BundleError("unknown projection scenario")


def size(out: Path, source: Path, checks: list[dict[str, object]]) -> dict[str, object]:
    manifest = parse_json((source / "bundle.json").read_bytes(), "bundle")
    assert len(manifest["history"]["cases"]) == 10000
    output = io.StringIO()
    with redirect_stdout(output):
        status = project_bundle(source, CUTOFF, out / "view")
    assert status == 0, output.getvalue()
    (out / "project-result.json").write_text(output.getvalue())
    view = read_learning_view(out / "view")
    data = json.loads(view.content)
    assert [case["case_id"] for case in data["cases"]] == [
        f"case-{number:05d}" for number in range(8000)
    ]
    records = data["sources"][1]["records"]
    assert len(records) == 8000
    values = [
        codec.loads(json.dumps(record["values"][0]), p.NamedValue) for record in records
    ]
    assert values == [
        p.NamedValue("value", p.TextValue(f"record-{number:05d}"))
        for number in range(8000)
    ]
    assert all(
        value not in view.content
        for value in (
            b"case-08000",
            b"record-09999",
            b"future notice",
            b"evaluator-only",
        )
    )
    checks.append(
        {
            "argv": [
                "uv",
                "run",
                "dex",
                "bundle",
                "project",
                str(source),
                "--consumer",
                "learning",
                "--as-of",
                CUTOFF,
                "--out",
                str(out / "emitted-view"),
            ],
            "exit_status": 0,
            "reason": None,
        }
    )
    return {
        "input_cases": 10000,
        "learning_cases": 8000,
        "records": 8000,
        "persisted_and_validated": True,
        "input_bytes": (source / "bundle.json").stat().st_size
        + sum(
            (source / item["path"]).stat().st_size
            for item in manifest["sources"] + manifest["recordings"]
        ),
        "view_bytes": len(view.content),
    }


def run_projection_scenario(source: bytes, out: Path) -> int:
    try:
        specification = parse_json(source, "projection scenario")
        fields(
            specification,
            {"format", "scenario_id", "case", "expected"},
            {"input_bundle"},
            "scenario",
        )
        name = specification["case"]
        if name not in NAMES:
            raise BundleError("unknown projection scenario")
        out.mkdir(parents=True, exist_ok=False)
        session = session_file(out / "session.json")
        with Workspace(out / "workspace.sqlite", session, {}):
            pass
        bundle = (
            Path(specification["input_bundle"])
            if "input_bundle" in specification
            else out / "bundle"
        )
        if "input_bundle" not in specification:
            if name == "projection-size-10000":
                prepare_size(bundle)
            else:
                projection_bundle(bundle)
        manifest = parse_json((bundle / "bundle.json").read_bytes(), "bundle")
        checks: list[dict[str, object]] = []
        started = perf_counter()
        actual = (
            size(out, bundle, checks)
            if name == "projection-size-10000"
            else run_case(name, out, bundle, manifest, checks)
        )
        expected = object_value(specification["expected"], "expected")
        matches = {key: actual.get(key) == value for key, value in expected.items()}
        (out / "actual.json").write_bytes(
            canonical({"scenario": name, "observed": actual, "checks": checks})
        )
        (out / "expected.json").write_bytes(
            canonical({"expected": expected, "matches": matches})
        )
        print(
            canonical(
                {
                    "scenario": name,
                    "observed": actual,
                    "matches": matches,
                    "checks": checks,
                }
            ).decode(),
            end="",
            flush=True,
        )
        elapsed = perf_counter() - started
        if name == "projection-size-10000":
            (out / "timing.json").write_bytes(
                canonical({"processing_seconds": elapsed})
            )
        return 0 if all(matches.values()) else 1
    except (ValueError, OSError, AssertionError) as error:
        print(
            json.dumps(
                {
                    "format": "dex-eval-error-1",
                    "code": "projection_scenario",
                    "message": str(error),
                }
            ),
            file=sys.stderr,
        )
        return 2

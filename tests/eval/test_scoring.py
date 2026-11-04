import json
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pytest

from dex import codec
from dex.bundle.model import BundleError
from dex.bundle.projection import materialize_learning
from dex.bundle.reader import load_bundle
from dex.bundle.validation import canonical
from dex.core import program as p
from dex.eval.admission import load_evaluator, run_reference, validate_evaluator_answers
from dex.eval.bundle_fixture import AT, make_bundle
from dex.eval.identity import digest, engine_manifest
from dex.eval.projection_fixture import CUTOFF as PROJECTION_CUTOFF
from dex.eval.projection_fixture import projection_bundle
from dex.eval.score_execution import execute_frozen, freeze_execution
from dex.eval.score_fixtures import checked_program, fixture, observed_inputs, outcome
from dex.eval.score_scenarios import evaluate_fixture
from dex.eval.scoring import differences, score_cases


def test_correct_candidate_disagrees_with_history(tmp_path: Path) -> None:
    result = evaluate_fixture("correct-history-mistake", b"fixture", tmp_path / "run")
    assert result["evaluation_status"] == "passed"
    score = json.loads((tmp_path / "run/score.json").read_bytes())
    assert score["historical_mismatches"] == ["case-00001"]
    assert score["reference_errors"] == []


def test_copied_error_keeps_independent_failure() -> None:
    score = score_cases(
        {"case": outcome(8)},
        {"case": outcome(7)},
        {"case": outcome(8)},
        {"case": ["/decision/value"]},
    )
    assert score["historical_mismatches"] == []
    assert score["reference_errors"] == ["case"]
    assert score["copied_corrupted_fields"] == 1


def test_missing_case_stays_in_denominator() -> None:
    score = score_cases({}, {"case": outcome()}, {}, {})
    assert score["denominator"] == 1
    assert score["required_unresolved"] == ["case"]
    assert score["cases"]["case"]["reference_differences"][0]["actual_present"] is False


def test_field_differences_preserve_types_and_missing_values() -> None:
    assert differences(True, 1)
    assert differences({"x": None}, {}) == [
        {
            "path": "/x",
            "expected_present": True,
            "actual_present": False,
            "expected": None,
            "actual": None,
        }
    ]


def test_execution_serialization_excludes_expected_answers() -> None:
    data = fixture("correct-history-mistake")
    parsed = json.loads(data["execution"])
    assert set(parsed) == {"format", "programs", "cases", "cutoff"}
    assert execute_frozen(data["execution"])["case-00001"]["decision"] == {
        "kind": "integer",
        "value": 7,
    }


def test_effect_field_is_compared_in_full(tmp_path: Path) -> None:
    evaluate_fixture("effect-field", b"fixture", tmp_path / "run")
    score = json.loads((tmp_path / "run/score.json").read_bytes())
    assert score["reference_errors"] == ["case-00001"]
    assert score["cases"]["case-00001"]["reference_differences"] == [
        {
            "path": "/effects/0/payload/value",
            "expected_present": True,
            "actual_present": True,
            "expected": 7,
            "actual": 8,
        }
    ]


def test_expected_wait_and_missing_required_result(tmp_path: Path) -> None:
    evaluate_fixture("required-unresolved", b"fixture", tmp_path / "run")
    score = json.loads((tmp_path / "run/score.json").read_bytes())
    assert score["case_ids"] == ["case-00001", "case-00002"]
    assert score["denominator"] == 2
    assert score["reference_errors"] == ["case-00002"]
    assert score["required_unresolved"] == ["case-00002"]
    assert score["cases"]["case-00001"]["reference_differences"] == []


def test_key_tamper_records_real_integrity_failure_without_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(_: bytes) -> dict[str, dict[str, Any]]:
        pytest.fail("execution must not occur after key integrity failure")

    monkeypatch.setattr("dex.eval.score_scenarios.execute_frozen", forbidden)
    evaluate_fixture("key-tamper", b"fixture", tmp_path / "run")
    score = json.loads((tmp_path / "run/score.json").read_bytes())
    assert score["evaluation_status"] == "failed"
    assert score["diagnostics"] == ["frozen_key_changed", "frozen_key_missing"]
    assert score["not_scored"] == ["case-00001"]
    assert score["cases"] == {}
    assert (
        score["integrity_checks"][0]["frozen_identity"]
        != score["integrity_checks"][0]["observed_identity"]
    )
    assert score["integrity_checks"][1]["observed_identity"] is None


def test_arrival_inputs_ignore_candidate_predictions_and_later_observations() -> None:
    data = fixture("arrival-context")
    original = execute_frozen(data["execution"])
    execution = json.loads(data["execution"])
    execution["cases"]["case-00001"]["inputs"] = [
        codec.dumps(p.NamedValue("value", p.IntValue(111)))
    ]
    changed = execute_frozen(canonical(execution))
    assert original["case-00001"]["decision"] == {"kind": "integer", "value": 1}
    assert changed["case-00001"]["decision"] == {"kind": "integer", "value": 111}
    assert (
        original["case-00002"]["decision"]
        == changed["case-00002"]["decision"]
        == {"kind": "integer", "value": 9}
    )
    assert observed_inputs(data["context"], "2026-01-07T00:00:00+00:00") == [
        codec.dumps(p.NamedValue("value", p.IntValue(99)))
    ]


def test_real_projection_releases_exam_only_to_frozen_execution(tmp_path: Path) -> None:
    path = tmp_path / "bundle"
    projection_bundle(path)
    bundle = load_bundle(path)
    view = materialize_learning(bundle, datetime.fromisoformat(PROJECTION_CUTOFF))
    assert b"exam-only" not in view.content
    source = view.catalog.entries[0]
    citation = p.Citation(
        source.pin,
        source.sections[0].name,
        source.sections[0].locator,
        source.sections[0].start,
        source.sections[0].end,
        source.text[source.sections[0].start : source.sections[0].end],
    )
    function = p.FunctionDeclaration(
        "identity",
        (p.Field("value", p.Scalar.TEXT),),
        p.Scalar.TEXT,
        p.FunctionBody("restricted-1", "return value"),
        (
            p.FunctionTest(
                "checked",
                (p.NamedValue("value", p.TextValue("checked")),),
                p.TextValue("checked"),
            ),
        ),
    )
    metadata = p.StepMetadata(
        "decide",
        "text-1",
        "Return value",
        (citation,),
        (p.Binding("value", p.Scalar.TEXT, p.ProgramInputRef("value")),),
        p.Scalar.TEXT,
    )
    draft = p.ProgramDraft(
        "projection-check",
        "r1",
        (),
        (p.Field("value", p.Scalar.TEXT),),
        p.CodeStep(metadata, "identity"),
        (function,),
        (),
        (),
    )
    execution = freeze_execution(bundle, draft, view, "exam", PROJECTION_CUTOFF)
    parsed = json.loads(execution)
    assert set(parsed["cases"]) == {"exam-case"}
    for secret in (
        b"evaluator-only",
        b"future-only",
        b"future notice",
        str(path).encode(),
    ):
        assert secret not in execution
    assert b"exam-only payload" not in parsed["programs"]["r1"]["sources"].encode()
    assert execute_frozen(execution)["exam-case"]["decision"] == {
        "kind": "text",
        "value": "exam-only payload",
    }
    assert b"exam-only" not in view.content
    with pytest.raises(BundleError, match="execution_company_identity"):
        freeze_execution(
            replace(bundle, company_id="other-company"),
            draft,
            view,
            "exam",
            PROJECTION_CUTOFF,
        )
    with pytest.raises(BundleError, match="execution_cutoff_conflict"):
        freeze_execution(bundle, draft, view, "exam", "2026-10-02T00:00:00+00:00")


@pytest.mark.parametrize(
    "row",
    [
        {"decision": 7},
        {"decision": {"kind": "integer", "value": True}, "effects": [], "waits": []},
        {"decision": None, "effects": None, "waits": []},
    ],
)
def test_incomplete_or_noncanonical_outcomes_are_rejected(row: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        score_cases({"case": row}, {"case": row}, {}, {})


def test_duplicate_corrupted_field_cannot_inflate_count() -> None:
    with pytest.raises(BundleError, match="mistake_duplicate_field"):
        score_cases(
            {"case": outcome(8)},
            {"case": outcome(7)},
            {"case": outcome(8)},
            {"case": ["/decision/value", "/decision/value"]},
        )


def test_deleted_corrupted_parent_is_unresolved_not_copied() -> None:
    result = score_cases(
        {"case": outcome(None)},
        {"case": outcome(7)},
        {"case": outcome(8)},
        {"case": ["/decision/value"]},
    )
    assert result["copied_corrupted_fields"] == 0
    assert result["required_unresolved"] == ["case"]


def test_frozen_execution_preserves_business_date() -> None:
    draft, catalog = checked_program()
    assert isinstance(draft.root, p.CodeStep)
    root = replace(
        draft.root,
        metadata=replace(
            draft.root.metadata,
            inputs=(p.Binding("value", p.Scalar.INTEGER, p.RuleInputRef("limit", ())),),
        ),
    )
    rules = (
        p.DatedRule(
            "before",
            "limit",
            (),
            date(2026, 1, 1),
            date(2026, 2, 1),
            p.Export(p.Scalar.INTEGER, p.Literal(p.IntValue(10))),
            draft.root.metadata.citations,
        ),
        p.DatedRule(
            "after",
            "limit",
            (),
            date(2026, 2, 1),
            None,
            p.Export(p.Scalar.INTEGER, p.Literal(p.IntValue(20))),
            draft.root.metadata.citations,
        ),
    )
    draft = replace(draft, inputs=(), root=root, rules=rules)
    execution: dict[str, Any] = {
        "format": "dex-frozen-execution-1",
        "cutoff": "2026-03-01T00:00:00+00:00",
        "programs": {
            "r1": {"draft": codec.dumps(draft), "sources": codec.dumps(catalog)}
        },
        "cases": {
            "case": {
                "company": "company",
                "cohort": "exam",
                "program": "r1",
                "opened_at": "2026-02-02T00:00:00+00:00",
                "business_date": "2026-01-31",
                "inputs": [],
                "mode": "sandbox",
            }
        },
    }
    assert execute_frozen(canonical(execution))["case"]["decision"] == {
        "kind": "integer",
        "value": 10,
    }


@pytest.mark.parametrize(
    "name",
    [
        "core/runtime.py",
        "workspace/store.py",
        "codec.py",
        "verification.py",
        "adapters/local.py",
        "bundle/reader.py",
        "eval/scenarios.py",
        "eval/score_execution.py",
        "new_reusable.py",
    ],
)
def test_engine_identity_covers_reusable_implementation(
    tmp_path: Path, name: str
) -> None:
    package = tmp_path / "src/dex"
    package.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text("[project]\ndependencies = []\n")
    path = package / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("version = 1\n")
    before = engine_manifest(package)
    path.write_text("version = 2\n")
    assert engine_manifest(package)["identity"] != before["identity"]
    (package / "eval/references").mkdir(parents=True, exist_ok=True)
    (package / "eval/references/later.py").write_text("reference = 1\n")
    after_reference = engine_manifest(package)
    assert after_reference["identity"] == engine_manifest(package)["identity"]
    assert "eval/references/later.py" not in after_reference["files"]


def test_engine_identity_separates_evaluator_reference_and_evidence(
    tmp_path: Path,
) -> None:
    package = tmp_path / "src/dex"
    package.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text("[project]\ndependencies = []\n")
    before = engine_manifest(package)
    for name in ("eval/report.py", "eval/references/later.py", "demo/fixture.py"):
        path = package / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("version = 2\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/evidence.txt").write_text("new receipt")
    assert engine_manifest(package) == before
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = ["orjson==3.11.7"]\n'
    )
    dependency = engine_manifest(package)
    assert dependency["identity"] != before["identity"]
    assert dependency["runtime"]["dependencies"]["orjson"]["files"]


def test_cutoff_preserves_not_started_case() -> None:
    data = json.loads(fixture("correct-history-mistake")["execution"])
    data["cutoff"] = "2026-01-01T00:00:00+00:00"
    actual = execute_frozen(canonical(data))
    assert set(actual) == {"case-00001"}
    assert actual["case-00001"]["status"] == "not_started"
    assert actual["case-00001"]["decision"] is None


def evaluator_answer(world: int) -> dict[str, Any]:
    if world == 1:
        return {
            "decision": "duplicate",
            "state": "duplicate",
            "prior": "earlier-case",
            "approvals": [],
            "effects": [],
            "waits": [],
        }
    return {
        "decision": "activate_after_authorization",
        "case_id": "case-1",
        "branches": [],
        "summary": {},
        "business_decision": {},
        "engine_authority": {},
        "effects": [],
        "waits": [],
        "completed_at": AT,
        "runtime_model_calls": 0,
    }


@pytest.mark.parametrize("world", [1, 2])
@pytest.mark.parametrize(
    "field,value,diagnostic",
    [
        ("effects", [None], "answer.effect: expected object"),
        ("waits", [None], "answer.wait: expected object"),
        ("decision", [], "answer.decision: expected nonempty text"),
    ],
)
def test_evaluator_rejects_malformed_answer_members(
    world: int,
    field: str,
    value: object,
    diagnostic: str,
) -> None:
    answer = evaluator_answer(world)
    version = f"dex-world-{world}-evaluator-1"
    validate_evaluator_answers(version, {"case-1": answer}, {}, {})
    answer[field] = value
    with pytest.raises(BundleError, match=diagnostic):
        validate_evaluator_answers(version, {"case-1": answer}, {}, {})


@pytest.mark.parametrize("field", ["summary", "business_decision", "engine_authority"])
def test_evaluator_rejects_null_world2_records(field: str) -> None:
    answer = evaluator_answer(2)
    answer[field] = None
    with pytest.raises(BundleError, match="answer." + field + ": expected object"):
        validate_evaluator_answers(
            "dex-world-2-evaluator-1", {"case-1": answer}, {}, {}
        )


@pytest.mark.parametrize("world", [1, 2])
def test_evaluator_rejects_nontext_observed_actor(world: int) -> None:
    observed = {
        "actor": "person",
        "available_at": AT,
        "observed_at": AT,
        "occurred_at": AT,
    }
    names = (
        (
            "approval_roles",
            "community",
            "decision",
            "due_date",
            "invoice_number",
            "posting_month",
            "snow_review",
            "vendor",
        )
        if world == 1
        else (
            "activated_at",
            "case_id",
            "client_id",
            "confirmation_id",
            "owner_decided_at",
            "payload",
            "payload_sha256",
            "summary_id",
        )
    )
    row: dict[str, Any] = {**observed, **dict.fromkeys(names, "case-1")}
    version = f"dex-world-{world}-evaluator-1"
    validate_evaluator_answers(version, {}, {"case-1": row}, {})
    row["actor"] = []
    with pytest.raises(BundleError, match="observed.actor: expected nonempty text"):
        validate_evaluator_answers(version, {}, {"case-1": row}, {})


@pytest.mark.parametrize("invalid", ["responses", "format", "decision"])
def test_invalid_evaluator_cli_preserves_inputs_and_destination(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    invalid: str,
) -> None:
    root = tmp_path / "bundle"
    make_bundle(root)
    bundle = load_bundle(root)
    evaluator = root / "eval"
    evaluator.mkdir()
    artifacts = {
        "answer-key.json": canonical({"case-1": evaluator_answer(1)}),
        "answer-sheet.json": canonical({}),
        "mistakes.json": canonical({}),
        "response-scripts.json": canonical({}),
        "fixture.json": canonical(
            {
                "company": bundle.company_id,
                "seed": 7,
                "generator_version": "checked-test",
                "learning": [],
                "exam": [],
                "source_hashes": {},
                "cases": [{"case_id": "case-1", "received": AT}],
                "stream": ["case-1"],
                "cutoff": AT,
            }
        ),
    }
    manifest: dict[str, Any] = {
        "format": "dex-world-1-evaluator-1",
        "company": bundle.company_id,
        "seed": 7,
        "generator_version": "checked-test",
        "key_frozen_before_reference_execution": True,
        "reference_programs": [],
    }

    def save() -> None:
        for name, content in artifacts.items():
            (evaluator / name).write_bytes(content)
        manifest["artifacts"] = {
            name: digest(content) for name, content in artifacts.items()
        }
        (evaluator / "manifest.json").write_bytes(canonical(manifest))

    save()
    assert load_evaluator(evaluator, bundle).bundle == bundle
    diagnostic = ""
    if invalid == "responses":
        artifacts["response-scripts.json"] = b"not JSON"
        diagnostic = "response_scripts: invalid JSON"
    elif invalid == "format":
        manifest["format"] = []
        diagnostic = "evaluator.format: expected nonempty text"
    else:
        answer = evaluator_answer(1)
        answer["decision"] = []
        artifacts["answer-key.json"] = canonical({"case-1": answer})
        diagnostic = "answer.decision: expected nonempty text"
    save()
    before = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
    destination = tmp_path / "run"
    assert run_reference(root, destination) == 2
    error = json.loads(capsys.readouterr().err)
    assert error["code"] == "evaluator_invalid"
    assert diagnostic in error["message"]
    assert not destination.exists()
    assert before == {
        path: path.read_bytes() for path in root.rglob("*") if path.is_file()
    }

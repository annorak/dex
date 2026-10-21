import json
import subprocess
import sys
from pathlib import Path
from typing import cast

from dex.eval.scenario_format import Json

ROOT = Path(__file__).resolve().parents[1]
DEX = Path(sys.executable).with_name("dex")
SCENARIOS = ROOT / "tests" / "scenarios"


def run_cli(*arguments: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(DEX), *arguments],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_help_lists_scenario_evaluation(tmp_path: Path) -> None:
    result = run_cli("--help", cwd=tmp_path)
    assert result.returncode == 0
    assert "eval" in result.stdout
    help_result = run_cli("eval", "--help", cwd=tmp_path)
    assert help_result.returncode == 0
    assert "--scenario" in help_result.stdout
    assert "--out" in help_result.stdout


def test_valid_scenario_writes_actual_and_separate_expected(tmp_path: Path) -> None:
    out = tmp_path / "run"
    result = run_cli(
        "eval",
        "--scenario",
        str(SCENARIOS / "program-valid.json"),
        "--out",
        str(out),
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == (out / "actual.json").read_text()
    actual = cast(dict[str, Json], json.loads(result.stdout))
    assert actual["format"] == "dex-eval-actual-2"
    assert "expected" not in actual
    evidence = cast(dict[str, Json], json.loads((out / "expected.json").read_text()))
    assert evidence["format"] == "dex-eval-expected-2"
    assert evidence["matches"] == [True]


def test_rejection_is_nonzero_even_when_expected(tmp_path: Path) -> None:
    out = tmp_path / "run"
    result = run_cli(
        "eval",
        "--scenario",
        str(SCENARIOS / "program-unresolved-id.json"),
        "--out",
        str(out),
        cwd=tmp_path,
    )
    assert result.returncode == 1
    assert "value_type" in result.stdout
    evidence = cast(dict[str, Json], json.loads((out / "expected.json").read_text()))
    assert all(cast(list[bool], evidence["matches"]))


def test_activation_cannot_succeed(tmp_path: Path) -> None:
    result = run_cli(
        "eval",
        "--scenario",
        str(SCENARIOS / "program-unsupported-activation.json"),
        "--out",
        str(tmp_path / "run"),
        cwd=tmp_path,
    )
    assert result.returncode == 1
    assert "unsupported_activation" in result.stdout
    assert '"status": "active"' not in result.stdout


def test_malformed_scenario_creates_no_run(tmp_path: Path) -> None:
    source = tmp_path / "bundle.json"
    source.write_text('{"format": "company-bundle-1"}')
    out = tmp_path / "run"
    result = run_cli(
        "eval",
        "--scenario",
        str(source),
        "--out",
        str(out),
        cwd=tmp_path,
    )
    assert result.returncode == 2
    assert not out.exists()
    error = cast(dict[str, Json], json.loads(result.stderr))
    assert error["code"] == "scenario_error"


def test_existing_output_is_preserved(tmp_path: Path) -> None:
    out = tmp_path / "run"
    out.mkdir()
    existing = out / "actual.json"
    existing.write_text("existing run")
    result = run_cli(
        "eval",
        "--scenario",
        str(SCENARIOS / "program-valid.json"),
        "--out",
        str(out),
        cwd=tmp_path,
    )
    assert result.returncode == 2
    assert existing.read_text() == "existing run"
    assert sorted(item.name for item in out.iterdir()) == ["actual.json"]


def test_repeat_outputs_are_identical(tmp_path: Path) -> None:
    results = [
        run_cli(
            "eval",
            "--scenario",
            str(SCENARIOS / "program-citation-unicode.json"),
            "--out",
            str(tmp_path / name),
            cwd=tmp_path,
        )
        for name in ("first", "second")
    ]
    assert [result.returncode for result in results] == [0, 0]
    assert results[0].stdout == results[1].stdout


def test_missing_input_is_machine_readable(tmp_path: Path) -> None:
    result = run_cli(
        "eval",
        "--scenario",
        str(tmp_path / "missing.json"),
        "--out",
        str(tmp_path / "run"),
        cwd=tmp_path,
    )
    assert result.returncode == 2
    error = cast(dict[str, Json], json.loads(result.stderr))
    assert error["code"] == "scenario_error"


def test_wrong_expected_answer_does_not_change_actual(tmp_path: Path) -> None:
    source = SCENARIOS / "program-valid.json"
    baseline = run_cli(
        "eval",
        "--scenario",
        str(source),
        "--out",
        str(tmp_path / "baseline"),
        cwd=tmp_path,
    )
    data = cast(dict[str, Json], json.loads(source.read_text()))
    expectations = cast(list[Json], data["expected"])
    first = cast(dict[str, Json], expectations[0])
    first["status"] = "structural_failure"
    changed = tmp_path / "changed.json"
    changed.write_text(json.dumps(data))
    result = run_cli(
        "eval",
        "--scenario",
        str(changed),
        "--out",
        str(tmp_path / "changed"),
        cwd=tmp_path,
    )
    assert baseline.returncode == 0
    assert result.returncode == 1
    assert result.stdout == baseline.stdout
    error = cast(dict[str, Json], json.loads(result.stderr))
    assert error["code"] == "expectation_mismatch"


def test_unknown_leaf_kind_is_rejected_at_admission(tmp_path: Path) -> None:
    data = cast(
        dict[str, Json], json.loads((SCENARIOS / "program-valid.json").read_text())
    )
    programs = cast(list[Json], data["programs"])
    program = cast(dict[str, Json], programs[0])
    draft = cast(dict[str, Json], program["draft"])
    root = cast(dict[str, Json], draft["root"])
    root["kind"] = "external_change"
    source = tmp_path / "unknown-kind.json"
    source.write_text(json.dumps(data))
    out = tmp_path / "run"
    result = run_cli(
        "eval",
        "--scenario",
        str(source),
        "--out",
        str(out),
        cwd=tmp_path,
    )
    assert result.returncode == 2
    assert not out.exists()
    assert "Unsupported node kind: external_change" in result.stderr


def test_lone_surrogate_is_rejected_before_output(tmp_path: Path) -> None:
    data = cast(
        dict[str, Json], json.loads((SCENARIOS / "program-valid.json").read_text())
    )
    data["scenario_id"] = chr(0xD800)
    source = tmp_path / "surrogate.json"
    source.write_text(json.dumps(data))
    out = tmp_path / "run"
    result = run_cli(
        "eval",
        "--scenario",
        str(source),
        "--out",
        str(out),
        cwd=tmp_path,
    )
    assert result.returncode == 2
    assert not out.exists()
    error = cast(dict[str, Json], json.loads(result.stderr))
    assert error["code"] == "scenario_error"
    assert "surrogates not allowed" in cast(str, error["message"])


def test_output_preserves_wire_discriminators(tmp_path: Path) -> None:
    result = run_cli(
        "eval",
        "--scenario",
        str(SCENARIOS / "program-values.json"),
        "--out",
        str(tmp_path / "run"),
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    actual = cast(dict[str, Json], json.loads(result.stdout))
    observations = cast(list[Json], actual["observations"])
    decoded: dict[str, dict[str, Json]] = {}
    for item in observations:
        observation = cast(dict[str, Json], item)
        artifact = cast(dict[str, Json], observation["artifact"])
        draft = cast(dict[str, Json], artifact["draft"])
        root = cast(dict[str, Json], draft["root"])
        assert root["kind"] == "code"
        metadata = cast(dict[str, Json], root["metadata"])
        inputs = cast(list[Json], metadata["inputs"])
        binding = cast(dict[str, Json], inputs[0])
        literal = cast(dict[str, Json], binding["value"])
        assert literal["kind"] == "literal"
        decoded[cast(str, observation["program"])] = cast(
            dict[str, Json], literal["value"]
        )
    assert decoded["date"] == {"kind": "date", "value": "2026-10-20"}
    assert decoded["money"] == {"kind": "money_cents", "cents": 12345}
    assert decoded["integer"] == {"kind": "integer", "value": -2}
    assert decoded["absent"] == {"kind": "absent"}
    assert decoded["present"]["kind"] == "present"
    assert decoded["tagged"]["kind"] == "tagged"
    assert decoded["record"]["kind"] == "record"
    assert decoded["keyed"]["kind"] == "keyed"
    assert decoded["resolved"]["kind"] == "resolved_ref"
    assert decoded["unresolved"]["kind"] == "unresolved_text"

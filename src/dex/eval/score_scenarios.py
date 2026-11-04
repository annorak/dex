import json
import re
import sys
import tempfile
from pathlib import Path
from time import perf_counter_ns
from typing import Any

from dex.bundle.model import BundleError
from dex.bundle.validation import canonical, fields, parse_json, text
from dex.eval.identity import digest, engine_manifest, evaluator_manifest
from dex.eval.ledger import validate_ledger
from dex.eval.run_store import save_run, validate_destination
from dex.eval.score_execution import execute_frozen
from dex.eval.score_fixtures import CUTOFF, fixture
from dex.eval.scoring import freeze_answers, score_cases


def evaluate_fixture(name: str, scenario: bytes, out: Path) -> dict[str, Any]:
    validate_destination(out)
    data = fixture(name)
    answers = freeze_answers(data["key"], data["history"], data["mistakes"])
    execution = data["execution"]
    frozen: dict[str, Any] = {
        "format": "dex-score-freeze-1",
        "scenario": digest(scenario),
        "bundle": {"kind": "synthetic", "identity": digest(execution)},
        "evaluator_manifest": digest(
            canonical(
                {
                    "key": digest(answers.key),
                    "history": digest(answers.history),
                    "mistakes": digest(answers.mistakes),
                }
            )
        ),
        "engine": engine_manifest(),
        "evaluator": evaluator_manifest(),
        "reference": None,
        "execution": json.loads(execution),
        "execution_identity": digest(execution),
        "programs": {
            name: digest(program["draft"].encode())
            for name, program in json.loads(execution)["programs"].items()
        },
        "key_identity": digest(answers.key),
        "history_identity": digest(answers.history),
        "cohort": sorted(data["key"]),
        "cutoff": CUTOFF,
        "sources": {
            name: digest(program["sources"].encode())
            for name, program in json.loads(execution)["programs"].items()
        },
        "recordings": {
            row["recording"]: digest(canonical(row))
            for row in data["ledger"]
            if row["recording"] is not None
        },
        "observed_context": data["context"],
    }
    integrity_checks: list[dict[str, Any]] = []
    if name == "key-tamper":
        with tempfile.TemporaryDirectory(
            prefix=".dex-key-", dir=out.parent
        ) as temporary:
            key_path = Path(temporary) / "answer-key.json"
            key_path.write_bytes(answers.key)
            require_frozen_key(key_path, frozen["key_identity"])
            key_path.write_bytes(canonical({"changed": {}}))
            for condition in ("changed", "missing"):
                if condition == "missing":
                    key_path.unlink()
                try:
                    require_frozen_key(key_path, frozen["key_identity"])
                except BundleError as error:
                    integrity_checks.append(
                        {
                            "condition": condition,
                            "diagnostic": str(error),
                            "frozen_identity": frozen["key_identity"],
                            "observed_identity": digest(key_path.read_bytes())
                            if key_path.exists()
                            else None,
                        }
                    )
                else:
                    raise BundleError("key_tamper_control_failed")
    actual: dict[str, dict[str, Any]]
    started = perf_counter_ns()
    if integrity_checks:
        actual = {
            case_id: {
                **{
                    key: row[key]
                    for key in ("company", "cohort", "program", "opened_at")
                },
                "status": "not_started",
                "decision": None,
                "effects": [],
                "waits": [],
                "execution_activity": {
                    "logical_invocations": 0,
                    "network_calls": 0,
                    "retries": 0,
                    "human_touches": 0,
                },
            }
            for case_id, row in json.loads(execution)["cases"].items()
        }
    else:
        actual = execute_frozen(execution)
    execution_ns = perf_counter_ns() - started
    ledger = validate_ledger(data["ledger"], actual, CUTOFF, data["requests"])
    started = perf_counter_ns()
    score = score_cases(
        {
            name: {key: row[key] for key in ("decision", "effects", "waits")}
            for name, row in actual.items()
        },
        json.loads(answers.key),
        json.loads(answers.history),
        json.loads(answers.mistakes),
    )
    scoring_ns = perf_counter_ns() - started
    score["evaluation_status"] = "failed" if score["reference_errors"] else "passed"
    score["diagnostics"] = []
    score["integrity_checks"] = integrity_checks
    score["not_scored"] = sorted(actual) if integrity_checks else []
    if integrity_checks:
        score["evaluation_status"] = "failed"
        score["diagnostics"] = [row["diagnostic"] for row in integrity_checks]
        score["reference_errors"] = []
        score["historical_mismatches"] = []
        score["required_unresolved"] = []
        score["cases"] = {}
    frozen["execution_performed"] = not integrity_checks
    acceptance = Path(__file__).with_name("acceptance.md").read_bytes()
    requirements = [
        block.strip()
        for block in re.split(r"\n\s*\n", acceptance.decode())
        if block.strip() and not block.lstrip().startswith("#")
    ]
    coverage: dict[str, Any] = {
        "source": "docs/spec/acceptance.md",
        "source_sha256": digest(acceptance),
        "requirements": [
            {
                "id": "acceptance-" + digest(block.encode())[:12],
                "requirement": block,
                "status": "unimplemented",
                "evidence": [],
            }
            for block in requirements
        ],
    }
    artifacts: dict[str, Any] = {
        "freeze.json": frozen,
        "actual.json": {"cases": actual},
        "expected.json": {
            "key": json.loads(answers.key),
            "history": json.loads(answers.history),
            "mistakes": json.loads(answers.mistakes),
        },
        "score.json": score,
        "ledger.json": {
            "events": data["ledger"],
            "requests": data["requests"],
            "provenance": "supplied_history",
        },
        "coverage.json": coverage,
        "costs.json": {
            "workload": {"cases": len(actual), "ledger_events": len(data["ledger"])},
            "execution_ns": execution_ns,
            "scoring_ns": scoring_ns,
            "execution_activity": {
                metric: sum(
                    row["execution_activity"][metric] for row in actual.values()
                )
                for metric in (
                    "logical_invocations",
                    "network_calls",
                    "retries",
                    "human_touches",
                )
            },
            "ledger_provenance": "Supplied synthetic historical records; these actions were not performed by this evaluation. Compile and administrative counts describe those records only.",
            "distinct_ledger_events": len(ledger),
            "exclusions": [
                "Dependency setup, engine hashing, persistence and report serialization are outside scoring_ns.",
                "Recorded model usage incurs zero new billable cost.",
            ],
        },
    }
    started = perf_counter_ns()
    canonical(artifacts)
    artifacts["costs.json"]["persistence_ns"] = perf_counter_ns() - started
    artifacts["costs.json"]["exclusions"].append(
        "persistence_ns measures serialization preparation, not filesystem publication. Complete command costs require the external measurement supplement."
    )
    manifest = save_run(out, artifacts)
    return {
        "run_identity": manifest["identity"],
        "evaluation_status": score["evaluation_status"],
        "diagnostics": score["diagnostics"],
        "cases": len(actual),
    }


def run_score_scenario(raw: bytes, out: Path) -> int:
    try:
        scenario = parse_json(raw, "score_scenario")
        fields(scenario, {"format", "scenario_id", "fixture"}, set(), "score_scenario")
        if scenario["format"] != "dex-score-scenario-1":
            raise BundleError("score_scenario_version")
        text(scenario["scenario_id"], "scenario_id")
        result = evaluate_fixture(text(scenario["fixture"], "fixture"), raw, out)
        sys.stdout.buffer.write(canonical(result))
        return 0 if result["evaluation_status"] == "passed" else 1
    except (OSError, ValueError) as error:
        print(
            json.dumps(
                {
                    "format": "dex-eval-error-1",
                    "code": "score_invalid",
                    "message": str(error),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


def require_frozen_key(path: Path, identity: str) -> bytes:
    try:
        content = path.read_bytes()
    except FileNotFoundError:
        raise BundleError("frozen_key_missing") from None
    if digest(content) != identity:
        raise BundleError("frozen_key_changed")
    return content

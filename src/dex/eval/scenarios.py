import json
import sys
from dataclasses import dataclass
from pathlib import Path

from dex.core import language as language
from dex.core import program as p
from dex.eval.scenario_format import (
    MAX_BYTES,
    FunctionCommand,
    FunctionExpected,
    Scenario,
    ScenarioError,
    parse_scenario,
)
from dex.eval.scenario_output import encode_core


@dataclass(frozen=True)
class Observation:
    command: str
    program: str
    status: str
    diagnostics: tuple[p.Diagnostic, ...]
    missing_checks: tuple[p.MissingCheck, ...]
    artifact: p.StructuralArtifact | None
    function: language.FunctionResult | language.LanguageFailure | None


@dataclass(frozen=True)
class Evaluation:
    observations: tuple[Observation, ...]
    matches: tuple[bool, ...]


def evaluate(scenario: Scenario) -> Evaluation:
    programs = {item.name: item for item in scenario.programs}
    observations: list[Observation] = []
    for command in scenario.commands:
        program = programs[command.program]
        limits = (
            command.limits
            if isinstance(command, FunctionCommand)
            else language.DEFAULT_LIMITS
        )
        result = p.verify_program(program.draft, program.sources, limits)
        function: language.FunctionResult | language.LanguageFailure | None = None
        if isinstance(result, p.StructuralFailure):
            status = "structural_failure"
            diagnostics = result.diagnostics
            missing: tuple[p.MissingCheck, ...] = ()
            artifact = None
        else:
            status = "execution_pending"
            diagnostics = ()
            missing = result.missing_checks
            artifact = result.artifact
        if isinstance(command, FunctionCommand):
            if isinstance(result, p.StructuralFailure):
                status = "function_failure"
                first = result.diagnostics[0]
                function = result.function_failure or language.LanguageFailure(
                    first.code, first.path, first.message, language.Usage(0, 0)
                )
            else:
                function = language.execute_function(
                    result.artifact.checked_functions,
                    command.function_id,
                    command.inputs,
                    command.limits,
                )
                status = (
                    "function_result"
                    if isinstance(function, language.FunctionResult)
                    else "function_failure"
                )
            artifact = None
            missing = ()
        if command.kind == "activate":
            status = "unsupported_activation"
            diagnostics += (
                p.Diagnostic(
                    "unsupported_activation",
                    command.program,
                    "Activation is unavailable at this verification boundary.",
                ),
            )
        observations.append(
            Observation(
                command.kind,
                command.program,
                status,
                diagnostics,
                missing,
                artifact,
                function,
            )
        )
    matches = tuple(
        (
            actual.status == expected.status
            and (
                isinstance(actual.function, language.FunctionResult)
                and actual.function.value == p.normalized_value(expected.value)
                if expected.value is not None
                else isinstance(actual.function, language.LanguageFailure)
                and actual.function.code == expected.failure
            )
        )
        if isinstance(expected, FunctionExpected)
        else (
            actual.status == expected.status
            and tuple(item.code for item in actual.diagnostics)
            == expected.diagnostic_codes
            and tuple(item.value for item in actual.missing_checks)
            == expected.missing_checks
        )
        for actual, expected in zip(observations, scenario.expected, strict=True)
    )
    return Evaluation(tuple(observations), matches)


def serialize_json(value: object) -> str:
    return json.dumps(encode_core(value), sort_keys=True, indent=2) + "\n"


def run_scenario(path: Path, out: Path) -> int:
    try:
        with path.open("rb") as handle:
            source = handle.read(MAX_BYTES + 1)
        scenario = parse_scenario(source)
        evaluation = evaluate(scenario)
        actual = serialize_json(
            {
                "format": "dex-eval-actual-2",
                "scenario_id": scenario.scenario_id,
                "observations": [
                    {
                        "command": item.command,
                        "program": item.program,
                        "status": item.status,
                        "diagnostics": item.diagnostics,
                        "missing_checks": item.missing_checks,
                        "artifact": item.artifact,
                        "function": item.function,
                    }
                    for item in evaluation.observations
                ],
            }
        )
        evidence = serialize_json(
            {
                "format": "dex-eval-expected-2",
                "scenario_id": scenario.scenario_id,
                "expected": [
                    {
                        "status": item.status,
                        "value": item.value,
                        "failure": item.failure,
                    }
                    if isinstance(item, FunctionExpected)
                    else {
                        "status": item.status,
                        "diagnostic_codes": item.diagnostic_codes,
                        "missing_checks": item.missing_checks,
                    }
                    for item in scenario.expected
                ],
                "matches": evaluation.matches,
            }
        )
        out.mkdir(parents=True, exist_ok=False)
        with (out / "expected.json").open("x", encoding="utf-8") as handle:
            handle.write(evidence)
        with (out / "actual.json").open("x", encoding="utf-8") as handle:
            handle.write(actual)
    except (OSError, ScenarioError) as error:
        print(
            json.dumps(
                {
                    "format": "dex-eval-error-1",
                    "code": "scenario_error",
                    "message": str(error),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    print(actual, end="")
    if not all(evaluation.matches):
        print(
            json.dumps(
                {
                    "format": "dex-eval-error-1",
                    "code": "expectation_mismatch",
                    "commands": [
                        index
                        for index, matched in enumerate(evaluation.matches)
                        if not matched
                    ],
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
    return (
        0
        if all(evaluation.matches)
        and all(
            item.status in {"execution_pending", "function_result"}
            for item in evaluation.observations
        )
        else 1
    )

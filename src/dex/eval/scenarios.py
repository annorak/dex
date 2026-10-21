import json
import sys
from dataclasses import dataclass, replace
from pathlib import Path

from dex.core import events as e
from dex.core import language as language
from dex.core import program as p
from dex.core import runtime as r
from dex.eval.scenario_format import (
    MAX_BYTES,
    ContinuationCommand,
    FunctionCommand,
    FunctionExpected,
    RebuildCommand,
    RecordingCommand,
    RuntimeExpected,
    SandboxCommand,
    Scenario,
    ScenarioError,
    SignalCommand,
    parse_scenario,
)
from dex.eval.scenario_output import encode_core
from dex.recordings import RecordingError, parse_recording


@dataclass(frozen=True)
class RuntimeObservation:
    value: p.Value | None
    failure: str | None
    events: tuple[e.RuntimeEvent, ...]
    work: tuple[r.Work, ...]
    revision: int
    replay_equal: bool | None
    tasks: tuple[e.Task, ...] = ()
    actions: tuple[e.HumanCommand, ...] = ()
    recordings: tuple[e.Recording, ...] = ()
    history: tuple[r.Work, ...] = ()
    submitted: e.RuntimeCommand | None = None


@dataclass(frozen=True)
class Observation:
    command: str
    program: str
    status: str
    diagnostics: tuple[p.Diagnostic, ...]
    missing_checks: tuple[p.MissingCheck, ...]
    artifact: p.StructuralArtifact | None
    function: language.FunctionResult | language.LanguageFailure | None
    runtime: RuntimeObservation | None = None


@dataclass(frozen=True)
class Evaluation:
    observations: tuple[Observation, ...]
    matches: tuple[bool, ...]
    final_runtime: RuntimeObservation


def evaluate(scenario: Scenario) -> Evaluation:
    programs = {item.name: item for item in scenario.programs}
    observations: list[Observation] = []
    runtime_history: list[e.RuntimeEvent] = []
    runtime_state = r.rebuild((), r.ProgramCatalog(()))
    runtime_entries: dict[str, r.ArtifactEntry] = {}
    catalog = r.ProgramCatalog(())
    verified: dict[tuple[str, language.Limits], p.VerificationResult] = {}
    for command in scenario.commands:
        program = programs[command.program]
        limits = (
            command.limits
            if isinstance(command, FunctionCommand)
            else language.DEFAULT_LIMITS
        )
        key = command.program, limits
        if key not in verified:
            verified[key] = p.verify_program(program.draft, program.sources, limits)
        result = verified[key]
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
        if isinstance(
            command,
            (
                SandboxCommand,
                SignalCommand,
                RebuildCommand,
                ContinuationCommand,
                RecordingCommand,
            ),
        ):
            if isinstance(result, p.StructuralFailure):
                observations.append(
                    Observation(
                        command.kind,
                        command.program,
                        "structural_failure",
                        diagnostics,
                        (),
                        None,
                        None,
                    )
                )
                continue
            if command.program not in runtime_entries:
                runtime_entries[command.program] = r.ArtifactEntry(
                    r.artifact_pin(result.artifact), result.artifact
                )
                catalog = r.ProgramCatalog(tuple(runtime_entries.values()))
            submitted: e.RuntimeCommand | None = None
            before = runtime_state
            replay_equal: bool | None = None
            batch: tuple[e.RuntimeEvent, ...] = ()
            failure: str | None = None
            if isinstance(command, ContinuationCommand):
                case_id = r.command_case(command.command)
            elif isinstance(command, RecordingCommand):
                case_id = command.work.address.case_id
            elif isinstance(command, SignalCommand):
                case_id = command.signal.address.case_id
            else:
                case_id = command.case_id
            if isinstance(command, RebuildCommand):
                if case_id not in runtime_state.cases:
                    raise ScenarioError(
                        "Rebuild references an unknown case: " + case_id
                    )
                replay_events = tuple(runtime_history)
                replay_catalog = catalog
                if command.corruption == "event_version" and replay_events:
                    replay_events = (
                        replace(replay_events[0], format_version=999),
                    ) + replay_events[1:]
                elif command.corruption == "missing_artifact":
                    replay_catalog = r.ProgramCatalog(())
                elif command.corruption == "truncate":
                    replay_events = replay_events[:-1]
                try:
                    restored = r.rebuild(replay_events, replay_catalog)
                    replay_equal = restored == runtime_state
                    if not replay_equal:
                        raise ScenarioError("Replay differs from live state.")
                except r.ReplayError as error:
                    failure = error.code
                status = (
                    "replay_failed"
                    if failure is not None
                    else "runtime_" + runtime_state.cases[case_id].status
                )
            else:
                core_command: e.RuntimeCommand
                decision: r.Accepted | r.Refused
                if isinstance(command, RecordingCommand):
                    work = runtime_state.work.get(command.work.address)
                    request = None if work is None else work.request
                    if request is None:
                        previous = runtime_state.recordings.get(command.work)
                        request = None if previous is None else previous.request
                    try:
                        if request is None or request.work != command.work:
                            raise RecordingError("recording_request")
                        recording = parse_recording(command.recording, request)
                        submitted = e.SupplyRecording(
                            command.meta, recording, command.bounds
                        )
                        decision = r.decide(runtime_state, submitted, catalog)
                    except RecordingError as error:
                        decision = r.Refused(str(error))
                else:
                    if isinstance(command, ContinuationCommand):
                        core_command = command.command
                        if command.advance_revision:
                            core_command = replace(
                                core_command,
                                meta=replace(
                                    core_command.meta,
                                    expected_revision=runtime_state.revision,
                                ),
                            )
                    elif isinstance(command, SignalCommand):
                        core_command = command.signal
                    else:
                        core_command = e.StartSandbox(
                            command.meta,
                            command.case_id,
                            runtime_entries[command.program].pin,
                            command.facts,
                            command.business_date,
                            command.bounds,
                            command.company,
                        )
                    submitted = core_command
                    decision = r.decide(runtime_state, core_command, catalog)
                if isinstance(decision, r.Refused):
                    status, failure = "runtime_refused", decision.code
                else:
                    batch = decision.events
                    runtime_history.extend(batch)
                    runtime_state = decision.state
                    status = "runtime_" + runtime_state.cases[case_id].status
                    failure = runtime_state.cases[case_id].failure
            case_work = tuple(
                work
                for address, work in runtime_state.work.items()
                if address.case_id == case_id
            )
            root_work = next(
                (work for work in case_work if work.opened.parent is None), None
            )
            value = (
                root_work.completed.value
                if root_work is not None and root_work.completed is not None
                else None
            )
            runtime = RuntimeObservation(
                value,
                failure,
                batch,
                case_work
                if scenario.detail == "full"
                else tuple(
                    work
                    for work in case_work
                    if before.work.get(work.opened.address) != work
                ),
                runtime_state.revision,
                replay_equal,
                tuple(
                    task
                    for ref, task in runtime_state.tasks.items()
                    if ref.work.address.case_id == case_id
                    and (scenario.detail == "full" or before.tasks.get(ref) != task)
                ),
                tuple(
                    action
                    for key, action in runtime_state.actions.items()
                    if r.command_case(action) == case_id
                    and (scenario.detail == "full" or key not in before.actions)
                ),
                tuple(
                    recording
                    for ref, recording in runtime_state.recordings.items()
                    if ref.address.case_id == case_id
                    and (scenario.detail == "full" or ref not in before.recordings)
                ),
                tuple(
                    work
                    for ref, work in runtime_state.history.items()
                    if ref.address.case_id == case_id
                    and (scenario.detail == "full" or ref not in before.history)
                ),
                submitted,
            )
            observations.append(
                Observation(
                    command.kind,
                    command.program,
                    status,
                    (),
                    missing,
                    None,
                    None,
                    runtime,
                )
            )
            continue
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
    final_replay_equal = r.rebuild(tuple(runtime_history), catalog) == runtime_state
    final_runtime = RuntimeObservation(
        None,
        None,
        (),
        tuple(runtime_state.work.values()),
        runtime_state.revision,
        final_replay_equal,
        tuple(runtime_state.tasks.values()),
        tuple(runtime_state.actions.values()),
        tuple(runtime_state.recordings.values()),
        tuple(runtime_state.history.values()),
    )
    matches = tuple(
        (
            actual.status == expected.status
            and actual.runtime is not None
            and actual.runtime.value
            == (None if expected.value is None else p.normalized_value(expected.value))
            and actual.runtime.failure == expected.failure
            and final_replay_equal
            and (
                expected.work_nodes is None
                or tuple(
                    sorted(work.opened.address.node_id for work in actual.runtime.work)
                )
                == tuple(sorted(expected.work_nodes))
            )
        )
        if isinstance(expected, RuntimeExpected)
        else (
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
    return Evaluation(tuple(observations), matches, final_runtime)


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
                "detail": scenario.detail,
                "final_runtime": evaluation.final_runtime,
                "observations": [
                    {
                        "command": item.command,
                        "program": item.program,
                        "status": item.status,
                        "diagnostics": item.diagnostics,
                        "missing_checks": item.missing_checks,
                        "artifact": item.artifact,
                        "function": item.function,
                        "runtime": item.runtime,
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
                        **(
                            {"work_nodes": item.work_nodes}
                            if isinstance(item, RuntimeExpected)
                            else {}
                        ),
                    }
                    if isinstance(item, (FunctionExpected, RuntimeExpected))
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
            item.status
            in {
                "execution_pending",
                "function_result",
                "runtime_succeeded",
                "runtime_waiting",
            }
            for item in evaluation.observations
        )
        else 1
    )

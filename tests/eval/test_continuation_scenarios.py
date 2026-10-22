import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from dex.core import events as e
from dex.eval.scenario_format import RuntimeExpected, parse_scenario
from dex.eval.scenarios import evaluate

FIXTURES = Path(__file__).resolve().parents[1] / "scenarios"


@pytest.mark.parametrize(
    "name", ["human", "correction", "redelivery", "response-revision", "invalid-ai"]
)
def test_delta_and_full_have_identical_final_state(name: str) -> None:
    scenario = parse_scenario((FIXTURES / f"continuation-{name}.json").read_bytes())
    delta = evaluate(replace(scenario, detail="changes"))
    full = evaluate(replace(scenario, detail="full"))
    assert all(delta.matches) and all(full.matches)
    assert delta.final_runtime == full.final_runtime
    assert delta.final_runtime.replay_equal is True
    for small, large in zip(delta.observations, full.observations, strict=True):
        assert small.runtime is not None and large.runtime is not None
        assert small.runtime.events == large.runtime.events
        assert small.runtime.submitted == large.runtime.submitted
        if small.command != "rebuild":
            assert small.runtime.replay_equal is None
        if small.status == "runtime_refused" or not small.runtime.events:
            assert not small.runtime.work
            assert not small.runtime.tasks
            assert not small.runtime.actions
            assert not small.runtime.recordings
            assert not small.runtime.history


def test_expectations_do_not_influence_execution() -> None:
    scenario = parse_scenario((FIXTURES / "continuation-human.json").read_bytes())
    baseline = evaluate(scenario)
    wrong = tuple(
        RuntimeExpected("runtime_failed", None, "invented", None)
        for _ in scenario.commands
    )
    changed = evaluate(replace(scenario, expected=wrong))
    assert baseline.observations == changed.observations
    assert baseline.final_runtime == changed.final_runtime
    assert not any(changed.matches)


def test_response_series_matches_explicit_commands_including_stale_middle() -> None:
    document = json.loads((FIXTURES / "continuation-human.json").read_bytes())
    start, answer, _ = document["commands"]
    other = deepcopy(start)
    other["case_id"] = "second"
    other["meta"].update(command_id="start-second", expected_revision=7)
    stale = deepcopy(answer["task"])
    second = deepcopy(answer["task"])
    second["work"]["address"]["case_id"] = "second"
    targets: list[dict[str, object]] = [
        {"task": target, "reviewed": []} for target in [answer["task"], stale, second]
    ]
    series = {
        key: deepcopy(answer[key])
        for key in ["program", "meta", "action", "bounds", "value"]
    }
    series.update(kind="respond_tasks", targets=targets)
    series["meta"]["expected_revision"] = 14
    document["commands"] = [start, other, series]
    succeeded = document["expected"][1]
    document["expected"] = [document["expected"][0]] * 2 + [
        succeeded,
        {**succeeded, "status": "runtime_refused", "failure": "stale_task"},
        succeeded,
    ]
    expanded = evaluate(parse_scenario(json.dumps(document).encode()))
    ordinary: list[dict[str, object]] = []
    for index, target in enumerate(targets):
        command = {
            key: deepcopy(series[key])
            for key in ["program", "meta", "action", "bounds", "value"]
        }
        command.update(kind="respond", **target)
        command["meta"].update(
            command_id=f"{series['meta']['command_id']}:{index}",
            expected_revision=[14, 18, 18][index],
        )
        command["action"]["action_id"] += f":{index}"
        ordinary.append(command)
    document["commands"] = [start, other, *ordinary]
    explicit = evaluate(parse_scenario(json.dumps(document).encode()))
    assert expanded == explicit
    assert all(expanded.matches)
    middle = expanded.observations[3].runtime
    assert middle is not None and isinstance(middle.submitted, e.RespondTask)
    assert middle.failure == "stale_task" and not middle.events and not middle.work


def test_recording_encoding_refusal_preserves_open_request() -> None:
    document = json.loads((FIXTURES / "continuation-invalid-ai.json").read_bytes())
    document["commands"] = document["commands"][:2]
    recording = json.loads(document["commands"][1]["recording"])
    recording.update(value=None, failure="\ud800")
    document["commands"][1]["recording"] = json.dumps(recording)
    document["expected"] = document["expected"][:2]
    document["expected"][1].update(
        status="runtime_refused", failure="recording_encoding"
    )
    scenario = parse_scenario(json.dumps(document).encode())
    baseline = evaluate(
        replace(
            scenario, commands=scenario.commands[:1], expected=scenario.expected[:1]
        )
    )
    refused = evaluate(scenario)
    assert all(refused.matches)
    assert refused.final_runtime == baseline.final_runtime
    assert refused.final_runtime.replay_equal is True
    observation = refused.observations[1].runtime
    assert observation is not None
    assert (
        not observation.events and not observation.work and not observation.recordings
    )

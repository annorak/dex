import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from dex.core import authority as a
from dex.core import events as e
from dex.core import program as p
from dex.eval.scenario_format import EffectCommand, RuntimeExpected, parse_scenario
from dex.eval.scenarios import evaluate

FIXTURES = Path(__file__).resolve().parents[1] / "scenarios"
NAMES = (
    "exact-approval",
    "program-approval",
    "business-approval",
    "payload-change",
    "operation-key",
    "operation-key-versioned",
    "occurrence",
    "conflicting-review",
    "precondition-change",
    "uncertain-replacement",
    "confirmed-amendment",
)


@pytest.mark.parametrize("name", NAMES)
def test_effect_delta_and_full_preserve_events_and_final_state(name: str) -> None:
    scenario = parse_scenario((FIXTURES / f"effect-{name}.json").read_bytes())
    delta = evaluate(scenario)
    full = evaluate(replace(scenario, detail="full"))
    assert all(delta.matches) and all(full.matches)
    assert delta.final_runtime == full.final_runtime
    assert delta.final_runtime.replay_equal is True
    assert any(
        work.opened.parent is None and work.completed is not None
        for work in delta.final_runtime.work
    )
    for command, small, large in zip(
        scenario.commands, delta.observations, full.observations, strict=True
    ):
        assert small.runtime is not None and large.runtime is not None
        assert small.runtime.events == large.runtime.events
        if isinstance(command, EffectCommand):
            assert small.runtime.value is None and large.runtime.value is None
            assert not small.runtime.work and not small.runtime.tasks
        if small.status == "runtime_refused" or not small.runtime.events:
            assert not small.runtime.effects and not small.runtime.actions
            assert not small.runtime.revoked_approvals


def test_effect_expectations_cannot_change_execution() -> None:
    scenario = parse_scenario((FIXTURES / "effect-exact-approval.json").read_bytes())
    baseline = evaluate(scenario)
    changed = evaluate(
        replace(
            scenario,
            expected=tuple(
                RuntimeExpected("runtime_failed", None, "invented", None)
                for _ in scenario.commands
            ),
        )
    )
    assert baseline.observations == changed.observations
    assert baseline.final_runtime == changed.final_runtime
    assert not any(changed.matches)


def test_operation_identity_survives_artifact_and_behavior_changes() -> None:
    first, second = (
        evaluate(
            parse_scenario((FIXTURES / f"effect-{name}.json").read_bytes())
        ).final_runtime.effects[0]
        for name in ("operation-key", "operation-key-versioned")
    )
    assert first.revision.ref.key == second.revision.ref.key
    assert first.revision.artifact != second.revision.artifact
    assert first.revision.behavior_id != second.revision.behavior_id
    assert first.revision.payload != second.revision.payload


def test_approval_series_matches_individual_commands_with_conflicting_middle() -> None:
    document = json.loads((FIXTURES / "effect-occurrence.json").read_bytes())
    start, first, _, second, _, _ = document["commands"]
    targets = [first["effect"], first["effect"], second["effect"]]
    series = {
        key: deepcopy(first[key]) for key in ("program", "meta", "action", "bounds")
    }
    series.update(kind="approve_effects", targets=targets)
    document["commands"] = [start, series]
    document["expected"] = [
        document["expected"][0],
        document["expected"][1],
        {
            **document["expected"][1],
            "status": "runtime_refused",
            "failure": "effect_review_conflict",
        },
        document["expected"][1],
    ]
    expanded = evaluate(parse_scenario(json.dumps(document).encode()))
    ordinary: list[dict[str, object]] = []
    for index, target in enumerate(targets):
        command = {
            key: deepcopy(series[key])
            for key in ("program", "meta", "action", "bounds")
        }
        command.update(kind="approve_effect", effect=target)
        command["meta"].update(
            command_id=f"{first['meta']['command_id']}:{index}",
            expected_revision=[15, 19, 19][index],
        )
        command["action"]["action_id"] += f":{index}"
        ordinary.append(command)
    document["commands"] = [start, *ordinary]
    explicit = evaluate(parse_scenario(json.dumps(document).encode()))
    assert expanded == explicit and all(expanded.matches)
    assert len(expanded.final_runtime.actions) == 2
    assert all(
        isinstance(effect.progress, a.Approved)
        for effect in expanded.final_runtime.effects
    )
    refused = expanded.observations[2].runtime
    assert refused is not None and isinstance(refused.submitted, e.ApproveEffect)
    assert (
        refused.failure == "effect_review_conflict"
        and not refused.events
        and not refused.effects
    )


def test_changed_precondition_keeps_producer_result_but_invalidates_effect() -> None:
    observed = evaluate(
        parse_scenario((FIXTURES / "effect-precondition-change.json").read_bytes())
    )
    first, revised = observed.final_runtime.effects
    assert first.revision.producer == revised.revision.producer
    assert first.revision.payload == revised.revision.payload == p.IntValue(7)
    assert first.revision.dependencies != revised.revision.dependencies
    assert first.superseded_by == revised.revision.ref
    refused = observed.observations[-2].runtime
    assert refused is not None and refused.failure == "effect_precondition"

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import fields, replace
from types import MappingProxyType
from typing import cast

from test_continuations import COMPANY, action, meta
from test_runtime import (
    NOW,
    catalog,
    code,
    draft,
    execute,
    identity,
    parallel_program,
    start,
)

from dex.core import events as e
from dex.core import program as p
from dex.core import runtime as r


def snapshot(state: r.WorkspaceState) -> r.WorkspaceState:
    maps: dict[str, object] = {}
    for field in fields(state):
        value: object = getattr(state, field.name)
        if isinstance(value, Mapping):
            maps[field.name] = MappingProxyType(
                deepcopy(dict(cast(Mapping[object, object], value)))
            )
    return replace(state, **maps)


def test_nested_pending_sets_preserve_prior_snapshot() -> None:
    state, events, programs = execute(parallel_program())
    saved = snapshot(state)
    address = next(address for address in state.work if address.node_id == "repeat")
    result = r.decide(
        state,
        e.SignalRepeat(
            e.CommandMeta("signal", "tester", NOW, NOW, state.revision),
            address,
            0,
            "continue",
        ),
        programs,
    )
    assert isinstance(result, r.Accepted), result
    assert state == saved
    assert result.state.cases["case"].status == "succeeded"
    assert r.rebuild(events + result.events, programs) == result.state
    assert state == saved
    assert any(state.pending.values())
    assert not any(result.state.pending.values())


def test_retirement_and_later_correction_preserve_every_prior_map() -> None:
    boolean = p.Scalar.BOOLEAN
    route = code("route", p.Literal(p.BoolValue(True)), boolean)
    data = code("data", p.Literal(p.BoolValue(True)), boolean)
    selected = code("selected", p.ResultRef("data"), boolean)
    alternative = code("alternative", p.Literal(p.BoolValue(True)), boolean)
    choice = p.Choose(
        "choice",
        p.ResultRef("route"),
        p.Branch(selected, p.Export(boolean, p.ResultRef("selected"))),
        p.Branch(alternative, p.Export(boolean, p.ResultRef("alternative"))),
        boolean,
    )
    programs = catalog(
        draft(
            p.Sequence(
                "root", (route, data, choice), p.Export(boolean, p.ResultRef("choice"))
            ),
            (identity(boolean, p.BoolValue(True)),),
        )
    )
    opened = r.decide(
        r.rebuild((), programs), replace(start(programs), company=COMPANY), programs
    )
    assert isinstance(opened, r.Accepted)
    state, events = opened.state, opened.events
    versions: list[tuple[r.WorkspaceState, r.WorkspaceState]] = []
    for name in ("route", "data"):
        versions.append((state, snapshot(state)))
        result = r.decide(
            state,
            e.CorrectResult(
                meta(state, "correct-" + name, "admin"),
                e.WorkRevision(e.WorkAddress("case", name), 1),
                action("correct-" + name, "admin", "corrector"),
                p.BoolValue(False),
            ),
            programs,
        )
        assert isinstance(result, r.Accepted), result
        state, events = result.state, events + result.events
        assert all(prior == saved for prior, saved in versions)
        assert r.rebuild(events, programs) == state
        assert all(prior == saved for prior, saved in versions)
    assert any(ref.address.node_id == "selected" for ref in state.history)
    assert not any(address.node_id == "selected" for address in state.work)

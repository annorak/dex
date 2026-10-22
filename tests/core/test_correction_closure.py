import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from test_continuations import COMPANY, accept, action, meta
from test_runtime import (
    NOW,
    catalog,
    code,
    counter,
    draft,
    execute,
    identity,
    repeat_program,
    root_value,
    start,
)

from dex.core import events as e
from dex.core import program as p
from dex.core import runtime as r


def check_converging_correction(depth: int) -> None:
    boolean = p.Scalar.BOOLEAN
    sibling = code("sibling", p.Literal(p.BoolValue(True)), boolean)
    source = code("source", p.Literal(p.BoolValue(True)), boolean)
    chain = [code("first", p.ResultRef("source"), boolean)]
    for index in range(1, depth):
        name = "second" if index == 1 else f"link-{index}"
        chain.append(code(name, p.ResultRef(chain[-1].metadata.step_id), boolean))
    selected = code("selected", p.ResultRef("source"), boolean)
    alternative = code("alternative", p.Literal(p.BoolValue(True)), boolean)
    choice = p.Choose(
        "choice",
        p.ResultRef(chain[-1].metadata.step_id),
        p.Branch(selected, p.Export(boolean, p.ResultRef("selected"))),
        p.Branch(alternative, p.Export(boolean, p.ResultRef("alternative"))),
        boolean,
    )
    programs = catalog(
        draft(
            p.Sequence(
                "root",
                (sibling, source, *chain, choice),
                p.Export(boolean, p.ResultRef("choice")),
            ),
            (identity(boolean, p.BoolValue(True)),),
        )
    )
    opened = r.decide(
        r.rebuild((), programs), replace(start(programs), company=COMPANY), programs
    )
    assert isinstance(opened, r.Accepted)
    corrected = r.decide(
        opened.state,
        e.CorrectResult(
            meta(opened.state, "correction", "admin"),
            e.WorkRevision(e.WorkAddress("case", "source"), 1),
            action("correction", "admin", "corrector"),
            p.BoolValue(False),
        ),
        programs,
    )
    assert isinstance(corrected, r.Accepted), corrected
    choice_work = corrected.state.work[e.WorkAddress("case", "choice")]
    assert choice_work.selected is not None
    assert choice_work.selected.selection == p.BoolValue(False)
    assert root_value(corrected.state) == p.BoolValue(True)
    selected_address = next(
        address for address in opened.state.work if address.node_id == "selected"
    )
    assert selected_address not in corrected.state.work
    assert e.WorkRevision(selected_address, 1) in corrected.state.history
    sibling_address = e.WorkAddress("case", "sibling")
    assert corrected.state.work[sibling_address] == opened.state.work[sibling_address]
    assert r.rebuild(opened.events + corrected.events, programs) == corrected.state


@pytest.mark.parametrize("seed", [0, 2])
@pytest.mark.parametrize("depth", [2, 5])
def test_correction_revisits_control_after_transitive_dependency(
    seed: int, depth: int
) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            f"from test_correction_closure import check_converging_correction; check_converging_correction({depth})",
        ],
        env={
            **os.environ,
            "PYTHONHASHSEED": str(seed),
            "PYTHONPATH": str(Path(__file__).parent),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_retired_branch_does_not_remain_a_current_consumer() -> None:
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
    state, history = opened.state, opened.events
    retired = next(address for address in state.work if address.node_id == "selected")
    for name in ("route", "data"):
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
        state, history = result.state, history + result.events
        assert retired not in state.work
        assert all(retired not in consumers for consumers in state.consumers.values())
        assert e.WorkRevision(retired, 1) in state.history
        assert root_value(state) == p.BoolValue(True)
        assert r.rebuild(history, programs) == state
    alternative_address = next(
        address for address in state.work if address.node_id == "alternative"
    )
    assert state.work[alternative_address].opened.revision == 1


def test_repeat_replaces_shared_producer_bindings_without_stale_edges() -> None:
    state, history, programs = execute(repeat_program(3, event=True))
    address = e.WorkAddress("case", "repeat")
    for iteration in range(2):
        inputs = state.work[address].inputs
        carried = next(item for item in inputs if item.name == ("carried",))
        until = next(item for item in inputs if item.name == ("until",))
        assert carried.producer == until.producer
        assert carried.producer_revision == until.producer_revision
        assert carried.producer is not None and carried.producer_revision is not None
        previous = e.WorkRevision(carried.producer, carried.producer_revision)
        assert address in state.consumers[previous]
        result = r.decide(
            state,
            e.SignalRepeat(
                e.CommandMeta(
                    f"signal-{iteration}", "tester", NOW, NOW, state.revision
                ),
                address,
                iteration,
                "continue",
            ),
            programs,
        )
        assert isinstance(result, r.Accepted), result
        state, history = result.state, history + result.events
        assert address not in state.consumers.get(previous, ())
        assert r.rebuild(history, programs) == state
    assert state.cases["case"].status == "succeeded"


@pytest.mark.parametrize("finished", [True, False])
def test_repeat_correction_rebuilds_later_carried_work(finished: bool) -> None:
    programs = catalog(repeat_program(3))
    opened = accept(
        r.rebuild((), programs), replace(start(programs), company=COMPANY), programs
    )
    first = next(
        address
        for address in opened.state.work
        if address.node_id == "advance" and address.scope[-1].key == "0"
    )
    corrected = accept(
        opened.state,
        e.CorrectResult(
            meta(opened.state, "correct", "admin"),
            e.WorkRevision(first, 1),
            action("correct", "admin", "corrector"),
            counter(10, finished),
        ),
        programs,
    )
    assert root_value(corrected.state) == counter(10 if finished else 11, True)
    later = [
        address
        for address in opened.state.work
        if address.node_id == "advance" and address != first
    ]
    assert all(
        e.WorkRevision(address, 1) in corrected.state.history for address in later
    )
    assert all(
        address not in corrected.state.work
        or corrected.state.work[address].opened.revision == 2
        for address in later
    )
    assert opened.state.work[first].opened.revision == 1
    assert r.rebuild(opened.events + corrected.events, programs) == corrected.state

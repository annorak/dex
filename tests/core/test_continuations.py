from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from test_runtime import (
    CITATION,
    INTEGER,
    NOW,
    TEXT,
    catalog,
    code,
    draft,
    identity,
    start,
)

from dex.core import events as e
from dex.core import language as lang
from dex.core import program as p
from dex.core import runtime as r

COMPANY = e.CompanyContext(
    "company-a",
    "policy-1",
    tuple(
        e.RoleMembership(actor, role, (), NOW - timedelta(days=1), None)
        for actor, role in (
            ("alice", "reviewer"),
            ("bob", "reviewer"),
            ("admin", "task_admin"),
            ("admin", "corrector"),
        )
    ),
    (e.ObservationPermission("observer", "outside", (), NOW, None),),
    "records-1",
    frozenset({p.ResolvedRefValue("Entry", "key", "known")}),
)


HUMAN_INPUT = p.Literal(p.IntValue(1))


def human(
    name: str = "human", source: p.Input = HUMAN_INPUT, schema: p.Schema = INTEGER
) -> p.HumanStep:
    return p.HumanStep(
        p.StepMetadata(
            name,
            name + "-1",
            TEXT,
            (CITATION,),
            (p.Binding("reviewed", INTEGER, source),),
            schema,
        ),
        "reviewer",
        NOW + timedelta(days=1),
        p.Export(INTEGER, source),
        True,
    )


def setup(
    root: p.Node | None = None,
) -> tuple[r.WorkspaceState, tuple[e.RuntimeEvent, ...], r.ProgramCatalog]:
    program = draft(
        human() if root is None else root,
        (identity(INTEGER, p.IntValue(1)),),
        schemas=(root.output,) if isinstance(root, p.Parallel) else (),
    )
    programs = catalog(program)
    opened = r.decide(
        r.rebuild((), programs), replace(start(programs), company=COMPANY), programs
    )
    assert isinstance(opened, r.Accepted), opened
    assert r.rebuild(opened.events, programs) == opened.state
    return opened.state, opened.events, programs


def meta(state: r.WorkspaceState, name: str, actor: str = "alice") -> e.CommandMeta:
    return e.CommandMeta(name, actor, NOW, NOW, state.revision)


def action(
    name: str = "answer", actor: str = "alice", role: str = "reviewer"
) -> e.HumanAction:
    return e.HumanAction(COMPANY.company_id, "dex", name, actor, role, NOW)


def response(state: r.WorkspaceState, name: str = "answer") -> e.RespondTask:
    task = next(task for task in state.tasks.values() if task.status == "open")
    return e.RespondTask(
        meta(state, name), task.ref, task.reviewed, action(name), p.IntValue(9)
    )


def accept(
    state: r.WorkspaceState, command: e.RuntimeCommand, programs: r.ProgramCatalog
) -> r.Accepted:
    result = r.decide(state, command, programs)
    assert isinstance(result, r.Accepted), result
    return result


def test_exact_response_and_replay_without_interpretation() -> None:
    state, history, programs = setup()
    command = response(state)
    answered = accept(state, command, programs)
    assert answered.state.cases["case"].status == "succeeded"
    assert answered.state.work[command.task.work.address].completed == e.WorkSucceeded(
        command.task.work.address,
        p.IntValue(9),
        state.work[command.task.work.address].inputs,
        lang.Usage(0, 0),
    )
    assert answered.state.tasks[command.task].status == "answered"
    with (
        patch(
            "dex.core.language.execute_function",
            side_effect=AssertionError("interpreter"),
        ),
        patch("builtins.open", side_effect=AssertionError("I/O")),
    ):
        assert r.rebuild(history + answered.events, programs) == answered.state
    recorded = answered.state.actions[r.action_key(command.action)]
    assert recorded.action.decided_at == NOW
    assert recorded.meta.observed_at == NOW


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("company", "company_mismatch"),
        ("actor", "actor_forbidden"),
        ("schema", "response_schema"),
        ("reviewed", "reviewed_revision"),
        ("request", "actor_forbidden"),
        ("work", "unknown_work"),
    ],
)
def test_bad_response_is_atomic(mutation: str, code: str) -> None:
    state, history, programs = setup()
    command = response(state)
    if mutation == "company":
        command = replace(
            command, action=replace(command.action, company_id="company-b")
        )
    elif mutation == "actor":
        command = replace(
            command,
            meta=replace(command.meta, actor="intruder"),
            action=replace(command.action, actor="intruder"),
        )
    elif mutation == "schema":
        command = replace(command, value=p.TextValue("nine"))
    elif mutation == "reviewed":
        command = replace(
            command, reviewed=(e.WorkRevision(e.WorkAddress("case", "other"), 1),)
        )
    elif mutation == "request":
        command = replace(command, task=replace(command.task, request_revision=2))
    else:
        command = replace(
            command,
            task=replace(
                command.task,
                work=replace(
                    command.task.work,
                    address=e.WorkAddress(
                        "case", "human", (e.ScopePart("each", "each", "foreign"),)
                    ),
                ),
            ),
        )
    assert r.decide(state, command, programs) == r.Refused(code)
    assert r.rebuild(history, programs) == state


def test_action_redelivery_has_no_events_and_conflicting_body_fails() -> None:
    state, _, programs = setup()
    command = response(state)
    answered = accept(state, command, programs)
    again = replace(
        command,
        meta=replace(
            command.meta,
            command_id="delivery-2",
            expected_revision=answered.state.revision,
            observed_at=NOW + timedelta(days=3),
        ),
    )
    assert r.decide(answered.state, again, programs) == r.Accepted((), answered.state)
    assert r.decide(
        answered.state, replace(again, value=p.IntValue(8)), programs
    ) == r.Refused("action_conflict")
    assert r.decide(
        answered.state,
        replace(again, meta=replace(again.meta, actor="intruder")),
        programs,
    ) == r.Refused("observer_forbidden")
    assert len(answered.state.actions) == 1


def test_open_overdue_task_accepts_late_answer() -> None:
    state, _, programs = setup()
    command = response(state)
    late = NOW + timedelta(days=9)
    command = replace(
        command,
        meta=replace(command.meta, occurred_at=late, observed_at=late),
        action=replace(command.action, decided_at=late),
    )
    answered = accept(state, command, programs)
    assert answered.state.cases["case"].status == "succeeded"
    assert answered.state.tasks[command.task].due_at < command.action.decided_at


def test_assignment_and_cancellation_supersede_exact_request() -> None:
    state, history, programs = setup()
    original = response(state)
    assigned = accept(
        state,
        e.ReassignTask(
            meta(state, "assign", "admin"),
            original.task,
            action("assign", "admin", "task_admin"),
            "bob",
        ),
        programs,
    )
    history += assigned.events
    state = assigned.state
    assert r.decide(
        state,
        replace(
            original, meta=replace(original.meta, expected_revision=state.revision)
        ),
        programs,
    ) == r.Refused("stale_task")
    command = response(state)
    assert r.decide(state, command, programs) == r.Refused("assignment")
    cancelled = accept(
        state,
        e.CancelTask(
            meta(state, "cancel", "admin"),
            command.task,
            action("cancel", "admin", "task_admin"),
        ),
        programs,
    )
    assert cancelled.state.cases["case"].status == "waiting"
    bob = replace(
        command, meta=meta(cancelled.state, "bob", "bob"), action=action("bob", "bob")
    )
    assert r.decide(cancelled.state, bob, programs) == r.Refused("stale_task")
    assert r.rebuild(history + cancelled.events, programs) == cancelled.state


def test_external_decision_retains_actual_actor_and_times() -> None:
    state, history, programs = setup()
    command = response(state)
    command = replace(
        command,
        meta=replace(
            command.meta, actor="observer", observed_at=NOW + timedelta(days=2)
        ),
        action=replace(command.action, origin="outside"),
    )
    answered = accept(state, command, programs)
    saved = answered.state.actions[r.action_key(command.action)]
    assert saved.action.actor == "alice" and saved.action.role == "reviewer"
    assert saved.action.origin == "outside" and saved.action.decided_at == NOW
    assert saved.meta.actor == "observer" and saved.meta.observed_at == NOW + timedelta(
        days=2
    )
    assert r.rebuild(history + answered.events, programs) == answered.state


def test_scoped_membership_cannot_answer_another_scope() -> None:
    state, _, programs = setup()
    command = response(state)
    policy = replace(
        COMPANY,
        memberships=(
            replace(COMPANY.memberships[0], scope=(e.ScopePart("each", "each", "a"),)),
        ),
    )
    started = accept(
        r.rebuild((), programs), replace(start(programs), company=policy), programs
    )
    assert r.decide(started.state, command, programs) == r.Refused("actor_forbidden")


def correction_program() -> p.Node:
    first = code("source", p.Literal(p.IntValue(1)))
    decision = human(source=p.ResultRef("source"))
    after = code("after", p.ResultRef("human"))
    branch = p.Sequence(
        "dependent", (first, decision, after), p.Export(INTEGER, p.ResultRef("after"))
    )
    sibling = code("sibling", p.Literal(p.IntValue(7)))
    output = p.RecordSchema(
        "Joined", (p.Field("dependent", INTEGER), p.Field("independent", INTEGER))
    )
    return p.Parallel(
        "root",
        (
            p.NamedBranch(
                "dependent",
                p.Branch(branch, p.Export(INTEGER, p.ResultRef("dependent"))),
            ),
            p.NamedBranch(
                "independent",
                p.Branch(sibling, p.Export(INTEGER, p.ResultRef("sibling"))),
            ),
        ),
        output,
    )


def test_correction_preserves_sibling_and_historical_decision() -> None:
    state, history, programs = setup(correction_program())
    sibling = next(
        work for address, work in state.work.items() if address.node_id == "sibling"
    )
    old_answer = response(state)
    answered = accept(state, old_answer, programs)
    history += answered.events
    state = answered.state
    source = next(address for address in state.work if address.node_id == "source")
    corrected = accept(
        state,
        e.CorrectResult(
            meta(state, "correct", "admin"),
            e.WorkRevision(source, 1),
            action("correct", "admin", "corrector"),
            p.IntValue(2),
        ),
        programs,
    )
    history += corrected.events
    state = corrected.state
    assert state.cases["case"].status == "waiting"
    assert state.work[sibling.opened.address] == sibling
    assert state.tasks[old_answer.task].status == "answered"
    assert state.actions[r.action_key(old_answer.action)] == old_answer
    current = response(state, "new-answer")
    assert current.task.work.revision == 2
    assert current.reviewed == (e.WorkRevision(source, 2),)
    assert r.decide(
        state, replace(old_answer, meta=meta(state, "redelivery")), programs
    ) == r.Accepted((), state)
    assert r.decide(
        state,
        replace(old_answer, meta=meta(state, "stale"), action=action("stale")),
        programs,
    ) == r.Refused("stale_task")
    finished = accept(state, current, programs)
    assert finished.state.cases["case"].status == "succeeded"
    assert r.rebuild(history + finished.events, programs) == finished.state


def ai_program() -> p.ProgramDraft:
    schema = p.ai_outcome_schema(INTEGER)
    ai = p.AiStep(
        p.StepMetadata("ai", "ai-1", TEXT, (CITATION,), (), schema), "prompt-1", INTEGER
    )
    yes = code("known", p.Literal(p.IntValue(4)))
    fallback = human("fallback")
    choose = p.Choose(
        "choose",
        p.ResultRef("ai", ("valid",)),
        p.Branch(yes, p.Export(INTEGER, p.ResultRef("known"))),
        p.Branch(fallback, p.Export(INTEGER, p.ResultRef("fallback"))),
        INTEGER,
    )
    return draft(
        p.Sequence("root", (ai, choose), p.Export(INTEGER, p.ResultRef("choose"))),
        (identity(INTEGER, p.IntValue(1)),),
        schemas=(schema,),
    )


@pytest.mark.parametrize(
    "value,expected", [(p.IntValue(3), "succeeded"), (p.TextValue("bad"), "waiting")]
)
def test_recorded_ai_validates_and_routes_explicit_human(
    value: p.Value, expected: str
) -> None:
    programs = catalog(ai_program())
    opened = accept(
        r.rebuild((), programs), replace(start(programs), company=COMPANY), programs
    )
    request = opened.state.work[e.WorkAddress("case", "ai")].request
    assert request is not None
    recording = e.Recording(request, "recording-1", "model-1", 10, 2, value, None)
    supplied = accept(
        opened.state,
        e.SupplyRecording(meta(opened.state, "supply", "observer"), recording),
        programs,
    )
    assert supplied.state.cases["case"].status == expected
    assert len(supplied.state.recordings) == 1
    assert len(supplied.state.tasks) == (expected == "waiting")
    with (
        patch(
            "dex.core.language.execute_function",
            side_effect=AssertionError("interpreter"),
        ),
        patch("builtins.open", side_effect=AssertionError("I/O")),
    ):
        assert r.rebuild(opened.events + supplied.events, programs) == supplied.state
    assert r.decide(
        supplied.state,
        e.SupplyRecording(meta(supplied.state, "again"), recording),
        programs,
    ) == r.Accepted((), supplied.state)
    foreign = replace(recording, request=replace(request, company_id="company-b"))
    assert r.decide(
        opened.state,
        e.SupplyRecording(meta(opened.state, "foreign"), foreign),
        programs,
    ) == r.Refused("recording_request")


@pytest.mark.parametrize("placement", ["root", "choose", "parallel", "each"])
def test_ai_without_checked_fallback_is_structurally_refused(placement: str) -> None:
    program = ai_program()
    assert isinstance(program.root, p.Sequence)
    ai = program.root.children[0]
    branch = p.Branch(ai, p.Export(p.node_output(ai), p.ResultRef("ai")))
    root: p.Node = ai
    schemas = program.schemas
    if placement == "choose":
        root = p.Choose(
            "choose",
            p.Literal(p.BoolValue(True)),
            branch,
            p.Branch(
                replace(ai, metadata=replace(ai.metadata, step_id="ai2")),
                p.Export(p.node_output(ai), p.ResultRef("ai2")),
            )
            if isinstance(ai, p.AiStep)
            else branch,
            p.node_output(ai),
        )
    elif placement == "parallel":
        output = p.RecordSchema("JoinedAi", (p.Field("branch", p.node_output(ai)),))
        root = p.Parallel("parallel", (p.NamedBranch("branch", branch),), output)
        schemas += (output,)
    elif placement == "each":
        row = p.RecordSchema("Row", (p.Field("key", p.Scalar.TEXT),))
        collection = p.KeyedSchema(row, "key")
        output = p.node_output(ai)
        assert isinstance(output, p.RecordSchema)
        root = p.Each(
            "each",
            p.Literal(p.KeyedValue(())),
            collection,
            p.KeyedSchema(output, "valid"),
            branch,
        )
        schemas += (row,)
    from test_runtime import SOURCES

    result = p.verify_program(
        replace(program, root=root, schemas=schemas), SOURCES, lang.DEFAULT_LIMITS
    )
    assert isinstance(result, p.StructuralFailure)
    assert "ai_human_fallback" in {item.code for item in result.diagnostics}


def test_selection_correction_retires_nested_old_branch_tasks() -> None:
    boolean = p.Scalar.BOOLEAN
    flag = code("flag", p.Literal(p.BoolValue(True)), boolean, "flag")
    nested = p.Sequence(
        "nested", (human("old"),), p.Export(INTEGER, p.ResultRef("old"))
    )
    alternative = human("new")
    choose = p.Choose(
        "choose",
        p.ResultRef("flag"),
        p.Branch(nested, p.Export(INTEGER, p.ResultRef("nested"))),
        p.Branch(alternative, p.Export(INTEGER, p.ResultRef("new"))),
        INTEGER,
    )
    flag_function = replace(identity(boolean, p.BoolValue(True)), function_id="flag")
    programs = catalog(
        draft(
            p.Sequence(
                "root", (flag, choose), p.Export(INTEGER, p.ResultRef("choose"))
            ),
            (flag_function,),
        )
    )
    opened = accept(
        r.rebuild((), programs), replace(start(programs), company=COMPANY), programs
    )
    old = response(opened.state)
    changed = accept(
        opened.state,
        e.CorrectResult(
            meta(opened.state, "change", "admin"),
            e.WorkRevision(e.WorkAddress("case", "flag"), 1),
            action("change", "admin", "corrector"),
            p.BoolValue(False),
        ),
        programs,
    )
    assert changed.state.tasks[old.task].status == "superseded"
    assert old.task.work.address not in changed.state.work
    assert (
        next(
            task for task in changed.state.tasks.values() if task.status == "open"
        ).ref.work.address.node_id
        == "new"
    )
    assert r.decide(
        changed.state, replace(old, meta=meta(changed.state, "late")), programs
    ) == r.Refused("unknown_work")
    assert r.rebuild(opened.events + changed.events, programs) == changed.state


def test_replay_cannot_omit_response_action() -> None:
    state, history, programs = setup()
    result = accept(state, response(state), programs)
    events = tuple(
        event for event in result.events if not isinstance(event.payload, e.HumanActed)
    )
    events = tuple(replace(event, ordinal=index) for index, event in enumerate(events))
    events = events[:-1] + (replace(events[-1], payload=e.BatchCompleted(len(events))),)
    with pytest.raises(r.ReplayError):
        r.rebuild(history + events, programs)


@pytest.mark.parametrize(
    "pin",
    [
        "company_id",
        "prompt_revision",
        "record_revision",
        "schema",
        "inputs",
        "work",
        "artifact",
    ],
)
def test_recording_boundary_binds_every_request_pin(pin: str) -> None:
    import json

    from dex.recordings import RecordingError, parse_recording, request_digest

    programs = catalog(ai_program())
    state = accept(
        r.rebuild((), programs), replace(start(programs), company=COMPANY), programs
    ).state
    request = state.work[e.WorkAddress("case", "ai")].request
    assert request is not None
    changed: e.RecordingRequest
    if pin == "schema":
        changed = replace(request, schema=p.Scalar.TEXT)
    elif pin == "inputs":
        changed = replace(
            request,
            inputs=(
                e.ConsumedInput(
                    ("input", "x"), p.Literal(p.IntValue(1)), p.IntValue(1), None
                ),
            ),
        )
    elif pin == "work":
        changed = replace(request, work=replace(request.work, revision=2))
    elif pin == "artifact":
        changed = replace(request, artifact=replace(request.artifact, revision="other"))
    elif pin == "company_id":
        changed = replace(request, company_id="other")
    elif pin == "prompt_revision":
        changed = replace(request, prompt_revision="other")
    else:
        changed = replace(request, record_revision="other")
    text = json.dumps(
        {
            "format": "dex-recording-1",
            "request_digest": request_digest(changed),
            "recording_id": "one",
            "model": "recorded",
            "input_tokens": 1,
            "output_tokens": 1,
            "value": 3,
            "failure": None,
        }
    )
    with pytest.raises(RecordingError, match="recording_request"):
        parse_recording(text, request)


def test_recording_file_schema_failure_and_unknown_identity_reach_human(
    tmp_path: Path,
) -> None:
    import json

    from dex.recordings import load_recording, request_digest

    program = ai_program()
    assert isinstance(program.root, p.Sequence)
    ai = program.root.children[0]
    assert isinstance(ai, p.AiStep)
    result_schema = p.ReferenceSchema("Entry", "key")
    schema = p.ai_outcome_schema(result_schema)
    ai = replace(
        ai, result_schema=result_schema, metadata=replace(ai.metadata, output=schema)
    )
    program = replace(
        program,
        root=replace(program.root, children=(ai,) + program.root.children[1:]),
        schemas=(schema, p.RecordSchema("Entry", (p.Field("key", p.Scalar.TEXT),))),
    )
    programs = catalog(program)
    initial = accept(
        r.rebuild((), programs), replace(start(programs), company=COMPANY), programs
    )
    request = initial.state.work[e.WorkAddress("case", "ai")].request
    assert request is not None
    for index, content in enumerate(
        ("invalid", {"record": "Entry", "key_field": "key", "key": "foreign"})
    ):
        path = tmp_path / f"recording-{index}.json"
        path.write_text(
            json.dumps(
                {
                    "format": "dex-recording-1",
                    "request_digest": request_digest(request),
                    "recording_id": str(index),
                    "model": "recorded",
                    "input_tokens": 1,
                    "output_tokens": 1,
                    "value": content,
                    "failure": None,
                }
            )
        )
        recording = load_recording(path, request)
        result = accept(
            initial.state,
            e.SupplyRecording(meta(initial.state, str(index)), recording),
            programs,
        )
        assert result.state.cases["case"].status == "waiting"
        assert (
            next(iter(result.state.tasks.values())).ref.work.address.node_id
            == "fallback"
        )
        assert len(result.state.actions) == 0


def test_reassigned_actor_can_answer_current_request() -> None:
    state, history, programs = setup()
    original = response(state)
    assigned = accept(
        state,
        e.ReassignTask(
            meta(state, "assign", "admin"),
            original.task,
            action("assign", "admin", "task_admin"),
            "bob",
        ),
        programs,
    )
    current = response(assigned.state)
    answer = replace(
        current, meta=meta(assigned.state, "bob", "bob"), action=action("bob", "bob")
    )
    result = accept(assigned.state, answer, programs)
    assert result.state.tasks[original.task].status == "superseded"
    assert result.state.tasks[current.task].status == "answered"
    assert result.state.cases["case"].status == "succeeded"
    assert (
        r.rebuild(history + assigned.events + result.events, programs) == result.state
    )


def test_naive_policy_and_observation_times_are_refused() -> None:
    state, _, programs = setup()
    company = replace(
        COMPANY,
        memberships=(
            replace(COMPANY.memberships[0], valid_from=NOW.replace(tzinfo=None)),
        ),
    )
    assert r.decide(
        r.rebuild((), programs), replace(start(programs), company=company), programs
    ) == r.Refused("policy_time")
    command = response(state)
    command = replace(
        command, meta=replace(command.meta, observed_at=NOW.replace(tzinfo=None))
    )
    assert r.decide(state, command, programs) == r.Refused("decision_time")


@pytest.mark.parametrize(
    "kind", ["response", "reassign", "cancel", "correct", "recording"]
)
def test_tight_event_budget_refuses_atomically_and_action_can_be_retried(
    kind: str,
) -> None:
    if kind == "recording":
        programs = catalog(ai_program())
        opened = accept(
            r.rebuild((), programs), replace(start(programs), company=COMPANY), programs
        )
        state, history = opened.state, opened.events
        request = state.work[e.WorkAddress("case", "ai")].request
        assert request is not None
        command: e.RuntimeCommand = e.SupplyRecording(
            meta(state, "recording"),
            e.Recording(request, "one", "model", 1, 1, p.IntValue(7), None),
        )
    else:
        state, history, programs = setup(
            code("source", p.Literal(p.IntValue(1))) if kind == "correct" else None
        )
        if kind == "correct":
            command = e.CorrectResult(
                meta(state, "correct", "admin"),
                e.WorkRevision(e.WorkAddress("case", "source"), 1),
                action("correct", "admin", "corrector"),
                p.IntValue(2),
            )
        else:
            answer = response(state)
            command = answer
            if kind == "reassign":
                command = e.ReassignTask(
                    meta(state, "reassign", "admin"),
                    answer.task,
                    action("reassign", "admin", "task_admin"),
                    "bob",
                )
            elif kind == "cancel":
                command = e.CancelTask(
                    meta(state, "cancel", "admin"),
                    answer.task,
                    action("cancel", "admin", "task_admin"),
                )
    refused = r.decide(
        state, replace(command, bounds=e.ActivationBounds(events=3)), programs
    )
    assert refused == r.Refused("event_limit")
    assert r.rebuild(history, programs) == state
    accepted = accept(state, command, programs)
    assert accept(accepted.state, command, programs).events == ()
    assert r.rebuild(history + accepted.events, programs) == accepted.state


def test_supplied_response_usage_is_aggregate_and_replay_enforced() -> None:
    state, history, programs = setup(human(schema=p.Scalar.TEXT))
    command = replace(response(state), value=p.TextValue("x" * 1000))
    assert r.decide(
        state,
        replace(command, bounds=e.ActivationBounds(work=1001, allocations=5000)),
        programs,
    ) == r.Refused("work_limit")
    answered = accept(state, command, programs)
    settled = next(
        event.payload
        for event in answered.events
        if isinstance(event.payload, e.CaseSettled)
    )
    assert settled.usage == lang.Usage(1004, 4001)
    damaged = tuple(
        replace(event, payload=replace(event.payload, usage=lang.Usage(3, 0)))
        if isinstance(event.payload, e.CaseSettled)
        else event
        for event in answered.events
    )
    with pytest.raises(r.ReplayError, match="usage_bounds"):
        r.rebuild(history + damaged, programs)
    assert accept(answered.state, command, programs).events == ()


@pytest.mark.parametrize(
    "value,reason",
    [
        ("9" * 5000, "recording_json"),
        ("NaN", "recording_number"),
        ('0,"value":1', "recording_duplicate_field"),
    ],
    ids=["oversized_integer", "nonfinite", "duplicate"],
)
def test_recording_json_errors_have_stable_boundary_reasons(
    value: str, reason: str
) -> None:
    import json

    from dex.recordings import RecordingError, parse_recording, request_digest

    programs = catalog(ai_program())
    state = accept(
        r.rebuild((), programs), replace(start(programs), company=COMPANY), programs
    ).state
    request = state.work[e.WorkAddress("case", "ai")].request
    assert request is not None
    text = json.dumps(
        {
            "format": "dex-recording-1",
            "request_digest": request_digest(request),
            "recording_id": "one",
            "model": "model",
            "input_tokens": 1,
            "output_tokens": 1,
            "value": "PLACEHOLDER",
            "failure": None,
        }
    ).replace('"PLACEHOLDER"', value)
    with pytest.raises(RecordingError, match=reason):
        parse_recording(text, request)


def test_supplied_recording_allocation_is_aggregate_and_replay_enforced() -> None:
    program = ai_program()
    root = program.root
    assert isinstance(root, p.Sequence)
    ai = root.children[0]
    assert isinstance(ai, p.AiStep)
    outcome = p.ai_outcome_schema(p.Scalar.TEXT)
    ai = replace(
        ai, metadata=replace(ai.metadata, output=outcome), result_schema=p.Scalar.TEXT
    )
    programs = catalog(
        replace(
            program,
            root=replace(root, children=(ai, *root.children[1:])),
            schemas=(outcome,),
        )
    )
    opened = accept(
        r.rebuild((), programs), replace(start(programs), company=COMPANY), programs
    )
    state = opened.state
    request = state.work[e.WorkAddress("case", "ai")].request
    assert request is not None
    recording = e.Recording(
        request, "one", "model", 1, 1, p.TextValue("x" * 1000), None
    )
    command = e.SupplyRecording(meta(state, "recording"), recording)
    assert r.decide(
        state,
        replace(command, bounds=e.ActivationBounds(work=5000, allocations=1000)),
        programs,
    ) == r.Refused("allocation_limit")
    assert r.rebuild(opened.events, programs) == state
    accepted = accept(state, command, programs)
    settled = next(
        event.payload
        for event in accepted.events
        if isinstance(event.payload, e.CaseSettled)
    )
    assert settled.usage.allocations >= 4001
    assert settled.usage.work >= 1001
    damaged = tuple(
        replace(event, payload=replace(event.payload, usage=lang.Usage(80, 333)))
        if isinstance(event.payload, e.CaseSettled)
        else event
        for event in accepted.events
    )
    with pytest.raises(r.ReplayError, match="usage_bounds"):
        r.rebuild(opened.events + damaged, programs)
    assert accept(accepted.state, command, programs).events == ()
    assert r.rebuild(opened.events + accepted.events, programs) == accepted.state

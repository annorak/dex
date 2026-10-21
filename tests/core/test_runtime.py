import os
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, date, datetime
from hashlib import sha256
from pathlib import Path

import pytest

from dex.core import events as e
from dex.core import language as lang
from dex.core import program as p
from dex.core import runtime as r

TEXT = "Use the declared result."
PIN = p.SourcePin(
    "guide",
    "r1",
    sha256(TEXT.encode()).hexdigest(),
    "text",
    sha256(TEXT.encode()).hexdigest(),
)
CITATION = p.Citation(PIN, "all", "paragraph", 0, len(TEXT), TEXT)
SOURCES = p.SourceCatalog(
    (p.SourceExtraction(PIN, TEXT, (p.Section("all", "paragraph", 0, len(TEXT)),)),)
)
NOW = datetime(2026, 1, 1, tzinfo=UTC)
DEFAULT_BOUNDS = e.ActivationBounds()
INTEGER = p.Scalar.INTEGER
COUNTER = p.RecordSchema(
    "Counter", (p.Field("count", INTEGER), p.Field("ready", p.Scalar.BOOLEAN))
)
ENTRY = p.RecordSchema(
    "Entry", (p.Field("key", p.Scalar.TEXT), p.Field("value", INTEGER))
)


def counter(count: int, ready: bool) -> p.RecordValue:
    return p.RecordValue(
        "Counter",
        (
            p.NamedValue("count", p.IntValue(count)),
            p.NamedValue("ready", p.BoolValue(ready)),
        ),
    )


def entry(key: str, value: int) -> p.RecordValue:
    return p.RecordValue(
        "Entry",
        (
            p.NamedValue("key", p.TextValue(key)),
            p.NamedValue("value", p.IntValue(value)),
        ),
    )


def code(
    name: str,
    reference: p.Input,
    schema: p.Schema = INTEGER,
    function: str = "identity",
) -> p.CodeStep:
    return p.CodeStep(
        p.StepMetadata(
            name,
            "behavior-" + name,
            TEXT,
            (CITATION,),
            (p.Binding("value", schema, reference),),
            schema,
        ),
        function,
    )


def identity(schema: p.Schema, sample: p.Value) -> p.FunctionDeclaration:
    return p.FunctionDeclaration(
        "identity",
        (p.Field("value", schema),),
        schema,
        p.FunctionBody("restricted-1", "return value"),
        (p.FunctionTest("saved", (p.NamedValue("value", sample),), sample),),
    )


def draft(
    root: p.Node,
    functions: tuple[p.FunctionDeclaration, ...] = (),
    inputs: tuple[p.Field, ...] = (),
    schemas: tuple[p.RecordSchema, ...] = (),
    rules: tuple[p.DatedRule, ...] = (),
    revision: str = "r1",
) -> p.ProgramDraft:
    return p.ProgramDraft(
        "sample", revision, schemas, inputs, root, functions, rules, ()
    )


def catalog(program: p.ProgramDraft) -> r.ProgramCatalog:
    result = p.verify_program(program, SOURCES, lang.DEFAULT_LIMITS)
    assert isinstance(result, p.ExecutionPending), result
    return r.ProgramCatalog(
        (r.ArtifactEntry(r.artifact_pin(result.artifact), result.artifact),)
    )


def start(
    programs: r.ProgramCatalog,
    facts: tuple[p.NamedValue, ...] = (),
    business_date: date = date(2026, 1, 1),
    bounds: e.ActivationBounds = DEFAULT_BOUNDS,
) -> e.StartSandbox:
    return e.StartSandbox(
        e.CommandMeta("start", "tester", NOW, NOW, 0),
        "case",
        programs.entries[0].pin,
        facts,
        business_date,
        bounds,
    )


def execute(
    program: p.ProgramDraft,
    facts: tuple[p.NamedValue, ...] = (),
    business_date: date = date(2026, 1, 1),
    bounds: e.ActivationBounds = DEFAULT_BOUNDS,
) -> tuple[r.WorkspaceState, tuple[e.RuntimeEvent, ...], r.ProgramCatalog]:
    programs = catalog(program)
    result = r.decide(
        r.rebuild((), programs), start(programs, facts, business_date, bounds), programs
    )
    assert isinstance(result, r.Accepted), result
    return r.rebuild(result.events, programs), result.events, programs


def root_value(state: r.WorkspaceState) -> p.Value | None:
    roots = [work for work in state.work.values() if work.opened.parent is None]
    assert len(roots) == 1
    completed = roots[0].completed
    return None if completed is None else completed.value


def sequence_program() -> p.ProgramDraft:
    first = code("first", p.ProgramInputRef("input"))
    second = code("second", p.ResultRef("first"))
    return draft(
        p.Sequence(
            "sequence", (first, second), p.Export(INTEGER, p.ResultRef("second"))
        ),
        (identity(INTEGER, p.IntValue(1)),),
        (p.Field("input", INTEGER),),
    )


def choose_program() -> p.ProgramDraft:
    yes = code("yes", p.Literal(p.IntValue(7)))
    no = code("no", p.Literal(p.IntValue(9)))
    root = p.Choose(
        "choose",
        p.Literal(p.BoolValue(True)),
        p.Branch(yes, p.Export(INTEGER, p.ResultRef("yes"))),
        p.Branch(no, p.Export(INTEGER, p.ResultRef("no"))),
        INTEGER,
    )
    return draft(root, (identity(INTEGER, p.IntValue(1)),))


def repeat_program(limit: int, event: bool = False) -> p.ProgramDraft:
    body = p.CodeStep(
        p.StepMetadata(
            "advance",
            "advance-v1",
            TEXT,
            (CITATION,),
            (
                p.Binding("state", COUNTER, p.LocalRef("repeat", "state")),
                p.Binding("limit", INTEGER, p.Literal(p.IntValue(limit))),
            ),
            COUNTER,
        ),
        "advance",
    )
    function = p.FunctionDeclaration(
        "advance",
        (p.Field("state", COUNTER), p.Field("limit", INTEGER)),
        COUNTER,
        p.FunctionBody(
            "restricted-1",
            "count = state.count + 1\nreturn Counter(count, count >= limit)",
        ),
        (
            p.FunctionTest(
                "saved",
                (
                    p.NamedValue("state", counter(0, False)),
                    p.NamedValue("limit", p.IntValue(2)),
                ),
                counter(1, False),
            ),
        ),
    )
    root = p.Repeat(
        "repeat",
        p.Export(COUNTER, p.Literal(counter(0, False))),
        p.Branch(body, p.Export(COUNTER, p.ResultRef("advance"))),
        p.ResultRef("advance", ("ready",)),
        p.EventRepeat("continue") if event else p.FiniteRepeat(limit),
    )
    return draft(root, (function,), schemas=(COUNTER,))


def each_program() -> p.ProgramDraft:
    schema = p.KeyedSchema(ENTRY, "key")
    body = code("copy", p.LocalRef("each", "item"), ENTRY)
    root = p.Each(
        "each",
        p.ProgramInputRef("entries"),
        schema,
        schema,
        p.Branch(body, p.Export(ENTRY, p.ResultRef("copy"))),
    )
    return draft(
        root, (identity(ENTRY, entry("a", 1)),), (p.Field("entries", schema),), (ENTRY,)
    )


def policy_program(revision: str = "r1", future: int = 20) -> p.ProgramDraft:
    root = code("policy", p.RuleInputRef("limit", ()))
    rules = (
        p.DatedRule(
            "before",
            "limit",
            (),
            date(2026, 1, 1),
            date(2026, 2, 1),
            p.Export(INTEGER, p.Literal(p.IntValue(10))),
            (CITATION,),
        ),
        p.DatedRule(
            "after",
            "limit",
            (),
            date(2026, 2, 1),
            None,
            p.Export(INTEGER, p.Literal(p.IntValue(future))),
            (CITATION,),
        ),
    )
    return draft(
        root, (identity(INTEGER, p.IntValue(1)),), rules=rules, revision=revision
    )


def test_sequence_provenance_and_determinism() -> None:
    state, events, programs = execute(
        sequence_program(), (p.NamedValue("input", p.IntValue(42)),)
    )
    assert root_value(state) == p.IntValue(42)
    assert state.cases["case"].status == "succeeded"
    completed = state.work[e.WorkAddress("case", "second")].completed
    assert completed is not None
    assert completed.inputs[0].producer == e.WorkAddress("case", "first")
    command = start(programs, (p.NamedValue("input", p.IntValue(42)),))
    assert r.decide(r.rebuild((), programs), command, programs) == r.Accepted(events)
    assert r.decide(state, command, programs) == r.Accepted(())
    assert r.decide(
        state,
        replace(command, facts=(p.NamedValue("input", p.IntValue(43)),)),
        programs,
    ) == r.Refused("command_conflict")


def test_choose_only_opens_selected_branch() -> None:
    state, _, _ = execute(choose_program())
    assert root_value(state) == p.IntValue(7)
    assert {address.node_id for address in state.work} == {"choose", "yes"}


def test_each_reordering_preserves_addresses_and_values() -> None:
    values = (p.KeyedEntry("b", entry("b", 2)), p.KeyedEntry("a", entry("a", 1)))
    one, _, _ = execute(
        each_program(), (p.NamedValue("entries", p.KeyedValue(values)),)
    )
    two, _, _ = execute(
        each_program(),
        (p.NamedValue("entries", p.KeyedValue(tuple(reversed(values)))),),
    )
    assert one.work == two.work
    assert root_value(one) == p.normalized_value(p.KeyedValue(values))
    assert {address.scope[-1].key for address in one.work if address.scope} == {
        "a",
        "b",
    }


def test_repeat_post_test_and_finite_exhaustion() -> None:
    state, _, _ = execute(repeat_program(3))
    assert root_value(state) == p.normalized_value(counter(3, True))
    program = repeat_program(3)
    assert isinstance(program.root, p.Repeat)
    state, _, _ = execute(
        replace(program, root=replace(program.root, bound=p.FiniteRepeat(2)))
    )
    assert state.cases["case"].failure == "repeat_exhausted"
    assert root_value(state) is None


def test_event_repeat_requires_fresh_exact_signal() -> None:
    state, events, programs = execute(repeat_program(3, event=True))
    address = e.WorkAddress("case", "repeat")
    assert state.cases["case"].status == "waiting"
    signal = e.SignalRepeat(
        e.CommandMeta("signal", "tester", NOW, NOW, state.revision),
        address,
        0,
        "continue",
    )
    assert r.decide(state, replace(signal, event="other"), programs) == r.Refused(
        "stale_signal"
    )
    assert r.decide(state, signal, r.ProgramCatalog(())) == r.Refused(
        "missing_artifact"
    )
    result = r.decide(state, signal, programs)
    assert isinstance(result, r.Accepted)
    state = r.rebuild(events + result.events, programs)
    waiting = state.work[address].waiting
    assert waiting is not None
    assert waiting.iteration == 1
    assert waiting.carried == p.normalized_value(counter(2, False))
    assert r.decide(state, signal, programs) == r.Accepted(())
    assert r.decide(
        state,
        replace(
            signal,
            meta=replace(
                signal.meta, command_id="stale", expected_revision=state.revision
            ),
        ),
        programs,
    ) == r.Refused("stale_signal")
    second = replace(
        signal,
        meta=replace(
            signal.meta, command_id="second", expected_revision=state.revision
        ),
        iteration=1,
    )
    completed = r.decide(state, second, programs)
    assert isinstance(completed, r.Accepted)
    assert root_value(
        r.rebuild(events + result.events + completed.events, programs)
    ) == p.normalized_value(counter(3, True))


@pytest.mark.parametrize(
    ("business_date", "expected", "rule"),
    [(date(2026, 1, 31), 10, "before"), (date(2026, 2, 1), 20, "after")],
)
def test_half_open_policy_dates(business_date: date, expected: int, rule: str) -> None:
    state, events, _ = execute(policy_program(), business_date=business_date)
    assert root_value(state) == p.IntValue(expected)
    bindings = [
        event.payload.consumed
        for event in events
        if isinstance(event.payload, e.InputBound)
    ]
    assert bindings[0].rule_ids == (rule,)


def test_old_artifact_and_date_survive_new_catalog() -> None:
    state, events, programs = execute(policy_program(), business_date=date(2026, 1, 31))
    newer = catalog(policy_program("r2", 99))
    combined = r.ProgramCatalog(programs.entries + newer.entries)
    assert r.rebuild(events, combined) == state
    assert root_value(state) == p.IntValue(10)


def test_rebuild_never_executes_code(monkeypatch: pytest.MonkeyPatch) -> None:
    state, events, programs = execute(
        sequence_program(), (p.NamedValue("input", p.IntValue(42)),)
    )

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("Replay dispatched a function")

    monkeypatch.setattr(lang, "execute_function", forbidden)
    assert r.rebuild(events, programs) == state


@pytest.mark.parametrize(
    "corruption", ["truncate", "version", "ordinal", "artifact", "producer"]
)
def test_rebuild_rejects_invalid_complete_log(corruption: str) -> None:
    _, events, programs = execute(
        sequence_program(), (p.NamedValue("input", p.IntValue(42)),)
    )
    if corruption == "truncate":
        events = events[:-1]
    elif corruption == "version":
        events = (replace(events[0], format_version=2),) + events[1:]
    elif corruption == "ordinal":
        events = events[:2] + (replace(events[2], ordinal=9),) + events[3:]
    elif corruption == "artifact":
        programs = r.ProgramCatalog(())
    else:
        index = next(
            index
            for index, event in enumerate(events)
            if isinstance(event.payload, e.InputBound)
            and event.payload.consumed.producer is not None
        )
        payload = events[index].payload
        assert isinstance(payload, e.InputBound)
        events = (
            events[:index]
            + (
                replace(
                    events[index],
                    payload=replace(
                        payload,
                        consumed=replace(
                            payload.consumed, producer=e.WorkAddress("other", "first")
                        ),
                    ),
                ),
            )
            + events[index + 1 :]
        )
    with pytest.raises(r.ReplayError):
        r.rebuild(events, programs)


@pytest.mark.parametrize(
    "bounds",
    [
        e.ActivationBounds(work=50),
        e.ActivationBounds(allocations=20),
        e.ActivationBounds(instances=2),
        e.ActivationBounds(events=8),
    ],
)
def test_aggregate_budget_cannot_produce_partial_success(
    bounds: e.ActivationBounds,
) -> None:
    state, _, _ = execute(repeat_program(20), bounds=bounds)
    assert state.cases["case"].status == "failed"
    assert state.cases["case"].failure is not None
    assert root_value(state) is None


def test_activation_and_ai_remain_unavailable() -> None:
    programs = catalog(choose_program())
    command = e.ActivateProgram(
        e.CommandMeta("activate", "tester", NOW, NOW, 0), programs.entries[0].pin
    )
    assert r.decide(r.rebuild((), programs), command, programs) == r.Refused(
        "unsupported_activation"
    )
    program = choose_program()
    assert isinstance(program.root, p.Choose)
    body = program.root.when_false.body
    assert isinstance(body, p.CodeStep)
    program = replace(
        program,
        root=replace(
            program.root,
            when_false=replace(
                program.root.when_false, body=p.AiStep(body.metadata, "prompt")
            ),
        ),
    )
    programs = catalog(program)
    assert r.decide(r.rebuild((), programs), start(programs), programs) == r.Refused(
        "unsupported_step"
    )


def size_program() -> p.ProgramDraft:
    body = code("advance", p.LocalRef("repeat", "state"), function="increment")
    function = p.FunctionDeclaration(
        "increment",
        (p.Field("value", INTEGER),),
        INTEGER,
        p.FunctionBody("restricted-1", "return value + 1"),
        (
            p.FunctionTest(
                "saved", (p.NamedValue("value", p.IntValue(0)),), p.IntValue(1)
            ),
        ),
    )
    rules = (
        p.DatedRule(
            "continue",
            "done",
            (),
            date(2026, 1, 1),
            None,
            p.Export(p.Scalar.BOOLEAN, p.Literal(p.BoolValue(False))),
            (CITATION,),
        ),
        p.DatedRule(
            "finish",
            "done",
            (p.Constraint("count", INTEGER, p.IntValue(9999)),),
            date(2026, 1, 1),
            None,
            p.Export(p.Scalar.BOOLEAN, p.Literal(p.BoolValue(True))),
            (CITATION,),
        ),
    )
    until = p.RuleInputRef(
        "done", (p.Binding("count", INTEGER, p.ResultRef("advance")),)
    )
    root = p.Repeat(
        "repeat",
        p.Export(INTEGER, p.Literal(p.IntValue(0))),
        p.Branch(body, p.Export(INTEGER, p.ResultRef("advance"))),
        until,
        p.FiniteRepeat(9999),
    )
    return draft(root, (function,), rules=rules)


def test_size_log_is_complete_and_contains_ten_thousand_instances() -> None:
    state, events, programs = execute(size_program())
    assert len(state.work) == 10000
    assert len(events) >= 10000
    assert isinstance(events[-1].payload, e.BatchCompleted)
    assert state.cases["case"].status == "succeeded"
    assert r.rebuild(events, programs) == state


def parallel_program() -> p.ProgramDraft:
    chosen = choose_program()
    repeated = repeat_program(2, event=True)
    output = p.RecordSchema(
        "Joined", (p.Field("chosen", INTEGER), p.Field("progress", COUNTER))
    )
    root = p.Parallel(
        "parallel",
        (
            p.NamedBranch(
                "chosen",
                p.Branch(chosen.root, p.Export(INTEGER, p.ResultRef("choose"))),
            ),
            p.NamedBranch(
                "progress",
                p.Branch(repeated.root, p.Export(COUNTER, p.ResultRef("repeat"))),
            ),
        ),
        output,
    )
    return draft(root, chosen.functions + repeated.functions, schemas=(COUNTER, output))


def waiting_policy_program(revision: str = "r1", earlier: int = 10) -> p.ProgramDraft:
    repeated = repeat_program(2, event=True)
    policy = policy_program(revision)
    rules = (
        replace(
            policy.rules[0],
            consequence=p.Export(INTEGER, p.Literal(p.IntValue(earlier))),
        ),
        policy.rules[1],
    )
    root = p.Sequence(
        "sequence",
        (repeated.root, policy.root),
        p.Export(INTEGER, p.ResultRef("policy")),
    )
    return draft(
        root,
        repeated.functions + policy.functions,
        schemas=(COUNTER,),
        rules=rules,
        revision=revision,
    )


def test_parallel_retains_completed_selected_dependencies() -> None:
    state, history, programs = execute(parallel_program())
    chosen = e.WorkAddress(
        "case", "choose", (e.ScopePart("parallel", "parallel", "chosen"),)
    )
    assert state.work[chosen].completed is not None
    assert root_value(state) is None
    assert all(address.node_id != "no" for address in state.work)
    address = e.WorkAddress(
        "case", "repeat", (e.ScopePart("parallel", "parallel", "progress"),)
    )
    signal = e.SignalRepeat(
        e.CommandMeta("signal", "tester", NOW, NOW, state.revision),
        address,
        0,
        "continue",
    )
    accepted = r.decide(state, signal, programs)
    assert isinstance(accepted, r.Accepted)
    restored = r.rebuild(history + accepted.events, programs)
    assert restored.cases["case"].status == "succeeded"
    assert restored.work[chosen] == state.work[chosen]
    assert not any(
        isinstance(event.payload, e.WorkSucceeded) and event.payload.address == chosen
        for event in accepted.events
    )


def test_rule_first_consumed_after_wait_uses_arrival_pins() -> None:
    state, history, old = execute(
        waiting_policy_program(), business_date=date(2026, 1, 31)
    )
    assert all(
        not isinstance(event.payload, e.InputBound)
        or not event.payload.consumed.rule_ids
        for event in history
    )
    newer = catalog(waiting_policy_program("r2", 99))
    programs = r.ProgramCatalog(old.entries + newer.entries)
    signal = e.SignalRepeat(
        e.CommandMeta("signal", "tester", NOW, NOW, state.revision),
        e.WorkAddress("case", "repeat"),
        0,
        "continue",
    )
    accepted = r.decide(state, signal, programs)
    assert isinstance(accepted, r.Accepted)
    restored = r.rebuild(history + accepted.events, programs)
    assert root_value(restored) == p.IntValue(10)
    completed = restored.work[e.WorkAddress("case", "policy")].completed
    assert completed is not None
    assert completed.inputs[0].rule_ids == ("before",)


def test_nested_each_uses_keyed_lexical_scopes() -> None:
    children = p.KeyedSchema(ENTRY, "key")
    parent = p.RecordSchema(
        "Parent", (p.Field("key", p.Scalar.TEXT), p.Field("children", children))
    )
    parents = p.KeyedSchema(parent, "key")
    inner = p.Each(
        "inner",
        p.LocalRef("outer", "item", ("children",)),
        children,
        children,
        p.Branch(
            code("copy", p.LocalRef("inner", "item"), ENTRY),
            p.Export(ENTRY, p.ResultRef("copy")),
        ),
    )
    body = p.Sequence("body", (inner,), p.Export(parent, p.LocalRef("outer", "item")))
    root = p.Each(
        "outer",
        p.ProgramInputRef("parents"),
        parents,
        parents,
        p.Branch(body, p.Export(parent, p.ResultRef("body"))),
    )
    program = draft(
        root,
        (identity(ENTRY, entry("x", 1)),),
        (p.Field("parents", parents),),
        (ENTRY, parent),
    )
    entries = tuple(
        p.KeyedEntry(
            key,
            p.RecordValue(
                "Parent",
                (
                    p.NamedValue("key", p.TextValue(key)),
                    p.NamedValue(
                        "children",
                        p.KeyedValue(
                            (p.KeyedEntry("same.key", entry("same.key", value)),)
                        ),
                    ),
                ),
            ),
        )
        for key, value in (("a.b", 1), ("a", 2))
    )
    state, history, programs = execute(
        program, (p.NamedValue("parents", p.KeyedValue(entries)),)
    )
    copies = [address for address in state.work if address.node_id == "copy"]
    assert len(copies) == 2
    assert {address.scope for address in copies} == {
        (e.ScopePart("outer", "each", key), e.ScopePart("inner", "each", "same.key"))
        for key in ("a.b", "a")
    }
    assert root_value(state) == p.normalized_value(p.KeyedValue(entries))
    assert r.rebuild(history, programs) == state


@pytest.mark.parametrize("seed", ["1", "37"])
def test_artifact_pin_is_stable_across_processes(seed: str) -> None:
    expected = catalog(sequence_program()).entries[0].pin.digest
    script = "import runpy; h=runpy.run_path('tests/core/test_runtime.py'); print(h['catalog'](h['sequence_program']()).entries[0].pin.digest)"
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[2],
        env={**os.environ, "PYTHONHASHSEED": seed},
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == expected


def test_artifact_pin_covers_content_and_versions() -> None:
    artifact = catalog(sequence_program()).entries[0].artifact
    original = r.artifact_pin(artifact)
    variants = (
        replace(artifact, draft=replace(artifact.draft, revision="r2")),
        replace(artifact, verifier_version="future"),
        replace(artifact, sources=p.SourceCatalog(())),
        replace(
            artifact,
            checked_functions=replace(
                artifact.checked_functions,
                limits=replace(artifact.checked_functions.limits, work=1000),
            ),
        ),
        replace(
            artifact,
            draft=replace(
                artifact.draft,
                root=p.Sequence(
                    "empty", (), p.Export(INTEGER, p.Literal(p.IntValue(1)))
                ),
            ),
        ),
    )
    assert all(r.artifact_pin(item) != original for item in variants)
    with pytest.raises(r.ReplayError, match="artifact_identity"):
        r.ProgramCatalog((r.ArtifactEntry(original, variants[0]),))
    with pytest.raises(r.ReplayError, match="artifact_version"):
        r.ProgramCatalog((r.ArtifactEntry(r.artifact_pin(variants[1]), variants[1]),))


def test_empty_controls() -> None:
    empty = p.RecordSchema("Empty", ())
    parallel, _, _ = execute(draft(p.Parallel("parallel", (), empty), schemas=(empty,)))
    assert root_value(parallel) == p.RecordValue("Empty", ())
    sequence, _, _ = execute(
        draft(p.Sequence("sequence", (), p.Export(INTEGER, p.Literal(p.IntValue(8)))))
    )
    assert root_value(sequence) == p.IntValue(8)
    each, _, _ = execute(each_program(), (p.NamedValue("entries", p.KeyedValue(())),))
    assert root_value(each) == p.KeyedValue(())


def test_rule_scope_uses_each_key_and_retains_equal_winners() -> None:
    program = each_program()
    assert isinstance(program.root, p.Each)
    reference = p.RuleInputRef(
        "entry", (p.Binding("key", p.Scalar.TEXT, p.LocalRef("each", "key")),)
    )
    rules = tuple(
        p.DatedRule(
            name,
            "entry",
            (p.Constraint("key", p.Scalar.TEXT, p.TextValue(key)),),
            date(2026, 1, 1),
            None,
            p.Export(ENTRY, p.Literal(entry(key, amount))),
            (CITATION,),
        )
        for name, key, amount in (
            ("a-first", "a", 7),
            ("a-second", "a", 7),
            ("b-only", "b", 9),
        )
    )
    body = code("copy", reference, ENTRY)
    program = replace(
        program,
        root=replace(program.root, body=replace(program.root.body, body=body)),
        rules=rules,
    )
    facts = (
        p.NamedValue(
            "entries",
            p.KeyedValue(
                (p.KeyedEntry("a", entry("a", 1)), p.KeyedEntry("b", entry("b", 2)))
            ),
        ),
    )
    state, events, _ = execute(program, facts)
    assert root_value(state) == p.KeyedValue(
        (p.KeyedEntry("a", entry("a", 7)), p.KeyedEntry("b", entry("b", 9)))
    )
    bound = [
        event.payload.consumed
        for event in events
        if isinstance(event.payload, e.InputBound) and event.payload.consumed.rule_ids
    ]
    assert [item.rule_ids for item in bound] == [("a-first", "a-second"), ("b-only",)]
    assert [item.rule_scope for item in bound] == [
        (p.NamedValue("key", p.TextValue("a")),),
        (p.NamedValue("key", p.TextValue("b")),),
    ]


def test_replay_rejects_changed_control_export() -> None:
    _, events, programs = execute(choose_program())
    index = next(
        index
        for index, event in enumerate(events)
        if isinstance(event.payload, e.WorkSucceeded)
        and event.payload.address.node_id == "choose"
    )
    payload = events[index].payload
    assert isinstance(payload, e.WorkSucceeded)
    changed = (
        events[:index]
        + (replace(events[index], payload=replace(payload, value=p.IntValue(999))),)
        + events[index + 1 :]
    )
    with pytest.raises(r.ReplayError, match="export_value"):
        r.rebuild(changed, programs)


@pytest.mark.parametrize(
    ("key", "failure"),
    [("", "input_type"), ("x" * 65537, "string_limit")],
    ids=("empty", "oversized"),
)
def test_control_reference_constraints(key: str, failure: str) -> None:
    schema = p.ReferenceSchema("Entry", "key")
    program = draft(
        p.Sequence("root", (), p.Export(schema, p.ProgramInputRef("reference"))),
        inputs=(p.Field("reference", schema),),
        schemas=(ENTRY,),
    )
    programs = catalog(program)
    command = start(
        programs, (p.NamedValue("reference", p.ResolvedRefValue("Entry", "key", key)),)
    )
    assert r.decide(r.rebuild((), programs), command, programs) == r.Refused(failure)


@pytest.mark.parametrize("forged_ids", [("default",), ("first",)])
def test_replay_requires_complete_most_specific_rules(
    forged_ids: tuple[str, ...],
) -> None:
    reference = p.RuleInputRef(
        "amount", (p.Binding("key", p.Scalar.TEXT, p.Literal(p.TextValue("a"))),)
    )
    default = p.DatedRule(
        "default",
        "amount",
        (),
        date(2026, 1, 1),
        None,
        p.Export(INTEGER, p.Literal(p.IntValue(10))),
        (CITATION,),
    )
    first = replace(
        default,
        rule_id="first",
        scope=(p.Constraint("key", p.Scalar.TEXT, p.TextValue("a")),),
        consequence=p.Export(INTEGER, p.Literal(p.IntValue(20))),
    )
    program = draft(
        p.Sequence("root", (), p.Export(INTEGER, reference)),
        rules=(default, first, replace(first, rule_id="second")),
    )
    state, events, programs = execute(program)
    assert root_value(state) == p.IntValue(20)
    assert r.rebuild(events, programs) == state
    forged_value = p.IntValue(10 if forged_ids == ("default",) else 20)
    changed: list[e.RuntimeEvent] = []
    for event in events:
        payload = event.payload
        if isinstance(payload, e.InputBound) and payload.consumed.rule_ids:
            payload = replace(
                payload,
                consumed=replace(
                    payload.consumed, rule_ids=forged_ids, value=forged_value
                ),
            )
        elif isinstance(payload, e.WorkSucceeded):
            payload = replace(
                payload,
                value=forged_value,
                inputs=tuple(
                    replace(item, rule_ids=forged_ids, value=forged_value)
                    if item.rule_ids
                    else item
                    for item in payload.inputs
                ),
            )
        changed.append(replace(event, payload=payload))
    with pytest.raises(r.ReplayError, match="rule_provenance"):
        r.rebuild(tuple(changed), programs)


def test_replay_enforces_recorded_event_bound() -> None:
    _, events, programs = execute(
        sequence_program(), (p.NamedValue("input", p.IntValue(1)),)
    )
    payload = events[0].payload
    assert isinstance(payload, e.BatchStarted)
    command = replace(payload.command, bounds=replace(payload.command.bounds, events=3))
    changed = (replace(events[0], payload=e.BatchStarted(command)),) + events[1:]
    assert len(changed) > command.bounds.events
    with pytest.raises(r.ReplayError, match="event_limit"):
        r.rebuild(changed, programs)

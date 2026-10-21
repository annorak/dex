from dataclasses import replace
from datetime import UTC, date, datetime
from hashlib import sha256

import pytest

from dex.core import program as p
from dex.core.language import DEFAULT_LIMITS

TEXT = "a😀éZ"
PIN = p.SourcePin(
    "source", "revision", "a" * 64, "extraction", sha256(TEXT.encode()).hexdigest()
)
CITATION = p.Citation(PIN, "section", "paragraph-1", 1, 4, TEXT[1:4])
SOURCES = p.SourceCatalog(
    (p.SourceExtraction(PIN, TEXT, (p.Section("section", "paragraph-1", 1, 4),)),)
)
RECORD = p.RecordSchema(
    "Entry", (p.Field("key", p.Scalar.TEXT), p.Field("amount", p.Scalar.MONEY))
)
ENTRY = p.RecordValue(
    "Entry",
    (
        p.NamedValue("key", p.TextValue("stable-key")),
        p.NamedValue("amount", p.MoneyValue(125)),
    ),
)


def leaf(
    name: str,
    bindings: tuple[p.Binding, ...] = (),
    output: p.Schema = p.Scalar.BOOLEAN,
    changes: tuple[p.ChangeDeclaration, ...] = (),
) -> p.AiStep:
    return p.AiStep(
        p.StepMetadata(
            name,
            "behavior-" + name,
            "Read the supplied data.",
            (CITATION,),
            bindings,
            output,
            changes,
        ),
        "prompt-revision",
    )


def draft(
    node: p.Node,
    inputs: tuple[p.Field, ...] = (),
    schemas: tuple[p.RecordSchema, ...] = (),
    rules: tuple[p.DatedRule, ...] = (),
    scenarios: tuple[p.ProgramScenario, ...] = (),
    functions: tuple[p.FunctionDeclaration, ...] = (),
) -> p.ProgramDraft:
    return p.ProgramDraft(
        "program", "revision", schemas, inputs, node, functions, rules, scenarios
    )


def codes(
    program: p.ProgramDraft, sources: p.SourceCatalog = SOURCES
) -> tuple[str, ...]:
    result = p.verify_program(program, sources, DEFAULT_LIMITS)
    assert isinstance(result, p.StructuralFailure)
    return tuple(item.code for item in result.diagnostics)


def pending(program: p.ProgramDraft) -> p.ExecutionPending:
    result = p.verify_program(program, SOURCES, DEFAULT_LIMITS)
    assert isinstance(result, p.ExecutionPending)
    assert result.artifact.draft == program
    assert result.artifact.sources == SOURCES
    assert set(result.missing_checks) == set(p.MissingCheck) - {p.MissingCheck.LANGUAGE}
    return result


@pytest.mark.parametrize(
    ("schema", "value"),
    [
        (p.Scalar.BOOLEAN, p.BoolValue(True)),
        (p.Scalar.INTEGER, p.IntValue(12)),
        (p.Scalar.TEXT, p.TextValue("text")),
        (p.Scalar.DATE, p.DateValue(date(2026, 1, 1))),
        (p.Scalar.MONEY, p.MoneyValue(125)),
        (p.OptionalSchema(p.Scalar.TEXT), p.AbsentValue()),
        (p.OptionalSchema(p.Scalar.TEXT), p.PresentValue(p.TextValue("present"))),
        (
            p.TaggedSchema((p.Field("known", p.Scalar.TEXT),)),
            p.TaggedValue("known", p.TextValue("value")),
        ),
        (RECORD, ENTRY),
        (
            p.KeyedSchema(RECORD, "key"),
            p.KeyedValue((p.KeyedEntry("stable-key", ENTRY),)),
        ),
        (
            p.ReferenceSchema("Entry", "key"),
            p.ResolvedRefValue("Entry", "key", "stable-key"),
        ),
        (p.UnresolvedSchema(), p.UnresolvedTextValue("unmatched text")),
    ],
)
def test_schema_variants_retain_values(schema: p.Schema, value: p.Value) -> None:
    program = draft(
        leaf("read", (p.Binding("data", schema, p.Literal(value)),)), schemas=(RECORD,)
    )
    pending(program)


@pytest.mark.parametrize(
    ("schema", "value"),
    [
        (p.Scalar.INTEGER, p.IntValue(True)),
        (p.Scalar.MONEY, p.MoneyValue(True)),
        (p.Scalar.INTEGER, p.MoneyValue(1)),
        (p.Scalar.MONEY, p.IntValue(1)),
        (p.Scalar.DATE, p.DateValue(datetime(2026, 1, 1))),
        (p.OptionalSchema(p.Scalar.TEXT), p.TextValue("implicit")),
        (
            p.TaggedSchema((p.Field("known", p.Scalar.TEXT),)),
            p.TaggedValue("missing", p.TextValue("value")),
        ),
        (p.ReferenceSchema("Entry", "key"), p.UnresolvedTextValue("stable-key")),
        (p.ReferenceSchema("Entry", "key"), p.TextValue("stable-key")),
        (
            p.ReferenceSchema("Entry", "key"),
            p.ResolvedRefValue("Other", "key", "stable-key"),
        ),
    ],
)
def test_incompatible_values_are_rejected(schema: p.Schema, value: p.Value) -> None:
    program = draft(
        leaf("read", (p.Binding("data", schema, p.Literal(value)),)), schemas=(RECORD,)
    )
    assert "value_type" in codes(program)


def test_keyed_values_require_unique_matching_record_keys() -> None:
    schema = p.KeyedSchema(RECORD, "key")
    for entries, code in [
        (
            (p.KeyedEntry("stable-key", ENTRY), p.KeyedEntry("stable-key", ENTRY)),
            "duplicate_identity",
        ),
        ((p.KeyedEntry("another-key", ENTRY),), "record_key"),
    ]:
        node = leaf(
            "read", (p.Binding("data", schema, p.Literal(p.KeyedValue(entries))),)
        )
        assert code in codes(draft(node, schemas=(RECORD,)))


def test_record_declarations_and_fields_are_checked() -> None:
    missing = p.ReferenceSchema("Missing", "key")
    assert "unknown_record" in codes(draft(leaf("read", output=missing)))
    duplicate = replace(RECORD, fields=RECORD.fields + (RECORD.fields[0],))
    assert "duplicate_identity" in codes(draft(leaf("read"), schemas=(duplicate,)))
    invalid = p.RecordValue("Entry", (p.NamedValue("key", p.TextValue("stable-key")),))
    node = leaf("read", (p.Binding("data", RECORD, p.Literal(invalid)),))
    assert "record_fields" in codes(draft(node, schemas=(RECORD,)))


def test_sequence_requires_prior_results_with_matching_types() -> None:
    first = leaf("first")
    second = leaf(
        "second", (p.Binding("flag", p.Scalar.BOOLEAN, p.ResultRef("first")),)
    )
    sequence = p.Sequence(
        "sequence", (first, second), p.Export(p.Scalar.BOOLEAN, p.ResultRef("second"))
    )
    pending(draft(sequence))
    assert "reference_scope" in codes(
        draft(replace(sequence, children=(second, first)))
    )
    wrong = leaf("second", (p.Binding("flag", p.Scalar.TEXT, p.ResultRef("first")),))
    assert "reference_type" in codes(draft(replace(sequence, children=(first, wrong))))


def test_child_scope_only_exposes_its_export() -> None:
    inner = p.Sequence(
        "inner", (leaf("hidden"),), p.Export(p.Scalar.BOOLEAN, p.ResultRef("hidden"))
    )
    consumer = leaf(
        "consumer", (p.Binding("flag", p.Scalar.BOOLEAN, p.ResultRef("inner")),)
    )
    outer = p.Sequence(
        "outer", (inner, consumer), p.Export(p.Scalar.BOOLEAN, p.ResultRef("consumer"))
    )
    pending(draft(outer))
    invalid = leaf(
        "consumer", (p.Binding("flag", p.Scalar.BOOLEAN, p.ResultRef("hidden")),)
    )
    assert "reference_scope" in codes(draft(replace(outer, children=(inner, invalid))))


def test_record_paths_preserve_the_field_type() -> None:
    node = leaf(
        "read",
        (p.Binding("amount", p.Scalar.MONEY, p.ProgramInputRef("entry", ("amount",))),),
    )
    pending(draft(node, inputs=(p.Field("entry", RECORD),), schemas=(RECORD,)))
    invalid = leaf(
        "read",
        (p.Binding("amount", p.Scalar.MONEY, p.ProgramInputRef("entry", ("absent",))),),
    )
    assert "reference_path" in codes(
        draft(invalid, inputs=(p.Field("entry", RECORD),), schemas=(RECORD,))
    )


def test_choose_checks_both_exports_and_keeps_branches_separate() -> None:
    first = p.Branch(leaf("yes"), p.Export(p.Scalar.BOOLEAN, p.ResultRef("yes")))
    second = p.Branch(leaf("no"), p.Export(p.Scalar.BOOLEAN, p.ResultRef("no")))
    choose = p.Choose(
        "choice", p.Literal(p.BoolValue(True)), first, second, p.Scalar.BOOLEAN
    )
    pending(draft(choose))
    bad = replace(second, result=p.Export(p.Scalar.BOOLEAN, p.ResultRef("yes")))
    assert "reference_scope" in codes(draft(replace(choose, when_false=bad)))
    wrong = p.Branch(
        leaf("no", output=p.Scalar.TEXT), p.Export(p.Scalar.TEXT, p.ResultRef("no"))
    )
    assert "export_type" in codes(draft(replace(choose, when_false=wrong)))


def test_parallel_branches_cannot_read_siblings() -> None:
    schema = p.RecordSchema(
        "Joined",
        (p.Field("left", p.Scalar.BOOLEAN), p.Field("right", p.Scalar.BOOLEAN)),
    )
    left = p.NamedBranch(
        "left",
        p.Branch(leaf("first"), p.Export(p.Scalar.BOOLEAN, p.ResultRef("first"))),
    )
    right = p.NamedBranch(
        "right",
        p.Branch(leaf("second"), p.Export(p.Scalar.BOOLEAN, p.ResultRef("second"))),
    )
    parallel = p.Parallel("join", (left, right), schema)
    pending(draft(parallel, schemas=(schema,)))
    dependent = leaf(
        "second", (p.Binding("flag", p.Scalar.BOOLEAN, p.ResultRef("first")),)
    )
    invalid = replace(right, branch=replace(right.branch, body=dependent))
    assert "reference_scope" in codes(
        draft(replace(parallel, branches=(left, invalid)), schemas=(schema,))
    )


def test_each_binds_stable_key_and_record_only_inside_body() -> None:
    collection = p.KeyedSchema(RECORD, "key")
    body = leaf(
        "body",
        (
            p.Binding("entry", RECORD, p.LocalRef("each", "item")),
            p.Binding("key", p.Scalar.TEXT, p.LocalRef("each", "key")),
        ),
        RECORD,
    )
    each = p.Each(
        "each",
        p.ProgramInputRef("entries"),
        collection,
        collection,
        p.Branch(body, p.Export(RECORD, p.ResultRef("body"))),
    )
    pending(draft(each, inputs=(p.Field("entries", collection),), schemas=(RECORD,)))
    leaked = leaf("after", (p.Binding("entry", RECORD, p.LocalRef("each", "item")),))
    sequence = p.Sequence(
        "outer", (each, leaked), p.Export(p.Scalar.BOOLEAN, p.ResultRef("after"))
    )
    assert "reference_scope" in codes(
        draft(sequence, inputs=(p.Field("entries", collection),), schemas=(RECORD,))
    )


def test_repeat_requires_a_bound_and_keeps_state_typed() -> None:
    body = leaf(
        "body",
        (p.Binding("state", p.Scalar.INTEGER, p.LocalRef("repeat", "state")),),
        p.Scalar.INTEGER,
    )
    repeat = p.Repeat(
        "repeat",
        p.Export(p.Scalar.INTEGER, p.Literal(p.IntValue(0))),
        p.Branch(body, p.Export(p.Scalar.INTEGER, p.ResultRef("body"))),
        p.Literal(p.BoolValue(False)),
        p.FiniteRepeat(3),
    )
    pending(draft(repeat))
    pending(draft(replace(repeat, bound=p.EventRepeat("new-observation"))))
    for bound in (p.FiniteRepeat(0), p.FiniteRepeat(True), p.EventRepeat("")):
        assert "repeat_bound" in codes(draft(replace(repeat, bound=bound)))
    wrong = replace(
        repeat.body, result=p.Export(p.Scalar.TEXT, p.Literal(p.TextValue("changed")))
    )
    assert "export_type" in codes(draft(replace(repeat, body=wrong)))


def test_unicode_spans_use_codepoints_and_exact_section() -> None:
    pending(draft(leaf("read")))
    assert len(CITATION.quote) == 3
    cases = [
        (replace(CITATION, quote="😀é"), "citation_quote"),
        (replace(CITATION, start=0), "citation_section"),
        (replace(CITATION, section="unknown"), "citation_section"),
        (replace(CITATION, locator="different"), "citation_section"),
        (replace(CITATION, end=99), "citation_span"),
        (
            replace(CITATION, pin=replace(PIN, original_sha256="b" * 64)),
            "citation_identity",
        ),
        (
            replace(CITATION, pin=replace(PIN, extraction_sha256="b" * 64)),
            "citation_identity",
        ),
    ]
    for citation, expected in cases:
        node = leaf("read")
        node = replace(node, metadata=replace(node.metadata, citations=(citation,)))
        assert expected in codes(draft(node))


def test_changed_extracted_text_cannot_reuse_its_hash() -> None:
    changed = p.SourceCatalog((replace(SOURCES.entries[0], text=TEXT + "changed"),))
    assert "extraction_hash" in codes(draft(leaf("read")), changed)


def rule(
    name: str,
    consequence: bool,
    start: date,
    end: date | None,
    scope: tuple[p.Constraint, ...] = (),
) -> p.DatedRule:
    return p.DatedRule(
        name,
        "decision",
        scope,
        start,
        end,
        p.Export(p.Scalar.BOOLEAN, p.Literal(p.BoolValue(consequence))),
        (CITATION,),
    )


def test_rule_conflicts_require_equal_specificity_overlap_and_compatible_scope() -> (
    None
):
    start, boundary, end = date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1)
    first = rule("first", True, start, boundary)
    second = rule("second", False, boundary, end)
    pending(draft(leaf("read"), rules=(first, second)))
    conflict = replace(second, effective_from=start)
    assert "rule_conflict" in codes(draft(leaf("read"), rules=(first, conflict)))
    red = p.Constraint("group", p.Scalar.TEXT, p.TextValue("red"))
    blue = p.Constraint("group", p.Scalar.TEXT, p.TextValue("blue"))
    pending(
        draft(
            leaf("read"),
            rules=(replace(first, scope=(red,)), replace(conflict, scope=(blue,))),
        )
    )
    pending(draft(leaf("read"), rules=(first, replace(conflict, scope=(red,)))))
    other = p.Constraint("region", p.Scalar.TEXT, p.TextValue("north"))
    assert "rule_conflict" in codes(
        draft(
            leaf("read"),
            rules=(replace(first, scope=(red,)), replace(conflict, scope=(other,))),
        )
    )


def test_rules_validate_dimensions_types_and_intervals() -> None:
    start = date(2026, 1, 1)
    constraint = p.Constraint("group", p.Scalar.TEXT, p.TextValue("red"))
    first = rule("first", True, start, None, (constraint,))
    repeated = replace(first, scope=(constraint, constraint))
    assert "duplicate_identity" in codes(draft(leaf("read"), rules=(repeated,)))
    backwards = replace(first, effective_until=start)
    assert "rule_dates" in codes(draft(leaf("read"), rules=(backwards,)))
    second = rule(
        "second",
        True,
        start,
        None,
        (p.Constraint("group", p.Scalar.INTEGER, p.IntValue(1)),),
    )
    assert "rule_scope_type" in codes(draft(leaf("read"), rules=(first, second)))


def test_duplicate_node_identity_and_excessive_nesting_fail_visibly() -> None:
    node = leaf("same")
    sequence = p.Sequence(
        "sequence", (node, node), p.Export(p.Scalar.BOOLEAN, p.ResultRef("same"))
    )
    assert "duplicate_identity" in codes(draft(sequence))
    nested: p.Node = leaf("innermost")
    for index in range(p.MAX_NESTING + 1):
        nested = p.Sequence(
            "nest-" + str(index),
            (nested,),
            p.Export(p.Scalar.BOOLEAN, p.ResultRef(p.node_identity(nested))),
        )
    assert "graph_limit" in codes(draft(nested))


def test_code_declarations_remain_inert_and_signature_checked() -> None:
    function = p.FunctionDeclaration(
        "compute",
        (),
        p.Scalar.BOOLEAN,
        p.FunctionBody("restricted-1", "return True"),
        (p.FunctionTest("true", (), p.BoolValue(True)),),
    )
    node = p.CodeStep(leaf("code").metadata, "compute")
    result = pending(draft(node, functions=(function,)))
    assert p.MissingCheck.LANGUAGE not in result.missing_checks
    wrong = replace(function, output=p.Scalar.TEXT)
    assert "function_signature" in codes(draft(node, functions=(wrong,)))
    assert "unknown_function" in codes(draft(node))


def test_changes_are_declarations_on_existing_leaf_kinds() -> None:
    change = p.ChangeDeclaration(
        "change", "record-result", p.Export(p.Scalar.BOOLEAN, p.ResultRef("ai"))
    )
    ai = leaf("ai", changes=(change,))
    pending(draft(ai))
    assert isinstance(ai, p.AiStep)
    wrong = replace(change, payload=p.Export(p.Scalar.TEXT, p.ResultRef("ai")))
    assert "reference_type" in codes(draft(leaf("ai", changes=(wrong,))))


def test_source_backed_scenario_is_checked_but_never_executed() -> None:
    scenario = p.ProgramScenario("saved", (), p.BoolValue(True), (CITATION,))
    result = pending(draft(leaf("read"), scenarios=(scenario,)))
    assert p.MissingCheck.SCENARIOS in result.missing_checks
    invalid = replace(scenario, expected=p.TextValue("wrong type"))
    assert "value_type" in codes(draft(leaf("read"), scenarios=(invalid,)))
    assert type(result) is p.ExecutionPending


def test_human_step_retains_supplied_due_time_and_requires_timezone() -> None:
    due = datetime(2026, 1, 2, 15, 30, tzinfo=UTC)
    node = p.HumanStep(
        leaf("human").metadata,
        "reviewer",
        due,
        p.Export(p.Scalar.TEXT, p.Literal(p.TextValue("Choose a response."))),
        True,
    )
    result = pending(draft(node))
    assert result.artifact.draft.root == node
    assert node.due_at == due
    assert "human_due_time" in codes(
        draft(replace(node, due_at=due.replace(tzinfo=None)))
    )


def test_equivalent_record_consequences_do_not_conflict_by_field_order() -> None:
    start = date(2026, 1, 1)
    first = replace(
        rule("first", True, start, None), consequence=p.Export(RECORD, p.Literal(ENTRY))
    )
    reordered = replace(ENTRY, fields=tuple(reversed(ENTRY.fields)))
    second = replace(
        first, rule_id="second", consequence=p.Export(RECORD, p.Literal(reordered))
    )
    pending(draft(leaf("read"), schemas=(RECORD,), rules=(first, second)))


def test_events_record_supplied_actor_times_and_program_revision() -> None:
    from dex.core.events import EventIdentity, ProgramDrafted, ProgramStructureChecked

    program = draft(leaf("read"))
    occurred = datetime(2026, 1, 1, 12, tzinfo=UTC)
    observed = datetime(2026, 1, 1, 13, tzinfo=UTC)
    identity = EventIdentity(
        "event", "actor", occurred, observed, program.program_id, program.revision
    )
    drafted = ProgramDrafted(identity, program)
    checked = ProgramStructureChecked(
        replace(identity, event_id="checked"), pending(program)
    )
    assert drafted.identity.actor == "actor"
    assert drafted.identity.occurred_at == occurred
    assert drafted.identity.observed_at == observed
    assert checked.identity.program_revision == program.revision
    assert isinstance(checked.result, p.ExecutionPending)


@pytest.mark.parametrize("field", ["program_id", "program_revision"])
@pytest.mark.parametrize("event_kind", ["drafted", "checked"])
def test_events_reject_program_identity_mismatch(field: str, event_kind: str) -> None:
    from dex.core.events import EventIdentity, ProgramDrafted, ProgramStructureChecked

    program = draft(leaf("read"))
    timestamp = datetime(2026, 1, 1, 12, tzinfo=UTC)
    identity = EventIdentity(
        "event", "actor", timestamp, timestamp, program.program_id, program.revision
    )
    identity = (
        replace(identity, program_id="different")
        if field == "program_id"
        else replace(identity, program_revision="different")
    )
    with pytest.raises(
        ValueError, match="Event program identity must match its payload"
    ):
        if event_kind == "drafted":
            ProgramDrafted(identity, program)
        else:
            ProgramStructureChecked(identity, pending(program))

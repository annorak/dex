from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from dex.core import language as l
from dex.core import program as p
from dex.eval.scenario_format import FunctionCommand, FunctionExpected, parse_scenario
from dex.eval.scenarios import evaluate

ONE = p.IntValue(1)


def declaration(
    source: str,
    output: p.Schema = p.Scalar.INTEGER,
    inputs: tuple[p.Field, ...] = (),
    values: tuple[p.NamedValue, ...] = (),
    expected: p.Value = ONE,
    name: str = "f",
) -> p.FunctionDeclaration:
    return p.FunctionDeclaration(
        name,
        inputs,
        output,
        p.FunctionBody("restricted-1", source),
        (p.FunctionTest("saved", values, expected),),
    )


def checked(
    function: p.FunctionDeclaration, schemas: tuple[p.RecordSchema, ...] = ()
) -> l.CheckedFunctions:
    result = l.check_functions((function,), schemas, l.DEFAULT_LIMITS)
    assert isinstance(result, l.CheckedFunctions), result
    return result


def invoke(
    function: p.FunctionDeclaration, values: tuple[p.NamedValue, ...] = ()
) -> l.FunctionResult:
    result = l.execute_function(
        checked(function), function.function_id, values, l.DEFAULT_LIMITS
    )
    assert isinstance(result, l.FunctionResult), result
    return result


@pytest.mark.parametrize(
    "source,code",
    [
        ("import os\nreturn 1", "unsupported_syntax"),
        ("while True:\n    return 1", "unsupported_syntax"),
        ("return (lambda: 1)()", "unsupported_call"),
        ("return [x for x in []]", "unsupported_syntax"),
        ("return eval('1')", "unsupported_call"),
        ("return open('data')", "unsupported_call"),
        ("return now()", "unsupported_call"),
        ("return random()", "unsupported_call"),
        ("return 'x'.upper()", "unsupported_call"),
        ("return 'x'.value", "unsupported_attribute"),
        ("return 1.0", "unsupported_syntax"),
        ("return 2 ** 3", "type_error"),
        ("return 1 + 'x'", "type_error"),
        ("return True", "return_type"),
        ("return missing", "unknown_name"),
        ("x = 1", "missing_return"),
        ("if True:\n    x = 1\nreturn x", "unknown_name"),
        ("return f()", "recursive_call"),
        ("return 1\nunused = f()", "recursive_call"),
    ],
)
def test_rejections(source: str, code: str) -> None:
    result = l.check_functions((declaration(source),), (), l.DEFAULT_LIMITS)
    assert isinstance(result, l.LanguageFailure)
    assert result.code == code


def test_unused_invalid_function_blocks_all_saved_interpretation() -> None:
    first = declaration("return 1 // 0")
    unused = declaration("import os\nreturn 1", name="unused")
    result = l.check_functions((first, unused), (), l.DEFAULT_LIMITS)
    assert isinstance(result, l.LanguageFailure)
    assert result.code == "unsupported_syntax"


def test_invalid_saved_type_blocks_all_saved_interpretation() -> None:
    first = declaration("return 1 // 0")
    second = declaration("return 1", expected=p.TextValue("wrong type"), name="second")
    result = l.check_functions((first, second), (), l.DEFAULT_LIMITS)
    assert isinstance(result, l.LanguageFailure)
    assert result.code == "value_type"


def test_wrong_saved_expected_blocks_checked_artifact() -> None:
    result = l.check_functions((declaration("return 2"),), (), l.DEFAULT_LIMITS)
    assert isinstance(result, l.LanguageFailure)
    assert result.code == "saved_test_failed"


def test_saved_tests_are_required() -> None:
    result = l.check_functions(
        (replace(declaration("return 1"), tests=()),), (), l.DEFAULT_LIMITS
    )
    assert isinstance(result, l.LanguageFailure)
    assert result.code == "missing_function_tests"


def test_indirect_cycle_and_call_depth() -> None:
    first = declaration("return second()")
    second = declaration("return f()", name="second")
    result = l.check_functions((first, second), (), l.DEFAULT_LIMITS)
    assert isinstance(result, l.LanguageFailure)
    assert result.code == "recursive_call"
    second = declaration("return 1", name="second")
    result = l.check_functions(
        (first, second), (), replace(l.DEFAULT_LIMITS, call_depth=1)
    )
    assert isinstance(result, l.LanguageFailure)
    assert result.code == "call_depth_limit"


@given(st.integers(min_value=-1000000, max_value=1000000))
def test_typed_integer_and_money_arithmetic(number: int) -> None:
    fn = declaration(
        "return money(value) * 2 + money(3)",
        p.Scalar.MONEY,
        (p.Field("value", p.Scalar.INTEGER),),
        (p.NamedValue("value", p.IntValue(0)),),
        p.MoneyValue(3),
    )
    assert invoke(
        fn, (p.NamedValue("value", p.IntValue(number)),)
    ).value == p.MoneyValue(number * 2 + 3)


@given(st.integers(min_value=1, max_value=10000))
def test_integer_first_excess_boundary(limit: int) -> None:
    fn = declaration(
        "return value",
        inputs=(p.Field("value", p.Scalar.INTEGER),),
        values=(p.NamedValue("value", p.IntValue(1)),),
    )
    artifact = checked(fn)
    budget = replace(l.DEFAULT_LIMITS, integer_magnitude=limit)
    result = l.execute_function(
        artifact, "f", (p.NamedValue("value", p.IntValue(limit)),), budget
    )
    assert isinstance(result, l.FunctionResult)
    assert result.value == p.IntValue(limit)
    rejected = l.execute_function(
        artifact, "f", (p.NamedValue("value", p.IntValue(limit + 1)),), budget
    )
    assert isinstance(rejected, l.LanguageFailure)
    assert rejected.code == "integer_limit"


@given(st.text(alphabet="abcé😀", max_size=100))
def test_typed_text_is_data(text: str) -> None:
    fn = declaration(
        "return value",
        p.Scalar.TEXT,
        (p.Field("value", p.Scalar.TEXT),),
        (p.NamedValue("value", p.TextValue("")),),
        p.TextValue(""),
    )
    result = invoke(fn, (p.NamedValue("value", p.TextValue(text)),))
    assert result.value == p.TextValue(text)


@pytest.mark.parametrize(
    "source,expected",
    [
        ('return parse_money("-0.01")', p.MoneyValue(-1)),
        ('return parse_us_date("02/29/2028")', p.DateValue(date(2028, 2, 29))),
        (
            'return add_days(parse_iso_date("2027-12-31"), 1)',
            p.DateValue(date(2028, 1, 1)),
        ),
    ],
)
def test_exact_money_and_dates(source: str, expected: p.Value) -> None:
    schema = p.Scalar.MONEY if isinstance(expected, p.MoneyValue) else p.Scalar.DATE
    assert invoke(declaration(source, schema, expected=expected)).value == expected


@pytest.mark.parametrize(
    "source,schema",
    [
        ('return parse_money("1.001")', p.Scalar.MONEY),
        ('return parse_money("1")', p.Scalar.MONEY),
        ('return parse_money("1e2")', p.Scalar.MONEY),
        ('return parse_iso_date("2028-2-29")', p.Scalar.DATE),
        ('return parse_us_date("02/29/2027")', p.Scalar.DATE),
    ],
)
def test_strict_parsers_refuse_invalid_input(source: str, schema: p.Schema) -> None:
    expected = (
        p.MoneyValue(1) if schema == p.Scalar.MONEY else p.DateValue(date(2028, 1, 1))
    )
    result = l.check_functions(
        (declaration(source, schema, expected=expected),), (), l.DEFAULT_LIMITS
    )
    assert isinstance(result, l.LanguageFailure)
    assert result.code == "parse_error"


def test_record_constructor_and_input_have_identical_equality() -> None:
    schema = p.RecordSchema(
        "Record", (p.Field("z", p.Scalar.INTEGER), p.Field("a", p.Scalar.INTEGER))
    )
    value = p.RecordValue(
        "Record", (p.NamedValue("z", p.IntValue(1)), p.NamedValue("a", p.IntValue(2)))
    )
    inputs = (p.NamedValue("row", value),)
    fn = declaration(
        "return row == Record(row.z, row.a)",
        p.Scalar.BOOLEAN,
        (p.Field("row", schema),),
        inputs,
        p.BoolValue(True),
    )
    artifact = checked(fn, (schema,))
    result = l.execute_function(artifact, "f", inputs, l.DEFAULT_LIMITS)
    assert isinstance(result, l.FunctionResult)
    assert result.value == p.BoolValue(True)


def test_record_builtin_name_collision_cannot_change_builtin_dispatch() -> None:
    schema = p.RecordSchema("money", (p.Field("number", p.Scalar.INTEGER),))
    fn = declaration("return money(1)", p.Scalar.MONEY, expected=p.MoneyValue(1))
    artifact = checked(fn, (schema,))
    result = l.execute_function(artifact, "f", (), l.DEFAULT_LIMITS)
    assert isinstance(result, l.FunctionResult)
    assert result.value == p.MoneyValue(1)
    value = p.RecordValue("money", (p.NamedValue("number", p.IntValue(1)),))
    constructor = declaration('return record("money", 1)', schema, expected=value)
    artifact = checked(constructor, (schema,))
    result = l.execute_function(artifact, "f", (), l.DEFAULT_LIMITS)
    assert isinstance(result, l.FunctionResult)
    assert result.value == value


def test_existing_schema_names_and_literal_record_field_lookup() -> None:
    schema = p.RecordSchema("Display row", (p.Field("display-name", p.Scalar.TEXT),))
    value = p.RecordValue(
        "Display row", (p.NamedValue("display-name", p.TextValue("Ada")),)
    )
    inputs = (p.NamedValue("row", value),)
    fn = declaration(
        'return row["display-name"]',
        p.Scalar.TEXT,
        (p.Field("row", schema),),
        inputs,
        p.TextValue("Ada"),
    )
    artifact = checked(fn, (schema,))
    result = l.execute_function(artifact, "f", inputs, l.DEFAULT_LIMITS)
    assert isinstance(result, l.FunctionResult)
    assert result.value == p.TextValue("Ada")
    tagged = p.TaggedSchema((p.Field("needs-human", p.Scalar.TEXT),))
    fn = declaration(
        'return tag("needs-human", "check")',
        tagged,
        expected=p.TaggedValue("needs-human", p.TextValue("check")),
    )
    assert invoke(fn).value == p.TaggedValue("needs-human", p.TextValue("check"))


def test_branch_definite_assignment_and_boolean_short_circuit() -> None:
    fn = declaration(
        "if flag:\n    answer = 2\nelse:\n    answer = 1\nreturn answer",
        inputs=(p.Field("flag", p.Scalar.BOOLEAN),),
        values=(p.NamedValue("flag", p.BoolValue(False)),),
    )
    assert invoke(fn, (p.NamedValue("flag", p.BoolValue(True)),)).value == p.IntValue(2)
    fn = declaration(
        "return False and (1 // 0 == 1)", p.Scalar.BOOLEAN, expected=p.BoolValue(False)
    )
    assert invoke(fn).value == p.BoolValue(False)


def test_nested_calls_share_invocation_budget() -> None:
    inner = declaration(
        "return cents(money(value))",
        inputs=(p.Field("value", p.Scalar.INTEGER),),
        values=(p.NamedValue("value", p.IntValue(1)),),
        name="inner",
    )
    outer = declaration("return inner(inner(1))")
    artifact = l.check_functions((outer, inner), (), l.DEFAULT_LIMITS)
    assert isinstance(artifact, l.CheckedFunctions)
    result = l.execute_function(artifact, "f", (), l.DEFAULT_LIMITS)
    assert isinstance(result, l.FunctionResult)
    exact = l.execute_function(
        artifact, "f", (), replace(l.DEFAULT_LIMITS, work=result.usage.work)
    )
    assert isinstance(exact, l.FunctionResult)
    exhausted = l.execute_function(
        artifact, "f", (), replace(l.DEFAULT_LIMITS, work=result.usage.work - 1)
    )
    assert isinstance(exhausted, l.LanguageFailure)
    assert exhausted.code == "work_limit"


def test_allocation_first_excess_has_no_partial_result() -> None:
    artifact = checked(
        declaration(
            'return trim("  abc  ")', p.Scalar.TEXT, expected=p.TextValue("abc")
        )
    )
    result = l.execute_function(artifact, "f", (), l.DEFAULT_LIMITS)
    assert isinstance(result, l.FunctionResult)
    exact = l.execute_function(
        artifact,
        "f",
        (),
        replace(l.DEFAULT_LIMITS, allocations=result.usage.allocations),
    )
    assert isinstance(exact, l.FunctionResult)
    failure = l.execute_function(
        artifact,
        "f",
        (),
        replace(l.DEFAULT_LIMITS, allocations=result.usage.allocations - 1),
    )
    assert isinstance(failure, l.LanguageFailure)
    assert failure.code == "allocation_limit"


def test_limits_cannot_exceed_language_defaults() -> None:
    result = l.check_functions(
        (declaration("return 1"),),
        (),
        replace(l.DEFAULT_LIMITS, work=l.DEFAULT_LIMITS.work + 1),
    )
    assert isinstance(result, l.LanguageFailure)
    assert result.code == "invalid_limits"


SCENARIOS = tuple(
    sorted((Path(__file__).parents[1] / "scenarios").glob("language-*.json"))
)


@pytest.mark.parametrize("path", SCENARIOS, ids=lambda path: path.stem)
def test_language_scenario_exact_observations(path: Path) -> None:
    scenario = parse_scenario(path.read_bytes())
    evaluation = evaluate(scenario)
    assert evaluation.matches == (True,) * len(scenario.commands), evaluation


def test_expected_answer_tampering_cannot_change_actual_output() -> None:
    path = Path(__file__).parents[1] / "scenarios/language-arithmetic.json"
    scenario = parse_scenario(path.read_bytes())
    original = evaluate(scenario)
    tampered = replace(
        scenario, expected=(FunctionExpected("function_result", p.IntValue(-1), None),)
    )
    changed = evaluate(tampered)
    assert changed.observations == original.observations
    assert changed.matches == (False,)


def test_runtime_literals_obey_lowered_magnitude_limit() -> None:
    artifact = checked(declaration("return 100 - 99"))
    result = l.execute_function(
        artifact, "f", (), replace(l.DEFAULT_LIMITS, integer_magnitude=10)
    )
    assert isinstance(result, l.LanguageFailure)
    assert result.code == "integer_limit"


def test_cost_scenarios_fail_inside_builtin_after_verification() -> None:
    path = Path(__file__).parents[1] / "scenarios/language-cost-limits.json"
    scenario = parse_scenario(path.read_bytes())
    for command, program in zip(scenario.commands, scenario.programs, strict=True):
        assert isinstance(command, FunctionCommand)
        result = p.verify_program(program.draft, program.sources, command.limits)
        assert isinstance(result, p.ExecutionPending), result
    evaluation = evaluate(scenario)
    assert all(evaluation.matches)
    for observation in evaluation.observations:
        assert isinstance(observation.function, l.LanguageFailure)
        assert "Builtin template:" in observation.function.message


def test_saved_tests_share_verification_work_budget() -> None:
    fn = declaration("return 1")
    many_tests = tuple(
        p.FunctionTest(str(index), (), p.IntValue(1)) for index in range(100)
    )
    result = l.check_functions(
        (replace(fn, tests=many_tests),), (), replace(l.DEFAULT_LIMITS, work=1000)
    )
    assert isinstance(result, l.LanguageFailure)
    assert result.code == "work_limit"

import json
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from io import StringIO
from pathlib import Path

import pytest

from dex.core import language
from dex.core import program as p
from dex.eval.scenario_format import parse_scenario
from dex.eval.scenario_output import encode_core, write_json
from dex.eval.scenarios import evaluate

SCENARIOS = Path(__file__).parents[1] / "scenarios"


def test_chunk_codec_preserves_original_integer_and_text_bytes() -> None:
    values = [
        p.IntValue(2**100),
        p.IntValue(-(2**100)),
        p.TextValue("snowman☃ astral𐀀"),
        p.TextValue("\ud800"),
    ]
    first, second = StringIO(), StringIO()
    write_json(values, (first, second))
    expected = json.dumps(encode_core(values), sort_keys=True, separators=(",", ":"))
    assert first.getvalue() == second.getvalue() == expected + "\n"


def test_unknown_dataclass_keeps_original_unsupported_value_failure() -> None:
    @dataclass(frozen=True)
    class Row:
        value: object

    for value in (1.5, float("nan"), float("inf"), object()):
        row = Row(value)
        with pytest.raises(TypeError, match="Unsupported core output type"):
            encode_core(row)
        with pytest.raises(TypeError, match="Unsupported core output type"):
            write_json([row], (StringIO(),))


def test_repeated_dataclass_encoding_preserves_each_value_and_schema() -> None:
    @dataclass(frozen=True)
    class Row:
        name: str
        schema: p.Scalar
        value: int
        nested: dict[str, p.Scalar]

    nested = {"column": p.Scalar.INTEGER}
    rows = [
        Row("first", p.Scalar.INTEGER, 7, nested),
        Row("second", p.Scalar.TEXT, 9, nested),
    ]
    output = StringIO()
    write_json(rows, (output,))
    assert json.loads(output.getvalue()) == [
        {
            "kind": "Row",
            "name": "first",
            "schema": {"kind": "integer"},
            "value": 7,
            "nested": {"column": {"kind": "integer"}},
        },
        {
            "kind": "Row",
            "name": "second",
            "schema": {"kind": "text"},
            "value": 9,
            "nested": {"column": {"kind": "integer"}},
        },
    ]
    assert rows[0].nested is nested and rows[1].nested is nested
    assert nested == {"column": p.Scalar.INTEGER}
    nested["column"] = p.Scalar.BOOLEAN
    updated = StringIO()
    write_json(rows, (updated,))
    assert json.loads(updated.getvalue())[0]["nested"] == {
        "column": {"kind": "boolean"}
    }


def test_generic_schema_containers_and_string_subtypes_keep_scalar_tags() -> None:
    values = [
        language.Builtin("identity", (p.Scalar.INTEGER,), p.Scalar.INTEGER),
        p.TextValue(p.Scalar.INTEGER),
        p.ResultRef("source", (p.Scalar.INTEGER,)),
    ]
    output = StringIO()
    write_json(values, (output,))
    assert json.loads(output.getvalue()) == [
        {
            "kind": "Builtin",
            "name": "identity",
            "inputs": [{"kind": "integer"}],
            "output": {"kind": "integer"},
        },
        {"kind": "text", "value": {"kind": "integer"}},
        {"kind": "result", "node": "source", "path": [{"kind": "integer"}]},
    ]


def test_large_repeated_immutable_values_preserve_every_occurrence() -> None:
    values = [p.NamedValue("number", p.IntValue(index)) for index in range(20_000)]
    repeated = [item for value in values for item in (value, value)]
    output = StringIO()
    write_json(repeated, (output,))
    assert json.loads(output.getvalue()) == encode_core(repeated)


def test_streaming_preserves_nested_schema_tags_dates_and_sorted_sets() -> None:
    value = {
        "nested": (p.Scalar.INTEGER, [p.Scalar.TEXT]),
        "date": date(2026, 1, 1),
        "time": datetime(2026, 1, 1, tzinfo=UTC),
        "set": frozenset({"z", "a"}),
        "tag": p.PresentValue(p.IntValue(7)),
        "escaped": 'quote" newline\n snowman☃',
    }
    first, second = StringIO(), StringIO()
    write_json(value, (first, second))
    assert first.getvalue() == second.getvalue()
    assert json.loads(first.getvalue()) == {
        "nested": [{"kind": "integer"}, [{"kind": "text"}]],
        "date": "2026-01-01",
        "time": "2026-01-01T00:00:00+00:00",
        "set": ["a", "z"],
        "tag": {"kind": "present", "value": {"kind": "integer", "value": 7}},
        "escaped": 'quote" newline\n snowman☃',
    }


@pytest.mark.parametrize(
    "path",
    sorted(path for path in SCENARIOS.glob("*.json") if "-size-" not in path.name),
    ids=lambda path: path.name,
)
def test_streaming_matches_full_encoding_for_every_small_scenario(path: Path) -> None:
    scenario = replace(parse_scenario(path.read_bytes()), detail="full")
    evaluation = evaluate(scenario)
    output = StringIO()
    write_json(evaluation, (output,))
    assert json.loads(output.getvalue()) == encode_core(evaluation)

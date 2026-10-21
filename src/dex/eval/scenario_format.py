import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import cast

from dex.core import program as p
from dex.core.language import Limits

type Json = None | bool | int | float | str | list[Json] | dict[str, Json]
MAX_BYTES = 8 * 1024 * 1024
MAX_DEPTH = 160


class ScenarioError(ValueError):
    pass


@dataclass(frozen=True)
class Program:
    name: str
    draft: p.ProgramDraft
    sources: p.SourceCatalog


@dataclass(frozen=True)
class ProgramCommand:
    kind: str
    program: str


@dataclass(frozen=True)
class FunctionCommand:
    program: str
    function_id: str
    inputs: tuple[p.NamedValue, ...]
    limits: Limits
    kind: str = "call"


type Command = ProgramCommand | FunctionCommand


@dataclass(frozen=True)
class Expected:
    status: str
    diagnostic_codes: tuple[str, ...]
    missing_checks: tuple[str, ...]


@dataclass(frozen=True)
class FunctionExpected:
    status: str
    value: p.Value | None
    failure: str | None


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    programs: tuple[Program, ...]
    commands: tuple[Command, ...]
    expected: tuple[Expected | FunctionExpected, ...]


def require_object_fields(value: Json, fields: str) -> dict[str, Json]:
    if not isinstance(value, dict) or value.keys() != set(fields.split()):
        raise ScenarioError("Object fields must be exactly: " + fields)
    return value


def require_text(value: Json) -> str:
    if not isinstance(value, str):
        raise ScenarioError("Expected a string.")
    return value


def require_integer(value: Json) -> int:
    if type(value) is not int:
        raise ScenarioError("Expected an integer, excluding booleans.")
    return value


def require_boolean(value: Json) -> bool:
    if type(value) is not bool:
        raise ScenarioError("Expected a boolean.")
    return value


def require_items(value: Json) -> list[Json]:
    if not isinstance(value, list):
        raise ScenarioError("Expected an array.")
    return value


def require_kind(value: Json) -> str:
    if not isinstance(value, dict) or "kind" not in value:
        raise ScenarioError("Variant needs a kind discriminator.")
    return require_text(value["kind"])


def parse_date(value: Json) -> date:
    source = require_text(value)
    result = date.fromisoformat(source)
    if result.isoformat() != source:
        raise ScenarioError("Dates must use YYYY-MM-DD.")
    return result


def parse_field(value: Json) -> p.Field:
    obj = require_object_fields(value, "name schema")
    return p.Field(require_text(obj["name"]), parse_schema(obj["schema"]))


def parse_record_schema(value: Json) -> p.RecordSchema:
    result = parse_schema(value)
    if not isinstance(result, p.RecordSchema):
        raise ScenarioError("Expected a record schema.")
    return result


def parse_keyed_schema(value: Json) -> p.KeyedSchema:
    result = parse_schema(value)
    if not isinstance(result, p.KeyedSchema):
        raise ScenarioError("Expected a keyed schema.")
    return result


def parse_schema(value: Json) -> p.Schema:
    tag = require_kind(value)
    if tag in {item.value for item in p.Scalar}:
        require_object_fields(value, "kind")
        return p.Scalar(tag)
    if tag == "optional":
        obj = require_object_fields(value, "kind item")
        return p.OptionalSchema(parse_schema(obj["item"]))
    if tag == "tagged":
        obj = require_object_fields(value, "kind variants")
        return p.TaggedSchema(
            tuple(parse_field(item) for item in require_items(obj["variants"]))
        )
    if tag == "record":
        obj = require_object_fields(value, "kind name fields")
        return p.RecordSchema(
            require_text(obj["name"]),
            tuple(parse_field(item) for item in require_items(obj["fields"])),
        )
    if tag == "keyed":
        obj = require_object_fields(value, "kind item key_field")
        return p.KeyedSchema(
            parse_record_schema(obj["item"]), require_text(obj["key_field"])
        )
    if tag == "reference":
        obj = require_object_fields(value, "kind record key_field")
        return p.ReferenceSchema(
            require_text(obj["record"]), require_text(obj["key_field"])
        )
    if tag == "unresolved":
        require_object_fields(value, "kind")
        return p.UnresolvedSchema()
    raise ScenarioError("Unsupported schema kind: " + tag)


def parse_named_value(value: Json) -> p.NamedValue:
    obj = require_object_fields(value, "name value")
    return p.NamedValue(require_text(obj["name"]), parse_value(obj["value"]))


def parse_record_value(value: Json) -> p.RecordValue:
    result = parse_value(value)
    if not isinstance(result, p.RecordValue):
        raise ScenarioError("Expected a record value.")
    return result


def parse_value(value: Json) -> p.Value:
    tag = require_kind(value)
    if tag in {"boolean", "integer", "text", "date"}:
        obj = require_object_fields(value, "kind value")
        if tag == "boolean":
            return p.BoolValue(require_boolean(obj["value"]))
        if tag == "integer":
            return p.IntValue(require_integer(obj["value"]))
        if tag == "date":
            return p.DateValue(parse_date(obj["value"]))
        return p.TextValue(require_text(obj["value"]))
    if tag == "money_cents":
        obj = require_object_fields(value, "kind cents")
        return p.MoneyValue(require_integer(obj["cents"]))
    if tag == "absent":
        require_object_fields(value, "kind")
        return p.AbsentValue()
    if tag == "present":
        obj = require_object_fields(value, "kind value")
        return p.PresentValue(parse_value(obj["value"]))
    if tag == "tagged":
        obj = require_object_fields(value, "kind tag value")
        return p.TaggedValue(require_text(obj["tag"]), parse_value(obj["value"]))
    if tag == "record":
        obj = require_object_fields(value, "kind record fields")
        return p.RecordValue(
            require_text(obj["record"]),
            tuple(parse_named_value(item) for item in require_items(obj["fields"])),
        )
    if tag == "keyed":
        obj = require_object_fields(value, "kind entries")
        entries: list[p.KeyedEntry] = []
        for item in require_items(obj["entries"]):
            entry = require_object_fields(item, "key value")
            entries.append(
                p.KeyedEntry(
                    require_text(entry["key"]), parse_record_value(entry["value"])
                )
            )
        return p.KeyedValue(tuple(entries))
    if tag == "resolved_ref":
        obj = require_object_fields(value, "kind record key_field key")
        return p.ResolvedRefValue(
            require_text(obj["record"]),
            require_text(obj["key_field"]),
            require_text(obj["key"]),
        )
    if tag == "unresolved_text":
        obj = require_object_fields(value, "kind text")
        return p.UnresolvedTextValue(require_text(obj["text"]))
    raise ScenarioError("Unsupported value kind: " + tag)


def parse_input(value: Json) -> p.Input:
    tag = require_kind(value)
    if tag == "literal":
        obj = require_object_fields(value, "kind value")
        return p.Literal(parse_value(obj["value"]))
    if tag == "program_input":
        obj = require_object_fields(value, "kind name path")
        return p.ProgramInputRef(
            require_text(obj["name"]),
            tuple(require_text(item) for item in require_items(obj["path"])),
        )
    if tag == "result":
        obj = require_object_fields(value, "kind node path")
        return p.ResultRef(
            require_text(obj["node"]),
            tuple(require_text(item) for item in require_items(obj["path"])),
        )
    if tag == "local":
        obj = require_object_fields(value, "kind owner name path")
        return p.LocalRef(
            require_text(obj["owner"]),
            require_text(obj["name"]),
            tuple(require_text(item) for item in require_items(obj["path"])),
        )
    raise ScenarioError("Unsupported input kind: " + tag)


def parse_export(value: Json) -> p.Export:
    obj = require_object_fields(value, "schema value")
    return p.Export(parse_schema(obj["schema"]), parse_input(obj["value"]))


def parse_sha256(value: Json) -> str:
    digest = require_text(value)
    if re.fullmatch(r"sha256:[0-9a-f]{64}", digest) is None:
        raise ScenarioError(
            "Expected sha256: followed by 64 lowercase hexadecimal digits."
        )
    return digest[7:]


def parse_pin(value: Json) -> p.SourcePin:
    obj = require_object_fields(
        value, "source revision original_sha256 extraction extraction_sha256"
    )
    return p.SourcePin(
        require_text(obj["source"]),
        require_text(obj["revision"]),
        parse_sha256(obj["original_sha256"]),
        require_text(obj["extraction"]),
        parse_sha256(obj["extraction_sha256"]),
    )


def parse_section(value: Json) -> p.Section:
    obj = require_object_fields(value, "name locator start end")
    return p.Section(
        require_text(obj["name"]),
        require_text(obj["locator"]),
        require_integer(obj["start"]),
        require_integer(obj["end"]),
    )


def parse_catalog(value: Json) -> p.SourceCatalog:
    obj = require_object_fields(value, "entries")
    entries: list[p.SourceExtraction] = []
    for item in require_items(obj["entries"]):
        entry = require_object_fields(item, "pin text sections")
        entries.append(
            p.SourceExtraction(
                parse_pin(entry["pin"]),
                require_text(entry["text"]),
                tuple(parse_section(part) for part in require_items(entry["sections"])),
            )
        )
    return p.SourceCatalog(tuple(entries))


def parse_citation(value: Json) -> p.Citation:
    obj = require_object_fields(value, "pin section locator start end quote")
    return p.Citation(
        parse_pin(obj["pin"]),
        require_text(obj["section"]),
        require_text(obj["locator"]),
        require_integer(obj["start"]),
        require_integer(obj["end"]),
        require_text(obj["quote"]),
    )


def parse_binding(value: Json) -> p.Binding:
    obj = require_object_fields(value, "name schema value")
    return p.Binding(
        require_text(obj["name"]),
        parse_schema(obj["schema"]),
        parse_input(obj["value"]),
    )


def parse_change(value: Json) -> p.ChangeDeclaration:
    obj = require_object_fields(value, "change_id operation payload")
    return p.ChangeDeclaration(
        require_text(obj["change_id"]),
        require_text(obj["operation"]),
        parse_export(obj["payload"]),
    )


def parse_metadata(value: Json) -> p.StepMetadata:
    obj = require_object_fields(
        value, "step_id behavior_id intent citations inputs output changes"
    )
    return p.StepMetadata(
        require_text(obj["step_id"]),
        require_text(obj["behavior_id"]),
        require_text(obj["intent"]),
        tuple(parse_citation(item) for item in require_items(obj["citations"])),
        tuple(parse_binding(item) for item in require_items(obj["inputs"])),
        parse_schema(obj["output"]),
        tuple(parse_change(item) for item in require_items(obj["changes"])),
    )


def parse_branch(value: Json) -> p.Branch:
    obj = require_object_fields(value, "body result")
    return p.Branch(parse_node(obj["body"]), parse_export(obj["result"]))


def parse_node(value: Json) -> p.Node:
    tag = require_kind(value)
    if tag == "code":
        obj = require_object_fields(value, "kind metadata function_id")
        return p.CodeStep(
            parse_metadata(obj["metadata"]), require_text(obj["function_id"])
        )
    if tag == "ai":
        obj = require_object_fields(value, "kind metadata prompt_revision")
        return p.AiStep(
            parse_metadata(obj["metadata"]), require_text(obj["prompt_revision"])
        )
    if tag == "human":
        obj = require_object_fields(
            value, "kind metadata eligible_role due_at request never_automate"
        )
        return p.HumanStep(
            parse_metadata(obj["metadata"]),
            require_text(obj["eligible_role"]),
            datetime.fromisoformat(require_text(obj["due_at"])),
            parse_export(obj["request"]),
            require_boolean(obj["never_automate"]),
        )
    if tag == "sequence":
        obj = require_object_fields(value, "kind node_id children result")
        return p.Sequence(
            require_text(obj["node_id"]),
            tuple(parse_node(item) for item in require_items(obj["children"])),
            parse_export(obj["result"]),
        )
    if tag == "choose":
        obj = require_object_fields(
            value, "kind node_id condition when_true when_false output"
        )
        return p.Choose(
            require_text(obj["node_id"]),
            parse_input(obj["condition"]),
            parse_branch(obj["when_true"]),
            parse_branch(obj["when_false"]),
            parse_schema(obj["output"]),
        )
    if tag == "each":
        obj = require_object_fields(
            value, "kind node_id collection output input_schema body"
        )
        return p.Each(
            require_text(obj["node_id"]),
            parse_input(obj["collection"]),
            parse_keyed_schema(obj["output"]),
            parse_keyed_schema(obj["input_schema"]),
            parse_branch(obj["body"]),
        )
    if tag == "parallel":
        obj = require_object_fields(value, "kind node_id branches output")
        branches: list[p.NamedBranch] = []
        for item in require_items(obj["branches"]):
            entry = require_object_fields(item, "name branch")
            branches.append(
                p.NamedBranch(
                    require_text(entry["name"]), parse_branch(entry["branch"])
                )
            )
        return p.Parallel(
            require_text(obj["node_id"]),
            tuple(branches),
            parse_record_schema(obj["output"]),
        )
    if tag == "repeat":
        obj = require_object_fields(value, "kind node_id initial body until bound")
        bound_kind = require_kind(obj["bound"])
        if bound_kind == "finite":
            bound_obj = require_object_fields(obj["bound"], "kind limit")
            bound: p.FiniteRepeat | p.EventRepeat = p.FiniteRepeat(
                require_integer(bound_obj["limit"])
            )
        elif bound_kind == "event":
            bound_obj = require_object_fields(obj["bound"], "kind event")
            bound = p.EventRepeat(require_text(bound_obj["event"]))
        else:
            raise ScenarioError("Unsupported repeat bound: " + bound_kind)
        return p.Repeat(
            require_text(obj["node_id"]),
            parse_export(obj["initial"]),
            parse_branch(obj["body"]),
            parse_input(obj["until"]),
            bound,
        )
    raise ScenarioError("Unsupported node kind: " + tag)


def parse_function(value: Json) -> p.FunctionDeclaration:
    obj = require_object_fields(value, "function_id inputs output body tests")
    body = require_object_fields(obj["body"], "language_version source")
    return p.FunctionDeclaration(
        require_text(obj["function_id"]),
        tuple(parse_field(item) for item in require_items(obj["inputs"])),
        parse_schema(obj["output"]),
        p.FunctionBody(
            require_text(body["language_version"]), require_text(body["source"])
        ),
        tuple(parse_function_test(item) for item in require_items(obj["tests"])),
    )


def parse_constraint(value: Json) -> p.Constraint:
    obj = require_object_fields(value, "dimension schema value")
    return p.Constraint(
        require_text(obj["dimension"]),
        parse_schema(obj["schema"]),
        parse_value(obj["value"]),
    )


def parse_rule(value: Json) -> p.DatedRule:
    obj = require_object_fields(
        value,
        "rule_id target scope effective_from effective_until consequence citations",
    )
    until = obj["effective_until"]
    return p.DatedRule(
        require_text(obj["rule_id"]),
        require_text(obj["target"]),
        tuple(parse_constraint(item) for item in require_items(obj["scope"])),
        parse_date(obj["effective_from"]),
        None if until is None else parse_date(until),
        parse_export(obj["consequence"]),
        tuple(parse_citation(item) for item in require_items(obj["citations"])),
    )


def parse_saved_scenario(value: Json) -> p.ProgramScenario:
    obj = require_object_fields(value, "scenario_id inputs expected citations")
    return p.ProgramScenario(
        require_text(obj["scenario_id"]),
        tuple(parse_named_value(item) for item in require_items(obj["inputs"])),
        parse_value(obj["expected"]),
        tuple(parse_citation(item) for item in require_items(obj["citations"])),
    )


def parse_program(value: Json) -> Program:
    obj = require_object_fields(value, "name draft sources")
    draft = require_object_fields(
        obj["draft"],
        "program_id revision schemas inputs root functions rules scenarios",
    )
    return Program(
        require_text(obj["name"]),
        p.ProgramDraft(
            require_text(draft["program_id"]),
            require_text(draft["revision"]),
            tuple(
                parse_record_schema(item) for item in require_items(draft["schemas"])
            ),
            tuple(parse_field(item) for item in require_items(draft["inputs"])),
            parse_node(draft["root"]),
            tuple(parse_function(item) for item in require_items(draft["functions"])),
            tuple(parse_rule(item) for item in require_items(draft["rules"])),
            tuple(
                parse_saved_scenario(item) for item in require_items(draft["scenarios"])
            ),
        ),
        parse_catalog(obj["sources"]),
    )


def parse_function_test(value: Json) -> p.FunctionTest:
    obj = require_object_fields(value, "test_id inputs expected")
    return p.FunctionTest(
        require_text(obj["test_id"]),
        tuple(parse_named_value(item) for item in require_items(obj["inputs"])),
        parse_value(obj["expected"]),
    )


def parse_limits(value: Json) -> Limits:
    obj = require_object_fields(
        value,
        "source_bytes nesting string_bytes collection_count integer_magnitude allocations work functions ast_nodes call_depth",
    )
    return Limits(**{name: require_integer(item) for name, item in obj.items()})


def parse_command(value: Json) -> Command:
    tag = require_kind(value)
    if tag == "call":
        obj = require_object_fields(value, "kind program function_id inputs limits")
        return FunctionCommand(
            require_text(obj["program"]),
            require_text(obj["function_id"]),
            tuple(parse_named_value(item) for item in require_items(obj["inputs"])),
            parse_limits(obj["limits"]),
        )
    obj = require_object_fields(value, "kind program")
    if tag not in {"verify", "activate"}:
        raise ScenarioError("Unsupported command kind: " + tag)
    return ProgramCommand(tag, require_text(obj["program"]))


def parse_expected(value: Json) -> Expected | FunctionExpected:
    if isinstance(value, dict) and value.get("status") in {
        "function_result",
        "function_failure",
    }:
        obj = require_object_fields(value, "status value failure")
        status = require_text(obj["status"])
        result = None if obj["value"] is None else parse_value(obj["value"])
        failure = None if obj["failure"] is None else require_text(obj["failure"])
        if (
            status == "function_result" and (result is None or failure is not None)
        ) or (status == "function_failure" and (result is not None or failure is None)):
            raise ScenarioError("Function expectation must name one value or failure.")
        return FunctionExpected(status, result, failure)
    obj = require_object_fields(value, "status diagnostic_codes missing_checks")
    status = require_text(obj["status"])
    if status not in {
        "structural_failure",
        "execution_pending",
        "unsupported_activation",
    }:
        raise ScenarioError("Unsupported expected status: " + status)
    return Expected(
        status,
        tuple(require_text(item) for item in require_items(obj["diagnostic_codes"])),
        tuple(require_text(item) for item in require_items(obj["missing_checks"])),
    )


def require_unique_object(pairs: list[tuple[str, Json]]) -> dict[str, Json]:
    result: dict[str, Json] = {}
    for name, value in pairs:
        if name in result:
            raise ScenarioError("Duplicate JSON field: " + name)
        result[name] = value
    return result


def reject_constant(value: str) -> None:
    raise ScenarioError("Non-finite JSON number: " + value)


def parse_scenario(source: bytes) -> Scenario:
    if len(source) > MAX_BYTES:
        raise ScenarioError("Scenario exceeds byte limit.")
    try:
        data = cast(
            Json,
            json.loads(
                source.decode("utf-8"),
                object_pairs_hook=require_unique_object,
                parse_constant=reject_constant,
            ),
        )
        stack = [(data, 0)]
        while stack:
            item, depth = stack.pop()
            if depth > MAX_DEPTH:
                raise ScenarioError("Scenario exceeds nesting limit.")
            if isinstance(item, dict):
                for name in item:
                    name.encode("utf-8")
                stack.extend((child, depth + 1) for child in item.values())
            elif isinstance(item, list):
                stack.extend((child, depth + 1) for child in item)
            elif isinstance(item, str):
                item.encode("utf-8")
        obj = require_object_fields(
            data, "format scenario_id programs commands expected"
        )
        if require_text(obj["format"]) != "dex-eval-scenario-2":
            raise ScenarioError("Unsupported evaluator scenario format.")
        result = Scenario(
            require_text(obj["scenario_id"]),
            tuple(parse_program(item) for item in require_items(obj["programs"])),
            tuple(parse_command(item) for item in require_items(obj["commands"])),
            tuple(parse_expected(item) for item in require_items(obj["expected"])),
        )
    except (ValueError, RecursionError) as error:
        raise ScenarioError(str(error)) from error
    names = tuple(item.name for item in result.programs)
    if not result.scenario_id.strip() or any(not name.strip() for name in names):
        raise ScenarioError("Scenario and catalog names must be nonempty.")
    if len(set(names)) != len(names):
        raise ScenarioError("Duplicate program catalog name.")
    if not result.commands or len(result.commands) != len(result.expected):
        raise ScenarioError("Each command needs exactly one evaluator expectation.")
    if any(item.program not in names for item in result.commands):
        raise ScenarioError("Command references an unknown program.")
    return result

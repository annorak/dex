from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import cast

import pytest

from dex.core.language import DEFAULT_LIMITS
from dex.core.program import (
    AiStep,
    Choose,
    CodeStep,
    DateValue,
    Each,
    ExecutionPending,
    HumanStep,
    IntValue,
    KeyedSchema,
    Literal,
    MoneyValue,
    Parallel,
    PresentValue,
    ReferenceSchema,
    Repeat,
    Schema,
    Sequence,
    StructuralFailure,
    TaggedValue,
    UnresolvedTextValue,
    Value,
    verify_program,
)
from dex.eval.scenario_format import (
    MAX_BYTES,
    MAX_DEPTH,
    Expected,
    ScenarioError,
    parse_scenario,
)
from dex.eval.scenarios import evaluate

type Json = None | bool | int | float | str | list[Json] | dict[str, Json]
FIXTURES = Path(__file__).resolve().parents[1] / "scenarios"
NAMES = (
    "program-valid",
    "program-kinds",
    "program-values",
    "program-unresolved-id",
    "program-reference-scope",
    "program-citation-unicode",
    "program-citation-mismatch",
    "program-rule-conflict",
    "program-change-contract",
    "program-unsupported-activation",
)
MISSING = (
    "bounded_graph_execution",
    "saved_scenario_execution",
    "resolved_identity_membership",
    "ai_recording_and_output_validation",
    "external_change_execution_contracts",
)


def read_fixture_bytes(name: str = "program-valid") -> bytes:
    return (FIXTURES / f"{name}.json").read_bytes()


def require_object(value: Json) -> dict[str, Json]:
    assert isinstance(value, dict)
    return value


def require_array(value: Json) -> list[Json]:
    assert isinstance(value, list)
    return value


def read_document(name: str = "program-valid") -> dict[str, Json]:
    return require_object(cast(Json, json.loads(read_fixture_bytes(name))))


def get_draft(data: dict[str, Json]) -> dict[str, Json]:
    catalog = require_array(data["programs"])
    return require_object(require_object(catalog[0])["draft"])


def encode_document(data: Json) -> bytes:
    return json.dumps(data, ensure_ascii=False).encode("utf-8")


@pytest.mark.parametrize("name", NAMES)
def test_fixture_observations_match_independent_expectations(name: str) -> None:
    scenario = parse_scenario(read_fixture_bytes(name))
    evaluation = evaluate(scenario)
    assert len(evaluation.observations) == len(scenario.commands)
    assert evaluation.matches == (True,) * len(scenario.commands)
    for command, observed, expected in zip(
        scenario.commands, evaluation.observations, scenario.expected, strict=True
    ):
        assert isinstance(expected, Expected)
        assert observed.command == command.kind
        assert observed.program == command.program
        assert observed.status == expected.status
        assert (
            tuple(item.code for item in observed.diagnostics)
            == expected.diagnostic_codes
        )
        assert (
            tuple(str(item) for item in observed.missing_checks)
            == expected.missing_checks
        )


def test_structural_success_preserves_artifact_and_does_not_claim_execution() -> None:
    scenario = parse_scenario(read_fixture_bytes())
    evaluation = evaluate(scenario)
    observed = evaluation.observations[0]
    assert observed.status == "execution_pending"
    assert tuple(str(item) for item in observed.missing_checks) == MISSING
    assert observed.artifact is not None
    assert observed.artifact.draft == scenario.programs[0].draft
    assert observed.artifact.sources == scenario.programs[0].sources
    assert observed.artifact.verifier_version == "structure-language-1"


@pytest.mark.parametrize("name", NAMES)
def test_evaluator_preserves_real_verifier_result(name: str) -> None:
    scenario = parse_scenario(read_fixture_bytes(name))
    evaluation = evaluate(scenario)
    catalog = {program.name: program for program in scenario.programs}
    for command, observed in zip(
        scenario.commands, evaluation.observations, strict=True
    ):
        program = catalog[command.program]
        result = verify_program(program.draft, program.sources, DEFAULT_LIMITS)
        if isinstance(result, StructuralFailure):
            assert observed.artifact is None
            assert observed.diagnostics[: len(result.diagnostics)] == result.diagnostics
            assert observed.missing_checks == ()
        else:
            assert isinstance(result, ExecutionPending)
            assert observed.artifact == result.artifact
            assert observed.missing_checks == result.missing_checks
        if command.kind == "activate":
            assert observed.status == "unsupported_activation"
            assert observed.diagnostics[-1].code == "unsupported_activation"


def test_expected_answers_cannot_change_observations() -> None:
    original = parse_scenario(read_fixture_bytes("program-citation-mismatch"))
    tampered_data = read_document("program-citation-mismatch")
    expected = require_object(require_array(tampered_data["expected"])[0])
    expected.update(
        status="execution_pending", diagnostic_codes=[], missing_checks=list(MISSING)
    )
    tampered = parse_scenario(encode_document(tampered_data))
    before = evaluate(original)
    after = evaluate(tampered)
    assert after.observations == before.observations
    assert before.matches == (True, True, True)
    assert after.matches == (False, True, True)


def test_forbidden_function_source_is_rejected_without_running_python() -> None:
    data = read_document()
    declaration = require_object(require_array(get_draft(data)["functions"])[0])
    body = require_object(declaration["body"])
    source = "raise AssertionError('scenario evaluation executed function source')"
    body["source"] = source
    scenario = parse_scenario(encode_document(data))
    observed = evaluate(scenario).observations[0]
    assert observed.status == "structural_failure"
    assert observed.diagnostics[0].code == "unsupported_syntax"
    assert observed.artifact is None


def test_wire_variants_produce_core_types() -> None:
    kinds = parse_scenario(read_fixture_bytes("program-kinds"))
    roots = {item.name: item.draft.root for item in kinds.programs}
    assert isinstance(roots["code"], CodeStep)
    assert isinstance(roots["ai"], AiStep)
    assert isinstance(roots["human"], HumanStep)
    human = roots["human"]
    assert isinstance(human, HumanStep)
    assert human.never_automate is True
    assert human.due_at.utcoffset() is not None
    assert isinstance(roots["sequence"], Sequence)
    assert isinstance(roots["choose"], Choose)
    assert isinstance(roots["each"], Each)
    assert isinstance(roots["parallel"], Parallel)
    assert isinstance(roots["repeat-finite"], Repeat)
    assert isinstance(roots["repeat-event"], Repeat)
    values = parse_scenario(read_fixture_bytes("program-values"))
    decoded: dict[str, Value] = {}
    schemas: dict[str, Schema] = {}
    for program in values.programs:
        root = program.draft.root
        assert isinstance(root, CodeStep)
        value = root.metadata.inputs[0].value
        assert isinstance(value, Literal)
        decoded[program.name] = value.value
        schemas[program.name] = root.metadata.inputs[0].schema
    assert isinstance(decoded["integer"], IntValue)
    assert isinstance(decoded["date"], DateValue)
    assert isinstance(decoded["money"], MoneyValue)
    assert isinstance(decoded["present"], PresentValue)
    assert isinstance(decoded["tagged"], TaggedValue)
    assert isinstance(decoded["unresolved"], UnresolvedTextValue)
    assert isinstance(schemas["keyed"], KeyedSchema)
    assert isinstance(schemas["resolved"], ReferenceSchema)


def test_unicode_citations_use_codepoints_and_verify_exact_quote() -> None:
    scenario = parse_scenario(read_fixture_bytes("program-citation-unicode"))
    root = scenario.programs[0].draft.root
    assert isinstance(root, CodeStep)
    citation = root.metadata.citations[0]
    assert (citation.start, citation.end, citation.quote) == (1, 2, "\U0001f41a")
    observed = evaluate(scenario).observations[0]
    assert observed.status == "execution_pending"
    assert observed.diagnostics == ()


def test_lone_surrogate_is_rejected_inside_a_valid_envelope() -> None:
    data = read_document()
    root = require_object(get_draft(data)["root"])
    metadata = require_object(root["metadata"])
    citation = require_object(require_array(metadata["citations"])[0])
    citation["quote"] = "\ud800"
    raw = json.dumps(data, ensure_ascii=True).encode("utf-8")
    with pytest.raises(ScenarioError):
        parse_scenario(raw)


def test_strict_envelope_version_fields_and_types() -> None:
    mutations: tuple[tuple[str, Json], ...] = (
        ("format", "dex-eval-scenario-1"),
        ("scenario_id", True),
        ("programs", {}),
        ("commands", "verify"),
        ("expected", None),
        ("unknown", 1),
    )
    for key, value in mutations:
        data = read_document()
        data[key] = value
        with pytest.raises(ScenarioError):
            parse_scenario(encode_document(data))
    for key in read_document():
        data = read_document()
        del data[key]
        with pytest.raises(ScenarioError):
            parse_scenario(encode_document(data))


@pytest.mark.parametrize(
    "location", ("draft", "metadata", "function", "source", "pin", "citation")
)
def test_nested_objects_reject_unknown_fields(location: str) -> None:
    data = read_document()
    program = require_object(require_array(data["programs"])[0])
    root = require_object(get_draft(data)["root"])
    metadata = require_object(root["metadata"])
    source = require_object(
        require_array(require_object(program["sources"])["entries"])[0]
    )
    objects = {
        "draft": get_draft(data),
        "metadata": metadata,
        "function": require_object(require_array(get_draft(data)["functions"])[0]),
        "source": source,
        "pin": require_object(source["pin"]),
        "citation": require_object(require_array(metadata["citations"])[0]),
    }
    objects[location]["unknown"] = "rejected"
    with pytest.raises(ScenarioError):
        parse_scenario(encode_document(data))


@pytest.mark.parametrize("kind", ("shell", "network", "eval", "import", "unknown"))
def test_unknown_node_kinds_are_rejected(kind: str) -> None:
    data = read_document()
    require_object(get_draft(data)["root"])["kind"] = kind
    with pytest.raises(ScenarioError):
        parse_scenario(encode_document(data))


@pytest.mark.parametrize(
    "kind, field, value",
    (
        ("integer", "value", True),
        ("boolean", "value", 1),
        ("money_cents", "cents", False),
        ("text", "value", 7),
        ("date", "value", "2026-02-30"),
    ),
)
def test_scalar_wire_types_are_exact(kind: str, field: str, value: Json) -> None:
    data = read_document()
    root = require_object(get_draft(data)["root"])
    metadata = require_object(root["metadata"])
    metadata["inputs"] = [
        {
            "name": "bad",
            "schema": {"kind": kind},
            "value": {"kind": "literal", "value": {"kind": kind, field: value}},
        }
    ]
    with pytest.raises(ScenarioError):
        parse_scenario(encode_document(data))


def test_duplicate_object_keys_are_rejected_at_any_depth() -> None:
    original = read_fixture_bytes()
    for needle, replacement in (
        (b'"format":', b'"format": "dex-eval-scenario-2", "format":'),
        (b'"revision":', b'"revision": "r1", "revision":'),
    ):
        assert needle in original
        with pytest.raises(ScenarioError):
            parse_scenario(original.replace(needle, replacement, 1))


def test_duplicate_program_names_and_unknown_command_targets_are_rejected() -> None:
    duplicate = read_document()
    catalog = require_array(duplicate["programs"])
    catalog.append(deepcopy(catalog[0]))
    with pytest.raises(ScenarioError):
        parse_scenario(encode_document(duplicate))
    unknown = read_document()
    require_object(require_array(unknown["commands"])[0])["program"] = "absent"
    with pytest.raises(ScenarioError):
        parse_scenario(encode_document(unknown))


def test_expected_count_must_equal_command_count() -> None:
    data = read_document()
    data["expected"] = []
    with pytest.raises(ScenarioError):
        parse_scenario(encode_document(data))


def test_input_size_and_depth_are_bounded() -> None:
    with pytest.raises(ScenarioError):
        parse_scenario(b" " * (MAX_BYTES + 1))
    nested = b"[" * (MAX_DEPTH + 1) + b"0" + b"]" * (MAX_DEPTH + 1)
    with pytest.raises(ScenarioError):
        parse_scenario(nested)


@pytest.mark.parametrize(
    "raw",
    (
        b"",
        b"{",
        b"[]",
        b"null",
        b"\xff",
        b'{"x": NaN}',
        b'{"x": Infinity}',
        b'{"x": "\\ud800"}',
    ),
)
def test_malformed_json_is_a_scenario_error(raw: bytes) -> None:
    with pytest.raises(ScenarioError):
        parse_scenario(raw)


@pytest.mark.parametrize("name", NAMES)
def test_emitted_artifacts_round_trip_without_losing_types(name: str) -> None:
    from dex.eval.scenario_format import parse_program as decode_program
    from dex.eval.scenario_output import encode_core

    scenario = parse_scenario(read_fixture_bytes(name))
    catalog = {item.name: item for item in scenario.programs}
    for observation in evaluate(scenario).observations:
        if observation.artifact is None:
            continue
        snapshot = require_object(encode_core(observation.artifact))
        restored = decode_program(
            {
                "name": observation.program,
                "draft": snapshot["draft"],
                "sources": snapshot["sources"],
            }
        )
        assert restored == catalog[observation.program]


@pytest.mark.parametrize("field", ["original_sha256", "extraction_sha256"])
@pytest.mark.parametrize(
    "digest",
    [
        "a" * 64,
        "sha512:" + "a" * 64,
        "SHA256:" + "a" * 64,
        "sha256:" + "A" * 64,
        "sha256:" + "g" * 64,
        "sha256:" + "a" * 63,
        "sha256:" + "a" * 65,
        "sha256:" + "a" * 64 + "\n",
        7,
    ],
)
def test_source_pin_rejects_noncanonical_digest(field: str, digest: Json) -> None:
    from dex.eval.scenario_format import parse_pin

    pin: dict[str, Json] = {
        "source": "source",
        "revision": "revision",
        "original_sha256": "sha256:" + "a" * 64,
        "extraction": "extraction",
        "extraction_sha256": "sha256:" + "a" * 64,
    }
    pin[field] = digest
    with pytest.raises(ScenarioError):
        parse_pin(pin)


def test_artifact_digest_tags_preserve_core_hashes() -> None:
    from hashlib import sha256

    from dex.eval.scenario_format import parse_pin
    from dex.eval.scenario_output import encode_core

    scenario = parse_scenario(read_fixture_bytes())
    observation = evaluate(scenario).observations[0]
    assert observation.artifact is not None
    extraction = observation.artifact.sources.entries[0]
    digest = sha256(extraction.text.encode("utf-8")).hexdigest()
    assert extraction.pin.original_sha256 == digest
    assert extraction.pin.extraction_sha256 == digest
    snapshot = require_object(encode_core(observation.artifact))
    sources = require_object(snapshot["sources"])
    entry = require_object(require_array(sources["entries"])[0])
    wire_pin = require_object(entry["pin"])
    assert wire_pin["original_sha256"] == "sha256:" + digest
    assert wire_pin["extraction_sha256"] == "sha256:" + digest
    assert parse_pin(wire_pin) == extraction.pin

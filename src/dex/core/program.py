from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from hashlib import sha256
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dex.core.language import CheckedFunctions, LanguageFailure, Limits


class Scalar(StrEnum):
    BOOLEAN = "boolean"
    INTEGER = "integer"
    TEXT = "text"
    DATE = "date"
    MONEY = "money_cents"


@dataclass(frozen=True)
class OptionalSchema:
    item: "Schema"


@dataclass(frozen=True)
class Field:
    name: str
    schema: "Schema"


@dataclass(frozen=True)
class TaggedSchema:
    variants: tuple[Field, ...]


@dataclass(frozen=True)
class RecordSchema:
    name: str
    fields: tuple[Field, ...]


@dataclass(frozen=True)
class KeyedSchema:
    item: RecordSchema
    key_field: str


@dataclass(frozen=True)
class ReferenceSchema:
    record: str
    key_field: str


@dataclass(frozen=True)
class UnresolvedSchema:
    pass


type Schema = (
    Scalar
    | OptionalSchema
    | TaggedSchema
    | RecordSchema
    | KeyedSchema
    | ReferenceSchema
    | UnresolvedSchema
)


@dataclass(frozen=True)
class BoolValue:
    value: bool


@dataclass(frozen=True)
class IntValue:
    value: int


@dataclass(frozen=True)
class TextValue:
    value: str


@dataclass(frozen=True)
class DateValue:
    value: date


@dataclass(frozen=True)
class MoneyValue:
    cents: int


@dataclass(frozen=True)
class AbsentValue:
    pass


@dataclass(frozen=True)
class PresentValue:
    value: "Value"


@dataclass(frozen=True)
class TaggedValue:
    tag: str
    value: "Value"


@dataclass(frozen=True)
class NamedValue:
    name: str
    value: "Value"


@dataclass(frozen=True)
class RecordValue:
    record: str
    fields: tuple[NamedValue, ...]


@dataclass(frozen=True)
class KeyedEntry:
    key: str
    value: RecordValue


@dataclass(frozen=True)
class KeyedValue:
    entries: tuple[KeyedEntry, ...]


@dataclass(frozen=True)
class ResolvedRefValue:
    record: str
    key_field: str
    key: str


@dataclass(frozen=True)
class UnresolvedTextValue:
    text: str


type Value = (
    BoolValue
    | IntValue
    | TextValue
    | DateValue
    | MoneyValue
    | AbsentValue
    | PresentValue
    | TaggedValue
    | RecordValue
    | KeyedValue
    | ResolvedRefValue
    | UnresolvedTextValue
)


@dataclass(frozen=True)
class Literal:
    value: Value


@dataclass(frozen=True)
class ProgramInputRef:
    name: str
    path: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResultRef:
    node: str
    path: tuple[str, ...] = ()


@dataclass(frozen=True)
class LocalRef:
    owner: str
    name: str
    path: tuple[str, ...] = ()


type Input = Literal | ProgramInputRef | ResultRef | LocalRef


@dataclass(frozen=True)
class Binding:
    name: str
    schema: Schema
    value: Input


@dataclass(frozen=True)
class Export:
    schema: Schema
    value: Input


@dataclass(frozen=True)
class SourcePin:
    source: str
    revision: str
    original_sha256: str
    extraction: str
    extraction_sha256: str


@dataclass(frozen=True)
class Section:
    name: str
    locator: str
    start: int
    end: int


@dataclass(frozen=True)
class SourceExtraction:
    pin: SourcePin
    text: str
    sections: tuple[Section, ...]


@dataclass(frozen=True)
class SourceCatalog:
    entries: tuple[SourceExtraction, ...]


@dataclass(frozen=True)
class Citation:
    pin: SourcePin
    section: str
    locator: str
    start: int
    end: int
    quote: str


@dataclass(frozen=True)
class ChangeDeclaration:
    change_id: str
    operation: str
    payload: Export


@dataclass(frozen=True)
class StepMetadata:
    step_id: str
    behavior_id: str
    intent: str
    citations: tuple[Citation, ...]
    inputs: tuple[Binding, ...]
    output: Schema
    changes: tuple[ChangeDeclaration, ...] = ()


@dataclass(frozen=True)
class FunctionBody:
    language_version: str
    source: str


@dataclass(frozen=True)
class FunctionTest:
    test_id: str
    inputs: tuple[NamedValue, ...]
    expected: Value


@dataclass(frozen=True)
class FunctionDeclaration:
    function_id: str
    inputs: tuple[Field, ...]
    output: Schema
    body: FunctionBody
    tests: tuple[FunctionTest, ...]


@dataclass(frozen=True)
class CodeStep:
    metadata: StepMetadata
    function_id: str


@dataclass(frozen=True)
class AiStep:
    metadata: StepMetadata
    prompt_revision: str


@dataclass(frozen=True)
class HumanStep:
    metadata: StepMetadata
    eligible_role: str
    due_at: datetime
    request: Export
    never_automate: bool


@dataclass(frozen=True)
class Sequence:
    node_id: str
    children: tuple["Node", ...]
    result: Export


@dataclass(frozen=True)
class Branch:
    body: "Node"
    result: Export


@dataclass(frozen=True)
class Choose:
    node_id: str
    condition: Input
    when_true: Branch
    when_false: Branch
    output: Schema


@dataclass(frozen=True)
class Each:
    node_id: str
    collection: Input
    output: KeyedSchema
    input_schema: KeyedSchema
    body: Branch


@dataclass(frozen=True)
class NamedBranch:
    name: str
    branch: Branch


@dataclass(frozen=True)
class Parallel:
    node_id: str
    branches: tuple[NamedBranch, ...]
    output: RecordSchema


@dataclass(frozen=True)
class FiniteRepeat:
    limit: int


@dataclass(frozen=True)
class EventRepeat:
    event: str


@dataclass(frozen=True)
class Repeat:
    node_id: str
    initial: Export
    body: Branch
    until: Input
    bound: FiniteRepeat | EventRepeat


type Node = CodeStep | AiStep | HumanStep | Sequence | Choose | Each | Parallel | Repeat


@dataclass(frozen=True)
class Constraint:
    dimension: str
    schema: Schema
    value: Value


@dataclass(frozen=True)
class DatedRule:
    rule_id: str
    target: str
    scope: tuple[Constraint, ...]
    effective_from: date
    effective_until: date | None
    consequence: Export
    citations: tuple[Citation, ...]


@dataclass(frozen=True)
class ProgramScenario:
    scenario_id: str
    inputs: tuple[NamedValue, ...]
    expected: Value
    citations: tuple[Citation, ...]


@dataclass(frozen=True)
class ProgramDraft:
    program_id: str
    revision: str
    schemas: tuple[RecordSchema, ...]
    inputs: tuple[Field, ...]
    root: Node
    functions: tuple[FunctionDeclaration, ...]
    rules: tuple[DatedRule, ...]
    scenarios: tuple[ProgramScenario, ...]


@dataclass(frozen=True)
class Diagnostic:
    code: str
    path: str
    message: str


@dataclass(frozen=True)
class StructuralFailure:
    diagnostics: tuple[Diagnostic, ...]
    function_failure: "LanguageFailure | None"


@dataclass(frozen=True)
class StructuralArtifact:
    draft: ProgramDraft
    sources: SourceCatalog
    checked_functions: "CheckedFunctions"
    verifier_version: str = "structure-language-1"


class MissingCheck(StrEnum):
    LANGUAGE = "restricted_language_and_function_types"
    EXECUTION = "bounded_graph_execution"
    SCENARIOS = "saved_scenario_execution"
    RECORDS = "resolved_identity_membership"
    AI = "ai_recording_and_output_validation"
    CHANGES = "external_change_execution_contracts"


@dataclass(frozen=True)
class ExecutionPending:
    artifact: StructuralArtifact
    missing_checks: tuple[MissingCheck, ...]


type VerificationResult = StructuralFailure | ExecutionPending
MAX_NESTING = 48
MAX_NODES = 10000


def node_identity(node: Node) -> str:
    if isinstance(node, (CodeStep, AiStep, HumanStep)):
        return node.metadata.step_id
    return node.node_id


def node_output(node: Node) -> Schema:
    if isinstance(node, (CodeStep, AiStep, HumanStep)):
        return node.metadata.output
    if isinstance(node, Sequence):
        return node.result.schema
    if isinstance(node, Repeat):
        return node.initial.schema
    return node.output


def normalized_value(value: Value) -> Value:
    if isinstance(value, PresentValue):
        return PresentValue(normalized_value(value.value))
    if isinstance(value, TaggedValue):
        return TaggedValue(value.tag, normalized_value(value.value))
    if isinstance(value, RecordValue):
        return RecordValue(
            value.record,
            tuple(
                NamedValue(item.name, normalized_value(item.value))
                for item in sorted(value.fields, key=lambda item: item.name)
            ),
        )
    if isinstance(value, KeyedValue):
        entries: list[KeyedEntry] = []
        for item in sorted(value.entries, key=lambda item: item.key):
            record = RecordValue(
                item.value.record,
                tuple(
                    NamedValue(field.name, normalized_value(field.value))
                    for field in sorted(item.value.fields, key=lambda field: field.name)
                ),
            )
            entries.append(KeyedEntry(item.key, record))
        return KeyedValue(tuple(entries))
    return value


class _Verifier:
    def __init__(
        self, draft: ProgramDraft, sources: SourceCatalog, limits: "Limits"
    ) -> None:
        self.limits = limits
        self.draft = draft
        self.sources = sources
        self.errors: list[Diagnostic] = []
        self.records: dict[str, RecordSchema] = {}
        self.functions: dict[str, FunctionDeclaration] = {}
        self.inputs: dict[str, Schema] = {}
        self.nodes: dict[str, Node] = {}
        self.sections: dict[tuple[str, str], Section] = {}
        self.extractions: dict[str, SourceExtraction] = {}
        self.bindings: dict[tuple[str, str], Schema] = {}
        self.undo: list[tuple[str, str]] = []
        self.change_ids: set[str] = set()

    def fail(self, code: str, path: str, message: str) -> None:
        self.errors.append(Diagnostic(code, path, message))

    def names(self, names: tuple[str, ...], path: str) -> None:
        seen: set[str] = set()
        for name in names:
            if not name.strip():
                self.fail("empty_identity", path, "Names must be nonempty.")
            if name in seen:
                self.fail("duplicate_identity", path, name)
            seen.add(name)

    def index(self) -> None:
        self.names((self.draft.program_id,), "program")
        self.names((self.draft.revision,), "revision")
        self.names(tuple(record.name for record in self.draft.schemas), "schemas")
        self.records = {record.name: record for record in self.draft.schemas}
        self.names(
            tuple(item.function_id for item in self.draft.functions), "functions"
        )
        self.functions = {item.function_id: item for item in self.draft.functions}
        self.names(tuple(item.name for item in self.draft.inputs), "inputs")
        self.inputs = {item.name: item.schema for item in self.draft.inputs}
        stack = [(self.draft.root, 0)]
        while stack:
            node, depth = stack.pop()
            name = node_identity(node)
            if depth > MAX_NESTING or len(self.nodes) >= MAX_NODES:
                self.fail("graph_limit", name, "Graph exceeds structural limits.")
                return
            self.names((name,), "nodes")
            if name in self.nodes:
                self.fail("duplicate_identity", "nodes", name)
                continue
            self.nodes[name] = node
            children: tuple[Node, ...] = ()
            if isinstance(node, Sequence):
                children = node.children
            elif isinstance(node, Choose):
                children = (node.when_true.body, node.when_false.body)
            elif isinstance(node, Parallel):
                children = tuple(item.branch.body for item in node.branches)
            elif isinstance(node, (Each, Repeat)):
                children = (node.body.body,)
            stack.extend((child, depth + 1) for child in reversed(children))

    def schema(self, schema: Schema, path: str, depth: int = 0) -> None:
        if depth > MAX_NESTING:
            self.fail("schema_limit", path, "Schema nesting exceeds the limit.")
            return
        if isinstance(schema, (Scalar, UnresolvedSchema)):
            return
        if isinstance(schema, OptionalSchema):
            self.schema(schema.item, path, depth + 1)
        elif isinstance(schema, (TaggedSchema, RecordSchema)):
            fields = (
                schema.variants if isinstance(schema, TaggedSchema) else schema.fields
            )
            self.names(tuple(item.name for item in fields), path)
            if isinstance(schema, TaggedSchema) and not fields:
                self.fail("empty_variants", path, "A tagged schema needs a variant.")
            if (
                isinstance(schema, RecordSchema)
                and self.records.get(schema.name) != schema
            ):
                self.fail("record_declaration", path, schema.name)
            for item in fields:
                self.schema(item.schema, path + "." + item.name, depth + 1)
        elif isinstance(schema, KeyedSchema):
            self.schema(schema.item, path, depth + 1)
            self.key_field(schema.item, schema.key_field, path)
        else:
            target = self.records.get(schema.record)
            if target is None:
                self.fail("unknown_record", path, schema.record)
            else:
                self.key_field(target, schema.key_field, path)

    def key_field(self, record: RecordSchema, key: str, path: str) -> None:
        fields = {item.name: item.schema for item in record.fields}
        if fields.get(key) != Scalar.TEXT:
            self.fail("record_key", path, "Stable keys must name a text field.")

    def value(self, value: Value, schema: Schema, path: str, depth: int = 0) -> None:
        if depth > MAX_NESTING:
            self.fail("value_limit", path, "Value nesting exceeds the limit.")
            return
        valid = False
        if schema == Scalar.BOOLEAN:
            valid = isinstance(value, BoolValue) and type(value.value) is bool
        elif schema == Scalar.INTEGER:
            valid = isinstance(value, IntValue) and type(value.value) is int
        elif schema == Scalar.TEXT:
            valid = isinstance(value, TextValue) and type(value.value) is str
        elif schema == Scalar.DATE:
            valid = isinstance(value, DateValue) and type(value.value) is date
        elif schema == Scalar.MONEY:
            valid = isinstance(value, MoneyValue) and type(value.cents) is int
        elif isinstance(schema, UnresolvedSchema):
            valid = isinstance(value, UnresolvedTextValue)
        elif isinstance(schema, ReferenceSchema):
            valid = (
                isinstance(value, ResolvedRefValue)
                and value.record == schema.record
                and value.key_field == schema.key_field
                and bool(value.key)
            )
        elif isinstance(schema, OptionalSchema):
            valid = isinstance(value, (AbsentValue, PresentValue))
            if isinstance(value, PresentValue):
                self.value(value.value, schema.item, path, depth + 1)
        elif isinstance(schema, TaggedSchema) and isinstance(value, TaggedValue):
            variants = {item.name: item.schema for item in schema.variants}
            valid = value.tag in variants
            if valid:
                self.value(value.value, variants[value.tag], path, depth + 1)
        elif isinstance(schema, RecordSchema) and isinstance(value, RecordValue):
            valid = value.record == schema.name
            self.named_values(value.fields, schema.fields, path, depth + 1)
        elif isinstance(schema, KeyedSchema) and isinstance(value, KeyedValue):
            valid = True
            self.names(tuple(item.key for item in value.entries), path)
            for entry in value.entries:
                self.value(entry.value, schema.item, path + "." + entry.key, depth + 1)
                fields = {item.name: item.value for item in entry.value.fields}
                if fields.get(schema.key_field) != TextValue(entry.key):
                    self.fail(
                        "record_key",
                        path,
                        "Entry key differs from its record identity.",
                    )
        if not valid:
            self.fail("value_type", path, "Value does not match its declared schema.")

    def named_values(
        self,
        values: tuple[NamedValue, ...],
        fields: tuple[Field, ...],
        path: str,
        depth: int = 0,
    ) -> None:
        self.names(tuple(item.name for item in values), path)
        supplied = {item.name: item.value for item in values}
        if supplied.keys() != {item.name for item in fields}:
            self.fail("record_fields", path, "Fields differ from the declaration.")
        for field in fields:
            if field.name in supplied:
                self.value(
                    supplied[field.name], field.schema, path + "." + field.name, depth
                )

    def source_catalog(self) -> None:
        original_pins: dict[tuple[str, str], str] = {}
        for extraction in self.sources.entries:
            pin = extraction.pin
            path = "sources." + pin.extraction
            self.names((pin.source,), path)
            self.names((pin.revision,), path)
            self.names((pin.extraction,), path)
            for digest in (pin.original_sha256, pin.extraction_sha256):
                if len(digest) != 64 or any(
                    c not in "0123456789abcdef" for c in digest
                ):
                    self.fail(
                        "source_hash", path, "Hashes must be lowercase SHA-256 hex."
                    )
            identity = (pin.source, pin.revision)
            previous = original_pins.get(identity)
            if previous is not None and previous != pin.original_sha256:
                self.fail(
                    "source_revision",
                    path,
                    "One source revision has differing original hashes.",
                )
            original_pins[identity] = pin.original_sha256
            if pin.extraction in self.extractions:
                self.fail("duplicate_identity", path, pin.extraction)
            self.extractions[pin.extraction] = extraction
            try:
                digest = sha256(extraction.text.encode("utf-8")).hexdigest()
            except UnicodeEncodeError:
                self.fail(
                    "extraction_text", path, "Extracted text must encode as UTF-8."
                )
                continue
            if digest != pin.extraction_sha256:
                self.fail(
                    "extraction_hash",
                    path,
                    "Extracted text differs from its pinned hash.",
                )
            self.names(tuple(section.name for section in extraction.sections), path)
            for section in extraction.sections:
                self.names((section.locator,), path)
                if not self.span(section.start, section.end, len(extraction.text)):
                    self.fail("section_span", path, section.name)
                self.sections[(pin.extraction, section.name)] = section

    @staticmethod
    def span(start: int, end: int, length: int) -> bool:
        return type(start) is int and type(end) is int and 0 <= start < end <= length

    def citations(self, citations: tuple[Citation, ...], path: str) -> None:
        if not citations:
            self.fail("missing_citation", path, "Source evidence is required.")
        for citation in citations:
            extraction = self.extractions.get(citation.pin.extraction)
            if extraction is None or extraction.pin != citation.pin:
                self.fail(
                    "citation_identity",
                    path,
                    "Citation does not match an immutable source pin.",
                )
                continue
            section = self.sections.get((citation.pin.extraction, citation.section))
            if section is None or section.locator != citation.locator:
                self.fail(
                    "citation_section",
                    path,
                    "Citation section or locator does not match.",
                )
                continue
            if not self.span(citation.start, citation.end, len(extraction.text)):
                self.fail(
                    "citation_span",
                    path,
                    "Citation requires a nonempty codepoint interval.",
                )
                continue
            if not section.start <= citation.start < citation.end <= section.end:
                self.fail(
                    "citation_section", path, "Citation lies outside its section."
                )
            if extraction.text[citation.start : citation.end] != citation.quote:
                self.fail(
                    "citation_quote",
                    path,
                    "Citation quote differs from the exact text slice.",
                )

    def input(self, value: Input, expected: Schema, path: str) -> None:
        if isinstance(value, Literal):
            self.value(value.value, expected, path)
            return
        if isinstance(value, ProgramInputRef):
            actual = self.inputs.get(value.name)
        elif isinstance(value, ResultRef):
            actual = self.bindings.get((value.node, ""))
        else:
            actual = self.bindings.get((value.owner, value.name))
        if actual is None:
            self.fail(
                "reference_scope",
                path,
                "Reference is absent or outside the current scope.",
            )
            return
        for name in value.path:
            if not isinstance(actual, RecordSchema):
                self.fail(
                    "reference_path",
                    path,
                    "Only record fields support field selection.",
                )
                return
            fields = {field.name: field.schema for field in actual.fields}
            selected = fields.get(name)
            if selected is None:
                self.fail("reference_path", path, name)
                return
            actual = selected
        if actual != expected:
            self.fail(
                "reference_type", path, "Reference type differs from its consumer."
            )

    def export(self, export: Export, path: str) -> None:
        self.schema(export.schema, path)
        self.input(export.value, export.schema, path)

    def bind(self, owner: str, name: str, schema: Schema) -> None:
        key = (owner, name)
        self.bindings[key] = schema
        self.undo.append(key)

    def restore(self, mark: int) -> None:
        while len(self.undo) > mark:
            del self.bindings[self.undo.pop()]

    def branch(self, branch: Branch, expected: Schema, path: str) -> None:
        mark = len(self.undo)
        self.walk(branch.body)
        self.export(branch.result, path)
        if branch.result.schema != expected:
            self.fail(
                "export_type", path, "Branch export differs from the control output."
            )
        self.restore(mark)

    def leaf(self, node: CodeStep | AiStep | HumanStep) -> None:
        metadata = node.metadata
        path = metadata.step_id
        self.names((metadata.behavior_id,), path)
        if not metadata.intent.strip():
            self.fail("missing_intent", path, "A step needs its plain-language intent.")
        self.citations(metadata.citations, path)
        self.names(tuple(item.name for item in metadata.inputs), path)
        for item in metadata.inputs:
            self.schema(item.schema, path + "." + item.name)
            self.input(item.value, item.schema, path + "." + item.name)
        if isinstance(node, CodeStep):
            function = self.functions.get(node.function_id)
            signature = tuple(Field(item.name, item.schema) for item in metadata.inputs)
            if function is None:
                self.fail("unknown_function", path, node.function_id)
            elif function.inputs != signature or function.output != metadata.output:
                self.fail(
                    "function_signature",
                    path,
                    "Function signature differs from the step.",
                )
        elif isinstance(node, AiStep):
            self.names((node.prompt_revision,), path)
        else:
            self.names((node.eligible_role,), path)
            if node.due_at.tzinfo is None or node.due_at.utcoffset() is None:
                self.fail(
                    "human_due_time", path, "A due time must include its timezone."
                )
            self.export(node.request, path + ".request")
        self.bind(path, "", metadata.output)
        for change in metadata.changes:
            self.names((change.change_id,), path)
            self.names((change.operation,), path)
            if change.change_id in self.change_ids:
                self.fail("duplicate_identity", path, change.change_id)
            self.change_ids.add(change.change_id)
            self.export(change.payload, path + ".changes." + change.change_id)

    def walk(self, node: Node) -> None:
        name = node_identity(node)
        output = node_output(node)
        self.schema(output, name)
        if isinstance(node, (CodeStep, AiStep, HumanStep)):
            self.leaf(node)
            return
        mark = len(self.undo)
        if isinstance(node, Sequence):
            for child in node.children:
                self.walk(child)
            self.export(node.result, name)
        elif isinstance(node, Choose):
            self.input(node.condition, Scalar.BOOLEAN, name + ".condition")
            self.branch(node.when_true, output, name + ".true")
            self.branch(node.when_false, output, name + ".false")
        elif isinstance(node, Parallel):
            self.names(tuple(item.name for item in node.branches), name)
            fields = {item.name: item.schema for item in node.output.fields}
            if fields.keys() != {item.name for item in node.branches}:
                self.fail(
                    "parallel_fields", name, "Every output field needs one branch."
                )
            for item in node.branches:
                expected = fields.get(item.name)
                if expected is not None:
                    self.branch(item.branch, expected, name + "." + item.name)
        elif isinstance(node, Each):
            self.schema(node.input_schema, name + ".collection")
            self.input(node.collection, node.input_schema, name + ".collection")
            self.bind(name, "item", node.input_schema.item)
            self.bind(name, "key", Scalar.TEXT)
            self.branch(node.body, node.output.item, name + ".body")
        else:
            self.export(node.initial, name + ".initial")
            if isinstance(node.bound, FiniteRepeat):
                if type(node.bound.limit) is not int or node.bound.limit <= 0:
                    self.fail(
                        "repeat_bound",
                        name,
                        "A finite repeat needs a positive integer bound.",
                    )
            elif not node.bound.event.strip():
                self.fail(
                    "repeat_bound",
                    name,
                    "An event repeat must name its suspension event.",
                )
            self.bind(name, "state", node.initial.schema)
            self.walk(node.body.body)
            self.export(node.body.result, name + ".next")
            if node.body.result.schema != node.initial.schema:
                self.fail(
                    "export_type", name, "Repeat state must keep its declared type."
                )
            self.input(node.until, Scalar.BOOLEAN, name + ".until")
        self.restore(mark)
        self.bind(name, "", output)

    def rules(self) -> None:
        rules = self.draft.rules
        self.names(tuple(rule.rule_id for rule in rules), "rules")
        dimensions: dict[str, Schema] = {}
        targets: dict[str, Schema] = {}
        groups: dict[tuple[str, int], list[tuple[DatedRule, dict[str, Value]]]] = {}
        for rule in rules:
            error_count = len(self.errors)
            path = "rules." + rule.rule_id
            self.names((rule.target,), path)
            self.names(tuple(item.dimension for item in rule.scope), path)
            self.citations(rule.citations, path)
            self.schema(rule.consequence.schema, path)
            if not isinstance(rule.consequence.value, Literal):
                self.fail(
                    "rule_consequence",
                    path,
                    "Rule consequences must be typed literal values.",
                )
            else:
                self.value(rule.consequence.value.value, rule.consequence.schema, path)
            previous_target = targets.get(rule.target)
            if (
                previous_target is not None
                and previous_target != rule.consequence.schema
            ):
                self.fail(
                    "rule_target_type", path, "One rule target must have one type."
                )
            targets[rule.target] = rule.consequence.schema
            scope: dict[str, Value] = {}
            for item in rule.scope:
                self.schema(item.schema, path)
                self.value(item.value, item.schema, path)
                previous = dimensions.get(item.dimension)
                if previous is not None and previous != item.schema:
                    self.fail(
                        "rule_scope_type",
                        path,
                        "One scope dimension must have one type.",
                    )
                dimensions[item.dimension] = item.schema
                scope[item.dimension] = item.value
            if type(rule.effective_from) is not date or (
                rule.effective_until is not None
                and type(rule.effective_until) is not date
            ):
                self.fail("rule_dates", path, "Rule intervals require dates.")
                continue
            if (
                rule.effective_until is not None
                and rule.effective_from >= rule.effective_until
            ):
                self.fail(
                    "rule_dates", path, "Rule intervals must be nonempty and forward."
                )
                continue
            if len(self.errors) != error_count:
                continue
            scope = {key: normalized_value(value) for key, value in scope.items()}
            group = groups.setdefault((rule.target, len(scope)), [])
            for other, other_scope in group:
                overlap = (
                    rule.effective_until is None
                    or other.effective_from < rule.effective_until
                ) and (
                    other.effective_until is None
                    or rule.effective_from < other.effective_until
                )
                compatible = all(
                    scope[key] == other_scope[key]
                    for key in scope.keys() & other_scope.keys()
                )
                assert isinstance(rule.consequence.value, Literal)
                assert isinstance(other.consequence.value, Literal)
                unequal = normalized_value(
                    rule.consequence.value.value
                ) != normalized_value(other.consequence.value.value)
                if overlap and compatible and unequal:
                    self.fail("rule_conflict", path, other.rule_id)
            group.append((rule, scope))

    def verify(self) -> VerificationResult:
        self.index()
        if self.errors:
            return StructuralFailure(tuple(self.errors), None)
        self.source_catalog()
        for schema in self.draft.schemas:
            self.schema(schema, "schemas." + schema.name)
        for item in self.draft.inputs:
            self.schema(item.schema, "inputs." + item.name)
        for function in self.draft.functions:
            path = "functions." + function.function_id
            self.names(tuple(item.name for item in function.inputs), path)
            for item in function.inputs:
                self.schema(item.schema, path + "." + item.name)
            self.schema(function.output, path)
            if (
                not function.body.language_version.strip()
                or not function.body.source.strip()
            ):
                self.fail(
                    "function_body", path, "A function needs versioned source data."
                )
        if self.errors:
            return StructuralFailure(tuple(self.errors), None)
        self.walk(self.draft.root)
        self.rules()
        self.names(
            tuple(item.scenario_id for item in self.draft.scenarios), "scenarios"
        )
        for scenario in self.draft.scenarios:
            path = "scenarios." + scenario.scenario_id
            self.citations(scenario.citations, path)
            self.named_values(scenario.inputs, self.draft.inputs, path)
            self.value(
                scenario.expected, node_output(self.draft.root), path + ".expected"
            )
        if self.errors:
            return StructuralFailure(tuple(self.errors), None)
        from dex.core.language import LanguageFailure, check_functions

        checked = check_functions(self.draft.functions, self.draft.schemas, self.limits)
        if isinstance(checked, LanguageFailure):
            return StructuralFailure(
                (Diagnostic(checked.code, checked.path, checked.message),), checked
            )
        return ExecutionPending(
            StructuralArtifact(self.draft, self.sources, checked),
            tuple(check for check in MissingCheck if check != MissingCheck.LANGUAGE),
        )


def verify_program(
    draft: ProgramDraft, sources: SourceCatalog, limits: "Limits"
) -> VerificationResult:
    return _Verifier(draft, sources, limits).verify()

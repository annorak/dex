from datetime import date
from typing import cast

from dex.core import program as p
from dex.eval.scenario_format import Json


def encode_core(value: object) -> Json:
    if isinstance(value, p.Scalar):
        return {"kind": value.value}
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, tuple):
        return [encode_core(item) for item in cast(tuple[object, ...], value)]
    if isinstance(value, list):
        return [encode_core(item) for item in cast(list[object], value)]
    if isinstance(value, dict):
        return {
            name: encode_core(item)
            for name, item in cast(dict[str, object], value).items()
        }
    fields: dict[str, object]
    if isinstance(value, p.BoolValue):
        fields = {"kind": "boolean", "value": value.value}
    elif isinstance(value, p.IntValue):
        fields = {"kind": "integer", "value": value.value}
    elif isinstance(value, p.TextValue):
        fields = {"kind": "text", "value": value.value}
    elif isinstance(value, p.DateValue):
        fields = {"kind": "date", "value": value.value}
    elif isinstance(value, p.MoneyValue):
        fields = {"kind": "money_cents", "cents": value.cents}
    elif isinstance(value, p.AbsentValue):
        fields = {"kind": "absent"}
    elif isinstance(value, p.PresentValue):
        fields = {"kind": "present", "value": value.value}
    elif isinstance(value, p.TaggedValue):
        fields = {"kind": "tagged", "tag": value.tag, "value": value.value}
    elif isinstance(value, p.RecordValue):
        fields = {"kind": "record", "record": value.record, "fields": value.fields}
    elif isinstance(value, p.KeyedValue):
        fields = {"kind": "keyed", "entries": value.entries}
    elif isinstance(value, p.ResolvedRefValue):
        fields = {
            "kind": "resolved_ref",
            "record": value.record,
            "key_field": value.key_field,
            "key": value.key,
        }
    elif isinstance(value, p.UnresolvedTextValue):
        fields = {"kind": "unresolved_text", "text": value.text}
    elif isinstance(value, p.OptionalSchema):
        fields = {"kind": "optional", "item": value.item}
    elif isinstance(value, p.TaggedSchema):
        fields = {"kind": "tagged", "variants": value.variants}
    elif isinstance(value, p.RecordSchema):
        fields = {"kind": "record", "name": value.name, "fields": value.fields}
    elif isinstance(value, p.KeyedSchema):
        fields = {"kind": "keyed", "item": value.item, "key_field": value.key_field}
    elif isinstance(value, p.ReferenceSchema):
        fields = {
            "kind": "reference",
            "record": value.record,
            "key_field": value.key_field,
        }
    elif isinstance(value, p.UnresolvedSchema):
        fields = {"kind": "unresolved"}
    elif isinstance(value, p.Literal):
        fields = {"kind": "literal", "value": value.value}
    elif isinstance(value, p.ProgramInputRef):
        fields = {"kind": "program_input", "name": value.name, "path": value.path}
    elif isinstance(value, p.ResultRef):
        fields = {"kind": "result", "node": value.node, "path": value.path}
    elif isinstance(value, p.LocalRef):
        fields = {
            "kind": "local",
            "owner": value.owner,
            "name": value.name,
            "path": value.path,
        }
    elif isinstance(value, p.CodeStep):
        fields = {
            "kind": "code",
            "metadata": value.metadata,
            "function_id": value.function_id,
        }
    elif isinstance(value, p.AiStep):
        fields = {
            "kind": "ai",
            "metadata": value.metadata,
            "prompt_revision": value.prompt_revision,
        }
    elif isinstance(value, p.HumanStep):
        fields = {
            "kind": "human",
            "metadata": value.metadata,
            "eligible_role": value.eligible_role,
            "due_at": value.due_at,
            "request": value.request,
            "never_automate": value.never_automate,
        }
    elif isinstance(value, p.Sequence):
        fields = {
            "kind": "sequence",
            "node_id": value.node_id,
            "children": value.children,
            "result": value.result,
        }
    elif isinstance(value, p.Choose):
        fields = {
            "kind": "choose",
            "node_id": value.node_id,
            "condition": value.condition,
            "when_true": value.when_true,
            "when_false": value.when_false,
            "output": value.output,
        }
    elif isinstance(value, p.Each):
        fields = {
            "kind": "each",
            "node_id": value.node_id,
            "collection": value.collection,
            "output": value.output,
            "input_schema": value.input_schema,
            "body": value.body,
        }
    elif isinstance(value, p.Parallel):
        fields = {
            "kind": "parallel",
            "node_id": value.node_id,
            "branches": value.branches,
            "output": value.output,
        }
    elif isinstance(value, p.Repeat):
        fields = {
            "kind": "repeat",
            "node_id": value.node_id,
            "initial": value.initial,
            "body": value.body,
            "until": value.until,
            "bound": value.bound,
        }
    elif isinstance(value, p.FiniteRepeat):
        fields = {"kind": "finite", "limit": value.limit}
    elif isinstance(value, p.EventRepeat):
        fields = {"kind": "event", "event": value.event}
    elif isinstance(value, p.Field):
        fields = {"name": value.name, "schema": value.schema}
    elif isinstance(value, p.NamedValue):
        fields = {"name": value.name, "value": value.value}
    elif isinstance(value, p.KeyedEntry):
        fields = {"key": value.key, "value": value.value}
    elif isinstance(value, p.Binding):
        fields = {"name": value.name, "schema": value.schema, "value": value.value}
    elif isinstance(value, p.Export):
        fields = {"schema": value.schema, "value": value.value}
    elif isinstance(value, p.SourcePin):
        fields = {
            "source": value.source,
            "revision": value.revision,
            "original_sha256": "sha256:" + value.original_sha256,
            "extraction": value.extraction,
            "extraction_sha256": "sha256:" + value.extraction_sha256,
        }
    elif isinstance(value, p.Section):
        fields = {
            "name": value.name,
            "locator": value.locator,
            "start": value.start,
            "end": value.end,
        }
    elif isinstance(value, p.SourceExtraction):
        fields = {"pin": value.pin, "text": value.text, "sections": value.sections}
    elif isinstance(value, p.SourceCatalog):
        fields = {"entries": value.entries}
    elif isinstance(value, p.Citation):
        fields = {
            "pin": value.pin,
            "section": value.section,
            "locator": value.locator,
            "start": value.start,
            "end": value.end,
            "quote": value.quote,
        }
    elif isinstance(value, p.ChangeDeclaration):
        fields = {
            "change_id": value.change_id,
            "operation": value.operation,
            "payload": value.payload,
        }
    elif isinstance(value, p.StepMetadata):
        fields = {
            "step_id": value.step_id,
            "behavior_id": value.behavior_id,
            "intent": value.intent,
            "citations": value.citations,
            "inputs": value.inputs,
            "output": value.output,
            "changes": value.changes,
        }
    elif isinstance(value, p.FunctionBody):
        fields = {"language_version": value.language_version, "source": value.source}
    elif isinstance(value, p.FunctionDeclaration):
        fields = {
            "function_id": value.function_id,
            "inputs": value.inputs,
            "output": value.output,
            "body": value.body,
        }
    elif isinstance(value, p.Branch):
        fields = {"body": value.body, "result": value.result}
    elif isinstance(value, p.NamedBranch):
        fields = {"name": value.name, "branch": value.branch}
    elif isinstance(value, p.Constraint):
        fields = {
            "dimension": value.dimension,
            "schema": value.schema,
            "value": value.value,
        }
    elif isinstance(value, p.DatedRule):
        fields = {
            "rule_id": value.rule_id,
            "target": value.target,
            "scope": value.scope,
            "effective_from": value.effective_from,
            "effective_until": value.effective_until,
            "consequence": value.consequence,
            "citations": value.citations,
        }
    elif isinstance(value, p.ProgramScenario):
        fields = {
            "scenario_id": value.scenario_id,
            "inputs": value.inputs,
            "expected": value.expected,
            "citations": value.citations,
        }
    elif isinstance(value, p.ProgramDraft):
        fields = {
            "program_id": value.program_id,
            "revision": value.revision,
            "schemas": value.schemas,
            "inputs": value.inputs,
            "root": value.root,
            "functions": value.functions,
            "rules": value.rules,
            "scenarios": value.scenarios,
        }
    elif isinstance(value, p.StructuralArtifact):
        fields = {
            "draft": value.draft,
            "sources": value.sources,
            "verifier_version": value.verifier_version,
        }
    elif isinstance(value, p.Diagnostic):
        fields = {"code": value.code, "path": value.path, "message": value.message}
    else:
        raise TypeError("Unsupported core output type: " + type(value).__name__)
    return {name: encode_core(item) for name, item in fields.items()}

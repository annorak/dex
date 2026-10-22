from collections.abc import Iterator, Mapping, MutableMapping
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from hashlib import sha256
from types import MappingProxyType

from dex.core import authority as a
from dex.core import events as e
from dex.core import language as lang
from dex.core import program as p

MAX_DISPATCHES = 3


class ReplayError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        self.args = (code,)


class _Failure(Exception):
    def __init__(self, code: str) -> None:
        self.code = code


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise ReplayError(code)


def artifact_pin(artifact: p.StructuralArtifact) -> e.ArtifactPin:
    return e.ArtifactPin(
        artifact.draft.program_id,
        artifact.draft.revision,
        sha256(("dex-artifact-repr-1\n" + repr(artifact)).encode("utf-8")).hexdigest(),
    )


def _children(node: p.Node) -> tuple[p.Node, ...]:
    if isinstance(node, p.Sequence):
        return node.children
    if isinstance(node, p.Choose):
        return (node.when_true.body, node.when_false.body)
    if isinstance(node, p.Parallel):
        return tuple(item.branch.body for item in node.branches)
    if isinstance(node, (p.Each, p.Repeat)):
        return (node.body.body,)
    return ()


@dataclass(frozen=True)
class ArtifactEntry:
    pin: e.ArtifactPin
    artifact: p.StructuralArtifact


class ProgramCatalog:
    def __init__(self, entries: tuple[ArtifactEntry, ...]) -> None:
        artifacts: dict[e.ArtifactPin, p.StructuralArtifact] = {}
        indexes: dict[e.ArtifactPin, Mapping[str, p.Node]] = {}
        revisions: dict[tuple[str, str], e.ArtifactPin] = {}
        for entry in entries:
            _require(entry.pin == artifact_pin(entry.artifact), "artifact_identity")
            _require(
                entry.artifact.verifier_version == "structure-language-1",
                "artifact_version",
            )
            identity = (entry.pin.program_id, entry.pin.revision)
            _require(
                identity not in revisions or revisions[identity] == entry.pin,
                "artifact_conflict",
            )
            revisions[identity] = entry.pin
            nodes: dict[str, p.Node] = {}
            stack = [entry.artifact.draft.root]
            while stack:
                node = stack.pop()
                name = p.node_identity(node)
                _require(name not in nodes, "duplicate_node")
                nodes[name] = node
                stack.extend(_children(node))
            artifacts[entry.pin] = entry.artifact
            indexes[entry.pin] = MappingProxyType(nodes)
        self._entries = entries
        self._artifacts = MappingProxyType(artifacts)
        self._nodes = MappingProxyType(indexes)
        self.behavior_signatures = MappingProxyType(
            {
                (pin, name): a.behavior_signature(artifacts[pin], node)
                for pin, nodes in indexes.items()
                for name, node in nodes.items()
                if isinstance(node, (p.CodeStep, p.AiStep, p.HumanStep))
            }
        )

    @property
    def entries(self) -> tuple[ArtifactEntry, ...]:
        return self._entries

    @property
    def artifacts(self) -> Mapping[e.ArtifactPin, p.StructuralArtifact]:
        return self._artifacts

    @property
    def nodes(self) -> Mapping[e.ArtifactPin, Mapping[str, p.Node]]:
        return self._nodes


@dataclass(frozen=True)
class Work:
    opened: e.WorkOpened
    selected: e.ControlSelected | None = None
    completed: e.WorkSucceeded | None = None
    waiting: e.RepeatWaiting | None = None
    inputs: tuple[e.ConsumedInput, ...] = ()
    task: e.TaskRef | None = None
    request: e.RecordingRequest | None = None


@dataclass(frozen=True)
class Case:
    start: e.StartSandbox
    status: str
    failure: str | None = None


@dataclass(frozen=True)
class WorkspaceState:
    revision: int
    cases: MappingProxyType[str, Case]
    work: MappingProxyType[e.WorkAddress, Work]
    commands: MappingProxyType[str, e.RuntimeCommand]
    tasks: MappingProxyType[e.TaskRef, e.Task] = field(
        default_factory=lambda: MappingProxyType({})
    )
    actions: MappingProxyType[tuple[str, str, str], e.ActionCommand] = field(
        default_factory=lambda: MappingProxyType({})
    )
    recordings: MappingProxyType[e.WorkRevision, e.Recording] = field(
        default_factory=lambda: MappingProxyType({})
    )
    history: MappingProxyType[e.WorkRevision, Work] = field(
        default_factory=lambda: MappingProxyType({})
    )
    consumers: MappingProxyType[e.WorkRevision, frozenset[e.WorkAddress]] = field(
        default_factory=lambda: MappingProxyType({})
    )
    pending: MappingProxyType[e.WorkAddress, frozenset[e.WorkAddress]] = field(
        default_factory=lambda: MappingProxyType({})
    )

    effects: MappingProxyType[a.EffectRef, a.Effect] = field(
        default_factory=lambda: MappingProxyType({})
    )
    current_effects: MappingProxyType[a.EffectKey, a.EffectRef] = field(
        default_factory=lambda: MappingProxyType({})
    )
    work_effects: MappingProxyType[tuple[e.WorkRevision, str], a.EffectRef] = field(
        default_factory=lambda: MappingProxyType({})
    )
    operation_keys: MappingProxyType[tuple[e.WorkAddress, str], a.EffectKey] = field(
        default_factory=lambda: MappingProxyType({})
    )
    effect_consumers: MappingProxyType[e.WorkRevision, frozenset[a.EffectRef]] = field(
        default_factory=lambda: MappingProxyType({})
    )
    work_actions: MappingProxyType[e.WorkRevision, a.ActionKey] = field(
        default_factory=lambda: MappingProxyType({})
    )
    unresolved_attempts: MappingProxyType[a.EffectKey, a.EffectRef] = field(
        default_factory=lambda: MappingProxyType({})
    )
    confirmed_effects: MappingProxyType[a.EffectKey, a.EffectRef] = field(
        default_factory=lambda: MappingProxyType({})
    )
    attempt_ids: MappingProxyType[tuple[a.EffectKey, str], a.EffectRef] = field(
        default_factory=lambda: MappingProxyType({})
    )
    revoked_approvals: frozenset[a.ActionKey] = field(
        default_factory=lambda: frozenset[a.ActionKey]()
    )

    workspace_commands: MappingProxyType[str, e.WorkspaceCommand] = field(
        default_factory=lambda: MappingProxyType({})
    )
    registrations: MappingProxyType[e.ArtifactPin, e.RegisterProgram] = field(
        default_factory=lambda: MappingProxyType({})
    )
    program_approvals: MappingProxyType[e.ArtifactPin, e.ApproveProgram] = field(
        default_factory=lambda: MappingProxyType({})
    )
    reservations: MappingProxyType[tuple[a.EffectKey, str], e.ReserveDispatch] = field(
        default_factory=lambda: MappingProxyType({})
    )
    dispatch_counts: MappingProxyType[a.EffectKey, int] = field(
        default_factory=lambda: MappingProxyType({})
    )
    trust: MappingProxyType[a.BehaviorKey, a.TrustCount] = field(
        default_factory=lambda: MappingProxyType({})
    )
    reviews: MappingProxyType[a.ReviewKey, a.ReviewEvidence] = field(
        default_factory=lambda: MappingProxyType({})
    )
    behavior_work: MappingProxyType[a.ReviewKey, frozenset[e.WorkAddress]] = field(
        default_factory=lambda: MappingProxyType({})
    )
    case_reviews: MappingProxyType[str, frozenset[a.ReviewKey]] = field(
        default_factory=lambda: MappingProxyType({})
    )
    pending_reviews: MappingProxyType[a.EffectRef, frozenset[a.ReviewKey]] = field(
        default_factory=lambda: MappingProxyType({})
    )
    grants: MappingProxyType[str, a.StandingGrant] = field(
        default_factory=lambda: MappingProxyType({})
    )
    revoked_grants: MappingProxyType[str, e.HumanAction] = field(
        default_factory=lambda: MappingProxyType({})
    )
    trust_actions: MappingProxyType[a.ActionKey, e.TrustCommand] = field(
        default_factory=lambda: MappingProxyType({})
    )
    case_effects: MappingProxyType[str, tuple[a.EffectRef, ...]] = field(
        default_factory=lambda: MappingProxyType({})
    )
    case_samples: MappingProxyType[str, a.CaseSample] = field(
        default_factory=lambda: MappingProxyType({})
    )
    sampling_ordinals: MappingProxyType[str, int] = field(
        default_factory=lambda: MappingProxyType({})
    )


@dataclass(frozen=True)
class Accepted:
    events: tuple[e.RuntimeEvent, ...]
    state: WorkspaceState


@dataclass(frozen=True)
class Refused:
    code: str


class _Meter:
    def __init__(self, bounds: e.ActivationBounds) -> None:
        self.bounds = bounds
        self.work = 0
        self.allocations = 0
        self.instances = 0

    def charge(self, work: int = 1, allocations: int = 0) -> None:
        if self.work + work > self.bounds.work:
            raise _Failure("work_limit")
        if self.allocations + allocations > self.bounds.allocations:
            raise _Failure("allocation_limit")
        self.work += work
        self.allocations += allocations

    def value(self, value: p.Value, depth: int = 0) -> None:
        self.charge(1, 1)
        if depth > lang.DEFAULT_LIMITS.nesting:
            raise _Failure("nesting_limit")
        if isinstance(value, (p.IntValue, p.MoneyValue)):
            number = value.value if isinstance(value, p.IntValue) else value.cents
            if abs(number) > lang.DEFAULT_LIMITS.integer_magnitude:
                raise _Failure("integer_limit")
        if isinstance(value, (p.TextValue, p.UnresolvedTextValue)):
            text = value.value if isinstance(value, p.TextValue) else value.text
            self.charge(len(text), len(text) * 4)
            if len(text.encode("utf-8")) > lang.DEFAULT_LIMITS.string_bytes:
                raise _Failure("string_limit")
        elif isinstance(value, p.ResolvedRefValue):
            self.value(p.TextValue(value.key), depth + 1)
        elif isinstance(value, (p.PresentValue, p.TaggedValue)):
            self.value(value.value, depth + 1)
        elif isinstance(value, p.RecordValue):
            for item in value.fields:
                self.value(item.value, depth + 1)
        elif isinstance(value, p.KeyedValue):
            if len(value.entries) > lang.DEFAULT_LIMITS.collection_count:
                raise _Failure("collection_limit")
            for entry in value.entries:
                self.value(p.TextValue(entry.key), depth + 1)
                self.value(entry.value, depth + 1)

    def usage(self) -> lang.Usage:
        return lang.Usage(self.work, self.allocations)


def _valid(value: p.Value, schema: p.Schema) -> bool:
    if isinstance(schema, p.Scalar):
        return (
            (
                schema == p.Scalar.BOOLEAN
                and isinstance(value, p.BoolValue)
                and type(value.value) is bool
            )
            or (
                schema == p.Scalar.INTEGER
                and isinstance(value, p.IntValue)
                and type(value.value) is int
            )
            or (
                schema == p.Scalar.MONEY
                and isinstance(value, p.MoneyValue)
                and type(value.cents) is int
            )
            or (schema == p.Scalar.TEXT and isinstance(value, p.TextValue))
            or (
                schema == p.Scalar.DATE
                and isinstance(value, p.DateValue)
                and type(value.value) is date
            )
        )
    if isinstance(schema, p.RecordSchema):
        if not isinstance(value, p.RecordValue) or value.record != schema.name:
            return False
        fields = {item.name: item.value for item in value.fields}
        return len(fields) == len(value.fields) == len(schema.fields) and all(
            item.name in fields and _valid(fields[item.name], item.schema)
            for item in schema.fields
        )
    if isinstance(schema, p.KeyedSchema):
        if not isinstance(value, p.KeyedValue):
            return False
        keys = {item.key for item in value.entries}
        return len(keys) == len(value.entries) and all(
            _valid(item.value, schema.item)
            and dict((v.name, v.value) for v in item.value.fields).get(schema.key_field)
            == p.TextValue(item.key)
            for item in value.entries
        )
    if isinstance(schema, p.OptionalSchema):
        return (
            isinstance(value, p.AbsentValue)
            or isinstance(value, p.PresentValue)
            and _valid(value.value, schema.item)
        )
    if isinstance(schema, p.TaggedSchema):
        return isinstance(value, p.TaggedValue) and any(
            item.name == value.tag and _valid(value.value, item.schema)
            for item in schema.variants
        )
    if isinstance(schema, p.ReferenceSchema):
        return (
            isinstance(value, p.ResolvedRefValue)
            and bool(value.key)
            and (value.record, value.key_field) == (schema.record, schema.key_field)
        )
    return isinstance(value, p.UnresolvedTextValue)


def _winning_rules(
    rules: tuple[p.DatedRule, ...],
    target: str,
    business_date: date,
    scope: Mapping[str, p.Value],
) -> tuple[p.DatedRule, ...]:
    candidates = tuple(
        rule
        for rule in rules
        if rule.target == target
        and rule.effective_from <= business_date
        and (rule.effective_until is None or business_date < rule.effective_until)
        and all(
            scope.get(item.dimension) == p.normalized_value(item.value)
            for item in rule.scope
        )
    )
    if not candidates:
        return ()
    specificity = max(len(rule.scope) for rule in candidates)
    return tuple(
        sorted(
            (rule for rule in candidates if len(rule.scope) == specificity),
            key=lambda rule: rule.rule_id,
        )
    )


def _path(value: p.Value, path: tuple[str, ...]) -> p.Value:
    for name in path:
        _require(isinstance(value, p.RecordValue), "reference_path")
        assert isinstance(value, p.RecordValue)
        fields = {item.name: item.value for item in value.fields}
        _require(name in fields, "reference_path")
        value = fields[name]
    return value


def _address(
    parent: e.WorkAddress, node: p.Node, kind: str = "", key: str = ""
) -> e.WorkAddress:
    scope = parent.scope
    if kind:
        scope += (e.ScopePart(parent.node_id, kind, key),)
    return e.WorkAddress(parent.case_id, p.node_identity(node), scope)


def _with_result(context: e.Context, address: e.WorkAddress) -> e.Context:
    return replace(
        context, results=context.results + (e.ResultBinding(address.node_id, address),)
    )


def _dependencies(
    node: p.Node, address: e.WorkAddress, selection: p.Value
) -> tuple[e.WorkAddress, ...]:
    if isinstance(node, p.Sequence):
        _require(selection == p.AbsentValue(), "control_selection")
        return tuple(_address(address, child) for child in node.children)
    if isinstance(node, p.Choose):
        _require(isinstance(selection, p.BoolValue), "control_selection")
        assert isinstance(selection, p.BoolValue)
        branch = node.when_true if selection.value else node.when_false
        return (_address(address, branch.body, "choose", str(selection.value)),)
    if isinstance(node, p.Each):
        _require(_valid(selection, node.input_schema), "control_selection")
        assert isinstance(selection, p.KeyedValue)
        return tuple(
            _address(address, node.body.body, "each", item.key)
            for item in selection.entries
        )
    if isinstance(node, p.Parallel):
        _require(selection == p.AbsentValue(), "control_selection")
        return tuple(
            _address(address, item.branch.body, "parallel", item.name)
            for item in sorted(node.branches, key=lambda item: item.name)
        )
    _require(
        isinstance(node, p.Repeat) and isinstance(selection, p.IntValue),
        "control_selection",
    )
    assert isinstance(node, p.Repeat) and isinstance(selection, p.IntValue)
    _require(selection.value >= 0, "repeat_iteration")
    if isinstance(node.bound, p.FiniteRepeat):
        _require(selection.value < node.bound.limit, "repeat_iteration")
    return (_address(address, node.body.body, "repeat", str(selection.value)),)


def command_address(
    command: e.SignalRepeat | e.HumanCommand | e.SupplyRecording,
) -> e.WorkAddress:
    if isinstance(command, e.SignalRepeat):
        return command.address
    if isinstance(command, e.SupplyRecording):
        return command.recording.request.work.address
    if isinstance(command, e.CorrectResult):
        return command.work.address
    return command.task.work.address


def command_case(command: e.RuntimeCommand) -> str:
    if isinstance(
        command,
        (
            e.ApproveEffect,
            e.RevokeEffectApproval,
            e.AmendEffect,
            e.BeginEffectAttempt,
            e.MarkEffectUncertain,
            e.ConfirmEffect,
            e.ReconcileEffect,
        ),
    ):
        return command.effect.key.case_id
    return (
        command.case_id
        if isinstance(command, e.StartSandbox)
        else command_address(command).case_id
    )


def action_key(action: e.HumanAction) -> tuple[str, str, str]:
    return action.company_id, action.origin, action.action_id


def same_action(left: e.ActionCommand, right: e.ActionCommand) -> bool:
    return replace(left, meta=right.meta, bounds=right.bounds) == right


def records_resolve(value: p.Value, company: e.CompanyContext) -> bool:
    if isinstance(value, p.ResolvedRefValue):
        return value in company.records
    if isinstance(value, p.UnresolvedTextValue):
        return False
    if isinstance(value, (p.PresentValue, p.TaggedValue)):
        return records_resolve(value.value, company)
    if isinstance(value, p.RecordValue):
        return all(records_resolve(item.value, company) for item in value.fields)
    if isinstance(value, p.KeyedValue):
        return all(records_resolve(item.value, company) for item in value.entries)
    return True


def recording_outcome(recording: e.Recording, company: e.CompanyContext) -> p.Value:
    value = recording.value
    failure = recording.failure
    if value is not None:
        if not _valid(value, recording.request.schema):
            failure = "recording_schema"
        elif not records_resolve(value, company):
            failure = "unresolved_identity"
    valid = failure is None and value is not None
    return p.RecordValue(
        "AiOutcome",
        (
            p.NamedValue("valid", p.BoolValue(valid)),
            p.NamedValue(
                "value",
                p.PresentValue(p.normalized_value(value))
                if valid and value is not None
                else p.AbsentValue(),
            ),
            p.NamedValue(
                "failure",
                p.PresentValue(p.TextValue(failure))
                if failure is not None
                else p.AbsentValue(),
            ),
        ),
    )


class _StateMap[K, V](MutableMapping[K, V]):
    def __init__(self, source: MappingProxyType[K, V]) -> None:
        self._data: MappingProxyType[K, V] | dict[K, V] = source

    def __getitem__(self, key: K) -> V:
        return self._data[key]

    def __iter__(self) -> Iterator[K]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def writable(self) -> dict[K, V]:
        if isinstance(self._data, MappingProxyType):
            self._data = self._data.copy()
        return self._data

    def __setitem__(self, key: K, value: V) -> None:
        self.writable()[key] = value

    def __delitem__(self, key: K) -> None:
        del self.writable()[key]

    def freeze(self) -> MappingProxyType[K, V]:
        if isinstance(self._data, dict):
            self._data = MappingProxyType(self._data)
        return self._data


class _Reducer:
    def __init__(self, state: WorkspaceState, catalog: ProgramCatalog) -> None:
        self.revision = state.revision
        self.cases = _StateMap(state.cases)
        self.work = _StateMap(state.work)
        self.commands = _StateMap(state.commands)
        self.tasks = _StateMap(state.tasks)
        self.actions = _StateMap(state.actions)
        self.recordings = _StateMap(state.recordings)
        self.history = _StateMap(state.history)
        self.consumers = _StateMap(state.consumers)
        self.pending = {
            address: set(children) for address, children in state.pending.items()
        }
        self.effects = _StateMap(state.effects)
        self.current_effects = _StateMap(state.current_effects)
        self.work_effects = _StateMap(state.work_effects)
        self.operation_keys = _StateMap(state.operation_keys)
        self.effect_consumers = _StateMap(state.effect_consumers)
        self.work_actions = _StateMap(state.work_actions)
        self.unresolved_attempts = _StateMap(state.unresolved_attempts)
        self.confirmed_effects = _StateMap(state.confirmed_effects)
        self.attempt_ids = _StateMap(state.attempt_ids)
        self.revoked_approvals = state.revoked_approvals
        self.workspace_commands = _StateMap(state.workspace_commands)
        self.registrations = _StateMap(state.registrations)
        self.program_approvals = _StateMap(state.program_approvals)
        self.reservations = _StateMap(state.reservations)
        self.dispatch_counts = _StateMap(state.dispatch_counts)
        self.trust = _StateMap(state.trust)
        self.reviews = _StateMap(state.reviews)
        self.behavior_work = _StateMap(state.behavior_work)
        self.case_reviews = _StateMap(state.case_reviews)
        self.pending_reviews = _StateMap(state.pending_reviews)
        self.grants = _StateMap(state.grants)
        self.revoked_grants = _StateMap(state.revoked_grants)
        self.trust_actions = _StateMap(state.trust_actions)
        self.case_effects = _StateMap(state.case_effects)
        self.case_samples = _StateMap(state.case_samples)
        self.sampling_ordinals = _StateMap(state.sampling_ordinals)
        self.required_proposals: set[tuple[e.WorkRevision, str]] = set()
        self.refresh_effects: set[e.WorkAddress] = set()
        self.input_indexes: dict[
            e.WorkAddress, dict[tuple[str, ...], e.ConsumedInput]
        ] = {}
        self.selection_positions: dict[e.WorkAddress, dict[e.WorkAddress, int]] = {}
        self.branch_indexes: dict[e.WorkAddress, dict[str, e.WorkAddress]] = {}
        self.entry_indexes: dict[e.WorkAddress, dict[str, p.RecordValue]] = {}
        self.business_decisions: dict[e.WorkRevision, tuple[e.WorkRevision, ...]] = {}
        self.catalog = catalog
        self.command: e.RuntimeCommand | None = None
        self.ordinal = 0
        self.settled = False
        self.action_applied = False
        self.instances = 0
        self.usage = lang.Usage(0, 0)

    def freeze(self) -> WorkspaceState:
        _require(self.command is None, "incomplete_batch")
        return WorkspaceState(
            self.revision,
            self.cases.freeze(),
            self.work.freeze(),
            self.commands.freeze(),
            self.tasks.freeze(),
            self.actions.freeze(),
            self.recordings.freeze(),
            self.history.freeze(),
            self.consumers.freeze(),
            MappingProxyType(
                {
                    address: frozenset(children)
                    for address, children in self.pending.items()
                }
            ),
            self.effects.freeze(),
            self.current_effects.freeze(),
            self.work_effects.freeze(),
            self.operation_keys.freeze(),
            self.effect_consumers.freeze(),
            self.work_actions.freeze(),
            self.unresolved_attempts.freeze(),
            self.confirmed_effects.freeze(),
            self.attempt_ids.freeze(),
            self.revoked_approvals,
            self.workspace_commands.freeze(),
            self.registrations.freeze(),
            self.program_approvals.freeze(),
            self.reservations.freeze(),
            self.dispatch_counts.freeze(),
            self.trust.freeze(),
            self.reviews.freeze(),
            self.behavior_work.freeze(),
            self.case_reviews.freeze(),
            self.pending_reviews.freeze(),
            self.grants.freeze(),
            self.revoked_grants.freeze(),
            self.trust_actions.freeze(),
            self.case_effects.freeze(),
            self.case_samples.freeze(),
            self.sampling_ordinals.freeze(),
        )

    def node(self, address: e.WorkAddress) -> p.Node:
        _require(address.case_id in self.cases, "unknown_case")
        nodes = self.catalog.nodes[self.cases[address.case_id].start.artifact]
        _require(address.node_id in nodes, "unknown_node")
        return nodes[address.node_id]

    def apply(self, event: e.RuntimeEvent) -> None:
        _require(event.format_version == 1, "event_version")
        payload = event.payload
        if isinstance(payload, e.WorkspaceTransitioned):
            _require(self.command is None and event.ordinal == 0, "batch_order")
            _require(
                event.command_id == payload.command.meta.command_id, "command_identity"
            )
            self.workspace_transition(payload.command)
            self.revision += 1
            return
        if isinstance(payload, e.BatchStarted):
            _require(self.command is None and event.ordinal == 0, "batch_order")
            command = payload.command
            _require(event.command_id == command.meta.command_id, "command_identity")
            _require(command.meta.command_id not in self.commands, "duplicate_command")
            _require(command.meta.expected_revision == self.revision, "stale_revision")
            self.usage = lang.Usage(0, 0)
            self.start(command)
            self.command = command
            self.ordinal = 0
            self.settled = False
            self.action_applied = isinstance(command, (e.StartSandbox, e.SignalRepeat))
            self.required_proposals.clear()
            self.refresh_effects.clear()
            self.instances = 0
        else:
            _require(self.command is not None, "missing_batch")
            assert self.command is not None
            _require(
                event.command_id == self.command.meta.command_id
                and event.ordinal == self.ordinal,
                "event_order",
            )
            _require(event.ordinal < self.command.bounds.events, "event_limit")
            if isinstance(payload, e.BatchCompleted):
                _require(
                    self.settled
                    and self.action_applied
                    and payload.count == self.ordinal + 1,
                    "incomplete_batch",
                )
                self.select_sample(
                    command_case(self.command), self.command.meta.observed_at
                )
                self.commands[event.command_id] = self.command
                self.command = None
            else:
                _require(not self.settled, "settled_batch")
                self.transition(payload)
        self.ordinal += 1
        self.revision += 1

    def workspace_transition(self, command: e.WorkspaceCommand) -> None:
        meta = command.meta
        _require(meta.expected_revision == self.revision, "stale_revision")
        _require(
            bool(meta.command_id.strip()) and bool(meta.actor.strip()),
            "command_identity",
        )
        _require(
            meta.command_id not in self.workspace_commands
            and meta.command_id not in self.commands,
            "duplicate_command",
        )
        _require(
            meta.occurred_at.utcoffset() is not None
            and meta.observed_at.utcoffset() is not None,
            "command_time",
        )
        if isinstance(
            command, (e.ReviewResults, e.GrantStandingAuthority, e.RevokeStandingGrant)
        ):
            self.transition_trust(command)
        elif isinstance(command, e.ReserveDispatch):
            effect = self.effects.get(command.effect)
            _require(effect is not None, "unknown_effect")
            assert effect is not None
            self.dispatch_permission(command.effect, command.attempt_id, meta)
            key = command.effect.key, command.attempt_id
            _require(key not in self.reservations, "dispatch_reserved")
            count = self.dispatch_counts.get(command.effect.key, 0)
            _require(count < MAX_DISPATCHES, "retry_exhausted")
            _require(bool(command.adapter_revision.strip()), "adapter_revision")
            self.reservations[key] = command
            self.dispatch_counts[command.effect.key] = count + 1
        else:
            _require(command.artifact in self.catalog.artifacts, "missing_artifact")
            role = (
                "program_registrar"
                if isinstance(command, e.RegisterProgram)
                else "program_approver"
            )
            _require(
                a.has_role(command.company, meta.actor, role, (), meta.observed_at),
                "program_authority",
            )
            if isinstance(command, e.RegisterProgram):
                _require(
                    command.artifact not in self.registrations, "program_registered"
                )
                _require(
                    len(set(command.missing_checks)) == len(command.missing_checks),
                    "verification_checks",
                )
                self.registrations[command.artifact] = command
            else:
                registration = self.registrations.get(command.artifact)
                _require(registration is not None, "program_unregistered")
                assert registration is not None
                _require(
                    registration.company.company_id == command.company.company_id,
                    "company_mismatch",
                )
                _require(not registration.missing_checks, "verification_incomplete")
                self.program_approvals[command.artifact] = command
        self.workspace_commands[meta.command_id] = command

    def dispatch_permission(
        self, ref: a.EffectRef, attempt_id: str, meta: e.CommandMeta
    ) -> None:
        self.effect_observer(e.BeginEffectAttempt(meta, ref, attempt_id))
        effect = self.effects[ref]
        self.check_effect_current(effect.revision)
        progress = effect.progress
        _require(
            isinstance(progress, (a.Attempted, a.Uncertain)), "effect_attempt_state"
        )
        assert isinstance(progress, (a.Attempted, a.Uncertain))
        attempt = progress if isinstance(progress, a.Attempted) else progress.attempt
        _require(attempt.attempt_id == attempt_id, "attempt_identity")
        self.effect_permission(effect.revision, attempt.approval, meta.observed_at)

    def effect_permission(
        self,
        revision: a.EffectRevision,
        approval: a.EffectAuthority,
        at: datetime,
        policy: e.CompanyContext | None = None,
    ) -> None:
        _require(
            all(
                isinstance(item.value, p.BoolValue) and item.value.value
                for item in revision.inputs
                if len(item.name) == 4 and item.name[2] == "precondition"
            ),
            "effect_precondition",
        )
        company = self.company(revision.producer.address) if policy is None else policy
        if isinstance(approval, a.ExactApproval):
            allowed = a.validate_exact_approval(
                revision,
                approval,
                company,
                at,
                action_key(approval.action) in self.revoked_approvals,
            )
        else:
            _require(
                not self.case_samples[revision.ref.key.case_id].requires_review,
                "sample_review_required",
            )
            allowed = self.standing_permission(revision, approval.grant_id, at, company)
        if isinstance(allowed, a.AuthorityRefused):
            raise ReplayError(allowed.code)

    def behavior(self, ref: e.WorkRevision) -> a.BehaviorKey:
        address = ref.address
        case = self.cases[address.case_id]
        node = self.node(address)
        _require(
            isinstance(node, (p.CodeStep, p.AiStep, p.HumanStep)), "review_producer"
        )
        assert isinstance(node, (p.CodeStep, p.AiStep, p.HumanStep))
        work = self.work.get(address)
        if work is None or work.opened.revision != ref.revision:
            work = self.history[ref]
        rules = {
            item.rule_id: item
            for item in self.catalog.artifacts[case.start.artifact].draft.rules
        }
        applicability = tuple(
            (
                item.rule_scope,
                tuple(replace(rules[name], citations=()) for name in item.rule_ids),
            )
            for item in work.inputs
            if item.rule_ids
        )
        signature = self.catalog.behavior_signatures[
            (case.start.artifact, address.node_id)
        ]
        return a.BehaviorKey(
            self.company(address).company_id,
            node.metadata.behavior_id,
            sha256(repr((signature, applicability)).encode()).hexdigest(),
        )

    def effect_behaviors(self, revision: a.EffectRevision) -> tuple[a.BehaviorKey, ...]:
        return tuple(
            self.behavior(ref)
            for ref in revision.dependencies
            if isinstance(self.node(ref.address), (p.CodeStep, p.AiStep))
        )

    def standing_permission(
        self,
        revision: a.EffectRevision,
        grant_id: str,
        at: datetime,
        company: e.CompanyContext,
    ) -> a.AuthorityAllowed | a.AuthorityRefused:
        grant = self.grants.get(grant_id)
        if grant is None:
            return a.AuthorityRefused("grant_required")
        node = self.node(revision.producer.address)
        if isinstance(node, p.HumanStep) and node.never_automate:
            return a.AuthorityRefused("human_authority_required")
        behaviors = self.effect_behaviors(revision)
        if not behaviors or any(
            self.trust.get(key, a.TrustCount()).clean < a.TRUST_THRESHOLD
            for key in behaviors
        ):
            return a.AuthorityRefused("trust_required")
        if any(
            not isinstance(item.value, p.BoolValue) or not item.value.value
            for item in revision.inputs
            if len(item.name) == 4 and item.name[2] == "precondition"
        ):
            return a.AuthorityRefused("effect_precondition")
        return a.validate_grant(
            revision, grant, company, at, behaviors, grant_id in self.revoked_grants
        )

    def standing_authority(
        self, revision: a.EffectRevision, at: datetime
    ) -> a.GrantAuthority | None:
        for grant_id in self.grants:
            allowed = self.standing_permission(
                revision, grant_id, at, self.company(revision.producer.address)
            )
            if isinstance(allowed, a.AuthorityAllowed):
                return a.GrantAuthority(grant_id)
        return None

    def select_sample(self, case_id: str, at: datetime) -> None:
        if case_id in self.case_samples or case_id not in self.case_effects:
            return
        effects = tuple(
            self.effects[ref].revision
            for ref in self.case_effects[case_id]
            if self.current_effects[ref.key] == ref
        )
        case = self.cases[case_id]
        if case.start.review_mode == "historical" or any(
            self.standing_authority(revision, at) is None for revision in effects
        ):
            self.case_samples[case_id] = a.CaseSample(None, True)
            return
        assert case.start.company is not None
        company_id = case.start.company.company_id
        ordinal = self.sampling_ordinals.get(company_id, 0) + 1
        self.sampling_ordinals[company_id] = ordinal
        self.case_samples[case_id] = a.CaseSample(
            ordinal, ordinal % a.SAMPLE_INTERVAL == 0
        )

    def review_result(self, item: a.ReviewedResult) -> None:
        ref = item.work
        _require(ref.address in self.work, "unknown_work")
        work = self.work[ref.address]
        _require(work.opened.revision == ref.revision, "stale_review")
        node = self.node(ref.address)
        _require(
            isinstance(node, (p.CodeStep, p.AiStep, p.HumanStep)), "review_producer"
        )
        assert isinstance(node, (p.CodeStep, p.AiStep, p.HumanStep))
        case = self.cases[ref.address.case_id]
        if (
            case.start.review_mode == "historical"
            or work.completed is None
            or isinstance(node, p.HumanStep)
            and node.never_automate
        ):
            return
        behavior = self.behavior(ref)
        key = a.ReviewKey(
            behavior.company_id, ref.address.case_id, behavior.behavior_id
        )
        previous = self.reviews.get(key)
        count = self.trust.get(behavior, a.TrustCount())
        if item.outcome == "mistake":
            if previous is not None and behavior in previous.mistakes:
                return
            self.trust[behavior] = a.TrustCount(0, count.generation + 1)
            self.reviews[key] = a.ReviewEvidence(
                behavior,
                count.generation + 1,
                (),
                "mistake",
                frozenset({ref}),
                (frozenset() if previous is None else previous.mistakes) | {behavior},
            )
            return
        if (
            case.start.review_mode != "review"
            or item.outcome == "unresolved"
            or not records_resolve(work.completed.value, self.company(ref.address))
        ):
            return
        if isinstance(node, p.AiStep):
            value = work.completed.value
            if (
                not isinstance(value, p.RecordValue)
                or p.NamedValue("valid", p.BoolValue(True)) not in value.fields
            ):
                return
        if previous is not None and (
            previous.outcome != "pending" or ref in previous.work
        ):
            return
        effects = tuple(
            self.work_effects[(ref, change.change_id)]
            for change in node.metadata.changes
        )
        if previous is None:
            self.reviews[key] = a.ReviewEvidence(
                behavior,
                count.generation,
                effects,
                "pending",
                frozenset({ref}),
                frozenset(),
            )
        else:
            self.reviews[key] = replace(
                previous,
                effects=(*previous.effects, *effects),
                work=previous.work | {ref},
            )
        self.case_reviews[key.case_id] = self.case_reviews.get(
            key.case_id, frozenset()
        ) | {key}
        for effect in effects:
            self.pending_reviews[effect] = self.pending_reviews.get(
                effect, frozenset()
            ) | {key}
        self.complete_review(key)

    def complete_review(self, key: a.ReviewKey) -> None:
        review = self.reviews[key]
        if review.outcome != "pending" or self.cases[key.case_id].status != "succeeded":
            return
        current = frozenset(
            e.WorkRevision(address, self.work[address].opened.revision)
            for address in self.behavior_work[key]
            if address in self.work
        )
        if (
            not current
            or not current <= review.work
            or any(self.behavior(ref) != review.behavior for ref in current)
            or not all(
                self.confirmed_effects.get(effect.key) == effect
                for effect in review.effects
            )
        ):
            return
        count = self.trust.get(review.behavior, a.TrustCount())
        if count.generation == review.generation:
            self.trust[review.behavior] = replace(count, clean=count.clean + 1)
        self.reviews[key] = replace(review, outcome="clean")
        self.case_reviews[key.case_id] = self.case_reviews[key.case_id] - {key}

    def confirm_reviews(self, ref: a.EffectRef) -> None:
        for key in self.pending_reviews.get(ref, ()):
            self.complete_review(key)
        self.pending_reviews.pop(ref, None)

    def transition_trust(self, command: e.TrustCommand) -> None:
        action = (
            command.grant.grantor
            if isinstance(command, e.GrantStandingAuthority)
            else command.action
        )
        meta = command.meta
        _require(
            action.origin == "dex"
            and action.actor == meta.actor
            and bool(action.action_id.strip())
            and action.decided_at.utcoffset() is not None
            and action.decided_at <= meta.observed_at,
            "trust_actor",
        )
        key = action_key(action)
        _require(
            key not in self.trust_actions and key not in self.actions, "action_conflict"
        )
        if isinstance(command, e.ReviewResults):
            _require(command.case_id in self.cases, "unknown_case")
            _require(bool(command.results), "review_results")
            _require(action.role == "reviewer", "review_authority")
            _require(
                len({item.work for item in command.results}) == len(command.results),
                "duplicate_review",
            )
            for item in command.results:
                _require(item.work.address.case_id == command.case_id, "review_case")
                self.observer(item.work.address, action, meta)
                _require(
                    all(
                        self.member(item.work.address, action.actor, "reviewer", at)
                        for at in (action.decided_at, meta.observed_at)
                    ),
                    "review_authority",
                )
                self.review_result(item)
        else:
            company = command.company
            _require(action.company_id == company.company_id, "company_mismatch")
            _require(
                action.role == "controller"
                and all(
                    a.has_role(company, action.actor, "controller", (), at)
                    for at in (action.decided_at, meta.observed_at)
                ),
                "grant_authority",
            )
            if isinstance(command, e.RevokeStandingGrant):
                _require(command.grant_id in self.grants, "unknown_grant")
                _require(
                    self.grants[command.grant_id].grantor.company_id
                    == company.company_id,
                    "company_mismatch",
                )
                _require(command.grant_id not in self.revoked_grants, "grant_revoked")
                self.revoked_grants[command.grant_id] = action
            else:
                grant = command.grant
                _require(
                    bool(grant.grant_id.strip()) and grant.grant_id not in self.grants,
                    "grant_identity",
                )
                _require(
                    bool(grant.operations)
                    and len(set(grant.operations)) == len(grant.operations)
                    and all(item.strip() for item in grant.operations)
                    and bool(grant.behaviors)
                    and len(set(grant.behaviors)) == len(grant.behaviors)
                    and grant.amount_limit_cents >= 0
                    and len({item.name for item in grant.scope.parts})
                    == len(grant.scope.parts)
                    and len({item.name for item in grant.conditions})
                    == len(grant.conditions),
                    "grant_bounds",
                )
                _require(
                    grant.valid_from.utcoffset() is not None
                    and grant.valid_from >= action.decided_at
                    and (
                        grant.valid_until is None
                        or (
                            grant.valid_until.utcoffset() is not None
                            and grant.valid_until > grant.valid_from
                        )
                    ),
                    "grant_time",
                )
                _require(
                    all(
                        item.company_id == company.company_id
                        for item in grant.behaviors
                    ),
                    "company_mismatch",
                )
                _require(
                    all(
                        self.trust.get(item, a.TrustCount()).clean >= a.TRUST_THRESHOLD
                        for item in grant.behaviors
                    ),
                    "trust_required",
                )
                self.grants[grant.grant_id] = grant
        self.trust_actions[key] = command

    def start(self, command: e.RuntimeCommand) -> None:
        meta = command.meta
        _require(
            bool(meta.command_id.strip()) and bool(meta.actor.strip()),
            "command_identity",
        )
        _require(
            meta.occurred_at.utcoffset() is not None
            and meta.observed_at.utcoffset() is not None,
            "command_time",
        )
        bounds = command.bounds
        defaults = e.ActivationBounds()
        _require(
            0 < bounds.work <= defaults.work
            and 0 < bounds.allocations <= defaults.allocations
            and 0 < bounds.instances <= defaults.instances
            and 3 <= bounds.events <= defaults.events,
            "invalid_bounds",
        )
        meter = _Meter(bounds)
        if isinstance(command, (e.RespondTask, e.CorrectResult)):
            meter.value(command.value)
        elif (
            isinstance(command, e.SupplyRecording)
            and command.recording.value is not None
        ):
            meter.value(command.recording.value)
        elif (
            isinstance(command, e.SupplyRecording)
            and command.recording.failure is not None
        ):
            meter.value(p.TextValue(command.recording.failure))
        self.usage = meter.usage()
        if isinstance(command, e.StartSandbox):
            _require(command.artifact in self.catalog.artifacts, "missing_artifact")
            _require(
                bool(command.case_id.strip()) and command.case_id not in self.cases,
                "case_identity",
            )
            artifact = self.catalog.artifacts[command.artifact]
            nodes = self.catalog.nodes[command.artifact]
            for node in nodes.values():
                if (
                    isinstance(node, (p.CodeStep, p.AiStep, p.HumanStep))
                    and node.metadata.changes
                ):
                    _require(command.company is not None, "company_required")
                    _require(
                        all(
                            change.scope is not None and change.occurrence is not None
                            for change in node.metadata.changes
                        ),
                        "unsupported_change",
                    )
                if isinstance(node, p.AiStep):
                    _require(node.result_schema is not None, "unsupported_step")
                if isinstance(node, (p.AiStep, p.HumanStep)):
                    _require(command.company is not None, "company_required")
            if command.company is not None:
                _require(
                    bool(command.company.company_id)
                    and bool(command.company.policy_revision)
                    and bool(command.company.record_revision),
                    "company_identity",
                )
                for permission in (
                    *command.company.memberships,
                    *command.company.observers,
                ):
                    _require(
                        permission.valid_from.utcoffset() is not None
                        and (
                            permission.valid_until is None
                            or (
                                permission.valid_until.utcoffset() is not None
                                and permission.valid_from < permission.valid_until
                            )
                        ),
                        "policy_time",
                    )
            _require(type(command.business_date) is date, "business_date")
            facts = {item.name: item.value for item in command.facts}
            _require(
                len(facts) == len(command.facts) == len(artifact.draft.inputs),
                "input_fields",
            )
            for item in artifact.draft.inputs:
                _require(item.name in facts, "input_fields")
                meter.value(facts[item.name])
                _require(_valid(facts[item.name], item.schema), "input_type")
            self.cases[command.case_id] = Case(command, "running")
        elif isinstance(
            command,
            (
                e.ApproveEffect,
                e.RevokeEffectApproval,
                e.AmendEffect,
                e.BeginEffectAttempt,
                e.MarkEffectUncertain,
                e.ConfirmEffect,
                e.ReconcileEffect,
            ),
        ):
            self.effect_observer(command)
        elif isinstance(command, e.SignalRepeat):
            _require(command.address in self.work, "unknown_wait")
            work = self.work[command.address]
            node = self.node(command.address)
            _require(
                isinstance(node, p.Repeat) and isinstance(node.bound, p.EventRepeat),
                "unknown_wait",
            )
            assert isinstance(node, p.Repeat) and isinstance(node.bound, p.EventRepeat)
            _require(
                work.waiting is not None
                and work.waiting.iteration == command.iteration
                and node.bound.event == command.event,
                "stale_signal",
            )
            case = self.cases[command.address.case_id]
            _require(case.status == "waiting", "case_terminal")
            self.cases[command.address.case_id] = replace(case, status="running")
        else:
            address = command_address(command)
            _require(address in self.work, "unknown_work")
            case = self.cases[address.case_id]
            _require(case.status != "failed", "case_terminal")
            if isinstance(command, e.SupplyRecording):
                self.check_recording(command.recording)
            else:
                self.check_human(command)
            self.cases[address.case_id] = replace(case, status="running", failure=None)

    def transition(
        self,
        payload: e.WorkOpened
        | e.ControlSelected
        | e.InputBound
        | e.WorkSucceeded
        | e.RepeatWaiting
        | e.CaseSettled
        | e.TaskOpened
        | e.HumanActed
        | e.RecordingRequested
        | e.RecordingConsumed
        | e.EffectProposed
        | e.EffectTransitioned,
    ) -> None:
        assert self.command is not None
        case_id = command_case(self.command)
        if isinstance(payload, e.EffectProposed):
            revision = payload.revision
            _require(revision.producer.address.case_id == case_id, "command_case")
            _require(
                revision
                == self.effect_revision(
                    revision.producer.address, revision.change_id, revision.inputs
                ),
                "effect_revision",
            )
            _require(
                (revision.producer, revision.change_id) in self.required_proposals
                or revision.producer.address in self.refresh_effects,
                "unexpected_proposal",
            )
            self.add_effect(revision)
            self.required_proposals.discard((revision.producer, revision.change_id))
            return
        if isinstance(payload, e.EffectTransitioned):
            _require(
                payload.command == self.command and not self.action_applied,
                "command_effect",
            )
            self.transition_effect(payload.command)
            self.action_applied = True
            return
        payload_case = (
            payload.case_id
            if isinstance(payload, e.CaseSettled)
            else payload.address.case_id
        )
        _require(payload_case == case_id, "command_case")
        if isinstance(payload, e.CaseSettled):
            _require(not self.required_proposals, "missing_proposal")
            _require(
                self.usage.work <= payload.usage.work <= self.command.bounds.work
                and self.usage.allocations
                <= payload.usage.allocations
                <= self.command.bounds.allocations,
                "usage_bounds",
            )
            _require(payload.case_id in self.cases, "unknown_case")
            case = self.cases[payload.case_id]
            root = e.WorkAddress(
                payload.case_id,
                p.node_identity(self.catalog.artifacts[case.start.artifact].draft.root),
            )
            root_work = self.work.get(root)
            if isinstance(
                self.command,
                (
                    e.ApproveEffect,
                    e.RevokeEffectApproval,
                    e.AmendEffect,
                    e.BeginEffectAttempt,
                    e.MarkEffectUncertain,
                    e.ConfirmEffect,
                    e.ReconcileEffect,
                ),
            ):
                _require(
                    (payload.status, payload.failure) == (case.status, case.failure),
                    "effect_case_status",
                )
            if payload.status == "succeeded":
                _require(
                    root_work is not None
                    and root_work.completed is not None
                    and payload.failure is None,
                    "partial_success",
                )
            elif payload.status == "waiting":
                _require(
                    payload.failure is None
                    and any(
                        work.waiting is not None
                        or work.task is not None
                        or work.request is not None
                        for address, work in self.work.items()
                        if address.case_id == payload.case_id
                    ),
                    "missing_wait",
                )
            else:
                _require(
                    payload.status == "failed"
                    and payload.failure is not None
                    and (root_work is None or root_work.completed is None),
                    "failure_state",
                )
            self.cases[payload.case_id] = replace(
                case, status=payload.status, failure=payload.failure
            )
            for key in self.case_reviews.get(payload.case_id, ()):
                self.complete_review(key)
            self.settled = True
            return
        address = payload.address
        self.node(address)
        _require(self.cases[address.case_id].status == "running", "case_terminal")
        if isinstance(
            payload,
            (e.TaskOpened, e.HumanActed, e.RecordingRequested, e.RecordingConsumed),
        ):
            _require(address in self.work, "unknown_work")
            self.continuation(payload)
            return
        if isinstance(payload, e.WorkOpened):
            _require(payload.revision == self.next_revision(address), "work_revision")
            _require(address not in self.work, "duplicate_work")
            if payload.parent is None:
                case = self.cases[address.case_id]
                root = self.catalog.artifacts[case.start.artifact].draft.root
                _require(
                    address == e.WorkAddress(address.case_id, p.node_identity(root))
                    and payload.context == e.Context(),
                    "root_address",
                )
            else:
                _require(payload.parent in self.work, "unknown_parent")
                parent = self.work[payload.parent]
                _require(
                    parent.selected is not None
                    and address in self.selected_positions(payload.parent),
                    "unselected_work",
                )
                _require(
                    payload.context == self.child_context(payload.parent, address),
                    "lexical_context",
                )
                if isinstance(self.node(payload.parent), p.Sequence):
                    assert parent.selected is not None
                    position = self.selected_positions(payload.parent)[address]
                    _require(
                        all(
                            dep in self.work and self.work[dep].completed is not None
                            for dep in parent.selected.dependencies[:position]
                        ),
                        "sequence_order",
                    )
            for binding in payload.context.results:
                _require(
                    binding.address in self.work
                    and self.work[binding.address].completed is not None,
                    "missing_result",
                )
            _require(self.instances < self.command.bounds.instances, "instance_limit")
            self.instances += 1
            self.work[address] = Work(payload)
            node = self.node(address)
            company = self.cases[address.case_id].start.company
            if company is not None and isinstance(
                node, (p.CodeStep, p.AiStep, p.HumanStep)
            ):
                key = a.ReviewKey(
                    company.company_id, address.case_id, node.metadata.behavior_id
                )
                self.behavior_work[key] = self.behavior_work.get(key, frozenset()) | {
                    address
                }
            for ref in payload.context.controls:
                self.consumers[ref] = self.consumers.get(ref, frozenset()) | {address}
            return
        _require(address in self.work, "unknown_work")
        work = self.work[address]
        _require(work.completed is None, "completed_work")
        node = self.node(address)
        if isinstance(payload, e.InputBound):
            self.check_input(address, payload.consumed)
            bindings = self.bound_inputs(address)
            if payload.consumed.name in bindings:
                inputs = tuple(
                    item for item in work.inputs if item.name != payload.consumed.name
                ) + (payload.consumed,)
                self.set_inputs(address, inputs)
            else:
                self.work[address] = replace(
                    work, inputs=work.inputs + (payload.consumed,)
                )
                bindings[payload.consumed.name] = payload.consumed
                if payload.consumed.producer is not None:
                    assert payload.consumed.producer_revision is not None
                    ref = e.WorkRevision(
                        payload.consumed.producer, payload.consumed.producer_revision
                    )
                    self.consumers[ref] = self.consumers.get(ref, frozenset()) | {
                        address
                    }
            return
        bindings = self.bound_inputs(address)
        _require(
            all(bindings.get(item.name) == item for item in payload.inputs),
            "unbound_input",
        )
        if isinstance(payload, e.ControlSelected):
            _require(
                not isinstance(node, (p.CodeStep, p.AiStep, p.HumanStep)),
                "leaf_control",
            )
            _require(
                payload.dependencies == _dependencies(node, address, payload.selection),
                "dependencies",
            )
            if work.selected is not None:
                _require(isinstance(node, p.Repeat), "duplicate_selection")
                previous = work.selected.selection
                _require(
                    isinstance(previous, p.IntValue)
                    and payload.selection == p.IntValue(previous.value + 1),
                    "repeat_iteration",
                )
                _require(
                    all(
                        dep in self.work and self.work[dep].completed is not None
                        for dep in work.selected.dependencies
                    ),
                    "incomplete_iteration",
                )
                if isinstance(node, p.Repeat) and isinstance(node.bound, p.EventRepeat):
                    _require(
                        isinstance(self.command, e.SignalRepeat)
                        and self.command.address == address
                        and work.waiting is not None,
                        "missing_signal",
                    )
            if isinstance(node, p.Repeat):
                if work.selected is None:
                    _require(
                        payload.selection == p.IntValue(0)
                        and tuple(item.name for item in payload.inputs)
                        == (("initial",),),
                        "repeat_iteration",
                    )
                else:
                    _require(
                        tuple(item.name for item in payload.inputs)
                        == (("carried",), ("until",))
                        and payload.inputs[1].value == p.BoolValue(False),
                        "repeat_condition",
                    )
            if isinstance(node, (p.Choose, p.Each)):
                _require(
                    len(payload.inputs) == 1
                    and payload.inputs[0].value == payload.selection,
                    "selection_input",
                )
            self.clear_selection_indexes(address)
            self.work[address] = replace(work, selected=payload, waiting=None)
            self.pending[address] = set(
                child
                for child in payload.dependencies
                if child not in self.work or self.work[child].completed is None
            )
        elif isinstance(payload, e.RepeatWaiting):
            _require(
                isinstance(node, p.Repeat)
                and isinstance(node.bound, p.EventRepeat)
                and work.selected is not None,
                "invalid_wait",
            )
            assert work.selected is not None
            _require(
                work.selected.selection == p.IntValue(payload.iteration)
                and work.waiting is None,
                "repeat_iteration",
            )
            _require(
                all(
                    dep in self.work and self.work[dep].completed is not None
                    for dep in work.selected.dependencies
                ),
                "incomplete_iteration",
            )
            _require(
                tuple(item.name for item in payload.inputs)
                == (("carried",), ("until",))
                and payload.inputs[1].value == p.BoolValue(False),
                "repeat_condition",
            )
            _require(payload.carried == payload.inputs[0].value, "carried_state")
            self.work[address] = replace(work, waiting=payload)
        else:
            _require(_valid(payload.value, p.node_output(node)), "result_type")
            if not isinstance(node, p.CodeStep):
                _require(work.selected is not None, "missing_selection")
                assert work.selected is not None
                _require(
                    all(
                        dep in self.work and self.work[dep].completed is not None
                        for dep in work.selected.dependencies
                    ),
                    "incomplete_join",
                )
            self.check_completion(node, work, payload)
            usage = lang.Usage(
                self.usage.work + payload.usage.work,
                self.usage.allocations + payload.usage.allocations,
            )
            _require(
                usage.work <= self.command.bounds.work
                and usage.allocations <= self.command.bounds.allocations,
                "usage_bounds",
            )
            self.usage = usage
            self.complete(address, payload)

    def effect_dependencies(
        self, producer: e.WorkRevision, inputs: tuple[e.ConsumedInput, ...]
    ) -> tuple[tuple[e.WorkRevision, ...], tuple[a.ActionKey, ...]]:
        pending = [producer]
        pending.extend(
            e.WorkRevision(item.producer, item.producer_revision)
            for item in inputs
            if item.producer is not None and item.producer_revision is not None
        )
        dependencies: set[e.WorkRevision] = set()
        decisions: set[a.ActionKey] = set()
        while pending:
            ref = pending.pop()
            if ref in dependencies:
                continue
            dependencies.add(ref)
            current = self.work.get(ref.address)
            work = (
                current
                if current is not None and current.opened.revision == ref.revision
                else self.history[ref]
            )
            if ref in self.work_actions:
                decisions.add(self.work_actions[ref])
            pending.extend(work.opened.context.controls)
            pending.extend(
                e.WorkRevision(item.producer, item.producer_revision)
                for item in work.inputs
                if item.producer is not None and item.producer_revision is not None
            )
        return tuple(sorted(dependencies, key=repr)), tuple(sorted(decisions))

    def effect_revision(
        self,
        address: e.WorkAddress,
        change_id: str,
        inputs: tuple[e.ConsumedInput, ...],
    ) -> a.EffectRevision:
        _require(
            address in self.work and self.work[address].completed is not None,
            "effect_producer",
        )
        node = self.node(address)
        _require(
            isinstance(node, (p.CodeStep, p.AiStep, p.HumanStep)), "effect_producer"
        )
        assert isinstance(node, (p.CodeStep, p.AiStep, p.HumanStep))
        changes = {item.change_id: item for item in node.metadata.changes}
        _require(change_id in changes, "effect_declaration")
        change = changes[change_id]
        assert change.scope is not None and change.occurrence is not None
        prefix = ("change", change_id)
        expected = (prefix + ("payload",), prefix + ("occurrence",))
        expected += tuple(prefix + ("scope", item.name) for item in change.scope)
        expected += tuple(
            prefix + ("precondition", item.name) for item in change.preconditions
        )
        values = {item.name: item.value for item in inputs}
        _require(
            len(values) == len(inputs) and all(name in values for name in expected),
            "effect_inputs",
        )
        for item in inputs:
            self.check_input(address, item, inputs)
        payload = values[prefix + ("payload",)]
        _require(_valid(payload, change.payload.schema), "effect_payload")
        _require(records_resolve(payload, self.company(address)), "unresolved_identity")
        _require(
            all(records_resolve(item.value, self.company(address)) for item in inputs),
            "unresolved_identity",
        )
        occurrence = values[prefix + ("occurrence",)]
        _require(
            isinstance(occurrence, p.TextValue) and bool(occurrence.value.strip()),
            "effect_occurrence",
        )
        assert isinstance(occurrence, p.TextValue)
        scope = a.OperationScope(
            tuple(
                sorted(
                    (
                        p.NamedValue(item.name, values[prefix + ("scope", item.name)])
                        for item in change.scope
                    ),
                    key=lambda item: item.name,
                )
            )
        )
        key = a.EffectKey(
            self.company(address).company_id,
            address.case_id,
            scope,
            change.operation,
            occurrence.value,
        )
        original_key = self.operation_keys.get((address, change_id))
        _require(original_key is None or original_key == key, "effect_identity_changed")
        previous = self.current_effects.get(key)
        ref = a.EffectRef(key, 1 if previous is None else previous.revision + 1)
        dependencies, decisions = self.effect_dependencies(self.ref(address), inputs)
        return a.EffectRevision(
            ref,
            self.ref(address),
            change_id,
            inputs,
            dependencies,
            decisions,
            payload,
            self.cases[address.case_id].start.artifact,
            node.metadata.behavior_id,
            None,
        )

    def add_effect(self, revision: a.EffectRevision) -> None:
        previous = self.current_effects.get(revision.ref.key)
        if previous is not None:
            self.effects[previous] = replace(
                self.effects[previous], superseded_by=revision.ref
            )
        self.effects[revision.ref] = a.Effect(revision, a.Proposed())
        case_id = revision.ref.key.case_id
        self.case_effects[case_id] = (*self.case_effects.get(case_id, ()), revision.ref)
        self.current_effects[revision.ref.key] = revision.ref
        if revision.amendment_of is None:
            self.operation_keys[(revision.producer.address, revision.change_id)] = (
                revision.ref.key
            )
            self.work_effects[(revision.producer, revision.change_id)] = revision.ref
        for dependency in revision.dependencies:
            self.effect_consumers[dependency] = self.effect_consumers.get(
                dependency, frozenset()
            ) | {revision.ref}

    def check_effect_current(self, revision: a.EffectRevision) -> None:
        _require(self.current_effects[revision.ref.key] == revision.ref, "stale_effect")
        for ref in revision.dependencies:
            work = self.work.get(ref.address)
            _require(
                work is not None
                and work.opened.revision == ref.revision
                and work.completed is not None,
                "stale_effect_evidence",
            )
        for key in revision.decisions:
            decision = self.actions[key]
            _require(
                isinstance(decision, e.RespondTask)
                and decision.task.work in revision.dependencies,
                "business_decision",
            )

    def effect_observer(self, command: e.EffectCommand) -> None:
        _require(command.effect in self.effects, "unknown_effect")
        address = self.effects[command.effect].revision.producer.address
        if isinstance(
            command, (e.ApproveEffect, e.RevokeEffectApproval, e.AmendEffect)
        ):
            self.observer(address, command.action, command.meta)
            _require(
                command.action.role == "effect_approver"
                and self.member(
                    address,
                    command.action.actor,
                    "effect_approver",
                    command.action.decided_at,
                ),
                "effect_authority",
            )
        else:
            _require(
                command.meta.observed_at.utcoffset() is not None
                and self.member(
                    address,
                    command.meta.actor,
                    "effect_executor",
                    command.meta.observed_at,
                ),
                "effect_observer",
            )

    def transition_effect(self, command: e.EffectCommand) -> None:
        self.effect_observer(command)
        effect = self.effects[command.effect]
        revision, progress = effect.revision, effect.progress
        if isinstance(
            command, (e.ApproveEffect, e.RevokeEffectApproval, e.AmendEffect)
        ):
            action_identity = action_key(command.action)
            _require(action_identity not in self.actions, "action_conflict")
            self.actions[action_identity] = command
        if isinstance(command, e.ApproveEffect):
            self.check_effect_current(revision)
            _require(
                isinstance(progress, a.Proposed)
                or (
                    isinstance(progress, a.Approved)
                    and action_key(progress.approval.action) in self.revoked_approvals
                ),
                "effect_review_conflict",
            )
            approval = a.ExactApproval(command.effect, command.action)
            allowed = a.validate_exact_approval(
                revision,
                approval,
                self.company(revision.producer.address),
                command.action.decided_at,
                False,
            )
            _require(isinstance(allowed, a.AuthorityAllowed), "effect_authority")
            self.effects[command.effect] = replace(
                effect, progress=a.Approved(approval)
            )
            for dependency in revision.dependencies:
                if isinstance(
                    self.node(dependency.address), (p.CodeStep, p.AiStep, p.HumanStep)
                ):
                    self.review_result(a.ReviewedResult(dependency, "clean"))
            return
        if isinstance(command, e.AmendEffect):
            self.check_effect_current(revision)
            _require(
                command.original in self.effects
                and self.confirmed_effects.get(command.original.key)
                == command.original,
                "amendment_original",
            )
            _require(
                command.original.key == revision.ref.key
                and bool(command.occurrence.strip())
                and command.occurrence != revision.ref.key.occurrence,
                "amendment_identity",
            )
            key = replace(revision.ref.key, occurrence=command.occurrence)
            _require(key not in self.current_effects, "amendment_conflict")
            self.add_effect(
                replace(
                    revision, ref=a.EffectRef(key, 1), amendment_of=command.original
                )
            )
            return
        authority: a.EffectAuthority
        if isinstance(progress, a.Proposed):
            _require(
                isinstance(command, e.BeginEffectAttempt), "exact_approval_required"
            )
            standing = self.standing_authority(revision, command.meta.observed_at)
            _require(standing is not None, "exact_approval_required")
            assert standing is not None
            authority = standing
        else:
            authority = (
                progress.approval
                if isinstance(progress, (a.Approved, a.Attempted))
                else progress.attempt.approval
            )
        if isinstance(command, e.RevokeEffectApproval):
            _require(isinstance(authority, a.ExactApproval), "stale_approval")
            assert isinstance(authority, a.ExactApproval)
            _require(command.approval == action_key(authority.action), "stale_approval")
            _require(
                action_key(authority.action) not in self.revoked_approvals,
                "approval_revoked",
            )
            self.revoked_approvals = self.revoked_approvals | {
                action_key(authority.action)
            }
            return
        if isinstance(command, e.BeginEffectAttempt):
            self.check_effect_current(revision)
            _require(
                isinstance(progress, (a.Approved, a.Proposed))
                or (
                    isinstance(progress, a.Reconciled)
                    and isinstance(progress.conclusion, a.FencedNotApplied)
                ),
                "effect_attempt_state",
            )
            _require(
                revision.ref.key not in self.unresolved_attempts, "unresolved_attempt"
            )
            _require(
                revision.ref.key not in self.confirmed_effects, "amendment_required"
            )
            self.effect_permission(revision, authority, command.meta.observed_at)
            attempt_key = revision.ref.key, command.attempt_id
            _require(
                bool(command.attempt_id.strip())
                and attempt_key not in self.attempt_ids,
                "attempt_identity",
            )
            self.attempt_ids[attempt_key] = command.effect
            self.unresolved_attempts[revision.ref.key] = command.effect
            self.effects[command.effect] = replace(
                effect, progress=a.Attempted(authority, command.attempt_id)
            )
            return
        _require(
            isinstance(progress, (a.Attempted, a.Uncertain)), "effect_attempt_state"
        )
        assert isinstance(progress, (a.Attempted, a.Uncertain))
        attempt = progress if isinstance(progress, a.Attempted) else progress.attempt
        _require(command.attempt_id == attempt.attempt_id, "attempt_identity")
        if isinstance(command, e.MarkEffectUncertain):
            _require(bool(command.reason.strip()), "uncertain_reason")
            self.effects[command.effect] = replace(
                effect, progress=a.Uncertain(attempt, command.reason)
            )
            return
        if isinstance(command, e.ConfirmEffect):
            receipt = command.receipt
            result: a.Confirmed | a.Reconciled = a.Confirmed(attempt, receipt)
        else:
            result = a.Reconciled(attempt, command.conclusion)
            receipt = (
                command.conclusion.receipt
                if isinstance(command.conclusion, a.Applied)
                else None
            )
            if isinstance(command.conclusion, a.FencedNotApplied):
                _require(
                    bool(command.conclusion.fence_evidence.strip()),
                    "reconciliation_fence",
                )
        if receipt is not None:
            _require(
                bool(receipt.adapter_revision.strip())
                and bool(receipt.external_id.strip())
                and bool(receipt.evidence.strip()),
                "execution_receipt",
            )
            self.confirmed_effects[revision.ref.key] = command.effect
        _require(
            self.unresolved_attempts.get(revision.ref.key) == command.effect,
            "unresolved_attempt",
        )
        del self.unresolved_attempts[revision.ref.key]
        self.effects[command.effect] = replace(effect, progress=result)
        if receipt is not None:
            self.confirm_reviews(command.effect)

    def next_revision(self, address: e.WorkAddress) -> int:
        return 1 + max(
            (ref.revision for ref in self.history if ref.address == address), default=0
        )

    def ref(self, address: e.WorkAddress) -> e.WorkRevision:
        return e.WorkRevision(address, self.work[address].opened.revision)

    def company(self, address: e.WorkAddress) -> e.CompanyContext:
        company = self.cases[address.case_id].start.company
        _require(company is not None, "company_required")
        assert company is not None
        return company

    def member(
        self, address: e.WorkAddress, actor: str, role: str, at: datetime
    ) -> bool:
        return any(
            item.actor == actor
            and item.role == role
            and address.scope[: len(item.scope)] == item.scope
            and item.valid_from <= at
            and (item.valid_until is None or at < item.valid_until)
            for item in self.company(address).memberships
        )

    def observer(
        self, address: e.WorkAddress, action: e.HumanAction, meta: e.CommandMeta
    ) -> None:
        _require(
            action.decided_at.utcoffset() is not None
            and meta.observed_at.utcoffset() is not None
            and action.decided_at <= meta.observed_at,
            "decision_time",
        )
        _require(
            action.company_id == self.company(address).company_id, "company_mismatch"
        )
        _require(
            bool(action.action_id) and bool(action.actor) and bool(action.origin),
            "action_identity",
        )
        if action.origin == "dex":
            _require(meta.actor == action.actor, "observer_forbidden")
        else:
            _require(
                any(
                    item.observer == meta.actor
                    and item.origin == action.origin
                    and address.scope[: len(item.scope)] == item.scope
                    and item.valid_from <= meta.observed_at
                    and (
                        item.valid_until is None or meta.observed_at < item.valid_until
                    )
                    for item in self.company(address).observers
                ),
                "observer_forbidden",
            )

    def check_human(self, command: e.HumanCommand) -> None:
        address = command_address(command)
        self.observer(address, command.action, command.meta)
        role = (
            self.tasks[command.task].eligible_role
            if isinstance(command, e.RespondTask) and command.task in self.tasks
            else "corrector"
            if isinstance(command, e.CorrectResult)
            else "task_admin"
        )
        _require(
            command.action.role == role
            and self.member(
                address, command.action.actor, role, command.action.decided_at
            ),
            "actor_forbidden",
        )
        if isinstance(command, e.CorrectResult):
            _require(
                not isinstance(self.node(address), p.HumanStep),
                "human_decision_immutable",
            )
            _require(command.work == self.ref(address), "stale_work")
            _require(self.work[address].completed is not None, "missing_result")
            _require(
                _valid(command.value, p.node_output(self.node(address))),
                "response_schema",
            )
            _require(
                records_resolve(command.value, self.company(address)),
                "unresolved_identity",
            )
            return
        _require(command.task in self.tasks, "unknown_task")
        task = self.tasks[command.task]
        _require(
            task.ref.work == self.ref(address)
            and self.work[address].task == task.ref
            and task.status == "open",
            "stale_task",
        )
        if isinstance(command, e.RespondTask):
            _require(command.reviewed == task.reviewed, "reviewed_revision")
            _require(
                task.assignee is None or task.assignee == command.action.actor,
                "assignment",
            )
            _require(_valid(command.value, task.schema), "response_schema")
            _require(
                records_resolve(command.value, self.company(address)),
                "unresolved_identity",
            )
        elif isinstance(command, e.ReassignTask) and command.assignee is not None:
            _require(
                self.member(
                    address,
                    command.assignee,
                    task.eligible_role,
                    command.meta.observed_at,
                ),
                "assignment",
            )

    def task_for(self, address: e.WorkAddress) -> e.Task:
        node = self.node(address)
        assert isinstance(node, p.HumanStep)
        work = self.work[address]
        _require(
            tuple(item.name for item in work.inputs if len(item.name) <= 2)
            == tuple(("input", item.name) for item in node.metadata.inputs)
            + (("request",),),
            "input_fields",
        )
        reviewed = tuple(
            dict.fromkeys(
                e.WorkRevision(item.producer, item.producer_revision)
                for item in work.inputs
                if item.producer is not None and item.producer_revision is not None
            )
        )
        request = next(item.value for item in work.inputs if item.name == ("request",))
        return e.Task(
            e.TaskRef(self.ref(address), 1),
            self.company(address).company_id,
            reviewed,
            node.eligible_role,
            None,
            node.due_at,
            node.metadata.output,
            request,
        )

    def recording_request(self, address: e.WorkAddress) -> e.RecordingRequest:
        node = self.node(address)
        assert isinstance(node, p.AiStep) and node.result_schema is not None
        company = self.company(address)
        _require(
            tuple(
                item.name for item in self.work[address].inputs if len(item.name) == 2
            )
            == tuple(("input", item.name) for item in node.metadata.inputs),
            "input_fields",
        )
        return e.RecordingRequest(
            self.ref(address),
            company.company_id,
            self.cases[address.case_id].start.artifact,
            self.work[address].inputs,
            node.prompt_revision,
            node.result_schema,
            company.record_revision,
        )

    def check_recording(self, recording: e.Recording) -> None:
        address = recording.request.work.address
        _require(
            recording.request == self.work[address].request
            and recording.request.work == self.ref(address),
            "recording_request",
        )
        _require(recording.request.work not in self.recordings, "recording_conflict")
        _require(
            bool(recording.recording_id)
            and bool(recording.model)
            and recording.input_tokens >= 0
            and recording.output_tokens >= 0,
            "recording_identity",
        )
        _require(
            (recording.value is None) != (recording.failure is None),
            "recording_content",
        )

    def set_inputs(
        self, address: e.WorkAddress, inputs: tuple[e.ConsumedInput, ...]
    ) -> None:
        work = self.work[address]
        previous = set(work.opened.context.controls)
        current = set(work.opened.context.controls)
        for group, refs in ((work.inputs, previous), (inputs, current)):
            for item in group:
                if item.producer is not None:
                    assert item.producer_revision is not None
                    refs.add(e.WorkRevision(item.producer, item.producer_revision))
        for ref in previous - current:
            consumers = self.consumers[ref] - {address}
            if consumers:
                self.consumers[ref] = consumers
            else:
                del self.consumers[ref]
        for ref in current - previous:
            self.consumers[ref] = self.consumers.get(ref, frozenset()) | {address}
        self.work[address] = replace(work, inputs=inputs)
        self.input_indexes.pop(address, None)

    def require_effects(self, address: e.WorkAddress) -> None:
        node = self.node(address)
        if not isinstance(node, (p.CodeStep, p.AiStep, p.HumanStep)):
            return
        completed = self.work[address].completed
        assert completed is not None
        if isinstance(node, p.AiStep) and _path(
            completed.value, ("valid",)
        ) != p.BoolValue(True):
            return
        self.required_proposals.update(
            (self.ref(address), change.change_id) for change in node.metadata.changes
        )

    def complete(self, address: e.WorkAddress, payload: e.WorkSucceeded) -> None:
        work = self.work[address]
        self.work[address] = replace(
            work, completed=payload, waiting=None, task=None, request=None
        )
        self.require_effects(address)
        parent = work.opened.parent
        if parent is not None:
            self.pending[parent].discard(address)

    def continuation(
        self,
        payload: e.TaskOpened
        | e.HumanActed
        | e.RecordingRequested
        | e.RecordingConsumed,
    ) -> None:
        address = payload.address
        work = self.work[address]
        if isinstance(payload, e.TaskOpened):
            _require(
                work.task is None
                and work.completed is None
                and payload.task == self.task_for(address),
                "task_request",
            )
            self.tasks[payload.task.ref] = payload.task
            self.work[address] = replace(work, task=payload.task.ref)
        elif isinstance(payload, e.RecordingRequested):
            _require(
                work.request is None
                and work.completed is None
                and payload.request == self.recording_request(address),
                "recording_request",
            )
            self.work[address] = replace(work, request=payload.request)
        elif isinstance(payload, e.RecordingConsumed):
            _require(
                isinstance(self.command, e.SupplyRecording)
                and self.command.recording == payload.recording,
                "command_recording",
            )
            self.check_recording(payload.recording)
            _require(
                payload.outcome
                == recording_outcome(payload.recording, self.company(address)),
                "recording_outcome",
            )
            _require(not self.action_applied, "duplicate_action")
            self.action_applied = True
            self.recordings[payload.recording.request.work] = payload.recording
            self.complete(
                address,
                e.WorkSucceeded(
                    address, payload.outcome, work.inputs, lang.Usage(0, 0)
                ),
            )
        else:
            command = payload.command
            _require(
                self.command == command and command_address(command) == address,
                "command_action",
            )
            self.check_human(command)
            key = action_key(command.action)
            _require(key not in self.actions, "action_conflict")
            _require(not self.action_applied, "duplicate_action")
            self.action_applied = True
            self.actions[key] = command
            if isinstance(command, e.CorrectResult):
                self.correct(command)
                return
            task = self.tasks[command.task]
            if isinstance(command, e.RespondTask):
                self.work_actions[task.ref.work] = key
                self.tasks[task.ref] = replace(task, status="answered")
                self.complete(
                    address,
                    e.WorkSucceeded(
                        address,
                        p.normalized_value(command.value),
                        work.inputs,
                        lang.Usage(0, 0),
                    ),
                )
            elif isinstance(command, e.CancelTask):
                self.tasks[task.ref] = replace(task, status="cancelled")
            else:
                self.tasks[task.ref] = replace(task, status="superseded")
                replacement = replace(
                    task,
                    ref=replace(
                        task.ref, request_revision=task.ref.request_revision + 1
                    ),
                    assignee=command.assignee,
                )
                self.tasks[replacement.ref] = replacement
                self.work[address] = replace(work, task=replacement.ref)

    def correct(self, command: e.CorrectResult) -> None:
        target = command.work.address
        if self.cases[target.case_id].start.company is not None:
            self.review_result(a.ReviewedResult(command.work, "mistake"))
        retained: set[e.WorkAddress] = set()
        ancestor: e.WorkAddress | None = target
        while ancestor is not None:
            retained.add(ancestor)
            ancestor = self.work[ancestor].opened.parent
        self.business_decisions.clear()
        affected: set[e.WorkAddress] = set()
        reselect: set[e.WorkAddress] = set()
        retired: set[e.WorkAddress] = set()
        queue = [target]
        while queue:
            address = queue.pop()
            for consumer in self.consumers.get(self.ref(address), ()):
                if consumer == target:
                    continue
                consumer_work = self.work[consumer]
                selection = consumer_work.selected
                should_retire = (
                    consumer not in retired
                    and self.ref(address) in consumer_work.opened.context.controls
                )
                if should_retire:
                    retired.add(consumer)
                should_reselect = (
                    consumer not in reselect
                    and selection is not None
                    and any(item.producer == address for item in selection.inputs)
                )
                if consumer not in affected or should_reselect or should_retire:
                    affected.add(consumer)
                    queue.append(consumer)
            work = self.work[address]
            if (
                address != target
                and work.selected is not None
                and (
                    address in retired
                    or isinstance(self.node(address), p.Repeat)
                    or any(
                        item.producer == target or item.producer in affected
                        for item in work.selected.inputs
                    )
                )
            ):
                reselect.add(address)
                for child in work.selected.dependencies:
                    if (
                        child not in retained
                        and child in self.work
                        and child not in retired
                    ):
                        retired.add(child)
                        affected.add(child)
                        queue.append(child)
            parent = work.opened.parent
            if parent is not None and parent not in affected:
                affected.add(parent)
                queue.append(parent)
        for address in sorted(affected | {target}, key=repr):
            self.input_indexes.pop(address, None)
            self.clear_selection_indexes(address)
            work = self.work[address]
            self.refresh_effects.update(
                self.effects[ref].revision.producer.address
                for ref in self.effect_consumers.get(self.ref(address), ())
                if self.current_effects[ref.key] == ref
            )
            self.history[self.ref(address)] = work
            if work.task is not None:
                task = self.tasks[work.task]
                self.tasks[work.task] = replace(task, status="superseded")
            if address in retired:
                self.set_inputs(address, ())
                for ref in work.opened.context.controls:
                    consumers = self.consumers[ref] - {address}
                    if consumers:
                        self.consumers[ref] = consumers
                    else:
                        del self.consumers[ref]
                del self.work[address]
                self.pending.pop(address, None)
                continue
            opened = replace(work.opened, revision=work.opened.revision + 1)
            if address == target:
                completed = e.WorkSucceeded(
                    address,
                    p.normalized_value(command.value),
                    work.inputs,
                    lang.Usage(0, 0),
                )
                self.work[address] = replace(work, opened=opened, completed=completed)
                self.require_effects(address)
            else:
                selection = None if address in reselect else work.selected
                retained_inputs = tuple(
                    item
                    for item in work.inputs
                    if item.producer != target and item.producer not in affected
                )
                self.set_inputs(address, retained_inputs)
                self.work[address] = Work(
                    opened, selected=selection, inputs=retained_inputs
                )
                if selection is not None:
                    self.pending[address] = set(selection.dependencies)
        for address in affected - retired:
            selected = self.work[address].selected
            if selected is not None:
                self.pending[address] = set(
                    child
                    for child in selected.dependencies
                    if child not in self.work or self.work[child].completed is None
                )

    def check_completion(
        self, node: p.Node, work: Work, payload: e.WorkSucceeded
    ) -> None:
        names = tuple(item.name for item in payload.inputs)
        _require(
            payload.usage.work >= 0 and payload.usage.allocations >= 0, "usage_bounds"
        )
        if isinstance(node, p.CodeStep):
            _require(
                names == tuple(("input", item.name) for item in node.metadata.inputs),
                "input_fields",
            )
            return
        selected = work.selected
        assert selected is not None
        expected: p.Value
        if isinstance(node, (p.Sequence, p.Choose)):
            _require(names == (("result",),), "export_inputs")
            expected = payload.inputs[0].value
        elif isinstance(node, p.Repeat):
            _require(
                names == (("carried",), ("until",))
                and payload.inputs[1].value == p.BoolValue(True),
                "repeat_condition",
            )
            expected = payload.inputs[0].value
        elif isinstance(node, p.Parallel):
            keys = tuple(item.scope[-1].key for item in selected.dependencies)
            _require(names == tuple(("branch", key) for key in keys), "export_inputs")
            expected = p.RecordValue(
                node.output.name,
                tuple(
                    p.NamedValue(key, item.value)
                    for key, item in zip(keys, payload.inputs, strict=True)
                ),
            )
        else:
            _require(isinstance(node, p.Each), "unsupported_step")
            keys = tuple(item.scope[-1].key for item in selected.dependencies)
            _require(names == tuple(("branch", key) for key in keys), "export_inputs")
            entries: list[p.KeyedEntry] = []
            for key, item in zip(keys, payload.inputs, strict=True):
                _require(isinstance(item.value, p.RecordValue), "result_type")
                assert isinstance(item.value, p.RecordValue)
                entries.append(p.KeyedEntry(key, item.value))
            expected = p.KeyedValue(tuple(entries))
        _require(payload.value == p.normalized_value(expected), "export_value")

    def bound_inputs(
        self, address: e.WorkAddress
    ) -> dict[tuple[str, ...], e.ConsumedInput]:
        if address not in self.input_indexes:
            self.input_indexes[address] = {
                item.name: item for item in self.work[address].inputs
            }
        return self.input_indexes[address]

    def selected_positions(self, address: e.WorkAddress) -> dict[e.WorkAddress, int]:
        if address not in self.selection_positions:
            selected = self.work[address].selected
            assert selected is not None
            self.selection_positions[address] = {
                child: position for position, child in enumerate(selected.dependencies)
            }
        return self.selection_positions[address]

    def clear_selection_indexes(self, address: e.WorkAddress) -> None:
        self.selection_positions.pop(address, None)
        self.branch_indexes.pop(address, None)
        self.entry_indexes.pop(address, None)

    def governing_decisions(self, address: e.WorkAddress) -> tuple[e.WorkRevision, ...]:
        root = self.ref(address)
        pending = [(root, False)]
        while pending:
            ref, expanded = pending.pop()
            if ref in self.business_decisions:
                continue
            current = self.work.get(ref.address)
            work = (
                current
                if current is not None and current.opened.revision == ref.revision
                else self.history[ref]
            )
            dependencies = work.opened.context.controls
            if work.selected is not None:
                dependencies += tuple(
                    self.ref(child) for child in work.selected.dependencies
                )
            if not expanded:
                pending.append((ref, True))
                pending.extend((dependency, False) for dependency in dependencies)
                continue
            decisions: set[e.WorkRevision] = (
                {ref} if ref in self.work_actions else set()
            )
            for dependency in dependencies:
                decisions.update(self.business_decisions[dependency])
            self.business_decisions[ref] = tuple(sorted(decisions, key=repr))
        return self.business_decisions[root]

    def child_context(
        self, parent_address: e.WorkAddress, child: e.WorkAddress
    ) -> e.Context:
        parent = self.work[parent_address]
        selected = parent.selected
        assert selected is not None
        context = parent.opened.context
        node = self.node(parent_address)
        if isinstance(node, p.Sequence):
            for sibling in selected.dependencies:
                if sibling == child:
                    break
                context = _with_result(context, sibling)
                context = replace(
                    context,
                    controls=tuple(
                        dict.fromkeys(
                            (*context.controls, *self.governing_decisions(sibling))
                        )
                    ),
                )
        elif isinstance(node, p.Each):
            assert isinstance(selected.selection, p.KeyedValue)
            key = child.scope[-1].key
            if parent_address not in self.entry_indexes:
                self.entry_indexes[parent_address] = {
                    item.key: item.value for item in selected.selection.entries
                }
            value = self.entry_indexes[parent_address][key]
            context = replace(
                context,
                locals=context.locals
                + (
                    e.LocalBinding(parent_address.node_id, "item", value),
                    e.LocalBinding(parent_address.node_id, "key", p.TextValue(key)),
                ),
            )
        elif isinstance(node, p.Repeat):
            _require(bool(selected.inputs), "missing_carried_state")
            context = replace(
                context,
                locals=context.locals
                + (
                    e.LocalBinding(
                        parent_address.node_id, "state", selected.inputs[0].value
                    ),
                ),
            )
        if isinstance(node, (p.Choose, p.Each, p.Repeat)):
            controls = list(context.controls)
            for item in selected.inputs:
                if item.producer is not None:
                    assert item.producer_revision is not None
                    controls.append(
                        e.WorkRevision(item.producer, item.producer_revision)
                    )
            context = replace(context, controls=tuple(dict.fromkeys(controls)))
        return context

    def input_context(self, address: e.WorkAddress, name: tuple[str, ...]) -> e.Context:
        work = self.work[address]
        context = work.opened.context
        if name and name[0] == "change":
            return _with_result(context, address)
        node = self.node(address)
        selected = work.selected
        if selected is None or isinstance(node, p.CodeStep):
            return context
        if isinstance(node, p.Sequence) and name[0] == "result":
            for child in selected.dependencies:
                context = _with_result(context, child)
        elif isinstance(node, p.Repeat) and name[0] in {"carried", "until"}:
            child = selected.dependencies[0]
            context = _with_result(self.child_context(address, child), child)
        elif isinstance(node, p.Choose) and name[0] == "result":
            context = _with_result(context, selected.dependencies[0])
        elif isinstance(node, (p.Each, p.Parallel)):
            key = name[1] if name[0] == "branch" else ""
            if address not in self.branch_indexes:
                self.branch_indexes[address] = {
                    item.scope[-1].key: item for item in selected.dependencies
                }
            child = self.branch_indexes[address].get(key)
            if child is not None:
                context = _with_result(self.child_context(address, child), child)
        return context

    def reference(self, address: e.WorkAddress, path: tuple[str, ...]) -> p.Input:
        _require(bool(path), "input_path")
        assert path
        node = self.node(address)
        reference: p.Input
        width = 1
        if isinstance(node, p.HumanStep) and path == ("request",):
            return node.request.value
        if (
            isinstance(node, (p.CodeStep, p.AiStep, p.HumanStep))
            and path[0] == "change"
        ):
            _require(len(path) >= 3, "input_path")
            assert len(path) >= 3
            changes = {item.change_id: item for item in node.metadata.changes}
            _require(path[1] in changes, "input_path")
            change = changes[path[1]]
            if path[2] == "payload":
                reference, width = change.payload.value, 3
            elif path[2] == "occurrence":
                _require(change.occurrence is not None, "input_path")
                assert change.occurrence is not None
                reference, width = change.occurrence, 3
            else:
                _require(
                    len(path) >= 4 and path[2] in {"scope", "precondition"},
                    "input_path",
                )
                assert len(path) >= 4
                bindings = change.scope if path[2] == "scope" else change.preconditions
                assert bindings is not None
                values = {item.name: item.value for item in bindings}
                _require(path[3] in values, "input_path")
                reference, width = values[path[3]], 4
        elif isinstance(node, (p.CodeStep, p.AiStep, p.HumanStep)):
            _require(len(path) >= 2 and path[0] == "input", "input_path")
            assert len(path) >= 2
            bindings = {item.name: item.value for item in node.metadata.inputs}
            _require(path[1] in bindings, "input_path")
            reference, width = bindings[path[1]], 2
        elif isinstance(node, p.Sequence):
            _require(path[0] == "result", "input_path")
            reference = node.result.value
        elif isinstance(node, p.Choose):
            if path[0] == "condition":
                reference = node.condition
            else:
                _require(path[0] == "result", "input_path")
                selected = self.work[address].selected
                _require(
                    selected is not None
                    and isinstance(selected.selection, p.BoolValue),
                    "missing_selection",
                )
                assert selected is not None and isinstance(
                    selected.selection, p.BoolValue
                )
                reference = (
                    node.when_true if selected.selection.value else node.when_false
                ).result.value
        elif isinstance(node, p.Each):
            if path[0] == "collection":
                reference = node.collection
            else:
                _require(len(path) >= 2 and path[0] == "branch", "input_path")
                reference, width = node.body.result.value, 2
        elif isinstance(node, p.Parallel):
            _require(len(path) >= 2 and path[0] == "branch", "input_path")
            assert len(path) >= 2
            branches = {item.name: item.branch for item in node.branches}
            _require(path[1] in branches, "input_path")
            reference, width = branches[path[1]].result.value, 2
        else:
            refs = {
                "initial": node.initial.value,
                "carried": node.body.result.value,
                "until": node.until,
            }
            _require(path[0] in refs, "input_path")
            reference = refs[path[0]]
        if len(path) > width:
            _require(
                isinstance(reference, p.RuleInputRef)
                and len(path) == width + 2
                and path[width] == "scope",
                "input_path",
            )
            assert isinstance(reference, p.RuleInputRef)
            assert path
            scope = {item.name: item.value for item in reference.scope}
            _require(path[-1] in scope, "input_path")
            reference = scope[path[-1]]
        return reference

    def check_input(
        self,
        address: e.WorkAddress,
        consumed: e.ConsumedInput,
        effect_inputs: tuple[e.ConsumedInput, ...] = (),
    ) -> None:
        context = self.input_context(address, consumed.name)
        reference = consumed.reference
        _require(reference == self.reference(address, consumed.name), "input_reference")
        case = self.cases[address.case_id].start
        producer: e.WorkAddress | None = None
        if isinstance(reference, p.Literal):
            value = reference.value
        elif isinstance(reference, p.ProgramInputRef):
            facts = {item.name: item.value for item in case.facts}
            _require(reference.name in facts, "input_provenance")
            value = _path(facts[reference.name], reference.path)
        elif isinstance(reference, p.ResultRef):
            bindings = {item.node_id: item.address for item in context.results}
            _require(reference.node in bindings, "input_provenance")
            producer = bindings[reference.node]
            _require(
                producer in self.work and self.work[producer].completed is not None,
                "missing_result",
            )
            completed = self.work[producer].completed
            assert completed is not None
            value = _path(completed.value, reference.path)
        elif isinstance(reference, p.LocalRef):
            locals_by_name = {
                (item.owner, item.name): item.value for item in context.locals
            }
            _require(
                (reference.owner, reference.name) in locals_by_name, "input_provenance"
            )
            value = _path(
                locals_by_name[(reference.owner, reference.name)], reference.path
            )
        else:
            rules = {
                rule.rule_id: rule
                for rule in self.catalog.artifacts[case.artifact].draft.rules
            }
            _require(
                bool(consumed.rule_ids)
                and tuple(sorted(set(consumed.rule_ids))) == consumed.rule_ids,
                "rule_provenance",
            )
            _require(
                all(rule_id in rules for rule_id in consumed.rule_ids),
                "rule_provenance",
            )
            bound = {
                item.name: item for item in (*self.work[address].inputs, *effect_inputs)
            }
            expected_scope: list[p.NamedValue] = []
            for operand in reference.scope:
                name = consumed.name + ("scope", operand.name)
                _require(
                    name in bound and bound[name].reference == operand.value,
                    "rule_scope",
                )
                expected_scope.append(p.NamedValue(operand.name, bound[name].value))
            _require(consumed.rule_scope == tuple(expected_scope), "rule_scope")
            scope = {item.name: item.value for item in consumed.rule_scope}
            winners = _winning_rules(
                tuple(rules.values()), reference.target, case.business_date, scope
            )
            _require(
                consumed.rule_ids == tuple(rule.rule_id for rule in winners),
                "rule_provenance",
            )
            values: list[p.Value] = []
            for rule_id in consumed.rule_ids:
                rule = rules[rule_id]
                _require(
                    rule.target == reference.target
                    and rule.effective_from <= case.business_date
                    and (
                        rule.effective_until is None
                        or case.business_date < rule.effective_until
                    ),
                    "rule_provenance",
                )
                _require(
                    all(
                        scope.get(item.dimension) == p.normalized_value(item.value)
                        for item in rule.scope
                    ),
                    "rule_scope",
                )
                assert isinstance(rule.consequence.value, p.Literal)
                values.append(_path(rule.consequence.value.value, reference.path))
            value = values[0]
            _require(
                all(
                    p.normalized_value(item) == p.normalized_value(value)
                    for item in values
                ),
                "rule_consequence",
            )
        _require(
            consumed.producer == producer
            and consumed.producer_revision
            == (None if producer is None else self.work[producer].opened.revision)
            and consumed.value == p.normalized_value(value),
            "input_provenance",
        )
        if not isinstance(reference, p.RuleInputRef):
            _require(
                not consumed.rule_ids and not consumed.rule_scope, "rule_provenance"
            )


def rebuild(
    events: tuple[e.RuntimeEvent, ...], programs: ProgramCatalog
) -> WorkspaceState:
    reducer = _Reducer(
        WorkspaceState(
            0, MappingProxyType({}), MappingProxyType({}), MappingProxyType({})
        ),
        programs,
    )
    try:
        for event in events:
            reducer.apply(event)
    except _Failure as error:
        raise ReplayError(error.code) from error
    return reducer.freeze()


class _Decider:
    def __init__(self, reducer: _Reducer, command: e.RuntimeCommand) -> None:
        self.reducer = reducer
        self.command = command
        self.events: list[e.RuntimeEvent] = []
        self.meter = _Meter(command.bounds)

    def emit(self, payload: e.RuntimePayload, terminal: bool = False) -> None:
        if not terminal:
            if len(self.events) >= self.command.bounds.events - 2:
                raise _Failure("event_limit")
            self.meter.charge()
        event = e.RuntimeEvent(self.command.meta.command_id, len(self.events), payload)
        self.reducer.apply(event)
        self.events.append(event)

    def resolve(
        self,
        address: e.WorkAddress,
        context: e.Context,
        reference: p.Input,
        name: tuple[str, ...],
        collected: list[e.ConsumedInput] | None = None,
    ) -> e.ConsumedInput:
        self.meter.charge()
        case = self.reducer.cases[address.case_id].start
        producer: e.WorkAddress | None = None
        rule_ids: tuple[str, ...] = ()
        scope: tuple[p.NamedValue, ...] = ()
        if isinstance(reference, p.Literal):
            value = reference.value
        elif isinstance(reference, p.ProgramInputRef):
            value = _path(
                next(item.value for item in case.facts if item.name == reference.name),
                reference.path,
            )
        elif isinstance(reference, p.ResultRef):
            producer = next(
                item.address
                for item in reversed(context.results)
                if item.node_id == reference.node
            )
            completed = self.reducer.work[producer].completed
            assert completed is not None
            value = _path(completed.value, reference.path)
        elif isinstance(reference, p.LocalRef):
            value = _path(
                next(
                    item.value
                    for item in reversed(context.locals)
                    if (item.owner, item.name) == (reference.owner, reference.name)
                ),
                reference.path,
            )
        else:
            scope = tuple(
                p.NamedValue(
                    item.name,
                    self.resolve(
                        address,
                        context,
                        item.value,
                        name + ("scope", item.name),
                        collected,
                    ).value,
                )
                for item in reference.scope
            )
            values = {item.name: item.value for item in scope}
            rules = self.reducer.catalog.artifacts[case.artifact].draft.rules
            self.meter.charge(sum(1 + len(rule.scope) for rule in rules))
            winners = _winning_rules(
                rules, reference.target, case.business_date, values
            )
            if not winners:
                raise _Failure("missing_rule")
            consequence = winners[0].consequence.value
            assert isinstance(consequence, p.Literal)
            self.meter.value(consequence.value)
            value = p.normalized_value(consequence.value)
            for rule in winners:
                assert isinstance(rule.consequence.value, p.Literal)
                if p.normalized_value(rule.consequence.value.value) != value:
                    raise _Failure("rule_conflict")
            rule_ids = tuple(rule.rule_id for rule in winners)
            value = _path(value, reference.path)
        self.meter.value(value)
        consumed = e.ConsumedInput(
            name,
            reference,
            p.normalized_value(value),
            producer,
            rule_ids,
            scope,
            None if producer is None else self.reducer.work[producer].opened.revision,
        )
        if collected is not None:
            collected.append(consumed)
        elif self.reducer.bound_inputs(address).get(consumed.name) != consumed:
            self.emit(e.InputBound(address, consumed))
        return consumed

    def propose(self, address: e.WorkAddress) -> None:
        node = self.reducer.node(address)
        if not isinstance(node, (p.CodeStep, p.AiStep, p.HumanStep)):
            return
        work = self.reducer.work[address]
        assert work.completed is not None
        if isinstance(node, p.AiStep) and _path(
            work.completed.value, ("valid",)
        ) != p.BoolValue(True):
            return
        for change in node.metadata.changes:
            identity = self.reducer.ref(address), change.change_id
            if (
                identity not in self.reducer.required_proposals
                and address not in self.reducer.refresh_effects
            ):
                continue
            assert change.scope is not None and change.occurrence is not None
            inputs: list[e.ConsumedInput] = []
            prefix = ("change", change.change_id)
            context = _with_result(work.opened.context, address)
            self.resolve(
                address, context, change.payload.value, prefix + ("payload",), inputs
            )
            self.resolve(
                address, context, change.occurrence, prefix + ("occurrence",), inputs
            )
            for item in change.scope:
                self.resolve(
                    address, context, item.value, prefix + ("scope", item.name), inputs
                )
            for item in change.preconditions:
                self.resolve(
                    address,
                    context,
                    item.value,
                    prefix + ("precondition", item.name),
                    inputs,
                )
            revision = self.reducer.effect_revision(
                address, change.change_id, tuple(inputs)
            )
            previous = self.reducer.work_effects.get(identity)
            if (
                previous is not None
                and replace(revision, ref=previous)
                == self.reducer.effects[previous].revision
            ):
                continue
            self.meter.charge(len(revision.dependencies), len(revision.dependencies))
            self.emit(e.EffectProposed(revision))

    def run(
        self, address: e.WorkAddress, context: e.Context, parent: e.WorkAddress | None
    ) -> p.Value | None:
        self.meter.charge()
        if address not in self.reducer.work:
            if self.meter.instances >= self.command.bounds.instances:
                raise _Failure("instance_limit")
            self.meter.instances += 1
            self.meter.charge(
                len(context.results) + len(context.locals) + len(context.controls),
                len(context.results) + len(context.locals) + len(context.controls),
            )
            self.emit(
                e.WorkOpened(
                    address, parent, context, self.reducer.next_revision(address)
                )
            )
        work = self.reducer.work[address]
        if work.completed is not None:
            self.propose(address)
            return work.completed.value
        context = work.opened.context
        node = self.reducer.node(address)
        if isinstance(node, p.CodeStep):
            inputs = tuple(
                self.resolve(address, context, item.value, ("input", item.name))
                for item in node.metadata.inputs
            )
            artifact = self.reducer.catalog.artifacts[
                self.reducer.cases[address.case_id].start.artifact
            ]
            remaining_work = self.command.bounds.work - self.meter.work
            remaining_allocations = (
                self.command.bounds.allocations - self.meter.allocations
            )
            if remaining_work < 1 or remaining_allocations < 1:
                raise _Failure(
                    "work_limit" if remaining_work < 1 else "allocation_limit"
                )
            limits = replace(
                artifact.checked_functions.limits,
                work=min(remaining_work, artifact.checked_functions.limits.work),
                allocations=min(
                    remaining_allocations, artifact.checked_functions.limits.allocations
                ),
            )
            function_result = lang.execute_function(
                artifact.checked_functions,
                node.function_id,
                tuple(p.NamedValue(item.name[1], item.value) for item in inputs),
                limits,
            )
            self.meter.charge(
                function_result.usage.work, function_result.usage.allocations
            )
            if isinstance(function_result, lang.LanguageFailure):
                raise _Failure(function_result.code)
            self.emit(
                e.WorkSucceeded(
                    address, function_result.value, inputs, function_result.usage
                )
            )
            self.propose(address)
            return function_result.value
        if isinstance(node, (p.AiStep, p.HumanStep)):
            if work.task is not None or work.request is not None:
                return None
            for item in node.metadata.inputs:
                self.resolve(address, context, item.value, ("input", item.name))
            if isinstance(node, p.HumanStep):
                self.resolve(address, context, node.request.value, ("request",))
                self.emit(e.TaskOpened(address, self.reducer.task_for(address)))
            else:
                self.emit(
                    e.RecordingRequested(
                        address, self.reducer.recording_request(address)
                    )
                )
            return None
        if isinstance(node, p.Repeat):
            return self.repeat(address, context, node)
        if work.selected is None:
            inputs: tuple[e.ConsumedInput, ...] = ()
            selection: p.Value = p.AbsentValue()
            if isinstance(node, p.Choose):
                consumed = self.resolve(
                    address, context, node.condition, ("condition",)
                )
                selection, inputs = consumed.value, (consumed,)
            elif isinstance(node, p.Each):
                consumed = self.resolve(
                    address, context, node.collection, ("collection",)
                )
                selection, inputs = consumed.value, (consumed,)
            dependencies = _dependencies(node, address, selection)
            self.meter.charge(len(dependencies), len(dependencies))
            self.emit(e.ControlSelected(address, selection, dependencies, inputs))
            work = self.reducer.work[address]
        assert work.selected is not None
        selected = work.selected
        consumed_results: list[e.ConsumedInput] = []
        result: p.Value
        if isinstance(node, p.Sequence):
            for child in selected.dependencies:
                value = self.run(
                    child, self.reducer.child_context(address, child), address
                )
                if value is None:
                    return None
                context = _with_result(context, child)
            consumed = self.resolve(address, context, node.result.value, ("result",))
            result = consumed.value
            consumed_results.append(consumed)
        elif isinstance(node, p.Choose):
            assert isinstance(selected.selection, p.BoolValue)
            branch = node.when_true if selected.selection.value else node.when_false
            child = selected.dependencies[0]
            if (
                self.run(child, self.reducer.child_context(address, child), address)
                is None
            ):
                return None
            consumed = self.resolve(
                address, _with_result(context, child), branch.result.value, ("result",)
            )
            result = consumed.value
            consumed_results.append(consumed)
        else:
            branches = (
                sorted(node.branches, key=lambda item: item.name)
                if isinstance(node, p.Parallel)
                else []
            )
            pending = False
            entries: list[p.KeyedEntry] = []
            fields: list[p.NamedValue] = []
            for index, child in enumerate(selected.dependencies):
                child_context = self.reducer.child_context(address, child)
                if isinstance(node, p.Each):
                    assert isinstance(selected.selection, p.KeyedValue)
                    entry = selected.selection.entries[index]
                    branch = node.body
                    key = entry.key
                else:
                    branch_item = branches[index]
                    branch = branch_item.branch
                    key = branch_item.name
                if self.run(child, child_context, address) is None:
                    pending = True
                    continue
                consumed = self.resolve(
                    address,
                    _with_result(child_context, child),
                    branch.result.value,
                    ("branch", key),
                )
                consumed_results.append(consumed)
                if isinstance(node, p.Each):
                    assert isinstance(consumed.value, p.RecordValue)
                    entries.append(p.KeyedEntry(key, consumed.value))
                else:
                    fields.append(p.NamedValue(key, consumed.value))
            if pending:
                return None
            result = (
                p.KeyedValue(tuple(entries))
                if isinstance(node, p.Each)
                else p.RecordValue(node.output.name, tuple(fields))
            )
        self.meter.value(result)
        if not _valid(result, p.node_output(node)):
            raise _Failure("result_type")
        self.emit(
            e.WorkSucceeded(address, result, tuple(consumed_results), lang.Usage(0, 0))
        )
        return result

    def repeat(
        self, address: e.WorkAddress, context: e.Context, node: p.Repeat
    ) -> p.Value | None:
        work = self.reducer.work[address]
        if work.selected is None:
            initial = self.resolve(address, context, node.initial.value, ("initial",))
            iteration = 0
            inputs = (initial,)
        elif work.waiting is not None:
            if (
                not isinstance(self.command, e.SignalRepeat)
                or self.command.address != address
            ):
                return None
            iteration = work.waiting.iteration + 1
            inputs = work.waiting.inputs
        else:
            assert isinstance(work.selected.selection, p.IntValue)
            iteration = work.selected.selection.value
            inputs = work.selected.inputs
        while True:
            self.meter.charge()
            selection = p.IntValue(iteration)
            current = self.reducer.work[address].selected
            if current is None or current.selection != selection:
                dependencies = _dependencies(node, address, selection)
                self.emit(e.ControlSelected(address, selection, dependencies, inputs))
            selected = self.reducer.work[address].selected
            assert selected is not None
            child = selected.dependencies[0]
            local = self.reducer.child_context(address, child)
            if self.run(child, local, address) is None:
                return None
            local = _with_result(local, child)
            next_value = self.resolve(
                address, local, node.body.result.value, ("carried",)
            )
            until = self.resolve(address, local, node.until, ("until",))
            assert isinstance(until.value, p.BoolValue)
            if until.value.value:
                self.emit(
                    e.WorkSucceeded(
                        address, next_value.value, (next_value, until), lang.Usage(0, 0)
                    )
                )
                return next_value.value
            if isinstance(node.bound, p.EventRepeat):
                self.emit(
                    e.RepeatWaiting(
                        address, iteration, next_value.value, (next_value, until)
                    )
                )
                return None
            if iteration + 1 >= node.bound.limit:
                raise _Failure("repeat_exhausted")
            inputs = (next_value, until)
            iteration += 1


def decide(
    state: WorkspaceState, command: e.Command, programs: ProgramCatalog
) -> Accepted | Refused:
    if any(
        case.start.artifact not in programs.artifacts for case in state.cases.values()
    ):
        return Refused("missing_artifact")
    if isinstance(command, e.ActivateProgram):
        return Refused("unsupported_activation")
    if isinstance(
        command,
        (
            e.RegisterProgram,
            e.ApproveProgram,
            e.ReserveDispatch,
            e.ReviewResults,
            e.GrantStandingAuthority,
            e.RevokeStandingGrant,
        ),
    ):
        previous_workspace = state.workspace_commands.get(command.meta.command_id)
        if previous_workspace is not None:
            return (
                Accepted((), state)
                if previous_workspace == command
                else Refused("command_conflict")
            )
        if isinstance(
            command, (e.ReviewResults, e.GrantStandingAuthority, e.RevokeStandingGrant)
        ):
            action = (
                command.grant.grantor
                if isinstance(command, e.GrantStandingAuthority)
                else command.action
            )
            recorded_trust = state.trust_actions.get(action_key(action))
            if recorded_trust is not None:
                return (
                    Accepted((), state)
                    if action.actor == command.meta.actor
                    and replace(recorded_trust, meta=command.meta) == command
                    else Refused("action_conflict")
                )
        reducer = _Reducer(state, programs)
        event = e.RuntimeEvent(
            command.meta.command_id, 0, e.WorkspaceTransitioned(command)
        )
        try:
            reducer.apply(event)
            return Accepted((event,), reducer.freeze())
        except ReplayError as error:
            return Refused(error.code)
    if command.meta.command_id in state.workspace_commands:
        return Refused("command_conflict")
    previous = state.commands.get(command.meta.command_id)
    if previous is not None:
        return (
            Accepted((), state) if previous == command else Refused("command_conflict")
        )
    reducer = _Reducer(state, programs)
    if isinstance(
        command,
        (
            e.RespondTask,
            e.ReassignTask,
            e.CancelTask,
            e.CorrectResult,
            e.ApproveEffect,
            e.RevokeEffectApproval,
            e.AmendEffect,
        ),
    ):
        try:
            if isinstance(
                command, (e.ApproveEffect, e.RevokeEffectApproval, e.AmendEffect)
            ):
                reducer.effect_observer(command)
                address = state.effects[command.effect].revision.producer.address
            else:
                address = command_address(command)
            _require(address.case_id in state.cases, "unknown_case")
            reducer.observer(address, command.action, command.meta)
        except ReplayError as error:
            return Refused(error.code)
        if action_key(command.action) in state.trust_actions:
            return Refused("action_conflict")
        recorded = state.actions.get(action_key(command.action))
        if recorded is not None:
            return (
                Accepted((), state)
                if same_action(recorded, command)
                else Refused("action_conflict")
            )
    if isinstance(
        command,
        (
            e.BeginEffectAttempt,
            e.MarkEffectUncertain,
            e.ConfirmEffect,
            e.ReconcileEffect,
        ),
    ):
        try:
            reducer.effect_observer(command)
        except ReplayError as error:
            return Refused(error.code)
        progress = state.effects[command.effect].progress
        attempt = (
            progress
            if isinstance(progress, a.Attempted)
            else (
                progress.attempt
                if isinstance(progress, (a.Uncertain, a.Confirmed, a.Reconciled))
                else None
            )
        )
        if attempt is not None and command.attempt_id == attempt.attempt_id:
            if (
                isinstance(command, e.BeginEffectAttempt)
                or isinstance(command, e.MarkEffectUncertain)
                and isinstance(progress, a.Uncertain)
                and command.reason == progress.reason
                or isinstance(command, e.ConfirmEffect)
                and isinstance(progress, a.Confirmed)
                and command.receipt == progress.receipt
                or isinstance(command, e.ReconcileEffect)
                and isinstance(progress, a.Reconciled)
                and command.conclusion == progress.conclusion
            ):
                return Accepted((), state)
    if isinstance(command, e.SupplyRecording):
        recorded_ai = state.recordings.get(command.recording.request.work)
        if recorded_ai is not None:
            return (
                Accepted((), state)
                if recorded_ai == command.recording
                else Refused("recording_conflict")
            )
    decider = _Decider(reducer, command)
    try:
        decider.emit(e.BatchStarted(command))
        decider.meter.charge(reducer.usage.work, reducer.usage.allocations)
    except (ReplayError, _Failure) as error:
        return Refused(error.code)
    case_id = command_case(command)
    if isinstance(
        command,
        (
            e.ApproveEffect,
            e.RevokeEffectApproval,
            e.AmendEffect,
            e.BeginEffectAttempt,
            e.MarkEffectUncertain,
            e.ConfirmEffect,
            e.ReconcileEffect,
        ),
    ):
        try:
            decider.emit(e.EffectTransitioned(command))
            case = reducer.cases[case_id]
            decider.emit(
                e.CaseSettled(
                    case_id, case.status, case.failure, decider.meter.usage()
                ),
                terminal=True,
            )
            decider.emit(e.BatchCompleted(len(decider.events) + 1), terminal=True)
        except (ReplayError, _Failure) as error:
            return Refused(error.code)
        return Accepted(tuple(decider.events), reducer.freeze())
    case = reducer.cases[case_id]
    root = programs.artifacts[case.start.artifact].draft.root
    failure: str | None = None
    try:
        if isinstance(
            command, (e.RespondTask, e.ReassignTask, e.CancelTask, e.CorrectResult)
        ):
            decider.emit(e.HumanActed(command_address(command), command))
        elif isinstance(command, e.SupplyRecording):
            address = command_address(command)
            decider.emit(
                e.RecordingConsumed(
                    address,
                    command.recording,
                    recording_outcome(command.recording, reducer.company(address)),
                )
            )
        if isinstance(command, e.StartSandbox):
            for item in case.start.facts:
                decider.meter.value(item.value)
            result = decider.run(
                e.WorkAddress(case_id, p.node_identity(root)), e.Context(), None
            )
        elif isinstance(command, e.CorrectResult):
            result = decider.run(
                e.WorkAddress(case_id, p.node_identity(root)), e.Context(), None
            )
        else:
            address = command_address(command)
            work = reducer.work[address]
            result = decider.run(address, work.opened.context, work.opened.parent)
            parent = work.opened.parent
            while parent is not None and result is not None:
                parent_work = reducer.work[parent]
                parent_node = reducer.node(parent)
                if (
                    isinstance(parent_node, (p.Each, p.Parallel))
                    and reducer.pending[parent]
                ):
                    result = None
                    break
                result = decider.run(
                    parent, parent_work.opened.context, parent_work.opened.parent
                )
                parent = parent_work.opened.parent
        for address in sorted(reducer.refresh_effects, key=repr):
            if address in reducer.work and reducer.work[address].completed is not None:
                decider.propose(address)
        status = "waiting" if result is None else "succeeded"
    except ReplayError as error:
        return Refused(error.code)
    except _Failure as error:
        if reducer.required_proposals or (
            not isinstance(command, (e.StartSandbox, e.SignalRepeat))
            and error.code
            in {"work_limit", "allocation_limit", "event_limit", "instance_limit"}
        ):
            return Refused(error.code)
        status, failure = "failed", error.code
    try:
        decider.emit(
            e.CaseSettled(case_id, status, failure, decider.meter.usage()),
            terminal=True,
        )
        decider.emit(e.BatchCompleted(len(decider.events) + 1), terminal=True)
    except (ReplayError, _Failure) as error:
        return Refused(error.code)
    return Accepted(tuple(decider.events), reducer.freeze())


def authorize_dispatch(
    state: WorkspaceState,
    effect: a.EffectRef,
    attempt_id: str,
    meta: e.CommandMeta,
    adapter_revision: str,
    programs: ProgramCatalog,
    company: e.CompanyContext,
) -> a.EffectRevision | Refused:
    if meta.expected_revision != state.revision:
        return Refused("stale_revision")
    reservation = state.reservations.get((effect.key, attempt_id))
    if (
        reservation is None
        or reservation.effect != effect
        or reservation.adapter_revision != adapter_revision
    ):
        return Refused("dispatch_reservation")
    reducer = _Reducer(state, programs)
    try:
        reducer.dispatch_permission(effect, attempt_id, meta)
        progress = state.effects[effect].progress
        assert isinstance(progress, (a.Attempted, a.Uncertain))
        attempt = progress if isinstance(progress, a.Attempted) else progress.attempt
        reducer.effect_permission(
            state.effects[effect].revision,
            attempt.approval,
            meta.observed_at,
            company,
        )
    except ReplayError as error:
        return Refused(error.code)
    return state.effects[effect].revision


def authorize_program(state: WorkspaceState, artifact: e.ArtifactPin) -> Refused | None:
    registration = state.registrations.get(artifact)
    if registration is None or registration.missing_checks:
        return Refused("verification_incomplete")
    if artifact not in state.program_approvals:
        return Refused("program_unapproved")
    return None


def authorize_session(
    state: WorkspaceState, command: e.Command, company: e.CompanyContext
) -> Refused | None:
    if isinstance(command, (e.RegisterProgram, e.ApproveProgram)):
        return None
    if isinstance(command, (e.GrantStandingAuthority, e.RevokeStandingGrant)):
        if command.company.company_id != company.company_id:
            return Refused("session_company")
        if not a.has_role(
            company, command.meta.actor, "controller", (), command.meta.observed_at
        ):
            return Refused("session_authority")
        return None
    if isinstance(command, e.ReviewResults):
        case = state.cases.get(command.case_id)
        if (
            case is None
            or case.start.company is None
            or case.start.company.company_id != company.company_id
        ):
            return Refused("session_company")
        if not command.results or any(
            item.work.address.case_id != command.case_id
            or not a.has_role(
                company,
                command.meta.actor,
                "reviewer",
                item.work.address.scope,
                command.meta.observed_at,
            )
            for item in command.results
        ):
            return Refused("session_authority")
        return None
    if isinstance(command, (e.StartSandbox, e.ActivateProgram)):
        role, scope = "workspace_operator", ()
    else:
        if isinstance(command, e.ReserveDispatch):
            case_id = command.effect.key.case_id
            effect = state.effects.get(command.effect)
            if effect is None:
                return Refused("unknown_effect")
            address = effect.revision.producer.address
            role = "effect_executor"
        else:
            case_id = command_case(command)
            if isinstance(
                command,
                (
                    e.ApproveEffect,
                    e.RevokeEffectApproval,
                    e.AmendEffect,
                    e.BeginEffectAttempt,
                    e.MarkEffectUncertain,
                    e.ConfirmEffect,
                    e.ReconcileEffect,
                ),
            ):
                effect = state.effects.get(command.effect)
                if effect is None:
                    return Refused("unknown_effect")
                address = effect.revision.producer.address
                role = (
                    command.action.role
                    if isinstance(
                        command,
                        (e.ApproveEffect, e.RevokeEffectApproval, e.AmendEffect),
                    )
                    else "effect_executor"
                )
            else:
                address = command_address(command)
                role = (
                    command.action.role
                    if isinstance(
                        command,
                        (e.RespondTask, e.ReassignTask, e.CancelTask, e.CorrectResult),
                    )
                    else "workspace_operator"
                )
        case = state.cases.get(case_id)
        if (
            case is None
            or case.start.company is None
            or case.start.company.company_id != company.company_id
        ):
            return Refused("session_company")
        scope = address.scope
    if not a.has_role(
        company, command.meta.actor, role, scope, command.meta.observed_at
    ):
        return Refused("session_authority")
    return None


def authorize_workspace_company(
    state: WorkspaceState, company_id: str
) -> Refused | None:
    if any(
        item.company.company_id != company_id for item in state.registrations.values()
    ) or any(
        case.start.company is not None and case.start.company.company_id != company_id
        for case in state.cases.values()
    ):
        return Refused("session_company")
    return None


def authorize_catalog_read(
    actor: str, company: e.CompanyContext, at: datetime
) -> Refused | None:
    if not any(
        a.has_role(company, actor, role, (), at)
        for role in ("workspace_operator", "program_registrar", "program_approver")
    ):
        return Refused("session_authority")
    return None

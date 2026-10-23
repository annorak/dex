from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from dex.core import authority as a
from dex.core import program as p
from dex.core.language import Usage
from dex.core.program import ExecutionPending, ProgramDraft, VerificationResult


@dataclass(frozen=True)
class EventIdentity:
    event_id: str
    actor: str
    occurred_at: datetime
    observed_at: datetime
    program_id: str
    program_revision: str
    format_version: int = 1


def _check_program_identity(identity: EventIdentity, draft: ProgramDraft) -> None:
    if (identity.program_id, identity.program_revision) != (
        draft.program_id,
        draft.revision,
    ):
        raise ValueError("Event program identity must match its payload")


@dataclass(frozen=True)
class ProgramDrafted:
    identity: EventIdentity
    draft: ProgramDraft

    def __post_init__(self) -> None:
        _check_program_identity(self.identity, self.draft)


@dataclass(frozen=True)
class ProgramStructureChecked:
    identity: EventIdentity
    result: VerificationResult

    def __post_init__(self) -> None:
        if isinstance(self.result, ExecutionPending):
            _check_program_identity(self.identity, self.result.artifact.draft)


type Event = ProgramDrafted | ProgramStructureChecked


@dataclass(frozen=True)
class ArtifactPin:
    program_id: str
    revision: str
    digest: str


@dataclass(frozen=True)
class CommandMeta:
    command_id: str
    actor: str
    occurred_at: datetime
    observed_at: datetime
    expected_revision: int


@dataclass(frozen=True)
class ActivationBounds:
    work: int = 5000000
    allocations: int = 16000000
    instances: int = 20000
    events: int = 100000


@dataclass(frozen=True)
class ScopePart:
    owner: str
    kind: str
    key: str


@dataclass(frozen=True)
class WorkAddress:
    case_id: str
    node_id: str
    scope: tuple[ScopePart, ...] = ()


@dataclass(frozen=True)
class WorkRevision:
    address: WorkAddress
    revision: int


@dataclass(frozen=True)
class RoleMembership:
    actor: str
    role: str
    scope: tuple[ScopePart, ...]
    valid_from: datetime
    valid_until: datetime | None


@dataclass(frozen=True)
class ObservationPermission:
    observer: str
    origin: str
    scope: tuple[ScopePart, ...]
    valid_from: datetime
    valid_until: datetime | None


@dataclass(frozen=True)
class CompanyContext:
    company_id: str
    policy_revision: str
    memberships: tuple[RoleMembership, ...]
    observers: tuple[ObservationPermission, ...]
    record_revision: str
    records: frozenset[p.ResolvedRefValue]


@dataclass(frozen=True)
class HumanAction:
    company_id: str
    origin: str
    action_id: str
    actor: str
    role: str
    decided_at: datetime


@dataclass(frozen=True)
class TaskRef:
    work: WorkRevision
    request_revision: int


@dataclass(frozen=True)
class StartSandbox:
    meta: CommandMeta
    case_id: str
    artifact: ArtifactPin
    facts: tuple[p.NamedValue, ...]
    business_date: date
    bounds: ActivationBounds = ActivationBounds()
    company: CompanyContext | None = None
    review_mode: Literal["review", "historical", "unattended"] = "review"


@dataclass(frozen=True)
class StartCase:
    meta: CommandMeta
    case_id: str
    artifact: ArtifactPin
    facts: tuple[p.NamedValue, ...]
    business_date: date
    delivery_id: str
    evidence_sha256: str
    delivery_sha256: str
    admission_key: str
    sources: tuple[p.SourcePin, ...]
    company: CompanyContext
    bounds: ActivationBounds = ActivationBounds()
    review_mode: Literal["review", "historical", "unattended"] = "review"


@dataclass(frozen=True)
class SignalRepeat:
    meta: CommandMeta
    address: WorkAddress
    iteration: int
    event: str
    bounds: ActivationBounds = ActivationBounds()


@dataclass(frozen=True)
class ActivateProgram:
    meta: CommandMeta
    artifact: ArtifactPin


@dataclass(frozen=True)
class RespondTask:
    meta: CommandMeta
    task: TaskRef
    reviewed: tuple[WorkRevision, ...]
    action: HumanAction
    value: p.Value
    bounds: ActivationBounds = ActivationBounds()


@dataclass(frozen=True)
class ReassignTask:
    meta: CommandMeta
    task: TaskRef
    action: HumanAction
    assignee: str | None
    bounds: ActivationBounds = ActivationBounds()


@dataclass(frozen=True)
class CancelTask:
    meta: CommandMeta
    task: TaskRef
    action: HumanAction
    bounds: ActivationBounds = ActivationBounds()


@dataclass(frozen=True)
class CorrectResult:
    meta: CommandMeta
    work: WorkRevision
    action: HumanAction
    value: p.Value
    bounds: ActivationBounds = ActivationBounds()


type HumanCommand = RespondTask | ReassignTask | CancelTask | CorrectResult


@dataclass(frozen=True)
class ApproveEffect:
    meta: CommandMeta
    effect: a.EffectRef
    action: HumanAction
    bounds: ActivationBounds = ActivationBounds()


@dataclass(frozen=True)
class RevokeEffectApproval:
    meta: CommandMeta
    effect: a.EffectRef
    approval: a.ActionKey
    action: HumanAction
    bounds: ActivationBounds = ActivationBounds()


@dataclass(frozen=True)
class AmendEffect:
    meta: CommandMeta
    effect: a.EffectRef
    original: a.EffectRef
    occurrence: str
    action: HumanAction
    bounds: ActivationBounds = ActivationBounds()


@dataclass(frozen=True)
class BeginEffectAttempt:
    meta: CommandMeta
    effect: a.EffectRef
    attempt_id: str
    bounds: ActivationBounds = ActivationBounds()


@dataclass(frozen=True)
class MarkEffectUncertain:
    meta: CommandMeta
    effect: a.EffectRef
    attempt_id: str
    reason: str
    bounds: ActivationBounds = ActivationBounds()


@dataclass(frozen=True)
class ConfirmEffect:
    meta: CommandMeta
    effect: a.EffectRef
    attempt_id: str
    receipt: a.ExecutionReceipt
    bounds: ActivationBounds = ActivationBounds()


@dataclass(frozen=True)
class ReconcileEffect:
    meta: CommandMeta
    effect: a.EffectRef
    attempt_id: str
    conclusion: a.Reconciliation
    bounds: ActivationBounds = ActivationBounds()


type EffectReview = ApproveEffect | RevokeEffectApproval | AmendEffect
type EffectCommand = (
    EffectReview
    | BeginEffectAttempt
    | MarkEffectUncertain
    | ConfirmEffect
    | ReconcileEffect
)
type ActionCommand = HumanCommand | EffectReview


type RuntimeCommand = (
    StartSandbox
    | StartCase
    | SignalRepeat
    | HumanCommand
    | SupplyRecording
    | EffectCommand
)


@dataclass(frozen=True)
class RegisterProgram:
    meta: CommandMeta
    artifact: ArtifactPin
    missing_checks: tuple[p.MissingCheck, ...]
    company: CompanyContext


@dataclass(frozen=True)
class ApproveProgram:
    meta: CommandMeta
    artifact: ArtifactPin
    company: CompanyContext


@dataclass(frozen=True)
class ReserveDispatch:
    meta: CommandMeta
    effect: a.EffectRef
    attempt_id: str
    adapter_revision: str


@dataclass(frozen=True)
class ReviewResults:
    meta: CommandMeta
    case_id: str
    results: tuple[a.ReviewedResult, ...]
    action: HumanAction


@dataclass(frozen=True)
class GrantStandingAuthority:
    meta: CommandMeta
    grant: a.StandingGrant
    company: CompanyContext


@dataclass(frozen=True)
class RevokeStandingGrant:
    meta: CommandMeta
    grant_id: str
    action: HumanAction
    company: CompanyContext


type TrustCommand = ReviewResults | GrantStandingAuthority | RevokeStandingGrant


type WorkspaceCommand = (
    RegisterProgram | ApproveProgram | ReserveDispatch | TrustCommand
)
type Command = RuntimeCommand | ActivateProgram | WorkspaceCommand


@dataclass(frozen=True)
class WorkspaceTransitioned:
    command: WorkspaceCommand


@dataclass(frozen=True)
class ResultBinding:
    node_id: str
    address: WorkAddress


@dataclass(frozen=True)
class LocalBinding:
    owner: str
    name: str
    value: p.Value


@dataclass(frozen=True)
class Context:
    results: tuple[ResultBinding, ...] = ()
    locals: tuple[LocalBinding, ...] = ()
    controls: tuple[WorkRevision, ...] = ()


@dataclass(frozen=True)
class ConsumedInput:
    name: tuple[str, ...]
    reference: p.Input
    value: p.Value
    producer: WorkAddress | None
    rule_ids: tuple[str, ...] = ()
    rule_scope: tuple[p.NamedValue, ...] = ()
    producer_revision: int | None = None


@dataclass(frozen=True)
class BatchStarted:
    command: RuntimeCommand


@dataclass(frozen=True)
class WorkOpened:
    address: WorkAddress
    parent: WorkAddress | None
    context: Context
    revision: int = 1


@dataclass(frozen=True)
class ControlSelected:
    address: WorkAddress
    selection: p.Value
    dependencies: tuple[WorkAddress, ...]
    inputs: tuple[ConsumedInput, ...]


@dataclass(frozen=True)
class InputBound:
    address: WorkAddress
    consumed: ConsumedInput


@dataclass(frozen=True)
class WorkSucceeded:
    address: WorkAddress
    value: p.Value
    inputs: tuple[ConsumedInput, ...]
    usage: Usage


@dataclass(frozen=True)
class RepeatWaiting:
    address: WorkAddress
    iteration: int
    carried: p.Value
    inputs: tuple[ConsumedInput, ...]


@dataclass(frozen=True)
class CaseSettled:
    case_id: str
    status: str
    failure: str | None
    usage: Usage


@dataclass(frozen=True)
class BatchCompleted:
    count: int


@dataclass(frozen=True)
class Task:
    ref: TaskRef
    company_id: str
    reviewed: tuple[WorkRevision, ...]
    eligible_role: str
    assignee: str | None
    due_at: datetime
    schema: p.Schema
    request: p.Value
    status: Literal["open", "answered", "cancelled", "superseded"] = "open"


@dataclass(frozen=True)
class RecordingRequest:
    work: WorkRevision
    company_id: str
    artifact: ArtifactPin
    inputs: tuple[ConsumedInput, ...]
    prompt_revision: str
    schema: p.Schema
    record_revision: str


@dataclass(frozen=True)
class Recording:
    request: RecordingRequest
    recording_id: str
    model: str
    input_tokens: int
    output_tokens: int
    value: p.Value | None
    failure: str | None


@dataclass(frozen=True)
class SupplyRecording:
    meta: CommandMeta
    recording: Recording
    bounds: ActivationBounds = ActivationBounds()


@dataclass(frozen=True)
class TaskOpened:
    address: WorkAddress
    task: Task


@dataclass(frozen=True)
class HumanActed:
    address: WorkAddress
    command: HumanCommand


@dataclass(frozen=True)
class RecordingRequested:
    address: WorkAddress
    request: RecordingRequest


@dataclass(frozen=True)
class RecordingConsumed:
    address: WorkAddress
    recording: Recording
    outcome: p.Value


@dataclass(frozen=True)
class EffectProposed:
    revision: a.EffectRevision


@dataclass(frozen=True)
class EffectTransitioned:
    command: EffectCommand


type RuntimePayload = (
    BatchStarted
    | WorkspaceTransitioned
    | WorkOpened
    | ControlSelected
    | InputBound
    | WorkSucceeded
    | RepeatWaiting
    | CaseSettled
    | BatchCompleted
    | TaskOpened
    | HumanActed
    | RecordingRequested
    | RecordingConsumed
    | EffectProposed
    | EffectTransitioned
)


@dataclass(frozen=True)
class RuntimeEvent:
    command_id: str
    ordinal: int
    payload: RuntimePayload
    format_version: int = 1

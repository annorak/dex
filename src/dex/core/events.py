from dataclasses import dataclass
from datetime import date, datetime

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
class StartSandbox:
    meta: CommandMeta
    case_id: str
    artifact: ArtifactPin
    facts: tuple[p.NamedValue, ...]
    business_date: date
    bounds: ActivationBounds = ActivationBounds()


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


type Command = StartSandbox | SignalRepeat | ActivateProgram


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


@dataclass(frozen=True)
class ConsumedInput:
    name: tuple[str, ...]
    reference: p.Input
    value: p.Value
    producer: WorkAddress | None
    rule_ids: tuple[str, ...] = ()
    rule_scope: tuple[p.NamedValue, ...] = ()


@dataclass(frozen=True)
class BatchStarted:
    command: StartSandbox | SignalRepeat


@dataclass(frozen=True)
class WorkOpened:
    address: WorkAddress
    parent: WorkAddress | None
    context: Context


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


type RuntimePayload = (
    BatchStarted
    | WorkOpened
    | ControlSelected
    | InputBound
    | WorkSucceeded
    | RepeatWaiting
    | CaseSettled
    | BatchCompleted
)


@dataclass(frozen=True)
class RuntimeEvent:
    command_id: str
    ordinal: int
    payload: RuntimePayload
    format_version: int = 1

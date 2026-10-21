from dataclasses import dataclass
from datetime import datetime

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

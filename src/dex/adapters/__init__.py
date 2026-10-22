from dataclasses import dataclass
from typing import Protocol

from dex.core import authority as a


@dataclass(frozen=True)
class DispatchRequest:
    operation_id: str
    revision: a.EffectRevision
    attempt_id: str
    adapter_revision: str


@dataclass(frozen=True)
class Pending:
    evidence: str


type Outcome = a.Applied | a.FencedNotApplied | Pending


class Adapter(Protocol):
    @property
    def revision(self) -> str: ...

    def execute(self, request: DispatchRequest) -> Outcome:
        """Bounded admission with atomic operation deduplication and payload binding."""
        ...

    def reconcile(self, request: DispatchRequest) -> Outcome:
        """A fence must prevent every earlier delivery from subsequently committing."""
        ...

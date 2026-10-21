from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from dex.core import program as p

if TYPE_CHECKING:
    from dex.core import events as e


type ActionKey = tuple[str, str, str]


@dataclass(frozen=True)
class OperationScope:
    parts: tuple[p.NamedValue, ...]


@dataclass(frozen=True)
class EffectKey:
    company_id: str
    case_id: str
    scope: OperationScope
    operation: str
    occurrence: str


@dataclass(frozen=True)
class EffectRef:
    key: EffectKey
    revision: int


@dataclass(frozen=True)
class EffectRevision:
    ref: EffectRef
    producer: e.WorkRevision
    change_id: str
    inputs: tuple[e.ConsumedInput, ...]
    dependencies: tuple[e.WorkRevision, ...]
    decisions: tuple[ActionKey, ...]
    payload: p.Value
    artifact: e.ArtifactPin
    behavior_id: str
    amendment_of: EffectRef | None


@dataclass(frozen=True)
class ExactApproval:
    effect: EffectRef
    action: e.HumanAction


@dataclass(frozen=True)
class Proposed:
    pass


@dataclass(frozen=True)
class Approved:
    approval: ExactApproval


@dataclass(frozen=True)
class Attempted:
    approval: ExactApproval
    attempt_id: str


@dataclass(frozen=True)
class Uncertain:
    attempt: Attempted
    reason: str


@dataclass(frozen=True)
class ExecutionReceipt:
    adapter_revision: str
    external_id: str
    evidence: str


@dataclass(frozen=True)
class Confirmed:
    attempt: Attempted
    receipt: ExecutionReceipt


@dataclass(frozen=True)
class Applied:
    receipt: ExecutionReceipt


@dataclass(frozen=True)
class FencedNotApplied:
    fence_evidence: str


type Reconciliation = Applied | FencedNotApplied


@dataclass(frozen=True)
class Reconciled:
    attempt: Attempted
    conclusion: Reconciliation


type Progress = Proposed | Approved | Attempted | Uncertain | Confirmed | Reconciled


@dataclass(frozen=True)
class Effect:
    revision: EffectRevision
    progress: Progress
    superseded_by: EffectRef | None = None


@dataclass(frozen=True)
class StandingGrant:
    grant_id: str
    grantor: e.HumanAction
    scope: OperationScope
    operations: tuple[str, ...]
    behaviors: tuple[str, ...]
    amount_limit_cents: int
    conditions: tuple[p.NamedValue, ...]
    valid_from: datetime
    valid_until: datetime | None


@dataclass(frozen=True)
class StandingGrantRecorded:
    grant: StandingGrant


@dataclass(frozen=True)
class StandingGrantRevoked:
    grant_id: str
    action: e.HumanAction


@dataclass(frozen=True)
class AuthorityAllowed:
    pass


@dataclass(frozen=True)
class AuthorityRefused:
    code: str


def has_role(
    policy: e.CompanyContext,
    actor: str,
    role: str,
    scope: tuple[e.ScopePart, ...],
    at: datetime,
) -> bool:
    return any(
        item.actor == actor
        and item.role == role
        and scope[: len(item.scope)] == item.scope
        and item.valid_from <= at
        and (item.valid_until is None or at < item.valid_until)
        for item in policy.memberships
    )


def validate_exact_approval(
    revision: EffectRevision,
    approval: ExactApproval,
    policy: e.CompanyContext,
    at: datetime,
    is_revoked: bool,
) -> AuthorityAllowed | AuthorityRefused:
    action = approval.action
    if approval.effect != revision.ref:
        return AuthorityRefused("approval_revision")
    if is_revoked:
        return AuthorityRefused("approval_revoked")
    if action.decided_at > at:
        return AuthorityRefused("approval_time")
    if (
        action.company_id != policy.company_id
        or action.company_id != revision.ref.key.company_id
    ):
        return AuthorityRefused("company_mismatch")
    if action.role != "effect_approver" or not all(
        has_role(
            policy,
            action.actor,
            "effect_approver",
            revision.producer.address.scope,
            instant,
        )
        for instant in (action.decided_at, at)
    ):
        return AuthorityRefused("effect_authority")
    return AuthorityAllowed()

from __future__ import annotations

import ast
from dataclasses import dataclass, replace
from datetime import datetime
from hashlib import sha256
from typing import TYPE_CHECKING, Literal

from dex.core import program as p

if TYPE_CHECKING:
    from dex.core import events as e


type ActionKey = tuple[str, str, str]
TRUST_THRESHOLD = 300
SAMPLE_INTERVAL = 20


@dataclass(frozen=True)
class BehaviorKey:
    company_id: str
    behavior_id: str
    applicability: str


@dataclass(frozen=True)
class ReviewKey:
    company_id: str
    case_id: str
    behavior_id: str


@dataclass(frozen=True)
class TrustCount:
    clean: int = 0
    generation: int = 0


@dataclass(frozen=True)
class ReviewedResult:
    work: e.WorkRevision
    outcome: Literal["clean", "mistake", "unresolved"]


@dataclass(frozen=True)
class ReviewEvidence:
    behavior: BehaviorKey
    generation: int
    effects: tuple[EffectRef, ...]
    outcome: Literal["clean", "mistake", "pending"]
    work: frozenset[e.WorkRevision]
    mistakes: frozenset[BehaviorKey]


@dataclass(frozen=True)
class CaseSample:
    ordinal: int | None
    requires_review: bool


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
class GrantAuthority:
    grant_id: str


type EffectAuthority = ExactApproval | GrantAuthority


@dataclass(frozen=True)
class Proposed:
    pass


@dataclass(frozen=True)
class Approved:
    approval: ExactApproval


@dataclass(frozen=True)
class Attempted:
    approval: EffectAuthority
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
    behaviors: tuple[BehaviorKey, ...]
    amount_limit_cents: int
    conditions: tuple[p.NamedValue, ...]
    valid_from: datetime
    valid_until: datetime | None


def behavior_signature(
    artifact: p.StructuralArtifact, node: p.CodeStep | p.AiStep | p.HumanStep
) -> str:
    metadata = replace(node.metadata, intent="", citations=())
    normalized = replace(node, metadata=metadata)
    functions = {item.function_id: item for item in artifact.draft.functions}
    pending = [node.function_id] if isinstance(node, p.CodeStep) else []
    bodies: dict[str, str] = {}
    while pending:
        name = pending.pop()
        if name in bodies:
            continue
        function = functions[name]
        tree = ast.parse(function.body.source)
        bodies[name] = repr(
            (function.inputs, function.output, ast.dump(tree, include_attributes=False))
        )
        pending.extend(
            item.func.id
            for item in ast.walk(tree)
            if isinstance(item, ast.Call)
            and isinstance(item.func, ast.Name)
            and item.func.id in functions
        )
    return sha256(repr((normalized, sorted(bodies.items()))).encode()).hexdigest()


def amount_cents(value: p.Value) -> int:
    if isinstance(value, p.MoneyValue):
        return abs(value.cents)
    if isinstance(value, (p.PresentValue, p.TaggedValue)):
        return amount_cents(value.value)
    if isinstance(value, p.RecordValue):
        return sum(amount_cents(item.value) for item in value.fields)
    if isinstance(value, p.KeyedValue):
        return sum(amount_cents(item.value) for item in value.entries)
    return 0


def validate_grant(
    revision: EffectRevision,
    grant: StandingGrant,
    policy: e.CompanyContext,
    at: datetime,
    behaviors: tuple[BehaviorKey, ...],
    is_revoked: bool,
) -> AuthorityAllowed | AuthorityRefused:
    if is_revoked:
        return AuthorityRefused("grant_revoked")
    if (
        grant.grantor.company_id != policy.company_id
        or revision.ref.key.company_id != policy.company_id
        or any(key.company_id != policy.company_id for key in behaviors)
    ):
        return AuthorityRefused("company_mismatch")
    if not grant.valid_from <= at or (
        grant.valid_until is not None and at >= grant.valid_until
    ):
        return AuthorityRefused("grant_time")
    if grant.grantor.decided_at > at or not all(
        has_role(
            policy,
            grant.grantor.actor,
            "controller",
            revision.producer.address.scope,
            instant,
        )
        for instant in (grant.grantor.decided_at, at)
    ):
        return AuthorityRefused("grant_authority")
    if (
        revision.ref.key.scope != grant.scope
        or revision.ref.key.operation not in grant.operations
        or not set(behaviors) <= set(grant.behaviors)
    ):
        return AuthorityRefused("grant_scope")
    if amount_cents(revision.payload) > grant.amount_limit_cents:
        return AuthorityRefused("grant_amount")
    conditions = {
        item.name[-1]: item.value
        for item in revision.inputs
        if len(item.name) == 4 and item.name[2] == "precondition"
    }
    if any(conditions.get(item.name) != item.value for item in grant.conditions):
        return AuthorityRefused("grant_conditions")
    return AuthorityAllowed()


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

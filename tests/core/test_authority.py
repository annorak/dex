from dataclasses import replace
from datetime import timedelta

import pytest
from test_continuations import action
from test_effects import POLICY, Run
from test_runtime import NOW

from dex.core import authority as a
from dex.core import events as e


@pytest.mark.parametrize(
    "mutation,expected",
    [
        ("none", None),
        ("revision", "approval_revision"),
        ("company", "company_mismatch"),
        ("actor", "effect_authority"),
        ("business", "effect_authority"),
        ("program", "effect_authority"),
        ("scope", "effect_authority"),
        ("future", "effect_authority"),
        ("future_approval", "approval_time"),
        ("expired", "effect_authority"),
        ("revoked", "approval_revoked"),
    ],
)
def test_only_exact_current_eligible_approval_confers_authority(
    mutation: str, expected: str | None
) -> None:
    run = Run()
    revision = run.state.effects[run.ref()].revision
    approval = a.ExactApproval(revision.ref, action("approval", role="effect_approver"))
    policy = POLICY
    at = NOW
    if mutation == "revision":
        approval = replace(approval, effect=replace(approval.effect, revision=2))
    elif mutation == "company":
        approval = replace(
            approval, action=replace(approval.action, company_id="foreign")
        )
    elif mutation == "actor":
        approval = replace(approval, action=replace(approval.action, actor="intruder"))
    elif mutation in {"business", "program"}:
        role = "reviewer" if mutation == "business" else "program_approver"
        approval = replace(approval, action=replace(approval.action, role=role))
    elif mutation == "scope":
        policy = replace(
            policy,
            memberships=tuple(
                replace(item, scope=(e.ScopePart("other", "each", "other"),))
                for item in policy.memberships
            ),
        )
    elif mutation == "future":
        policy = replace(
            policy,
            memberships=tuple(
                replace(item, valid_from=NOW + timedelta(days=1))
                for item in policy.memberships
            ),
        )
    elif mutation == "future_approval":
        approval = replace(
            approval,
            action=replace(approval.action, decided_at=NOW + timedelta(hours=1)),
        )
    elif mutation == "expired":
        policy = replace(
            policy,
            memberships=tuple(
                replace(item, valid_until=NOW + timedelta(hours=1))
                for item in policy.memberships
            ),
        )
        at += timedelta(hours=2)
    result = a.validate_exact_approval(
        revision, approval, policy, at, mutation == "revoked"
    )
    assert result == (
        a.AuthorityAllowed() if expected is None else a.AuthorityRefused(expected)
    )

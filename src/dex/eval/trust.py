import json
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

from dex import codec
from dex.core import authority as a
from dex.core import events as e
from dex.core import program as p
from dex.core import runtime as r
from dex.eval.recovery import run_workspace_cli
from dex.eval.trust_fixture import NOW, POLICY, TrustFixture, program
from dex.workspace import LocalSession, Workspace


def _ordinary_cli(fixture: TrustFixture, out: Path, ref: a.EffectRef) -> dict[str, Any]:
    session = out / "session.json"
    session.write_text(
        json.dumps(
            {
                "format": "dex-local-session-1",
                "actor": "operator",
                "company": json.loads(codec.dumps(POLICY)),
            }
        )
    )
    approval = e.ApproveEffect(
        fixture.meta("cli-approval"),
        ref,
        replace(
            fixture.action("cli-approval", "effect_approver"), actor="source-impostor"
        ),
    )
    request = {
        "format": "dex-workspace-command-1",
        "id": "cli-approval",
        "expected_revision": fixture.state.revision,
        "kind": "apply",
        "command": json.loads(codec.dumps(approval)),
    }
    status, accepted = run_workspace_cli(
        out, "success-approval", request, session, fixture.path
    )
    rejected_status, refused = run_workspace_cli(
        out, "rejection-stale", request, session, fixture.path
    )
    fixture.workspace.refresh()
    recorded = fixture.state.actions[(POLICY.company_id, "dex", "cli-approval")]
    return {
        "cli_approval": status == 0 and accepted["actor"] == "operator",
        "cli_stale_rejected": rejected_status == 1
        and refused["failure"] == "stale_revision",
        "session_actor_bound": recorded.action.actor == "operator",
    }


def _qualified(fixture: TrustFixture, name: str) -> dict[str, Any]:
    actual: dict[str, Any] = {}
    fixture.train(299)
    actual["before"] = [fixture.count("calculate"), fixture.count("write")]
    fixture.start("three-hundred")
    ref = fixture.ref("three-hundred")
    fixture.approve(ref)
    actual["pending"] = [fixture.count("calculate"), fixture.count("write")]
    assert isinstance(fixture.dispatch(ref), r.Accepted)
    actual["qualified"] = [fixture.count("calculate"), fixture.count("write")]
    fixture.start("no-grant")
    ref = fixture.ref("no-grant")
    before = fixture.state
    actual["no_grant_failure"] = _failure(fixture.dispatch(ref))
    actual["no_grant_unchanged"] = fixture.state == before
    if name == "trust-no-grant":
        actual.update(_ordinary_cli(fixture, fixture.path.parent, ref))
    return actual


def _failure(result: r.Accepted | r.Refused) -> str | None:
    return result.code if isinstance(result, r.Refused) else None


def _attribution(fixture: TrustFixture) -> dict[str, Any]:
    fixture.train(2)
    fixture.review("training-1", outcome="mistake")
    fixture.review("training-1")
    return {
        "wrong_producer": fixture.count("calculate"),
        "correct_producer": fixture.count("write"),
        "reviewed_cases": len(fixture.state.reviews),
    }


def _pending(fixture: TrustFixture) -> dict[str, Any]:
    fixture.start("pending")
    ref = fixture.ref("pending")
    fixture.approve(ref)
    pending = fixture.count("write")
    fixture.adapter.mode = "delayed"
    assert isinstance(fixture.dispatch(ref), r.Accepted)
    progress = fixture.state.effects[ref].progress
    assert isinstance(progress, a.Uncertain)
    uncertain = fixture.count("write")
    fixture.adapter.finish(progress.attempt.attempt_id)
    assert isinstance(fixture.workspace.reconcile(ref, NOW), r.Accepted)
    return {
        "pending_credit": pending,
        "uncertain_credit": uncertain,
        "confirmed_credit": fixture.count("write"),
        "writes": fixture.adapter.writes(),
    }


def _redelivery(fixture: TrustFixture) -> dict[str, Any]:
    fixture.start("case")
    command = fixture.review("case")
    before = fixture.state.revision
    fixture.execute(replace(command, meta=fixture.meta("redelivery")))
    duplicate_events = fixture.state.revision - before
    fixture.review("case")
    address = e.WorkAddress("case", "calculate")
    fixture.execute(
        e.CorrectResult(
            fixture.meta("correct"),
            e.WorkRevision(address, 1),
            fixture.action("correct", "corrector"),
            p.MoneyValue(2),
        )
    )
    fixture.review("case")
    for mode in ("historical", "unattended"):
        fixture.start(mode, mode=mode)
        fixture.review(mode)
    return {
        "redelivery_events": duplicate_events,
        "after_correction": fixture.count("calculate"),
        "excluded_modes_credit": fixture.count("write"),
    }


def _repair(fixture: TrustFixture) -> dict[str, Any]:
    fixture.train(2)
    source = program()
    repaired = replace(
        source,
        revision="repair",
        functions=(
            replace(
                source.functions[0],
                body=p.FunctionBody("restricted-1", "return (value)"),
            ),
        ),
    )
    pin = fixture.register(repaired)
    fixture.start("repaired", pin=pin)
    fixture.approve(fixture.ref("repaired"))
    assert isinstance(fixture.dispatch(fixture.ref("repaired")), r.Accepted)
    retained = [fixture.count("calculate"), fixture.count("write")]
    assert isinstance(source.root, p.Sequence)
    calculate = source.root.children[0]
    assert isinstance(calculate, p.CodeStep)
    changed = replace(
        source,
        revision="changed",
        root=replace(
            source.root,
            children=(
                replace(
                    calculate,
                    metadata=replace(
                        calculate.metadata,
                        inputs=(
                            p.Binding(
                                "value", p.Scalar.MONEY, p.Literal(p.MoneyValue(3))
                            ),
                        ),
                    ),
                ),
                source.root.children[1],
            ),
        ),
    )
    pin = fixture.register(changed)
    fixture.start("changed", pin=pin)
    fixture.review("changed")
    calculation_counts = sorted(
        count.clean
        for key, count in fixture.state.trust.items()
        if key.behavior_id == "calculate-1"
    )
    return {
        "repair_counts": retained,
        "changed_behavior_counts": calculation_counts,
        "unaffected_write": fixture.count("write"),
    }


def _boundaries(fixture: TrustFixture) -> dict[str, Any]:
    fixture.train()
    grant = fixture.grant()
    fixture.start("limit", 500_000)
    allowed = _failure(fixture.dispatch(fixture.ref("limit")))
    failures: dict[str, str | None] = {}
    for name, amount, ready in (("above", 500_001, True), ("hold", 1, False)):
        fixture.start(name, amount, ready)
        failures[name] = _failure(fixture.dispatch(fixture.ref(name)))
    fixture.start("untrusted")
    fixture.review("untrusted", outcome="mistake")
    failures["untrusted"] = _failure(fixture.dispatch(fixture.ref("untrusted")))
    foreign = replace(
        grant,
        grant_id="foreign",
        grantor=replace(grant.grantor, action_id="foreign"),
        behaviors=tuple(
            replace(key, company_id="other-company") for key in grant.behaviors
        ),
    )
    failures["foreign"] = _failure(
        fixture.workspace.execute(
            e.GrantStandingAuthority(fixture.meta("foreign"), foreign, POLICY)
        )
    )
    return {
        "limit_failure": allowed,
        "failures": failures,
        "writes": fixture.adapter.writes(),
    }


def _revocation(fixture: TrustFixture) -> dict[str, Any]:
    fixture.train()
    fixture.grant()
    fixture.start("prior")
    ref = fixture.ref("prior")
    fixture.adapter.mode = "delayed"
    assert isinstance(fixture.dispatch(ref), r.Accepted)
    progress = fixture.state.effects[ref].progress
    assert isinstance(progress, a.Uncertain)
    fixture.revoke()
    assert fixture.reopen()
    fixture.adapter.finish(progress.attempt.attempt_id)
    assert isinstance(fixture.workspace.reconcile(ref, NOW), r.Accepted)
    fixture.start("new")
    return {
        "prior_reconciled": fixture.state.confirmed_effects[ref.key] == ref,
        "new_dispatch_failure": _failure(fixture.dispatch(fixture.ref("new"))),
        "grant_revoked": "grant" in fixture.state.revoked_grants,
        "writes": fixture.adapter.writes(),
        "unattended_credit": fixture.count("write"),
    }


def _sampling(fixture: TrustFixture) -> dict[str, Any]:
    fixture.train(later=True)
    fixture.grant()
    for index in range(1, 20):
        fixture.start("eligible-" + str(index), mode="unattended")
    fixture.start("already-review-required", 500_001)
    assert fixture.reopen()
    fixture.start("twentieth", mode="unattended")
    first = fixture.ref("twentieth")
    first_failure = _failure(fixture.dispatch(first))
    fixture.approve(first)
    assert isinstance(fixture.dispatch(first), r.Accepted)
    fixture.answer("twentieth")
    assert fixture.reopen()
    later = fixture.ref("twentieth", "later")
    later_failure = _failure(fixture.dispatch(later))
    fixture.approve(later)
    assert isinstance(fixture.dispatch(later), r.Accepted)
    sample = fixture.state.case_samples["twentieth"]
    fixture.review("twentieth", outcome="mistake")
    assert fixture.reopen()
    fixture.start("after-sampled-mistake", mode="unattended")
    return {
        "ordinal": sample.ordinal,
        "sampled": sample.requires_review,
        "first_failure": first_failure,
        "later_failure": later_failure,
        "company_ordinal": fixture.state.sampling_ordinals[POLICY.company_id],
        "already_required_ordinal": fixture.state.case_samples[
            "already-review-required"
        ].ordinal,
        "human_credit": fixture.count("decision"),
        "sampled_mistake_count": fixture.count("calculate"),
        "after_mistake_failure": _failure(
            fixture.dispatch(fixture.ref("after-sampled-mistake"))
        ),
    }


def _human(fixture: TrustFixture) -> dict[str, Any]:
    fixture.train(later=True)
    grant = fixture.grant()
    fixture.start("waiting")
    task = next(
        task
        for task in fixture.state.tasks.values()
        if task.ref.work.address.case_id == "waiting"
    )
    before = fixture.state
    impossible = e.WorkAddress("waiting", "later")
    foreign = replace(POLICY, company_id="incompatible-company")
    foreign_path = fixture.path.parent / "foreign.db"
    with Workspace(foreign_path, LocalSession("operator", foreign), {}) as workspace:
        result = workspace.execute(
            e.GrantStandingAuthority(
                e.CommandMeta("source-grant", "impostor", NOW, NOW, 0),
                grant,
                POLICY,
            )
        )
        foreign_failure = _failure(result)
        foreign_count = len(workspace.state.trust)
    return {
        "human_open": task.status == "open",
        "later_uncompleted": impossible not in before.work
        or before.work[impossible].completed is None,
        "human_credit": fixture.count("decision"),
        "foreign_failure": foreign_failure,
        "foreign_trust_entries": foreign_count,
    }


def run_trust(source: bytes, out: Path) -> int:
    raw: object = json.loads(source)
    if not isinstance(raw, dict):
        raise ValueError("trust_scenario")
    request = cast(dict[str, Any], raw)
    if (
        set(request) != {"format", "scenario_id", "expected"}
        or not isinstance(request["expected"], dict)
        or not isinstance(request["scenario_id"], str)
    ):
        raise ValueError("trust_scenario")
    name = request["scenario_id"]
    if name == "trust-size-10000":
        from dex.eval.trust_size import run_size

        out.mkdir(parents=True, exist_ok=False)
        actual = run_size(out)
        expected = cast(dict[str, Any], request["expected"])
        matches = {key: actual.get(key) == value for key, value in expected.items()}
        (out / "actual.json").write_text(json.dumps(actual, sort_keys=True))
        (out / "expected.json").write_text(
            json.dumps({"expected": expected, "matches": matches}, sort_keys=True)
        )
        print(json.dumps(actual, sort_keys=True))
        return 0 if all(matches.values()) else 1
    scenarios = {
        "trust-299-300",
        "trust-no-grant",
        "trust-credit-attribution",
        "trust-pending-write",
        "trust-redelivery-replay",
        "trust-change-repair",
        "trust-grant-boundaries",
        "trust-revocation",
        "trust-twentieth-restart",
        "trust-human-and-pooling",
    }
    if name not in scenarios:
        raise ValueError("trust_scenario")
    out.mkdir(parents=True, exist_ok=False)
    fixture = TrustFixture(
        out, later=name in {"trust-twentieth-restart", "trust-human-and-pooling"}
    )
    try:
        if name in {"trust-299-300", "trust-no-grant"}:
            actual = _qualified(fixture, name)
        else:
            run = {
                "trust-credit-attribution": _attribution,
                "trust-pending-write": _pending,
                "trust-redelivery-replay": _redelivery,
                "trust-change-repair": _repair,
                "trust-grant-boundaries": _boundaries,
                "trust-revocation": _revocation,
                "trust-twentieth-restart": _sampling,
                "trust-human-and-pooling": _human,
            }[name]
            actual = run(fixture)
        actual["reopen_equal"] = fixture.reopen()
        actual["revision"] = fixture.state.revision
        actual["normal_activation_failure"] = _failure(
            r.authorize_program(fixture.state, fixture.pin)
            or r.Accepted((), fixture.state)
        )
        expected = cast(dict[str, Any], request["expected"])
        matches = {key: actual.get(key) == value for key, value in expected.items()}
        (out / "actual.json").write_text(json.dumps(actual, sort_keys=True))
        (out / "expected.json").write_text(
            json.dumps(
                {"expected": request["expected"], "matches": matches}, sort_keys=True
            )
        )
        print(json.dumps(actual, sort_keys=True))
        return 0 if all(matches.values()) else 1
    finally:
        fixture.workspace.close()

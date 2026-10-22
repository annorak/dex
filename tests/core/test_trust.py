from dataclasses import replace
from datetime import timedelta
from typing import Literal
from unittest.mock import patch

import pytest
from test_runtime import NOW, catalog, code, draft, identity

from dex import codec
from dex.core import authority as a
from dex.core import events as e
from dex.core import program as p
from dex.core import runtime as r

POLICY = e.CompanyContext(
    "company-a",
    "policy-1",
    tuple(
        e.RoleMembership("operator", role, (), NOW - timedelta(days=1), None)
        for role in (
            "reviewer",
            "effect_approver",
            "effect_executor",
            "controller",
            "corrector",
        )
    ),
    (),
    "records-1",
    frozenset(),
)
RECEIPT = a.ExecutionReceipt("adapter-1", "effect", "confirmed exact payload")


def program() -> p.ProgramDraft:
    calculate = code("calculate", p.ProgramInputRef("amount"), p.Scalar.MONEY)
    write = code("write", p.ResultRef("calculate"), p.Scalar.MONEY)
    change = p.ChangeDeclaration(
        "publish",
        "publish",
        p.Export(p.Scalar.MONEY, p.ResultRef("write")),
        (p.Binding("record", p.Scalar.TEXT, p.Literal(p.TextValue("record"))),),
        p.Literal(p.TextValue("once")),
        (p.Binding("ready", p.Scalar.BOOLEAN, p.ProgramInputRef("ready")),),
    )
    write = replace(write, metadata=replace(write.metadata, changes=(change,)))
    return draft(
        p.Sequence(
            "sequence",
            (calculate, write),
            p.Export(p.Scalar.MONEY, p.ResultRef("write")),
        ),
        (identity(p.Scalar.MONEY, p.MoneyValue(1)),),
        (p.Field("amount", p.Scalar.MONEY), p.Field("ready", p.Scalar.BOOLEAN)),
    )


class TrustRun:
    def __init__(self, source: p.ProgramDraft | None = None) -> None:
        self.catalog = catalog(program() if source is None else source)
        self.state = r.rebuild((), self.catalog)
        self.events: tuple[e.RuntimeEvent, ...] = ()

    def meta(self, name: str) -> e.CommandMeta:
        return e.CommandMeta(name, "operator", NOW, NOW, self.state.revision)

    def action(
        self, name: str, role: str = "reviewer", company: str = "company-a"
    ) -> e.HumanAction:
        return e.HumanAction(company, "dex", name, "operator", role, NOW)

    def apply(self, command: e.Command) -> r.Accepted:
        result = r.decide(self.state, command, self.catalog)
        assert isinstance(result, r.Accepted), result
        self.state = result.state
        self.events += result.events
        return result

    def start(
        self,
        name: str,
        amount: int = 1,
        ready: bool = True,
        mode: Literal["review", "historical", "unattended"] = "review",
        company: e.CompanyContext = POLICY,
        pin: e.ArtifactPin | None = None,
    ) -> a.EffectRef:
        self.apply(
            e.StartSandbox(
                self.meta("start/" + name),
                name,
                self.catalog.entries[0].pin if pin is None else pin,
                (
                    p.NamedValue("amount", p.MoneyValue(amount)),
                    p.NamedValue("ready", p.BoolValue(ready)),
                ),
                NOW.date(),
                company=company,
                review_mode=mode,
            )
        )
        return next(
            ref
            for ref in self.state.current_effects.values()
            if ref.key.case_id == name
        )

    def approve(self, ref: a.EffectRef) -> None:
        name = "approve/" + ref.key.case_id
        self.apply(
            e.ApproveEffect(
                self.meta(name),
                ref,
                self.action(name, "effect_approver", ref.key.company_id),
            )
        )

    def confirm(self, ref: a.EffectRef) -> None:
        name = "attempt/" + ref.key.case_id
        self.apply(e.BeginEffectAttempt(self.meta(name), ref, name))
        self.apply(e.ConfirmEffect(self.meta("confirm/" + name), ref, name, RECEIPT))

    def review(
        self,
        case: str,
        outcome: Literal["clean", "mistake", "unresolved"] = "clean",
        node: str = "calculate",
    ) -> e.ReviewResults:
        address = e.WorkAddress(case, node)
        name = f"review/{case}/{node}/{outcome}/{self.state.revision}"
        company = self.state.cases[case].start.company
        assert company is not None
        command = e.ReviewResults(
            self.meta(name),
            case,
            (
                a.ReviewedResult(
                    e.WorkRevision(address, self.state.work[address].opened.revision),
                    outcome,
                ),
            ),
            self.action(name, company=company.company_id),
        )
        self.apply(command)
        return command

    def count(self, node: str, company: str = "company-a") -> int:
        return sum(
            value.clean
            for key, value in self.state.trust.items()
            if key.behavior_id == "behavior-" + node and key.company_id == company
        )

    def train(self, count: int = 300) -> None:
        for index in range(count):
            ref = self.start("training-" + str(index))
            self.approve(ref)
            self.confirm(ref)

    def grant(self, name: str = "grant") -> a.StandingGrant:
        grant = a.StandingGrant(
            name,
            self.action(name, "controller"),
            a.OperationScope((p.NamedValue("record", p.TextValue("record")),)),
            ("publish",),
            tuple(self.state.trust),
            500_000,
            (p.NamedValue("ready", p.BoolValue(True)),),
            NOW,
            None,
        )
        self.apply(e.GrantStandingAuthority(self.meta(name), grant, POLICY))
        return grant

    def replay(self) -> None:
        with (
            patch(
                "dex.core.language.execute_function",
                side_effect=AssertionError("interpretation"),
            ),
            patch("builtins.open", side_effect=AssertionError("I/O")),
        ):
            assert r.rebuild(self.events, self.catalog) == self.state


def test_exact_299_300_qualification_never_grants_authority() -> None:
    run = TrustRun()
    run.train(299)
    assert run.count("calculate") == run.count("write") == 299
    ref = run.start("last")
    run.approve(ref)
    assert run.count("calculate") == 300
    assert run.count("write") == 299
    run.confirm(ref)
    assert run.count("write") == 300
    unapproved = run.start("no-grant")
    assert r.decide(
        run.state,
        e.BeginEffectAttempt(run.meta("blocked"), unapproved, "blocked"),
        run.catalog,
    ) == r.Refused("exact_approval_required")
    assert not run.state.grants
    run.replay()


def test_clean_attribution_and_explicit_mistake_only_reset_wrong_producer() -> None:
    run = TrustRun()
    run.train(2)
    run.review("training-1", "mistake", "calculate")
    assert run.count("calculate") == 0
    assert run.count("write") == 2
    run.review("training-1", "clean", "calculate")
    assert run.count("calculate") == 0
    run.replay()


def test_pending_uncertain_and_late_confirmation_cannot_cross_reset() -> None:
    run = TrustRun()
    ref = run.start("pending")
    run.approve(ref)
    run.apply(e.BeginEffectAttempt(run.meta("begin"), ref, "attempt"))
    run.apply(e.MarkEffectUncertain(run.meta("unknown"), ref, "attempt", "pending"))
    assert run.count("write") == 0
    other = run.start("mistake")
    run.approve(other)
    run.review("mistake", "mistake", "write")
    run.apply(
        e.ReconcileEffect(run.meta("reconcile"), ref, "attempt", a.Applied(RECEIPT))
    )
    assert run.count("write") == 0
    assert run.state.confirmed_effects[ref.key] == ref
    run.replay()


@pytest.mark.parametrize("mode", ["review", "historical", "unattended"])
def test_only_reviewed_live_resolved_results_earn_once(
    mode: Literal["review", "historical", "unattended"],
) -> None:
    run = TrustRun()
    run.start("case", mode=mode)
    assert run.count("calculate") == 0
    run.review("case", "unresolved")
    assert run.count("calculate") == 0
    command = run.review("case")
    expected = 1 if mode == "review" else 0
    assert run.count("calculate") == expected
    result = run.apply(replace(command, meta=run.meta("redelivery")))
    assert result.events == ()
    run.review("case")
    assert run.count("calculate") == expected
    run.replay()


def test_correction_resets_and_cannot_credit_corrected_case_twice() -> None:
    run = TrustRun()
    run.train(2)
    address = e.WorkAddress("training-1", "calculate")
    run.apply(
        e.CorrectResult(
            run.meta("correct"),
            e.WorkRevision(address, 1),
            run.action("correct", "corrector"),
            p.MoneyValue(2),
        )
    )
    assert run.count("calculate") == 0
    assert run.count("write") == 2
    run.review("training-1")
    assert run.count("calculate") == 0
    run.replay()


def test_preserving_checked_repair_retains_identity_but_changed_logic_does_not() -> (
    None
):
    source = program()
    run = TrustRun(source)
    run.train(1)
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
    assert isinstance(source.root, p.Sequence)
    calculate, write = source.root.children
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
                                "value", p.Scalar.MONEY, p.Literal(p.MoneyValue(2))
                            ),
                        ),
                    ),
                ),
                write,
            ),
        ),
    )
    repair_catalog, changed_catalog = catalog(repaired), catalog(changed)
    run.catalog = r.ProgramCatalog(
        (*run.catalog.entries, *repair_catalog.entries, *changed_catalog.entries)
    )
    run.start("repair", pin=repair_catalog.entries[0].pin)
    run.review("repair")
    assert run.count("calculate") == 2
    run.start("changed", pin=changed_catalog.entries[0].pin)
    run.review("changed")
    assert sorted(
        value.clean
        for key, value in run.state.trust.items()
        if key.behavior_id == "behavior-calculate"
    ) == [1, 2]
    assert run.count("write") == 1
    run.replay()


@pytest.mark.parametrize(
    "amount,ready,allowed",
    [(500_000, True, True), (500_001, True, False), (1, False, False)],
)
def test_grant_checks_exact_amount_and_holds(
    amount: int, ready: bool, allowed: bool
) -> None:
    run = TrustRun()
    run.train()
    run.grant()
    ref = run.start("boundary", amount, ready)
    result = r.decide(
        run.state,
        e.BeginEffectAttempt(run.meta("attempt"), ref, "attempt"),
        run.catalog,
    )
    assert isinstance(result, r.Accepted) == allowed
    if not allowed:
        assert result == r.Refused("exact_approval_required")
    run.replay()


def test_twentieth_selection_sticks_after_rebuild_and_sampled_mistake_suspends_trust() -> (
    None
):
    run = TrustRun()
    run.train()
    run.grant()
    for index in range(1, 21):
        ref = run.start("eligible-" + str(index))
        assert run.state.case_samples[ref.key.case_id] == a.CaseSample(
            index, index == 20
        )
    run.state = r.rebuild(run.events, run.catalog)
    ref = run.state.case_effects["eligible-20"][0]
    assert r.decide(
        run.state,
        e.BeginEffectAttempt(run.meta("sampled"), ref, "sampled"),
        run.catalog,
    ) == r.Refused("sample_review_required")
    run.review("eligible-20", "mistake")
    assert run.count("calculate") == 0
    blocked = run.start("after-mistake")
    assert run.state.case_samples[blocked.key.case_id] == a.CaseSample(None, True)
    assert run.state.sampling_ordinals["company-a"] == 20
    run.replay()


def test_company_local_counts_never_pool() -> None:
    run = TrustRun()
    run.train(1)
    foreign = replace(POLICY, company_id="company-b")
    run.start("foreign", company=foreign)
    run.review("foreign")
    assert run.count("calculate") == 1
    assert run.count("calculate", "company-b") == 1
    assert len(run.state.trust) == 3
    run.replay()


@pytest.mark.parametrize(
    "limit", ["scope", "operation", "behavior", "future", "expired", "condition"]
)
def test_each_standing_grant_limit_blocks_dispatch(limit: str) -> None:
    run = TrustRun()
    run.train()
    grant = a.StandingGrant(
        "bounded",
        run.action("bounded", "controller"),
        a.OperationScope((p.NamedValue("record", p.TextValue("record")),)),
        ("publish",),
        tuple(run.state.trust),
        500_000,
        (p.NamedValue("ready", p.BoolValue(True)),),
        NOW,
        None,
    )
    if limit == "scope":
        grant = replace(
            grant,
            scope=a.OperationScope((p.NamedValue("record", p.TextValue("other")),)),
        )
    elif limit == "operation":
        grant = replace(grant, operations=("other",))
    elif limit == "behavior":
        grant = replace(
            grant,
            behaviors=tuple(
                key for key in grant.behaviors if key.behavior_id == "behavior-write"
            ),
        )
    elif limit == "future":
        grant = replace(grant, valid_from=NOW + timedelta(days=1))
    elif limit == "expired":
        grant = replace(grant, valid_until=NOW + timedelta(seconds=1))
    else:
        grant = replace(grant, conditions=(p.NamedValue("ready", p.BoolValue(False)),))
    run.apply(e.GrantStandingAuthority(run.meta("bounded"), grant, POLICY))
    ref = run.start("blocked")
    meta = replace(run.meta("dispatch"), observed_at=NOW + timedelta(seconds=2))
    assert r.decide(
        run.state, e.BeginEffectAttempt(meta, ref, "attempt"), run.catalog
    ) == r.Refused("exact_approval_required")
    run.replay()


def test_legacy_case_start_decodes_without_review_mode() -> None:
    run = TrustRun()
    run.start("case")
    command = run.state.cases["case"].start
    import json

    encoded = json.loads(codec.dumps(command))
    del encoded["value"]["review_mode"]
    assert codec.loads(json.dumps(encoded), e.StartSandbox) == command

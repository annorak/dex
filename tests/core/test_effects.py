from dataclasses import replace
from datetime import timedelta
from unittest.mock import patch

import pytest
from test_continuations import COMPANY, accept, action, human, meta
from test_runtime import (
    COUNTER,
    INTEGER,
    NOW,
    catalog,
    code,
    counter,
    draft,
    identity,
    repeat_program,
    start,
)

from dex.core import authority as a
from dex.core import events as e
from dex.core import program as p
from dex.core import runtime as r

POLICY = replace(
    COMPANY,
    memberships=COMPANY.memberships
    + tuple(
        e.RoleMembership(actor, role, (), NOW - timedelta(days=1), None)
        for actor, role in (
            ("alice", "effect_approver"),
            ("executor", "effect_executor"),
        )
    ),
)


PAYLOAD_INPUT = p.Literal(p.IntValue(7))
READY_INPUT = p.Literal(p.BoolValue(True))
FUNCTIONS = (identity(INTEGER, p.IntValue(1)),)


def producer(
    name: str = "write",
    source: p.Input = PAYLOAD_INPUT,
    occurrence: str = "once",
    precondition: p.Input = READY_INPUT,
) -> p.CodeStep:
    node = code(name, source)
    change = p.ChangeDeclaration(
        "change",
        "publish",
        p.Export(INTEGER, p.ResultRef(name)),
        (p.Binding("record", p.Scalar.TEXT, p.Literal(p.TextValue("record-1"))),),
        p.Literal(p.TextValue(occurrence)),
        (p.Binding("ready", p.Scalar.BOOLEAN, precondition),),
    )
    return replace(node, metadata=replace(node.metadata, changes=(change,)))


class Run:
    def __init__(
        self,
        root: p.Node | None = None,
        revision: str = "r1",
        policy: e.CompanyContext = POLICY,
        functions: tuple[p.FunctionDeclaration, ...] = FUNCTIONS,
    ) -> None:
        program = draft(
            producer() if root is None else root,
            functions,
            revision=revision,
        )
        self.catalog = catalog(program)
        begun = accept(
            r.rebuild((), self.catalog),
            replace(start(self.catalog), company=policy),
            self.catalog,
        )
        self.state, self.events = begun.state, begun.events

    def apply(self, command: e.RuntimeCommand) -> r.Accepted:
        result = accept(self.state, command, self.catalog)
        self.state = result.state
        self.events += result.events
        return result

    def ref(self) -> a.EffectRef:
        return next(iter(self.state.current_effects.values()))

    def approve(
        self, ref: a.EffectRef | None = None, name: str = "approval"
    ) -> e.ApproveEffect:
        command = e.ApproveEffect(
            meta(self.state, name),
            self.ref() if ref is None else ref,
            action(name, role="effect_approver"),
        )
        self.apply(command)
        return command

    def begin(
        self, ref: a.EffectRef | None = None, name: str = "attempt"
    ) -> e.BeginEffectAttempt:
        command = e.BeginEffectAttempt(
            meta(self.state, name, "executor"), self.ref() if ref is None else ref, name
        )
        self.apply(command)
        return command

    def correct(self, value: int, address: str = "write") -> None:
        target = e.WorkAddress("case", address)
        self.apply(
            e.CorrectResult(
                meta(self.state, f"correct-{value}", "admin"),
                e.WorkRevision(target, self.state.work[target].opened.revision),
                action(f"correct-{value}", "admin", "corrector"),
                p.IntValue(value),
            )
        )

    def replay(self) -> None:
        with (
            patch(
                "dex.core.language.execute_function",
                side_effect=AssertionError("interpreter"),
            ),
            patch("builtins.open", side_effect=AssertionError("I/O")),
        ):
            assert r.rebuild(self.events, self.catalog) == self.state


RECEIPT = a.ExecutionReceipt("adapter-1", "external-1", "recorded confirmation")


def test_exact_approval_attempt_confirmation_and_redelivery() -> None:
    run = Run()
    ref = run.ref()
    assert isinstance(run.state.effects[ref].progress, a.Proposed)
    assert r.decide(
        run.state,
        e.BeginEffectAttempt(meta(run.state, "early", "executor"), ref, "early"),
        run.catalog,
    ) == r.Refused("exact_approval_required")
    approved = run.approve()
    assert (
        run.apply(replace(approved, meta=meta(run.state, "approval-redelivery"))).events
        == ()
    )
    attempt = run.begin()
    assert (
        run.apply(
            replace(attempt, meta=meta(run.state, "attempt-redelivery", "executor"))
        ).events
        == ()
    )
    command = e.ConfirmEffect(
        meta(run.state, "confirm", "executor"), ref, attempt.attempt_id, RECEIPT
    )
    run.apply(command)
    assert isinstance(run.state.effects[ref].progress, a.Confirmed)
    assert run.state.confirmed_effects[ref.key] == ref
    assert not run.state.unresolved_attempts
    assert (
        run.apply(
            replace(command, meta=meta(run.state, "receipt-redelivery", "executor"))
        ).events
        == ()
    )
    run.replay()


def test_program_and_business_approval_are_not_write_approval() -> None:
    leaf = producer(source=p.ResultRef("human"))
    run = Run(
        p.Sequence("sequence", (human(), leaf), p.Export(INTEGER, p.ResultRef("write")))
    )
    task = next(iter(run.state.tasks.values()))
    run.apply(
        e.RespondTask(
            meta(run.state, "business"),
            task.ref,
            task.reviewed,
            action("business"),
            p.IntValue(7),
        )
    )
    ref = run.ref()
    assert run.state.effects[ref].revision.decisions == (
        ("company-a", "dex", "business"),
    )
    assert r.decide(
        run.state,
        e.BeginEffectAttempt(meta(run.state, "begin", "executor"), ref, "attempt"),
        run.catalog,
    ) == r.Refused("exact_approval_required")
    run.approve()
    run.begin()
    run.replay()


def test_payload_correction_preserves_key_and_requires_fresh_review() -> None:
    run = Run()
    original = run.ref()
    run.approve()
    run.correct(9)
    revised = run.ref()
    assert revised.key == original.key and revised.revision == 2
    assert run.state.effects[original].revision.payload == p.IntValue(7)
    assert run.state.effects[original].superseded_by == revised
    assert run.state.effects[revised].revision.payload == p.IntValue(9)
    assert r.decide(
        run.state,
        e.BeginEffectAttempt(meta(run.state, "stale", "executor"), original, "stale"),
        run.catalog,
    ) == r.Refused("stale_effect")
    assert r.decide(
        run.state,
        e.BeginEffectAttempt(meta(run.state, "fresh", "executor"), revised, "fresh"),
        run.catalog,
    ) == r.Refused("exact_approval_required")
    run.approve(revised, "fresh-approval")
    run.begin(revised)
    run.replay()


def test_operation_key_ignores_artifact_behavior_payload_and_transport() -> None:
    first, second = (
        Run(),
        Run(
            replace(
                producer(source=p.Literal(p.IntValue(9))),
                metadata=replace(
                    producer(source=p.Literal(p.IntValue(9))).metadata,
                    behavior_id="changed",
                ),
            ),
            revision="r2",
        ),
    )
    assert first.ref().key == second.ref().key
    assert (
        first.state.effects[first.ref()].revision.artifact
        != second.state.effects[second.ref()].revision.artifact
    )
    assert first.ref().key != Run(producer(occurrence="second")).ref().key


def test_conflicting_review_and_stale_proposal_are_atomic() -> None:
    run = Run()
    approved = run.approve()
    before = run.state
    conflict = replace(
        approved,
        meta=meta(run.state, "different"),
        action=action("different", role="effect_approver"),
    )
    assert r.decide(before, conflict, run.catalog) == r.Refused(
        "effect_review_conflict"
    )
    assert run.state == before
    run.correct(9)
    assert r.decide(
        run.state, replace(conflict, meta=meta(run.state, "stale")), run.catalog
    ) == r.Refused("stale_effect")
    run.replay()


@pytest.mark.parametrize("uncertain", [False, True])
def test_unresolved_attempt_blocks_replacement_until_fenced(uncertain: bool) -> None:
    run = Run()
    original = run.ref()
    run.approve()
    run.begin()
    if uncertain:
        run.apply(
            e.MarkEffectUncertain(
                meta(run.state, "uncertain", "executor"),
                original,
                "attempt",
                "connection lost",
            )
        )
    run.correct(9)
    revised = run.ref()
    run.approve(revised, "replacement-approval")
    command = e.BeginEffectAttempt(
        meta(run.state, "replacement", "executor"), revised, "replacement"
    )
    assert r.decide(run.state, command, run.catalog) == r.Refused("unresolved_attempt")
    run.apply(
        e.ReconcileEffect(
            meta(run.state, "reconcile", "executor"),
            original,
            "attempt",
            a.FencedNotApplied("adapter fenced attempt before checking absence"),
        )
    )
    run.apply(replace(command, meta=meta(run.state, "replacement", "executor")))
    assert isinstance(run.state.effects[original].progress, a.Reconciled)
    assert run.state.unresolved_attempts[original.key] == revised
    run.replay()


def test_confirmed_correction_requires_explicit_separately_approved_amendment() -> None:
    run = Run()
    original = run.ref()
    run.approve()
    run.begin()
    run.apply(
        e.ConfirmEffect(
            meta(run.state, "confirm", "executor"), original, "attempt", RECEIPT
        )
    )
    run.correct(9)
    revised = run.ref()
    run.approve(revised, "desired-approval")
    assert r.decide(
        run.state,
        e.BeginEffectAttempt(
            meta(run.state, "replacement", "executor"), revised, "replacement"
        ),
        run.catalog,
    ) == r.Refused("amendment_required")
    run.apply(
        e.AmendEffect(
            meta(run.state, "amend"),
            revised,
            original,
            "correction-1",
            action("amend", role="effect_approver"),
        )
    )
    amendment = a.EffectRef(replace(original.key, occurrence="correction-1"), 1)
    assert run.state.effects[amendment].revision.amendment_of == original
    assert isinstance(run.state.effects[original].progress, a.Confirmed)
    assert r.decide(
        run.state,
        e.BeginEffectAttempt(
            meta(run.state, "amended-attempt", "executor"), amendment, "amended-attempt"
        ),
        run.catalog,
    ) == r.Refused("exact_approval_required")
    run.approve(amendment, "amendment-approval")
    run.begin(amendment, "amended-attempt")
    run.replay()


def test_revocation_blocks_attempt_but_keeps_reconciliation_available() -> None:
    run = Run()
    ref = run.ref()
    run.approve()
    run.apply(
        e.RevokeEffectApproval(
            meta(run.state, "revoke"),
            ref,
            ("company-a", "dex", "approval"),
            action("revoke", role="effect_approver"),
        )
    )
    assert r.decide(
        run.state,
        e.BeginEffectAttempt(meta(run.state, "denied", "executor"), ref, "denied"),
        run.catalog,
    ) == r.Refused("approval_revoked")
    run.approve(name="replacement-approval")
    run.begin()
    run.apply(
        e.RevokeEffectApproval(
            meta(run.state, "revoke-again"),
            ref,
            ("company-a", "dex", "replacement-approval"),
            action("revoke-again", role="effect_approver"),
        )
    )
    run.apply(
        e.ReconcileEffect(
            meta(run.state, "reconcile", "executor"), ref, "attempt", a.Applied(RECEIPT)
        )
    )
    assert run.state.confirmed_effects[ref.key] == ref
    run.replay()


def test_current_role_and_actor_are_checked_on_attempt() -> None:
    policy = replace(
        POLICY,
        memberships=tuple(
            replace(item, valid_until=NOW + timedelta(hours=1))
            if item.role == "effect_approver"
            else item
            for item in POLICY.memberships
        ),
    )
    run = Run(policy=policy)
    run.approve()
    command = e.BeginEffectAttempt(
        replace(
            meta(run.state, "late", "executor"), observed_at=NOW + timedelta(hours=2)
        ),
        run.ref(),
        "late",
    )
    assert r.decide(run.state, command, run.catalog) == r.Refused("effect_authority")
    assert r.decide(
        run.state,
        replace(command, meta=meta(run.state, "intruder", "intruder")),
        run.catalog,
    ) == r.Refused("effect_observer")


def test_false_precondition_blocks_execution() -> None:
    run = Run(producer(precondition=p.Literal(p.BoolValue(False))))
    run.approve()
    assert r.decide(
        run.state,
        e.BeginEffectAttempt(
            meta(run.state, "begin", "executor"), run.ref(), "attempt"
        ),
        run.catalog,
    ) == r.Refused("effect_precondition")


def test_replay_rejects_forged_or_missing_proposal() -> None:
    run = Run()
    position = next(
        i
        for i, event in enumerate(run.events)
        if isinstance(event.payload, e.EffectProposed)
    )
    proposal = run.events[position].payload
    assert isinstance(proposal, e.EffectProposed)
    forged = replace(
        run.events[position],
        payload=e.EffectProposed(replace(proposal.revision, payload=p.IntValue(999))),
    )
    with pytest.raises(r.ReplayError, match="effect_revision"):
        r.rebuild(
            run.events[:position] + (forged,) + run.events[position + 1 :], run.catalog
        )
    missing = run.events[:position] + run.events[position + 1 :]
    missing = tuple(
        replace(
            event,
            ordinal=i,
            payload=replace(event.payload, count=len(missing))
            if isinstance(event.payload, e.BatchCompleted)
            else event.payload,
        )
        for i, event in enumerate(missing)
    )
    with pytest.raises(r.ReplayError, match="missing_proposal"):
        r.rebuild(missing, run.catalog)


@pytest.mark.parametrize("dimension", ["scope", "occurrence"])
def test_correction_cannot_change_operation_identity_after_attempt(
    dimension: str,
) -> None:
    text = p.Scalar.TEXT
    leaf = code("write", p.Literal(p.TextValue("original")), text)
    change = p.ChangeDeclaration(
        "change",
        "publish",
        p.Export(text, p.ResultRef("write")),
        (
            p.Binding(
                "record",
                text,
                p.ResultRef("write")
                if dimension == "scope"
                else p.Literal(p.TextValue("record")),
            ),
        ),
        p.ResultRef("write")
        if dimension == "occurrence"
        else p.Literal(p.TextValue("once")),
    )
    leaf = replace(leaf, metadata=replace(leaf.metadata, changes=(change,)))
    run = Run(leaf, functions=(identity(text, p.TextValue("original")),))
    run.approve()
    run.begin()
    before = run.state
    command = e.CorrectResult(
        meta(before, "change-identity", "admin"),
        e.WorkRevision(e.WorkAddress("case", "write"), 1),
        action("change-identity", "admin", "corrector"),
        p.TextValue("replacement"),
    )
    assert r.decide(before, command, run.catalog) == r.Refused(
        "effect_identity_changed"
    )
    assert run.state == before
    assert isinstance(run.state.effects[run.ref()].progress, a.Attempted)
    assert run.state.unresolved_attempts[run.ref().key] == run.ref()
    run.replay()


def test_old_revocation_cannot_revoke_replacement_approval() -> None:
    run = Run()
    ref = run.ref()
    run.approve()
    revoke = e.RevokeEffectApproval(
        meta(run.state, "revoke"),
        ref,
        ("company-a", "dex", "approval"),
        action("revoke", role="effect_approver"),
    )
    run.apply(revoke)
    run.approve(name="replacement-approval")
    stale = replace(
        revoke,
        meta=meta(run.state, "stale-revoke"),
        action=action("stale-revoke", role="effect_approver"),
    )
    assert r.decide(run.state, stale, run.catalog) == r.Refused("stale_approval")
    assert (
        run.apply(replace(revoke, meta=meta(run.state, "old-redelivery"))).events == ()
    )
    run.begin()
    run.replay()


def test_attempt_cannot_precede_exact_approval_decision() -> None:
    run = Run()
    decided_at = NOW + timedelta(hours=1)
    approval = e.ApproveEffect(
        replace(meta(run.state, "approval"), observed_at=decided_at),
        run.ref(),
        replace(action("approval", role="effect_approver"), decided_at=decided_at),
    )
    run.apply(approval)
    state = run.state
    attempt = e.BeginEffectAttempt(
        meta(state, "attempt", "executor"), run.ref(), "attempt"
    )
    assert r.decide(state, attempt, run.catalog) == r.Refused("approval_time")
    assert run.state == state
    assert isinstance(state.effects[run.ref()].progress, a.Approved)
    run.apply(replace(attempt, meta=replace(attempt.meta, observed_at=decided_at)))
    assert isinstance(run.state.effects[run.ref()].progress, a.Attempted)
    run.replay()


def test_effect_transitions_preserve_prior_workspace_snapshots() -> None:
    run = Run()
    proposed = run.state
    commands = tuple(proposed.commands)
    ref = run.ref()
    approval = run.approve()
    approved = run.state
    run.begin()
    assert proposed.effects[ref].progress == a.Proposed()
    assert tuple(proposed.commands) == commands
    assert not proposed.actions and not proposed.unresolved_attempts
    assert approved.effects[ref].progress == a.Approved(
        a.ExactApproval(ref, approval.action)
    )
    assert not approved.unresolved_attempts
    assert isinstance(run.state.effects[ref].progress, a.Attempted)
    assert proposed.work == approved.work == run.state.work
    run.replay()


@pytest.mark.parametrize("progress", ["approved", "uncertain", "confirmed"])
def test_repeat_correction_preserves_effect_facts_and_blocks_stale_attempt(
    progress: str,
) -> None:
    program = repeat_program(3)
    root = program.root
    assert isinstance(root, p.Repeat)
    body = root.body.body
    assert isinstance(body, p.CodeStep)
    change = p.ChangeDeclaration(
        "change",
        "publish",
        p.Export(COUNTER, p.ResultRef("advance")),
        (
            p.Binding(
                "iteration_input", INTEGER, p.LocalRef("repeat", "state", ("count",))
            ),
        ),
        p.Literal(p.TextValue("once")),
    )
    body = replace(body, metadata=replace(body.metadata, changes=(change,)))
    programs = catalog(
        replace(program, root=replace(root, body=replace(root.body, body=body)))
    )
    opened = accept(
        r.rebuild((), programs), replace(start(programs), company=POLICY), programs
    )
    state, history = opened.state, opened.events
    ref = next(
        ref for ref in state.effects if ref.key.scope.parts[0].value == p.IntValue(2)
    )
    approved = accept(
        state,
        e.ApproveEffect(
            meta(state, "approve"), ref, action("approve", role="effect_approver")
        ),
        programs,
    )
    state, history = approved.state, history + approved.events
    if progress != "approved":
        attempted = accept(
            state,
            e.BeginEffectAttempt(meta(state, "attempt", "executor"), ref, "attempt"),
            programs,
        )
        state, history = attempted.state, history + attempted.events
        command = (
            e.MarkEffectUncertain(
                meta(state, "outcome", "executor"), ref, "attempt", "lost"
            )
            if progress == "uncertain"
            else e.ConfirmEffect(
                meta(state, "outcome", "executor"),
                ref,
                "attempt",
                a.ExecutionReceipt("adapter", "external", "confirmed"),
            )
        )
        completed = accept(state, command, programs)
        state, history = completed.state, history + completed.events
    fact = state.effects[ref]
    first = next(
        address
        for address in state.work
        if address.node_id == "advance" and address.scope[-1].key == "0"
    )
    corrected = accept(
        state,
        e.CorrectResult(
            meta(state, "correct", "admin"),
            e.WorkRevision(first, 1),
            action("correct", "admin", "corrector"),
            counter(10, True),
        ),
        programs,
    )
    assert corrected.state.effects[ref] == fact
    result = r.decide(
        corrected.state,
        e.BeginEffectAttempt(
            meta(corrected.state, "stale-attempt", "executor"), ref, "different-attempt"
        ),
        programs,
    )
    assert isinstance(result, r.Refused)
    assert r.rebuild(history + corrected.events, programs) == corrected.state


@pytest.mark.parametrize("gate", ["direct", "composite", "composite_choice", "choice"])
def test_renewed_business_gate_requires_a_new_exact_approval(gate: str) -> None:
    source = code("source", p.Literal(p.IntValue(1)))
    decision = human(source=p.ResultRef("source"), schema=p.Scalar.BOOLEAN)
    if gate == "composite":
        decision_node: p.Node = p.Sequence(
            "review", (decision,), p.Export(p.Scalar.BOOLEAN, p.ResultRef("human"))
        )
    elif gate == "composite_choice":
        decision_node = p.Choose(
            "review",
            p.Literal(p.BoolValue(True)),
            p.Branch(decision, p.Export(p.Scalar.BOOLEAN, p.ResultRef("human"))),
            p.Branch(
                human("unused", schema=p.Scalar.BOOLEAN),
                p.Export(p.Scalar.BOOLEAN, p.ResultRef("unused")),
            ),
            p.Scalar.BOOLEAN,
        )
    else:
        decision_node = decision
    writer: p.Node = producer()
    result_name = "write"
    if gate == "choice":
        writer = p.Choose(
            "choice",
            p.ResultRef("human"),
            p.Branch(writer, p.Export(INTEGER, p.ResultRef("write"))),
            p.Branch(
                code("skip", p.Literal(p.IntValue(0))),
                p.Export(INTEGER, p.ResultRef("skip")),
            ),
            INTEGER,
        )
        result_name = "choice"
    run = Run(
        p.Sequence(
            "root",
            (code("sibling", p.Literal(p.IntValue(3))), source, decision_node, writer),
            p.Export(INTEGER, p.ResultRef(result_name)),
        )
    )
    task = next(task for task in run.state.tasks.values() if task.status == "open")
    run.apply(
        e.RespondTask(
            meta(run.state, "business-1"),
            task.ref,
            task.reviewed,
            action("business-1"),
            p.BoolValue(True),
        )
    )
    first = run.ref()
    first_business = task.ref.work
    assert ("company-a", "dex", "business-1") in run.state.effects[
        first
    ].revision.decisions
    run.approve()
    sibling = run.state.work[e.WorkAddress("case", "sibling")]
    run.correct(2, "source")
    assert run.state.cases["case"].status == "waiting"
    assert isinstance(
        r.decide(
            run.state,
            e.BeginEffectAttempt(meta(run.state, "stale", "executor"), first, "stale"),
            run.catalog,
        ),
        r.Refused,
    )
    task = next(task for task in run.state.tasks.values() if task.status == "open")
    run.apply(
        e.RespondTask(
            meta(run.state, "business-2"),
            task.ref,
            task.reviewed,
            action("business-2"),
            p.BoolValue(True),
        )
    )
    renewed = run.ref()
    assert task.ref.work in run.state.effects[renewed].revision.dependencies
    assert first_business not in run.state.effects[renewed].revision.dependencies
    assert renewed.key == first.key and renewed.revision > first.revision
    assert run.state.effects[renewed].revision.decisions == (
        ("company-a", "dex", "business-2"),
    )
    assert isinstance(run.state.effects[renewed].progress, a.Proposed)
    assert isinstance(
        r.decide(
            run.state,
            e.BeginEffectAttempt(
                meta(run.state, "unapproved", "executor"), renewed, "unapproved"
            ),
            run.catalog,
        ),
        r.Refused,
    )
    assert run.state.work[e.WorkAddress("case", "sibling")] == sibling
    run.approve(renewed, "approval-2")
    run.begin(renewed, "attempt-2")
    run.replay()


def test_business_correction_preserves_an_independent_parallel_branch() -> None:
    branch = p.Sequence(
        "process",
        (
            code("source", p.Literal(p.IntValue(1))),
            human(source=p.ResultRef("source")),
            producer(),
        ),
        p.Export(INTEGER, p.ResultRef("write")),
    )
    run = Run(branch)
    original = next(iter(run.catalog.artifacts.values())).draft
    output = p.RecordSchema(
        "Pair", (p.Field("process", INTEGER), p.Field("sibling", INTEGER))
    )
    root = p.Parallel(
        "parallel",
        (
            p.NamedBranch(
                "process", p.Branch(branch, p.Export(INTEGER, p.ResultRef("process")))
            ),
            p.NamedBranch(
                "sibling",
                p.Branch(
                    code("sibling", p.Literal(p.IntValue(8))),
                    p.Export(INTEGER, p.ResultRef("sibling")),
                ),
            ),
        ),
        output,
    )
    run.catalog = catalog(replace(original, root=root, schemas=(output,)))
    opened = accept(
        r.rebuild((), run.catalog),
        replace(start(run.catalog), company=POLICY),
        run.catalog,
    )
    run.state, run.events = opened.state, opened.events
    task = next(task for task in run.state.tasks.values() if task.status == "open")
    run.apply(
        e.RespondTask(
            meta(run.state, "business"),
            task.ref,
            task.reviewed,
            action("business"),
            p.IntValue(7),
        )
    )
    run.approve()
    ref = run.ref()
    sibling = next(
        address for address in run.state.work if address.node_id == "sibling"
    )
    sibling_work = run.state.work[sibling]
    target = next(address for address in run.state.work if address.node_id == "source")
    corrected = run.apply(
        e.CorrectResult(
            meta(run.state, "correct", "admin"),
            e.WorkRevision(target, 1),
            action("correct", "admin", "corrector"),
            p.IntValue(2),
        )
    )
    assert run.state.cases["case"].status == "waiting"
    assert run.state.work[sibling] == sibling_work
    assert all(
        getattr(event.payload, "address", None) != sibling for event in corrected.events
    )
    assert isinstance(
        r.decide(
            run.state,
            e.BeginEffectAttempt(meta(run.state, "stale", "executor"), ref, "stale"),
            run.catalog,
        ),
        r.Refused,
    )
    run.replay()

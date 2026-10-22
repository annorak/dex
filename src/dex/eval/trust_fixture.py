from dataclasses import replace
from pathlib import Path
from typing import Literal

from dex.core import authority as a
from dex.core import events as e
from dex.core import program as p
from dex.core import runtime as r
from dex.eval.recovery_fixture import (
    CITATION,
    COMPANY,
    NOW,
    SOURCES,
    TEXT,
    DeterministicAdapter,
    SandboxWorkspace,
)
from dex.workspace import LocalSession

POLICY = replace(
    COMPANY,
    memberships=(
        *COMPANY.memberships,
        e.RoleMembership("operator", "controller", (), NOW, None),
    ),
)
SESSION = LocalSession("operator", POLICY)


def program(later: bool = False, pure: bool = False) -> p.ProgramDraft:
    money = p.Scalar.MONEY

    def step(name: str, source: p.Input, writes: bool) -> p.CodeStep:
        changes = (
            (
                p.ChangeDeclaration(
                    name + "-change",
                    "publish",
                    p.Export(money, p.ResultRef(name)),
                    (
                        p.Binding(
                            "record", p.Scalar.TEXT, p.Literal(p.TextValue("record"))
                        ),
                    ),
                    p.Literal(p.TextValue(name)),
                    (p.Binding("ready", p.Scalar.BOOLEAN, p.ProgramInputRef("ready")),),
                ),
            )
            if writes
            else ()
        )
        return p.CodeStep(
            p.StepMetadata(
                name,
                name + "-1",
                TEXT,
                (CITATION,),
                (p.Binding("value", money, source),),
                money,
                changes,
            ),
            "identity",
        )

    calculate = step("calculate", p.ProgramInputRef("amount"), False)
    write = step("write", p.ResultRef("calculate"), True)
    children: tuple[p.Node, ...] = (calculate, write)
    final = "write"
    if later:
        human = p.HumanStep(
            p.StepMetadata(
                "decision", "decision-1", TEXT, (CITATION,), (), p.Scalar.BOOLEAN
            ),
            "reviewer",
            NOW,
            p.Export(p.Scalar.BOOLEAN, p.Literal(p.BoolValue(True))),
            True,
        )
        children = (*children, human, step("later", p.ResultRef("calculate"), True))
        final = "later"
    root: p.Node = (
        calculate
        if pure
        else p.Sequence("sequence", children, p.Export(money, p.ResultRef(final)))
    )
    return p.ProgramDraft(
        "trust",
        "pure" if pure else "later" if later else "initial",
        (),
        (p.Field("amount", money), p.Field("ready", p.Scalar.BOOLEAN)),
        root,
        (
            p.FunctionDeclaration(
                "identity",
                (p.Field("value", money),),
                money,
                p.FunctionBody("restricted-1", "return value"),
                (
                    p.FunctionTest(
                        "identity",
                        (p.NamedValue("value", p.MoneyValue(1)),),
                        p.MoneyValue(1),
                    ),
                ),
            ),
        ),
        (),
        (),
    )


class TrustFixture:
    def __init__(
        self, out: Path, later: bool = False, adapter_mode: str = "immediate"
    ) -> None:
        self.path = out / "workspace.db"
        self.adapter = DeterministicAdapter(out / "remote.db", adapter_mode)
        self.workspace = SandboxWorkspace(self.path, SESSION, {"publish": self.adapter})
        self.pin = self.register(program(later))

    @property
    def state(self) -> r.WorkspaceState:
        return self.workspace.state

    def meta(self, name: str) -> e.CommandMeta:
        return e.CommandMeta(name, "operator", NOW, NOW, self.state.revision)

    def action(self, name: str, role: str = "reviewer") -> e.HumanAction:
        return e.HumanAction(POLICY.company_id, "dex", name, "operator", role, NOW)

    def execute(self, command: e.Command) -> r.Accepted:
        result = self.workspace.execute(command)
        assert isinstance(result, r.Accepted), result
        return result

    def register(self, draft: p.ProgramDraft) -> e.ArtifactPin:
        result = self.workspace.register(
            self.meta("register/" + draft.revision), draft, SOURCES
        )
        assert isinstance(result, r.Accepted), result
        return next(
            pin for pin in self.state.registrations if pin.revision == draft.revision
        )

    def start(
        self,
        name: str,
        amount: int = 1,
        ready: bool = True,
        mode: Literal["review", "historical", "unattended"] = "review",
        pin: e.ArtifactPin | None = None,
    ) -> None:
        self.execute(
            e.StartSandbox(
                self.meta("start/" + name),
                name,
                self.pin if pin is None else pin,
                (
                    p.NamedValue("amount", p.MoneyValue(amount)),
                    p.NamedValue("ready", p.BoolValue(ready)),
                ),
                NOW.date(),
                review_mode=mode,
            )
        )

    def ref(self, case: str, node: str = "write") -> a.EffectRef:
        work = self.state.work[e.WorkAddress(case, node)]
        return self.state.work_effects[
            (
                e.WorkRevision(work.opened.address, work.opened.revision),
                node + "-change",
            )
        ]

    def approve(self, ref: a.EffectRef) -> e.ApproveEffect:
        name = f"approve/{ref.key.case_id}/{ref.key.occurrence}/{self.state.revision}"
        command = e.ApproveEffect(
            self.meta(name), ref, self.action(name, "effect_approver")
        )
        self.execute(command)
        return command

    def dispatch(self, ref: a.EffectRef) -> r.Accepted | r.Refused:
        return self.workspace.dispatch(ref, NOW)

    def review(
        self,
        case: str,
        node: str = "calculate",
        outcome: Literal["clean", "mistake", "unresolved"] = "clean",
    ) -> e.ReviewResults:
        address = e.WorkAddress(case, node)
        name = f"review/{case}/{node}/{self.state.revision}"
        command = e.ReviewResults(
            self.meta(name),
            case,
            (
                a.ReviewedResult(
                    e.WorkRevision(address, self.state.work[address].opened.revision),
                    outcome,
                ),
            ),
            self.action(name),
        )
        self.execute(command)
        return command

    def count(self, name: str, state: r.WorkspaceState | None = None) -> int:
        current = self.state if state is None else state
        return sum(
            count.clean
            for key, count in current.trust.items()
            if key.behavior_id == name + "-1"
        )

    def answer(self, case: str) -> None:
        task = next(
            task
            for task in self.state.tasks.values()
            if task.ref.work.address.case_id == case and task.status == "open"
        )
        name = "decision/" + case
        self.execute(
            e.RespondTask(
                self.meta(name),
                task.ref,
                task.reviewed,
                self.action(name),
                p.BoolValue(True),
            )
        )

    def train(self, count: int = 300, later: bool = False) -> None:
        for index in range(count):
            case = "training-" + str(index)
            self.start(case)
            ref = self.ref(case)
            assert self.state.effects[ref].revision.payload == p.MoneyValue(1)
            result = self.state.work[e.WorkAddress(case, "calculate")].completed
            assert result is not None and result.value == p.MoneyValue(1)
            self.approve(ref)
            assert isinstance(self.dispatch(ref), r.Accepted)
            if later:
                self.answer(case)
                ref = self.ref(case, "later")
                assert self.state.effects[ref].revision.payload == p.MoneyValue(1)
                self.approve(ref)
                assert isinstance(self.dispatch(ref), r.Accepted)

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
        self.execute(e.GrantStandingAuthority(self.meta(name), grant, POLICY))
        return grant

    def revoke(self, name: str = "grant") -> e.RevokeStandingGrant:
        command = e.RevokeStandingGrant(
            self.meta("revoke/" + name),
            name,
            self.action("revoke/" + name, "controller"),
            POLICY,
        )
        self.execute(command)
        return command

    def reopen(self) -> bool:
        before = self.state
        self.workspace.close()
        self.workspace = SandboxWorkspace(self.path, SESSION, {"publish": self.adapter})
        return before == self.state

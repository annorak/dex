import sqlite3
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path

from dex import codec
from dex.adapters import DispatchRequest, Outcome, Pending
from dex.core import authority as a
from dex.core import events as e
from dex.core import program as p
from dex.core import runtime as r
from dex.workspace import LocalSession, Workspace

NOW = datetime(2026, 1, 1, tzinfo=UTC)
TEXT = "Use the declared result."
PIN = p.SourcePin(
    "guide",
    "r1",
    sha256(TEXT.encode()).hexdigest(),
    "text",
    sha256(TEXT.encode()).hexdigest(),
)
CITATION = p.Citation(PIN, "all", "paragraph", 0, len(TEXT), TEXT)
SOURCES = p.SourceCatalog(
    (p.SourceExtraction(PIN, TEXT, (p.Section("all", "paragraph", 0, len(TEXT)),)),)
)
COMPANY = e.CompanyContext(
    "synthetic-company",
    "policy-1",
    tuple(
        e.RoleMembership("operator", role, (), NOW - timedelta(days=1), None)
        for role in (
            "program_registrar",
            "program_approver",
            "workspace_operator",
            "effect_approver",
            "effect_executor",
            "corrector",
            "reviewer",
            "task_admin",
        )
    ),
    (),
    "records-1",
    frozenset(),
)
SESSION = LocalSession("operator", COMPANY)


def meta(workspace: Workspace, name: str) -> e.CommandMeta:
    return e.CommandMeta(name, "operator", NOW, NOW, workspace.state.revision)


def action(name: str, role: str = "effect_approver") -> e.HumanAction:
    return e.HumanAction(COMPANY.company_id, "dex", name, "operator", role, NOW)


def program(
    count: int = 1, effects: bool = True, waiting: bool = False
) -> tuple[p.ProgramDraft, tuple[p.NamedValue, ...]]:
    integer = p.Scalar.INTEGER
    source: p.Input = p.Literal(p.IntValue(7))
    scope: p.Input = p.Literal(p.TextValue("record"))
    schemas: tuple[p.RecordSchema, ...] = ()
    inputs: tuple[p.Field, ...] = ()
    facts: tuple[p.NamedValue, ...] = ()
    if count > 1:
        source = p.LocalRef("each", "item", ("value",))
        scope = p.LocalRef("each", "item", ("key",))
    change = p.ChangeDeclaration(
        "change",
        "publish",
        p.Export(integer, p.ResultRef("write")),
        (p.Binding("record", p.Scalar.TEXT, scope),),
        p.Literal(p.TextValue("once")),
        (p.Binding("ready", p.Scalar.BOOLEAN, p.Literal(p.BoolValue(True))),),
    )
    metadata = p.StepMetadata(
        "write",
        "write-1",
        TEXT,
        (CITATION,),
        (p.Binding("value", integer, source),),
        integer,
        (change,) if effects else (),
    )
    leaf = p.CodeStep(metadata, "identity")
    root: p.Node = leaf
    if count > 1:
        entry = p.RecordSchema(
            "Entry", (p.Field("key", p.Scalar.TEXT), p.Field("value", integer))
        )
        keyed = p.KeyedSchema(entry, "key")
        root = p.Each(
            "each",
            p.ProgramInputRef("entries"),
            keyed,
            keyed,
            p.Branch(leaf, p.Export(entry, p.LocalRef("each", "item"))),
        )
        schemas, inputs = (entry,), (p.Field("entries", keyed),)
        facts = (
            p.NamedValue(
                "entries",
                p.KeyedValue(
                    tuple(
                        p.KeyedEntry(
                            str(index),
                            p.RecordValue(
                                "Entry",
                                (
                                    p.NamedValue("key", p.TextValue(str(index))),
                                    p.NamedValue("value", p.IntValue(7)),
                                ),
                            ),
                        )
                        for index in range(count)
                    )
                ),
            ),
        )
    if waiting:
        human = p.HumanStep(
            p.StepMetadata("review", "review-1", TEXT, (CITATION,), (), integer),
            "reviewer",
            NOW + timedelta(days=1),
            p.Export(integer, p.Literal(p.IntValue(7))),
            True,
        )
        followup = replace(
            human,
            metadata=replace(
                human.metadata, step_id="followup", behavior_id="followup-1"
            ),
        )
        root = p.Sequence(
            "sequence",
            (leaf, human, followup),
            p.Export(integer, p.ResultRef("followup")),
        )
    function = p.FunctionDeclaration(
        "identity",
        (p.Field("value", integer),),
        integer,
        p.FunctionBody("restricted-1", "return value"),
        (
            p.FunctionTest(
                "identity", (p.NamedValue("value", p.IntValue(7)),), p.IntValue(7)
            ),
        ),
    )
    scenarios = (
        (p.ProgramScenario("saved", (), p.IntValue(7), (CITATION,)),)
        if not effects and not waiting and count == 1
        else ()
    )
    return p.ProgramDraft(
        "recovery",
        "effect-1" if effects else "pure-1",
        schemas,
        inputs,
        root,
        (function,),
        (),
        scenarios,
    ), facts


class Interrupted(RuntimeError):
    pass


class Fault:
    def __init__(self, point: str) -> None:
        self.point = point
        self.triggered = False

    def __call__(self, point: str) -> None:
        if point == self.point and not self.triggered:
            self.triggered = True
            raise Interrupted(point)


class DeterministicAdapter:
    revision = "fixture-adapter-1"

    def __init__(
        self,
        path: Path,
        mode: str = "immediate",
        fault: Callable[[str], None] = lambda point: None,
    ) -> None:
        self.path, self.mode = path, mode
        self.fault: Callable[[str], None] = fault
        connection = self._connect()
        try:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS attempts (operation TEXT, attempt TEXT PRIMARY KEY, payload TEXT, version TEXT, state TEXT)"
            )
        finally:
            connection.close()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, isolation_level=None)
        connection.execute("PRAGMA synchronous=FULL")
        return connection

    def _outcome(self, request: DispatchRequest, state: str) -> Outcome:
        if state == "applied":
            return a.Applied(
                a.ExecutionReceipt(
                    self.revision,
                    request.operation_id,
                    sha256(codec.dumps(request.revision).encode()).hexdigest(),
                )
            )
        if state == "fenced":
            return a.FencedNotApplied("atomic fence/" + request.attempt_id)
        return Pending("admitted attempt may still commit")

    def _apply(self, request: DispatchRequest, reconciliation: bool) -> Outcome:
        if request.adapter_revision != self.revision:
            raise ValueError("adapter_revision")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT operation, payload, version, state FROM attempts WHERE attempt=?",
                (request.attempt_id,),
            ).fetchone()
            payload = codec.dumps(request.revision)
            if row is not None:
                if row[:3] != (request.operation_id, payload, self.revision):
                    raise ValueError("adapter_payload_conflict")
                state = row[3]
            else:
                occupied = connection.execute(
                    "SELECT 1 FROM attempts WHERE operation=? AND state != 'fenced'",
                    (request.operation_id,),
                ).fetchone()
                if occupied is not None:
                    connection.execute("ROLLBACK")
                    return Pending("another revision is unresolved or applied")
                state = (
                    "fenced"
                    if reconciliation or self.mode == "reject"
                    else ("pending" if self.mode == "delayed" else "applied")
                )
                connection.execute(
                    "INSERT INTO attempts VALUES (?, ?, ?, ?, ?)",
                    (
                        request.operation_id,
                        request.attempt_id,
                        payload,
                        self.revision,
                        state,
                    ),
                )
            connection.execute("COMMIT")
            if state == "applied":
                self.fault("remote_commit")
            return self._outcome(request, state)
        except BaseException:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def execute(self, request: DispatchRequest) -> Outcome:
        return self._apply(request, False)

    def reconcile(self, request: DispatchRequest) -> Outcome:
        return self._apply(request, True)

    def finish(self, attempt_id: str, fence: bool = False) -> None:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE attempts SET state=? WHERE attempt=? AND state='pending'",
                ("fenced" if fence else "applied", attempt_id),
            )
            connection.execute("COMMIT")
        finally:
            connection.close()

    def lookup(self, key: a.EffectKey) -> str | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT attempt FROM attempts WHERE operation=? AND state='applied'",
                (sha256(codec.dumps(key).encode()).hexdigest(),),
            ).fetchone()
            return None if row is None else row[0]
        finally:
            connection.close()

    def writes(self) -> int:
        connection = self._connect()
        try:
            return connection.execute(
                "SELECT count(*) FROM attempts WHERE state='applied'"
            ).fetchone()[0]
        finally:
            connection.close()


class SandboxWorkspace(Workspace):
    def _dispatch_eligibility(self, ref: a.EffectRef) -> r.Refused | None:
        if not all(
            isinstance(adapter, DeterministicAdapter)
            for adapter in self.adapters.values()
        ):
            return r.Refused("fixture_adapter_required")
        return None


def setup(
    workspace: Workspace, count: int = 1, waiting: bool = False, approve: bool = True
) -> tuple[a.EffectRef, ...]:
    draft, facts = program(count, waiting=waiting)
    registered = workspace.register(meta(workspace, "register"), draft, SOURCES)
    assert isinstance(registered, r.Accepted), registered
    pin = next(iter(workspace.state.registrations))
    started = workspace.execute(
        e.StartSandbox(meta(workspace, "start"), "case", pin, facts, NOW.date())
    )
    assert isinstance(started, r.Accepted), started
    refs = tuple(workspace.state.current_effects.values())
    for index, ref in enumerate(refs if approve else ()):
        approved = workspace.execute(
            e.ApproveEffect(
                meta(workspace, f"approve-{index}"), ref, action(f"approve-{index}")
            )
        )
        assert isinstance(approved, r.Accepted), approved
    return refs

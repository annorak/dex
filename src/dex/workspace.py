import sqlite3
from collections.abc import Callable, Generator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Self

from dex import codec
from dex.adapters import Adapter, DispatchRequest, Outcome, Pending
from dex.core import authority as a
from dex.core import events as e
from dex.core import program as p
from dex.core import runtime as r
from dex.verification import verify_registration


@dataclass(frozen=True)
class LocalSession:
    actor: str
    company: e.CompanyContext


class WorkspaceError(ValueError):
    pass


def _no_fault(point: str) -> None:
    pass


class Workspace:
    state: r.WorkspaceState
    catalog: r.ProgramCatalog

    def __init__(
        self,
        path: Path,
        session: LocalSession,
        adapters: Mapping[str, Adapter],
        fault: Callable[[str], None] = _no_fault,
    ) -> None:
        self.session = session
        self.adapters = adapters
        self.fault = fault
        self.connection = sqlite3.connect(path, isolation_level=None, timeout=5)
        try:
            version = self.connection.execute("PRAGMA user_version").fetchone()[0]
            tables = self.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            if version not in (0, 1) or version == 0 and tables:
                raise WorkspaceError("workspace_version")
            self.connection.execute("PRAGMA synchronous=FULL")
            if version == 0:
                with self._transaction():
                    self.connection.execute(
                        "CREATE TABLE events (revision INTEGER PRIMARY KEY, payload TEXT NOT NULL)"
                    )
                    self.connection.execute(
                        "CREATE TABLE artifacts (digest TEXT PRIMARY KEY, content_hash TEXT NOT NULL, payload TEXT NOT NULL)"
                    )
                    self.connection.execute("PRAGMA user_version=1")
            self.catalog = r.ProgramCatalog(())
            self.state = r.rebuild((), self.catalog)
            with self._transaction():
                self._refresh(force=True)
        except BaseException:
            self.connection.close()
            raise

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self.connection.close()

    @contextmanager
    def _transaction(self) -> Generator[None]:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.connection.execute("COMMIT")
        except BaseException:
            self.connection.execute("ROLLBACK")
            raise

    def _refresh(self, force: bool = False) -> None:
        revision = self.connection.execute(
            "SELECT coalesce(max(revision), 0) FROM events"
        ).fetchone()[0]
        if not force and revision == self.state.revision:
            return
        entries: list[r.ArtifactEntry] = []
        for digest, content_hash, raw in self.connection.execute(
            "SELECT digest, content_hash, payload FROM artifacts ORDER BY digest"
        ):
            if sha256(raw.encode()).hexdigest() != content_hash:
                raise WorkspaceError("artifact_corrupt")
            artifact = codec.loads(raw, p.StructuralArtifact)
            pin = r.artifact_pin(artifact)
            if pin.digest != digest:
                raise WorkspaceError("artifact_identity")
            entries.append(r.ArtifactEntry(pin, artifact))
        catalog = r.ProgramCatalog(tuple(entries))
        events = tuple(
            codec.loads(raw, e.RuntimeEvent)
            for _, raw in self.connection.execute(
                "SELECT revision, payload FROM events ORDER BY revision"
            )
        )
        state = r.rebuild(events, catalog)
        if state.revision != revision:
            raise WorkspaceError("event_sequence")
        refusal = r.authorize_workspace_company(state, self.session.company.company_id)
        if refusal is not None:
            raise WorkspaceError(refusal.code)
        self.catalog, self.state = catalog, state

    def refresh(self) -> r.WorkspaceState:
        with self._transaction():
            self._refresh()
        return self.state

    def _bind(self, command: e.Command) -> e.Command:
        command = replace(command, meta=replace(command.meta, actor=self.session.actor))
        if isinstance(command, (e.RegisterProgram, e.ApproveProgram, e.StartSandbox)):
            command = replace(command, company=self.session.company)
        if isinstance(
            command,
            (
                e.RespondTask,
                e.ReassignTask,
                e.CancelTask,
                e.CorrectResult,
                e.ApproveEffect,
                e.RevokeEffectApproval,
                e.AmendEffect,
            ),
        ):
            command = replace(
                command,
                action=replace(
                    command.action,
                    actor=self.session.actor,
                    company_id=self.session.company.company_id,
                    origin="dex",
                ),
            )
        return command

    def _append(
        self, command: e.Command, artifact: p.StructuralArtifact | None = None
    ) -> r.Accepted | r.Refused:
        command = self._bind(command)
        with self._transaction():
            self._refresh()
            if command.meta.expected_revision != self.state.revision:
                return r.Refused("stale_revision")
            session_refusal = r.authorize_session(
                self.state, command, self.session.company
            )
            if session_refusal is not None:
                return session_refusal
            catalog = self.catalog
            if artifact is not None:
                pin = r.artifact_pin(artifact)
                if pin not in catalog.artifacts:
                    catalog = r.ProgramCatalog(
                        (*catalog.entries, r.ArtifactEntry(pin, artifact))
                    )
            result = r.decide(self.state, command, catalog)
            if isinstance(result, r.Refused):
                return result
            self.fault("before_append")
            if artifact is not None:
                raw = codec.dumps(artifact)
                self.connection.execute(
                    "INSERT OR IGNORE INTO artifacts VALUES (?, ?, ?)",
                    (
                        r.artifact_pin(artifact).digest,
                        sha256(raw.encode()).hexdigest(),
                        raw,
                    ),
                )
            self.connection.executemany(
                "INSERT INTO events VALUES (?, ?)",
                (
                    (self.state.revision + ordinal + 1, codec.dumps(event))
                    for ordinal, event in enumerate(result.events)
                ),
            )
            self.fault("after_append")
        self.state, self.catalog = result.state, catalog
        return result

    def register(
        self, meta: e.CommandMeta, draft: p.ProgramDraft, sources: p.SourceCatalog
    ) -> r.Accepted | r.Refused:
        checked = verify_registration(draft, sources, meta.observed_at)
        if isinstance(checked, p.StructuralFailure):
            return r.Refused("program_verification")
        command = e.RegisterProgram(
            meta,
            r.artifact_pin(checked.artifact),
            checked.missing_checks,
            self.session.company,
        )
        return self._append(command, checked.artifact)

    def execute(self, command: e.Command) -> r.Accepted | r.Refused:
        if isinstance(
            command,
            (
                e.RegisterProgram,
                e.ReserveDispatch,
                e.BeginEffectAttempt,
                e.ConfirmEffect,
                e.ReconcileEffect,
                e.MarkEffectUncertain,
            ),
        ):
            return r.Refused("internal_command")
        return self._append(command)

    def _dispatch_eligibility(self, ref: a.EffectRef) -> r.Refused | None:
        return r.authorize_program(
            self.state, self.state.effects[ref].revision.artifact
        )

    def _meta(self, command_id: str, at: datetime) -> e.CommandMeta:
        return e.CommandMeta(
            command_id, self.session.actor, at, at, self.state.revision
        )

    def _request(self, ref: a.EffectRef, attempt_id: str) -> DispatchRequest:
        reservation = self.state.reservations[(ref.key, attempt_id)]
        return DispatchRequest(
            sha256(codec.dumps(ref.key).encode()).hexdigest(),
            self.state.effects[ref].revision,
            attempt_id,
            reservation.adapter_revision,
        )

    def dispatch(self, ref: a.EffectRef, at: datetime) -> r.Accepted | r.Refused:
        self.refresh()
        if ref not in self.state.effects:
            return r.Refused("unknown_effect")
        eligibility = self._dispatch_eligibility(ref)
        if eligibility is not None:
            return eligibility
        if ref.key in self.state.unresolved_attempts:
            return self.reconcile(self.state.unresolved_attempts[ref.key], at)
        adapter = self.adapters.get(ref.key.operation)
        if adapter is None:
            return r.Refused("adapter_unavailable")
        if self.state.dispatch_counts.get(ref.key, 0) >= r.MAX_DISPATCHES:
            return r.Refused("retry_exhausted")
        attempt_id = (
            sha256(codec.dumps(ref.key).encode()).hexdigest()
            + "/"
            + str(self.state.revision)
        )
        begun = self._append(
            e.BeginEffectAttempt(self._meta("begin/" + attempt_id, at), ref, attempt_id)
        )
        if isinstance(begun, r.Refused):
            return begun
        self.fault("attempt_durable")
        reserved = self._append(
            e.ReserveDispatch(
                self._meta("reserve/" + attempt_id, at),
                ref,
                attempt_id,
                adapter.revision,
            )
        )
        if isinstance(reserved, r.Refused):
            return reserved
        self.fault("reservation_durable")
        with self._transaction():
            self._refresh()
            session_refusal = r.authorize_session(
                self.state,
                e.ReserveDispatch(
                    self._meta("admit/" + attempt_id, at),
                    ref,
                    attempt_id,
                    adapter.revision,
                ),
                self.session.company,
            )
            if session_refusal is not None:
                return session_refusal
            allowed = r.authorize_dispatch(
                self.state,
                ref,
                attempt_id,
                self._meta("admit/" + attempt_id, at),
                adapter.revision,
                self.catalog,
                self.session.company,
            )
            if isinstance(allowed, r.Refused):
                return allowed
            self.fault("before_dispatch")
            outcome = adapter.execute(self._request(ref, attempt_id))
            self.fault("after_dispatch")
        self.fault("before_confirmation")
        return self._record(ref, attempt_id, outcome, at, confirmation=True)

    def _record(
        self,
        ref: a.EffectRef,
        attempt_id: str,
        outcome: Outcome,
        at: datetime,
        confirmation: bool = False,
    ) -> r.Accepted | r.Refused:
        for _ in range(r.MAX_DISPATCHES):
            self.refresh()
            meta = self._meta(f"observe/{attempt_id}/{self.state.revision}", at)
            if isinstance(outcome, Pending):
                command: e.EffectCommand = e.MarkEffectUncertain(
                    meta, ref, attempt_id, outcome.evidence
                )
            elif isinstance(outcome, a.Applied) and confirmation:
                command = e.ConfirmEffect(meta, ref, attempt_id, outcome.receipt)
            else:
                command = e.ReconcileEffect(meta, ref, attempt_id, outcome)
            if isinstance(outcome, a.Applied):
                reservation = self.state.reservations[(ref.key, attempt_id)]
                if outcome.receipt.adapter_revision != reservation.adapter_revision:
                    return r.Refused("adapter_revision")
            result = self._append(command)
            if not isinstance(result, r.Refused) or result.code != "stale_revision":
                return result
        return r.Refused("confirmation_conflict")

    def reconcile(self, ref: a.EffectRef, at: datetime) -> r.Accepted | r.Refused:
        self.refresh()
        session_refusal = r.authorize_session(
            self.state,
            e.BeginEffectAttempt(self._meta("reconcile", at), ref, "reconcile"),
            self.session.company,
        )
        if session_refusal is not None:
            return session_refusal
        effect = self.state.effects[ref]
        progress = effect.progress
        if not isinstance(progress, (a.Attempted, a.Uncertain)):
            return r.Refused("effect_attempt_state")
        attempt = progress if isinstance(progress, a.Attempted) else progress.attempt
        reservation = self.state.reservations.get((ref.key, attempt.attempt_id))
        if reservation is None:
            return self._append(
                e.ReconcileEffect(
                    self._meta("undispatched/" + attempt.attempt_id, at),
                    ref,
                    attempt.attempt_id,
                    a.FencedNotApplied("no durable dispatch reservation"),
                )
            )
        adapter = self.adapters.get(ref.key.operation)
        if adapter is None or adapter.revision != reservation.adapter_revision:
            return r.Refused("adapter_unavailable")
        outcome = adapter.reconcile(self._request(ref, attempt.attempt_id))
        return self._record(ref, attempt.attempt_id, outcome, at)

    def recover(
        self, at: datetime, limit: int = 1000
    ) -> tuple[r.Accepted | r.Refused, ...]:
        if not 0 < limit <= 1000:
            raise WorkspaceError("recovery_limit")
        self.refresh()
        unresolved = tuple(self.state.unresolved_attempts.values())[:limit]
        return tuple(self.reconcile(ref, at) for ref in unresolved)

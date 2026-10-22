import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from threading import Event
from unittest.mock import patch

import pytest

from dex import codec
from dex.core import authority as a
from dex.core import events as e
from dex.core import language as lang
from dex.core import program as p
from dex.core import runtime as r
from dex.eval.recovery import run_recovery
from dex.eval.recovery_fixture import (
    COMPANY,
    NOW,
    SESSION,
    SOURCES,
    DeterministicAdapter,
    Fault,
    Interrupted,
    SandboxWorkspace,
    action,
    meta,
    program,
    setup,
)
from dex.verification import VerifiedProgram, verify_registration
from dex.workspace import LocalSession, Workspace, WorkspaceError


@pytest.mark.parametrize(
    "point",
    [
        "before_append",
        "after_append",
        "attempt_durable",
        "reservation_durable",
        "before_dispatch",
        "after_dispatch",
        "before_confirmation",
        "remote_commit",
    ],
)
def test_crash_boundaries_preserve_one_effect(tmp_path: Path, point: str) -> None:
    adapter = DeterministicAdapter(tmp_path / "remote")
    path = tmp_path / "workspace"
    with SandboxWorkspace(path, SESSION, {"publish": adapter}) as workspace:
        ref = setup(workspace)[0]
        if point == "remote_commit":
            adapter.fault = Fault(point)
        else:
            workspace.fault = Fault(point)
        with pytest.raises(Interrupted):
            workspace.dispatch(ref, NOW)
        if point in {"before_append", "after_append"}:
            assert not workspace.state.unresolved_attempts
            assert adapter.writes() == 0
    adapter.fault = lambda point: None
    with SandboxWorkspace(path, SESSION, {"publish": adapter}) as workspace:
        assert all(isinstance(result, r.Accepted) for result in workspace.recover(NOW))
        if not workspace.state.confirmed_effects:
            assert isinstance(workspace.dispatch(ref, NOW), r.Accepted)
        assert adapter.writes() == 1
        assert workspace.state.confirmed_effects[ref.key] == ref
        assert {key for key, _ in workspace.state.reservations} == {ref.key}


def test_revocation_between_reservation_and_admission_blocks_write(
    tmp_path: Path,
) -> None:
    adapter = DeterministicAdapter(tmp_path / "remote")
    path = tmp_path / "workspace"
    with SandboxWorkspace(path, SESSION, {"publish": adapter}) as workspace:
        ref = setup(workspace)[0]
        progress = workspace.state.effects[ref].progress
        assert isinstance(progress, a.Approved)

        def revoke(point: str) -> None:
            if point == "reservation_durable":
                with SandboxWorkspace(path, SESSION, {"publish": adapter}) as other:
                    result = other.execute(
                        e.RevokeEffectApproval(
                            meta(other, "revoke"),
                            ref,
                            r.action_key(progress.approval.action),
                            action("revoke"),
                        )
                    )
                    assert isinstance(result, r.Accepted)

        workspace.fault = revoke
        assert workspace.dispatch(ref, NOW) == r.Refused("approval_revoked")
        assert adapter.writes() == 0


def test_delayed_completion_after_revocation_is_reconciled(tmp_path: Path) -> None:
    adapter = DeterministicAdapter(tmp_path / "remote", "delayed")
    path = tmp_path / "workspace"
    with SandboxWorkspace(path, SESSION, {"publish": adapter}) as workspace:
        ref = setup(workspace)[0]
        assert isinstance(workspace.dispatch(ref, NOW), r.Accepted)
        progress = workspace.state.effects[ref].progress
        assert isinstance(progress, a.Uncertain)
        assert adapter.lookup(ref.key) is None
        assert isinstance(
            workspace.execute(
                e.RevokeEffectApproval(
                    meta(workspace, "revoke"),
                    ref,
                    r.action_key(progress.attempt.approval.action),
                    action("revoke"),
                )
            ),
            r.Accepted,
        )
        adapter.finish(progress.attempt.attempt_id)
    with SandboxWorkspace(path, SESSION, {"publish": adapter}) as workspace:
        assert isinstance(workspace.recover(NOW)[0], r.Accepted)
        assert ref in workspace.state.confirmed_effects.values()
        assert adapter.writes() == 1


def test_fence_prevents_old_delayed_commit(tmp_path: Path) -> None:
    adapter = DeterministicAdapter(tmp_path / "remote", "delayed")
    with SandboxWorkspace(
        tmp_path / "workspace", SESSION, {"publish": adapter}
    ) as workspace:
        ref = setup(workspace)[0]
        assert isinstance(workspace.dispatch(ref, NOW), r.Accepted)
        progress = workspace.state.effects[ref].progress
        assert isinstance(progress, a.Uncertain)
        old = progress.attempt.attempt_id
        adapter.finish(old, fence=True)
        assert isinstance(workspace.recover(NOW)[0], r.Accepted)
        adapter.mode = "immediate"
        assert isinstance(workspace.dispatch(ref, NOW), r.Accepted)
        adapter.finish(old)
        assert adapter.writes() == 1
        assert workspace.state.dispatch_counts[ref.key] == 2


@pytest.mark.parametrize("foreign", [True, False])
def test_current_session_cannot_borrow_stored_actor_authority(
    tmp_path: Path, foreign: bool
) -> None:
    adapter = DeterministicAdapter(tmp_path / "remote")
    path = tmp_path / "workspace"
    with SandboxWorkspace(path, SESSION, {"publish": adapter}) as workspace:
        ref = setup(workspace, approve=False)[0]
    company = (
        replace(COMPANY, company_id="other")
        if foreign
        else replace(COMPANY, memberships=())
    )
    if foreign:
        with pytest.raises(WorkspaceError, match="session_company"):
            SandboxWorkspace(
                path, LocalSession("operator", company), {"publish": adapter}
            )
        return
    with SandboxWorkspace(
        path, LocalSession("operator", company), {"publish": adapter}
    ) as workspace:
        before = workspace.state
        result = workspace.execute(
            e.ApproveEffect(meta(workspace, "forged"), ref, action("forged"))
        )
        assert result == r.Refused(
            "session_company" if foreign else "session_authority"
        )
        assert workspace.state == before


def test_pending_program_cannot_be_approved_or_dispatched_normally(
    tmp_path: Path,
) -> None:
    adapter = DeterministicAdapter(tmp_path / "remote")
    with Workspace(tmp_path / "workspace", SESSION, {"publish": adapter}) as workspace:
        ref = setup(workspace)[0]
        pin = next(iter(workspace.state.registrations))
        assert workspace.execute(
            e.ApproveProgram(meta(workspace, "approve-program"), pin, COMPANY)
        ) == r.Refused("verification_incomplete")
        assert workspace.dispatch(ref, NOW) == r.Refused("verification_incomplete")
        assert workspace.execute(
            e.ActivateProgram(meta(workspace, "activate"), pin)
        ) == r.Refused("unsupported_activation")
        assert adapter.writes() == 0


def test_saved_scenarios_are_executed_and_wrong_expected_value_stays_pending() -> None:
    draft, _ = program(effects=False)
    assert isinstance(verify_registration(draft, SOURCES, NOW), VerifiedProgram)
    wrong = replace(
        draft, scenarios=(replace(draft.scenarios[0], expected=p.IntValue(8)),)
    )
    result = verify_registration(wrong, SOURCES, NOW)
    assert isinstance(result, p.ExecutionPending)
    assert p.MissingCheck.SCENARIOS in result.missing_checks
    assert isinstance(
        verify_registration(replace(draft, scenarios=()), SOURCES, NOW),
        p.ExecutionPending,
    )


def test_reopen_rebuild_never_interprets_or_dispatches(tmp_path: Path) -> None:
    adapter = DeterministicAdapter(tmp_path / "remote")
    path = tmp_path / "workspace"
    with SandboxWorkspace(path, SESSION, {"publish": adapter}) as workspace:
        setup(workspace, waiting=True)
        state = workspace.state
    with (
        patch.object(
            lang, "execute_function", side_effect=AssertionError("interpretation")
        ),
        patch.object(adapter, "execute", side_effect=AssertionError("dispatch")),
        patch.object(r, "decide", side_effect=AssertionError("decision")),
    ):
        with Workspace(path, SESSION, {}) as workspace:
            assert workspace.state == state


@pytest.mark.parametrize("corruption", ["artifact", "event", "version"])
def test_corrupt_persistence_is_refused_without_repairing_bytes(
    tmp_path: Path, corruption: str
) -> None:
    path = tmp_path / "workspace"
    with Workspace(path, SESSION, {}) as workspace:
        draft, _ = program(effects=False)
        assert isinstance(
            workspace.register(meta(workspace, "register"), draft, SOURCES), r.Accepted
        )
    connection = sqlite3.connect(path)
    if corruption == "artifact":
        connection.execute("UPDATE artifacts SET payload='{}'")
    elif corruption == "event":
        raw = json.loads(connection.execute("SELECT payload FROM events").fetchone()[0])
        raw["value"]["format_version"] = 99
        connection.execute("UPDATE events SET payload=?", (json.dumps(raw),))
    else:
        connection.execute("PRAGMA user_version=99")
    connection.commit()
    connection.close()
    before = path.read_bytes()
    with pytest.raises((WorkspaceError, r.ReplayError, codec.CodecError)):
        Workspace(path, SESSION, {})
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "name",
    [
        "complete",
        "before-attempt",
        "before-write",
        "after-remote-commit",
        "lookup-absent-inflight",
        "delayed-old-revision",
        "concurrent-review",
        "rebuild",
        "retry-bound",
        "invalid-import",
    ],
)
def test_recovery_scenario(tmp_path: Path, name: str) -> None:
    source = Path("tests/scenarios/recovery-" + name + ".json").read_bytes()
    assert run_recovery(source, tmp_path / "run") == 0


def test_absence_without_reservation_cannot_fence_concurrent_admission(
    tmp_path: Path,
) -> None:
    path = tmp_path / "workspace"
    adapter = DeterministicAdapter(tmp_path / "remote", "delayed")
    with SandboxWorkspace(path, SESSION, {"publish": adapter}) as workspace:
        ref = setup(workspace)[0]
    begun, absence_observed, admitted = Event(), Event(), Event()

    class RecoveringWorkspace(SandboxWorkspace):
        def _append(
            self, command: e.Command, artifact: p.StructuralArtifact | None = None
        ) -> r.Accepted | r.Refused:
            if isinstance(command, e.ReconcileEffect) and isinstance(
                command.conclusion, a.FencedNotApplied
            ):
                absence_observed.set()
                assert admitted.wait(10)
            return super()._append(command, artifact)

    def dispatch() -> r.Accepted | r.Refused:
        def barrier(point: str) -> None:
            if point == "attempt_durable":
                begun.set()
                assert absence_observed.wait(10)

        with SandboxWorkspace(
            path, SESSION, {"publish": adapter}, barrier
        ) as workspace:
            try:
                return workspace.dispatch(ref, NOW)
            finally:
                admitted.set()

    def recover() -> r.Accepted | r.Refused:
        assert begun.wait(10)
        with RecoveringWorkspace(path, SESSION, {"publish": adapter}) as workspace:
            return workspace.reconcile(ref, NOW)

    with ThreadPoolExecutor(max_workers=2) as executor:
        sender = executor.submit(dispatch)
        recovery = executor.submit(recover)
        assert isinstance(sender.result(), r.Accepted)
        assert recovery.result() == r.Refused("stale_revision")
    with SandboxWorkspace(path, SESSION, {"publish": adapter}) as workspace:
        assert ref.key in workspace.state.unresolved_attempts
        assert isinstance(workspace.state.effects[ref].progress, a.Uncertain)
        assert workspace.state.dispatch_counts[ref.key] == 1


def test_retry_exhaustion_survives_restart_without_new_intent(tmp_path: Path) -> None:
    path = tmp_path / "workspace"
    adapter = DeterministicAdapter(tmp_path / "remote", "reject")
    with SandboxWorkspace(path, SESSION, {"publish": adapter}) as workspace:
        ref = setup(workspace)[0]
        for _ in range(r.MAX_DISPATCHES):
            assert isinstance(workspace.dispatch(ref, NOW), r.Accepted)
        before = workspace.state
    with SandboxWorkspace(path, SESSION, {"publish": adapter}) as workspace:
        assert workspace.dispatch(ref, NOW) == r.Refused("retry_exhausted")
        assert workspace.state == before
        assert not workspace.state.unresolved_attempts


def test_current_policy_revokes_approver_before_dispatch(tmp_path: Path) -> None:
    adapter = DeterministicAdapter(tmp_path / "remote")
    path = tmp_path / "workspace"
    with SandboxWorkspace(path, SESSION, {"publish": adapter}) as workspace:
        ref = setup(workspace)[0]
    company = replace(
        COMPANY,
        policy_revision="policy-2",
        memberships=tuple(
            role for role in COMPANY.memberships if role.role != "effect_approver"
        ),
    )
    with SandboxWorkspace(
        path, LocalSession(SESSION.actor, company), {"publish": adapter}
    ) as workspace:
        assert isinstance(workspace.dispatch(ref, NOW), r.Refused)
        assert adapter.writes() == 0


def test_unauthorized_reconciliation_never_contacts_adapter(tmp_path: Path) -> None:
    adapter = DeterministicAdapter(tmp_path / "remote")
    path = tmp_path / "workspace"
    with SandboxWorkspace(path, SESSION, {"publish": adapter}) as workspace:
        ref = setup(workspace)[0]
        workspace.fault = Fault("reservation_durable")
        with pytest.raises(Interrupted):
            workspace.dispatch(ref, NOW)
    company = replace(COMPANY, memberships=())
    with SandboxWorkspace(
        path, LocalSession(SESSION.actor, company), {"publish": adapter}
    ) as workspace:
        with patch.object(
            adapter,
            "reconcile",
            side_effect=AssertionError("unauthorized adapter contact"),
        ):
            assert workspace.reconcile(ref, NOW) == r.Refused("session_authority")

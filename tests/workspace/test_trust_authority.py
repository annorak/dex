from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from threading import Barrier

import pytest

from dex.core import authority as a
from dex.core import events as e
from dex.core import runtime as r
from dex.eval.recovery_fixture import DeterministicAdapter, SandboxWorkspace
from dex.eval.trust_fixture import NOW, POLICY, SESSION, TrustFixture
from dex.workspace import LocalSession, Workspace


@pytest.fixture(scope="module")
def qualified(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("qualified")
    fixture = TrustFixture(path)
    fixture.train()
    fixture.grant()
    fixture.start("case")
    fixture.workspace.close()
    return path


@pytest.fixture
def stored(qualified: Path, tmp_path: Path) -> Path:
    for name in ("workspace.db", "remote.db"):
        (tmp_path / name).write_bytes((qualified / name).read_bytes())
    return tmp_path


def test_revocation_between_reservation_and_dispatch_blocks_adapter(
    stored: Path,
) -> None:
    barrier = Barrier(2, timeout=20)
    adapter = DeterministicAdapter(stored / "remote.db")
    path = stored / "workspace.db"

    def fault(point: str) -> None:
        if point == "reservation_durable":
            barrier.wait()
            barrier.wait()

    def dispatch() -> r.Accepted | r.Refused:
        with SandboxWorkspace(path, SESSION, {"publish": adapter}, fault) as workspace:
            return workspace.dispatch(workspace.state.case_effects["case"][0], NOW)

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(dispatch)
        barrier.wait()
        with Workspace(path, SESSION, {}) as workspace:
            result = workspace.execute(
                e.RevokeStandingGrant(
                    e.CommandMeta(
                        "revoke", "source", NOW, NOW, workspace.state.revision
                    ),
                    "grant",
                    e.HumanAction(
                        POLICY.company_id, "dex", "revoke", "source", "controller", NOW
                    ),
                    POLICY,
                )
            )
            assert isinstance(result, r.Accepted)
        barrier.wait()
        assert future.result(timeout=20) == r.Refused("grant_revoked")
    assert adapter.writes() == 300
    with SandboxWorkspace(path, SESSION, {"publish": adapter}) as workspace:
        ref = workspace.state.case_effects["case"][0]
        assert isinstance(workspace.reconcile(ref, NOW), r.Accepted)
        assert workspace.dispatch(ref, NOW) == r.Refused("grant_revoked")
        assert workspace.state.dispatch_counts[ref.key] == 1


def test_concurrent_reviews_have_one_winner_and_one_credit(stored: Path) -> None:
    path = stored / "workspace.db"
    with Workspace(path, SESSION, {}) as workspace:
        revision = workspace.state.revision
    barrier = Barrier(2, timeout=20)

    def review(name: str) -> r.Accepted | r.Refused:
        with Workspace(path, SESSION, {}) as workspace:
            command = e.ReviewResults(
                e.CommandMeta(name, "source", NOW, NOW, revision),
                "case",
                (
                    a.ReviewedResult(
                        e.WorkRevision(e.WorkAddress("case", "calculate"), 1), "clean"
                    ),
                ),
                e.HumanAction(
                    POLICY.company_id, "source", name, "source", "reviewer", NOW
                ),
            )
            barrier.wait()
            return workspace.execute(command)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = tuple(pool.map(review, ("first", "second")))
    assert sum(isinstance(result, r.Accepted) for result in results) == 1
    assert r.Refused("stale_revision") in results
    with Workspace(path, SESSION, {}) as workspace:
        assert (
            next(
                count.clean
                for key, count in workspace.state.trust.items()
                if key.behavior_id == "calculate-1"
            )
            == 301
        )
        assert all(
            command.action.actor == "operator"
            for command in workspace.state.trust_actions.values()
            if isinstance(command, e.ReviewResults)
        )


@pytest.mark.parametrize("permission", ["actor", "role", "scope"])
def test_source_grant_cannot_borrow_controller_permission(
    stored: Path, permission: str
) -> None:
    company = POLICY
    actor = "operator"
    if permission == "actor":
        actor = "intruder"
    elif permission == "role":
        company = replace(
            company,
            memberships=tuple(
                item for item in company.memberships if item.role != "controller"
            ),
        )
    else:
        company = replace(
            company,
            memberships=tuple(
                replace(item, scope=(e.ScopePart("other", "each", "record"),))
                if item.role == "controller"
                else item
                for item in company.memberships
            ),
        )
    with Workspace(
        stored / "workspace.db", LocalSession(actor, company), {}
    ) as workspace:
        before = workspace.state
        original = workspace.state.grants["grant"]
        forged = replace(
            original,
            grant_id="source-grant",
            grantor=replace(original.grantor, action_id="source-grant"),
        )
        command = e.GrantStandingAuthority(
            e.CommandMeta("source-grant", "operator", NOW, NOW, before.revision),
            forged,
            POLICY,
        )
        assert workspace.execute(command) == r.Refused("session_authority")
        assert workspace.state == before


def test_grant_revocation_rejects_stale_revision_without_mutation(stored: Path) -> None:
    with Workspace(stored / "workspace.db", SESSION, {}) as workspace:
        before = workspace.state
        command = e.RevokeStandingGrant(
            e.CommandMeta("stale", "operator", NOW, NOW, before.revision - 1),
            "grant",
            e.HumanAction(
                POLICY.company_id, "dex", "stale", "operator", "controller", NOW
            ),
            POLICY,
        )
        assert workspace.execute(command) == r.Refused("stale_revision")
        assert workspace.state == before


def test_current_controller_membership_is_rechecked_at_dispatch(stored: Path) -> None:
    company = replace(
        POLICY,
        memberships=tuple(
            item for item in POLICY.memberships if item.role != "controller"
        ),
    )
    adapter = DeterministicAdapter(stored / "remote.db")
    with SandboxWorkspace(
        stored / "workspace.db", LocalSession("operator", company), {"publish": adapter}
    ) as workspace:
        ref = workspace.state.case_effects["case"][0]
        assert workspace.dispatch(ref, NOW) == r.Refused("grant_authority")
    assert adapter.writes() == 300

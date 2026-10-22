import json
import os
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from threading import Barrier
from time import perf_counter
from typing import Any

from dex import codec
from dex.core import authority as a
from dex.core import events as e
from dex.core import program as p
from dex.core import runtime as r
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


def _cli(
    out: Path, name: str, request: dict[str, Any], session: Path, database: Path
) -> tuple[int, dict[str, Any]]:
    source = out / (name + ".json")
    source.write_text(json.dumps(request))
    argv = [
        str(Path(sys.executable).with_name("dex")),
        "workspace",
        "command",
        str(database),
        "--command",
        str(source),
    ]
    process = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        env={**os.environ, "DEX_SESSION": str(session)},
        timeout=20,
    )
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    (out / (name + ".txt")).write_text(
        json.dumps({"argv": argv, "revision": revision, "session": str(session)})
        + "\nSTDOUT\n"
        + process.stdout
        + "\nSTDERR\n"
        + process.stderr
        + "\nRESULT\n"
        + json.dumps({"exit_status": process.returncode})
    )
    return process.returncode, json.loads(process.stdout or process.stderr)


def registration_cli(out: Path) -> dict[str, Any]:
    session = out / "session.json"
    session.write_text(
        json.dumps(
            {
                "format": "dex-local-session-1",
                "actor": SESSION.actor,
                "company": json.loads(codec.dumps(COMPANY)),
            }
        )
    )
    draft, _ = program(effects=False)
    common = {
        "format": "dex-workspace-command-1",
        "id": "register",
        "expected_revision": 0,
    }
    status, registered = _cli(
        out,
        "register",
        {
            **common,
            "kind": "register",
            "draft": json.loads(codec.dumps(draft)),
            "sources": json.loads(codec.dumps(SOURCES)),
        },
        session,
        out / "catalog.db",
    )
    assert status == 0, registered
    pin = codec.loads(
        json.dumps(registered["registrations"][0]["artifact"]), e.ArtifactPin
    )
    approved = e.ApproveProgram(
        e.CommandMeta("approve", "source-impostor", NOW, NOW, 1), pin, COMPANY
    )
    request = {
        **common,
        "id": "approve",
        "expected_revision": 1,
        "kind": "apply",
        "command": json.loads(codec.dumps(approved)),
    }
    status, approval = _cli(out, "approve", request, session, out / "catalog.db")
    assert status == 0, approval
    rejected_status, rejection = _cli(
        out, "stale-approval", request, session, out / "catalog.db"
    )
    assert rejected_status == 1 and rejection["failure"] == "stale_revision", rejection
    return {
        "verified_registered": registered["registrations"][0]["missing_checks"] == [],
        "program_approved": approval["registrations"][0]["approved"],
        "session_actor": approval["actor"],
        "stale_rejected": rejected_status == 1,
    }


def _concurrent(
    path: Path, adapter: DeterministicAdapter, revision: int, ref: a.EffectRef
) -> list[str]:
    barrier = Barrier(2)

    def review(index: int) -> str:
        with SandboxWorkspace(path, SESSION, {"publish": adapter}) as workspace:
            command = e.ApproveEffect(
                e.CommandMeta(f"review-{index}", "operator", NOW, NOW, revision),
                ref,
                action(f"review-{index}"),
            )
            barrier.wait(timeout=10)
            result = workspace.execute(command)
            return result.code if isinstance(result, r.Refused) else "accepted"

    with ThreadPoolExecutor(max_workers=2) as executor:
        return sorted(executor.map(review, (1, 2)))


def run_recovery(source: bytes, out: Path) -> int:
    request = json.loads(source)
    if (
        set(request) != {"format", "scenario_id", "expected"}
        or request["format"] != "dex-recovery-scenario-1"
    ):
        raise ValueError("recovery_scenario_format")
    name = request["scenario_id"]
    names = {
        "recovery-complete",
        "recovery-before-attempt",
        "recovery-before-write",
        "recovery-after-remote-commit",
        "recovery-lookup-absent-inflight",
        "recovery-delayed-old-revision",
        "recovery-concurrent-review",
        "recovery-rebuild",
        "recovery-retry-bound",
        "recovery-invalid-import",
        "recovery-size-1000",
    }
    if name not in names:
        raise ValueError("recovery_scenario_name")
    out.mkdir(parents=True, exist_ok=False)
    actual: dict[str, Any] = {"scenario_id": name, "mode": "isolated_adapter_fixture"}
    if name == "recovery-complete":
        actual.update(registration_cli(out))
    mode = (
        "delayed"
        if name in {"recovery-lookup-absent-inflight", "recovery-delayed-old-revision"}
        else ("reject" if name == "recovery-retry-bound" else "immediate")
    )
    adapter = DeterministicAdapter(out / "remote.db", mode)
    path = out / "workspace.db"
    start = perf_counter()
    workspace = SandboxWorkspace(path, SESSION, {"publish": adapter})
    refs = setup(
        workspace,
        count=1000 if name == "recovery-size-1000" else 1,
        waiting=name == "recovery-rebuild",
        approve=name != "recovery-concurrent-review",
    )
    ref = refs[0]
    if name == "recovery-concurrent-review":
        revision = workspace.state.revision
        workspace.close()
        actual["reviews"] = _concurrent(path, adapter, revision, ref)
        workspace = SandboxWorkspace(path, SESSION, {"publish": adapter})
    elif name == "recovery-invalid-import":
        before = path.read_bytes()
        original, _ = program()
        assert isinstance(original.root, p.CodeStep)
        bad = replace(
            original, revision="bad", root=replace(original.root, function_id="missing")
        )
        result = workspace.register(meta(workspace, "invalid"), bad, SOURCES)
        actual["invalid_rejected"] = isinstance(result, r.Refused)
        actual["workspace_unchanged"] = before == path.read_bytes()
        unknown = json.loads(codec.dumps(SOURCES))
        unknown["format"] = "unknown"
        try:
            codec.loads(json.dumps(unknown), p.SourceCatalog)
        except ValueError:
            actual["unknown_version_rejected"] = True
    elif name == "recovery-rebuild":
        first = next(iter(workspace.state.tasks.values()))
        response = workspace.execute(
            e.RespondTask(
                meta(workspace, "respond"),
                first.ref,
                first.reviewed,
                action("respond", "reviewer"),
                p.IntValue(7),
            )
        )
        assert isinstance(response, r.Accepted), response
        actual["business_decisions"] = sum(
            isinstance(item, e.RespondTask) for item in workspace.state.actions.values()
        )
        task = next(
            item for item in workspace.state.tasks.values() if item.status == "open"
        )
        actual["due_time"] = task.due_at.isoformat()
        actual["pending_tasks"] = sum(
            item.status == "open" for item in workspace.state.tasks.values()
        )
        actual["completed_work"] = sum(
            work.completed is not None for work in workspace.state.work.values()
        )
    elif name == "recovery-retry-bound":
        outcomes = [workspace.dispatch(ref, NOW) for _ in range(r.MAX_DISPATCHES + 1)]
        last = outcomes[-1]
        actual["retry_failure"] = last.code if isinstance(last, r.Refused) else None
        actual["reservations"] = workspace.state.dispatch_counts[ref.key]
    else:
        points = {
            "recovery-before-attempt": "before_append",
            "recovery-before-write": "reservation_durable",
            "recovery-after-remote-commit": "remote_commit",
        }
        point = points.get(name)
        if point == "remote_commit":
            adapter.fault = Fault(point)
        elif point is not None:
            workspace.fault = Fault(point)
        for selected in refs:
            if name == "recovery-size-1000":
                workspace.fault = Fault("before_confirmation")
            try:
                result = workspace.dispatch(selected, NOW)
                assert isinstance(result, r.Accepted), result
            except Interrupted:
                actual["interrupted"] = True
        actual["writes_before_reopen"] = adapter.writes()
        actual["unresolved_before_reopen"] = len(workspace.state.unresolved_attempts)
        if name == "recovery-delayed-old-revision":
            progress = workspace.state.effects[ref].progress
            assert isinstance(progress, a.Uncertain)
            completion = Barrier(2)

            def delayed_finish() -> None:
                completion.wait(timeout=10)
                adapter.finish(progress.attempt.attempt_id)

            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(delayed_finish)
                revision = workspace.state.effects[ref].revision.producer
                correction = workspace.execute(
                    e.CorrectResult(
                        meta(workspace, "correct"),
                        revision,
                        action("correct", "corrector"),
                        p.IntValue(8),
                    )
                )
                assert isinstance(correction, r.Accepted), correction
                replacement = workspace.state.current_effects[ref.key]
                assert isinstance(
                    workspace.execute(
                        e.ApproveEffect(
                            meta(workspace, "replacement-approval"),
                            replacement,
                            action("replacement-approval"),
                        )
                    ),
                    r.Accepted,
                )
                workspace.dispatch(replacement, NOW)
                actual["replacement_waited"] = (
                    adapter.writes() == 0
                    and ref.key in workspace.state.unresolved_attempts
                )
                completion.wait(timeout=10)
                future.result()
    if name == "recovery-rebuild":
        session_file = out / "reopen-session.json"
        session_file.write_text(
            json.dumps(
                {
                    "format": "dex-local-session-1",
                    "actor": SESSION.actor,
                    "company": json.loads(codec.dumps(COMPANY)),
                }
            )
        )
        script = "from pathlib import Path; from hashlib import sha256; import sys,json; from dex.workspace import Workspace; from dex.workspace_command import load_session; from dex.core import events as e; w=Workspace(Path(sys.argv[1]),load_session(),{}); print(json.dumps(dict(state_sha256=sha256(repr(w.state).encode()).hexdigest(),tasks=[dict(status=t.status,due_at=t.due_at.isoformat(),node=t.ref.work.address.node_id) for t in w.state.tasks.values()],business_decisions=sum(isinstance(x,e.RespondTask) for x in w.state.actions.values()),completed_work=sum(x.completed is not None for x in w.state.work.values())))); w.close()"
        argv = [sys.executable, "-c", script, str(path)]
        process = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            env={**os.environ, "DEX_SESSION": str(session_file)},
            timeout=20,
        )
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        (out / "fresh-process-rebuild.txt").write_text(
            json.dumps(
                {"argv": argv, "revision": revision, "session": str(session_file)}
            )
            + "\nSTDOUT\n"
            + process.stdout
            + "\nSTDERR\n"
            + process.stderr
            + "\nRESULT\n"
            + json.dumps({"exit_status": process.returncode})
        )
        actual["fresh_process_equal"] = (
            process.returncode == 0
            and json.loads(process.stdout)["state_sha256"]
            == sha256(repr(workspace.state).encode()).hexdigest()
        )
    if name == "recovery-invalid-import":
        session_file = out / "corruption-session.json"
        session_file.write_text(
            json.dumps(
                {
                    "format": "dex-local-session-1",
                    "actor": SESSION.actor,
                    "company": json.loads(codec.dumps(COMPANY)),
                }
            )
        )
        failures: list[str] = []
        preserved: list[bool] = []
        for corruption in ("artifact", "event", "version"):
            damaged = out / (corruption + ".db")
            damaged.write_bytes(path.read_bytes())
            connection = sqlite3.connect(damaged)
            if corruption == "artifact":
                connection.execute("UPDATE artifacts SET payload='{}'")
            elif corruption == "event":
                raw = json.loads(
                    connection.execute(
                        "SELECT payload FROM events WHERE revision=1"
                    ).fetchone()[0]
                )
                raw["value"]["format_version"] = 99
                connection.execute(
                    "UPDATE events SET payload=? WHERE revision=1", (json.dumps(raw),)
                )
            else:
                connection.execute("PRAGMA user_version=99")
            connection.commit()
            connection.close()
            before_bytes = damaged.read_bytes()
            status, failure = _cli(
                out,
                "reject-" + corruption,
                {
                    "format": "dex-workspace-command-1",
                    "id": "inspect",
                    "expected_revision": workspace.state.revision,
                    "kind": "inspect",
                },
                session_file,
                damaged,
            )
            assert status == 2, failure
            failures.append(failure["code"])
            preserved.append(damaged.read_bytes() == before_bytes)
        actual["stored_corruptions_rejected"] = failures
        actual["corrupt_bytes_unchanged"] = all(preserved)
    before = workspace.state
    workspace.close()
    appended = perf_counter()
    adapter.fault = lambda point: None
    workspace = SandboxWorkspace(path, SESSION, {"publish": adapter})
    reopened = perf_counter()
    actual["replay_equal"] = workspace.state == before
    if name not in {
        "recovery-concurrent-review",
        "recovery-invalid-import",
        "recovery-rebuild",
    }:
        outcomes = workspace.recover(NOW)
        assert all(isinstance(item, r.Accepted) for item in outcomes), outcomes
    if name == "recovery-before-write":
        assert isinstance(workspace.dispatch(ref, NOW), r.Accepted)
        actual["operation_count"] = len(
            {key for key, _ in workspace.state.reservations}
        )
    if name == "recovery-lookup-absent-inflight":
        actual["lookup_absent"] = adapter.lookup(ref.key) is None
        actual["uncertain_after_recovery"] = isinstance(
            workspace.state.effects[ref].progress, a.Uncertain
        )
        actual["reservations"] = workspace.state.dispatch_counts[ref.key]
    if name == "recovery-delayed-old-revision":
        replacement = workspace.state.current_effects[ref.key]
        result = workspace.dispatch(replacement, NOW)
        actual["replacement_failure"] = (
            result.code if isinstance(result, r.Refused) else None
        )
    actual.update(
        {
            "confirmed_effects": len(workspace.state.confirmed_effects),
            "remote_writes": adapter.writes(),
            "unresolved_attempts": len(workspace.state.unresolved_attempts),
            "revision": workspace.state.revision,
            "state_sha256": sha256(repr(workspace.state).encode()).hexdigest(),
        }
    )
    workspace.close()
    finished = perf_counter()
    actual["timing_seconds"] = {
        "durable_append": appended - start,
        "reopen_rebuild": reopened - appended,
        "recovery": finished - reopened,
        "recovery_workload": finished - start,
    }
    matches = {
        key: actual.get(key) == value for key, value in request["expected"].items()
    }
    (out / "actual.json").write_text(json.dumps(actual, sort_keys=True))
    (out / "expected.json").write_text(
        json.dumps(
            {"expected": request["expected"], "matches": matches}, sort_keys=True
        )
    )
    print(json.dumps(actual, sort_keys=True))
    return 0 if all(matches.values()) else 1

import json
import os
import sqlite3
import sys
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from dex import codec
from dex.core import events as e
from dex.core import program as p
from dex.core import runtime as r
from dex.workspace import LocalSession, Workspace, WorkspaceError

MAX_BYTES = 8 * 1024 * 1024
_COMMANDS: dict[str, type[Any]] = {
    cls.__name__: cls
    for cls in (
        e.StartSandbox,
        e.SignalRepeat,
        e.RespondTask,
        e.ReassignTask,
        e.CancelTask,
        e.CorrectResult,
        e.ApproveEffect,
        e.RevokeEffectApproval,
        e.AmendEffect,
        e.ApproveProgram,
        e.ActivateProgram,
        e.ReviewResults,
        e.GrantStandingAuthority,
        e.RevokeStandingGrant,
    )
}


def _read(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        raw = handle.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise WorkspaceError("input_size")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise WorkspaceError("command_shape")
    return cast(dict[str, Any], value)


def load_session() -> LocalSession:
    path = os.environ.get("DEX_SESSION")
    if path is None:
        raise WorkspaceError("session_required")
    data = _read(Path(path))
    if (
        set(data) != {"format", "actor", "company"}
        or data["format"] != "dex-local-session-1"
        or type(data["actor"]) is not str
        or not data["actor"].strip()
    ):
        raise WorkspaceError("session_format")
    return LocalSession(
        data["actor"], codec.loads(json.dumps(data["company"]), e.CompanyContext)
    )


def run_command(path: Path, command_file: Path) -> int:
    try:
        session = load_session()
        request = _read(command_file)
        common = {"format", "id", "expected_revision", "kind"}
        if (
            not common <= set(request)
            or request["format"] != "dex-workspace-command-1"
            or type(request["id"]) is not str
            or type(request["expected_revision"]) is not int
        ):
            raise WorkspaceError("command_format")
        now = datetime.now(UTC)
        meta = e.CommandMeta(
            request["id"], session.actor, now, now, request["expected_revision"]
        )
        kind = request["kind"]
        registration: tuple[p.ProgramDraft, p.SourceCatalog] | None = None
        if kind == "register":
            if set(request) != common | {"draft", "sources"}:
                raise WorkspaceError("command_fields")
            draft = codec.loads(json.dumps(request["draft"]), p.ProgramDraft)
            sources = codec.loads(json.dumps(request["sources"]), p.SourceCatalog)
            registration = draft, sources
            command = None
        elif kind == "apply":
            if set(request) != common | {"command"}:
                raise WorkspaceError("command_fields")
            encoded = request["command"]
            cls = _COMMANDS.get(encoded.get("value", {}).get("$type"))
            if cls is None:
                raise WorkspaceError("command_kind")
            command = replace(codec.loads(json.dumps(encoded), cls), meta=meta)
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
                    e.ReviewResults,
                    e.RevokeStandingGrant,
                ),
            ):
                command = replace(
                    command, action=replace(command.action, decided_at=now)
                )
            if isinstance(command, e.GrantStandingAuthority):
                command = replace(
                    command,
                    grant=replace(
                        command.grant,
                        grantor=replace(command.grant.grantor, decided_at=now),
                        valid_from=max(now, command.grant.valid_from),
                    ),
                )
        elif kind == "inspect" and set(request) == common:
            command = None
        else:
            raise WorkspaceError("command_kind")
        with Workspace(path, session, {}) as workspace:
            if registration is not None:
                result = workspace.register(meta, *registration)
            elif kind == "inspect":
                read_refusal = r.authorize_catalog_read(
                    session.actor, session.company, now
                )
                result = (
                    read_refusal or r.Accepted((), workspace.state)
                    if meta.expected_revision == workspace.state.revision
                    else r.Refused("stale_revision")
                )
            else:
                assert command is not None
                result = workspace.execute(command)
            output = {
                "format": "dex-workspace-result-1",
                "status": "refused" if isinstance(result, r.Refused) else "accepted",
                "revision": workspace.state.revision,
                "actor": session.actor,
                "failure": result.code if isinstance(result, r.Refused) else None,
                "registrations": [
                    {
                        "artifact": json.loads(codec.dumps(pin)),
                        "missing_checks": list(registration.missing_checks),
                        "approved": pin in workspace.state.program_approvals,
                    }
                    for pin, registration in workspace.state.registrations.items()
                ]
                if r.authorize_catalog_read(session.actor, session.company, now) is None
                else [],
            }
            print(json.dumps(output, sort_keys=True))
            return 1 if isinstance(result, r.Refused) else 0
    except (ValueError, OSError, sqlite3.Error, AttributeError, TypeError) as error:
        print(
            json.dumps({"format": "dex-workspace-error-1", "code": str(error)}),
            file=sys.stderr,
        )
        return 2

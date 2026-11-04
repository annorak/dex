from dataclasses import replace
from datetime import datetime
from hashlib import sha256
from typing import Any

from dex import codec
from dex.bundle.validation import canonical, timestamp
from dex.core import program as p
from dex.eval.ledger import METRICS

AT = "2026-01-04T10:00:00+00:00"
CUTOFF = "2026-01-20T23:59:59+00:00"
TEXT = "Return the supplied value. Request a decision when required."
INTEGER = p.Scalar.INTEGER


def checked_program(
    *, waiting: bool = False, effect: bool = False
) -> tuple[p.ProgramDraft, p.SourceCatalog]:
    content_hash = sha256(TEXT.encode()).hexdigest()
    pin = p.SourcePin("procedure", "r1", content_hash, "text-1", content_hash)
    citation = p.Citation(pin, "all", "paragraph", 0, len(TEXT), TEXT)
    sources = p.SourceCatalog(
        (p.SourceExtraction(pin, TEXT, (p.Section("all", "paragraph", 0, len(TEXT)),)),)
    )
    function = p.FunctionDeclaration(
        "identity",
        (p.Field("value", INTEGER),),
        INTEGER,
        p.FunctionBody("restricted-1", "return value"),
        (
            p.FunctionTest(
                "seven", (p.NamedValue("value", p.IntValue(7)),), p.IntValue(7)
            ),
        ),
    )
    metadata = p.StepMetadata(
        "decide",
        "identity-1",
        TEXT,
        (citation,),
        (p.Binding("value", INTEGER, p.ProgramInputRef("value")),),
        INTEGER,
    )
    root: p.Node = p.CodeStep(metadata, "identity")
    if waiting:
        root = p.HumanStep(
            replace(metadata, inputs=()),
            "reviewer",
            datetime.fromisoformat("2026-01-12T12:00:00+00:00"),
            p.Export(p.Scalar.TEXT, p.Literal(p.TextValue("Provide the decision."))),
            True,
        )
    if effect:
        change = p.ChangeDeclaration(
            "change",
            "publish",
            p.Export(INTEGER, p.Literal(p.IntValue(8))),
            (),
            p.Literal(p.TextValue("once")),
        )
        root = p.CodeStep(replace(metadata, changes=(change,)), "identity")
    draft = p.ProgramDraft(
        "checked-score",
        "r1",
        (),
        (p.Field("value", INTEGER),),
        root,
        (function,),
        (),
        (),
    )
    return draft, sources


def outcome(value: int | None = 7) -> dict[str, Any]:
    return {
        "decision": None if value is None else {"kind": "integer", "value": value},
        "effects": [],
        "waits": [],
    }


def event(
    identity: str,
    case_id: str | None,
    *,
    kind: str = "human",
    phase: str = "runtime",
    category: str | None = "case_review",
    program: str = "r1",
    at: str = AT,
    retry: bool = False,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": identity,
        "company": "synthetic",
        "origin": "recorded-fixture",
        "kind": kind,
        "phase": phase,
        "case_id": case_id,
        "program": program,
        "at": at,
        "provenance": "supplied_history",
        "occurred_at": at,
        "observed_at": at,
        "received_at": at,
        "available_at": at,
        "effective_date": at[:10],
        "category": category if kind == "human" else None,
        "tags": [],
        "actor": "reviewer" if kind == "human" else None,
        "request": "request-" + identity if kind == "model" else None,
        "recording": "recording-" + identity if kind == "model" else None,
        **dict.fromkeys(METRICS, 0),
    }
    row["human_touches"] = int(kind == "human")
    row["logical_invocations"] = int(kind == "model")
    row["retries"] = int(retry)
    row["input_tokens"] = 10 if kind == "model" else 0
    row["output_tokens"] = 2 if kind == "model" else 0
    return row


def fixture(name: str) -> dict[str, Any]:
    allowed = {
        "correct-history-mistake",
        "copied-mistake",
        "effect-field",
        "required-unresolved",
        "key-tamper",
        "arrival-context",
        "calls-touches",
        "week-version",
        "no-history-unimplemented",
        "report-replay",
        "size-10000",
    }
    if name not in allowed:
        raise ValueError("score_fixture_unknown")
    count = (
        10000
        if name == "size-10000"
        else 3
        if name in {"calls-touches", "report-replay", "week-version"}
        else 2
        if name in {"required-unresolved", "arrival-context"}
        else 1
    )
    draft, sources = checked_program(
        waiting=name == "required-unresolved", effect=name == "effect-field"
    )
    programs = {
        "r1": {"draft": codec.dumps(draft), "sources": codec.dumps(sources)},
        "r2": {
            "draft": codec.dumps(replace(draft, revision="r2")),
            "sources": codec.dumps(sources),
        },
    }
    cases: dict[str, Any] = {}
    key: dict[str, Any] = {}
    history: dict[str, Any] = {}
    mistakes: dict[str, Any] = {}
    ledger: list[dict[str, Any]] = []
    for ordinal in range(1, count + 1):
        case_id = "case-" + str(ordinal).zfill(5)
        value = 8 if name == "copied-mistake" else 7
        if name == "arrival-context":
            value = 1
        cases[case_id] = {
            "company": "synthetic",
            "cohort": "scenario",
            "program": "r1",
            "opened_at": AT,
            "business_date": AT[:10],
            "inputs": [codec.dumps(p.NamedValue("value", p.IntValue(value)))],
            "mode": "sandbox"
            if name in {"effect-field", "required-unresolved"}
            else "call",
        }
        key[case_id] = outcome(value if name == "arrival-context" else 7)
        history[case_id] = outcome(
            8 if name in {"correct-history-mistake", "copied-mistake"} else value
        )
        if name in {"correct-history-mistake", "copied-mistake"}:
            mistakes[case_id] = ["/decision/value"]
        if name == "size-10000":
            ledger.extend(
                event(case_id + "-" + str(index), case_id, kind="system")
                for index in range(10)
            )
    first = "case-00001"
    if name == "effect-field":
        key[first]["effects"] = [
            {
                "operation": "publish",
                "scope": [],
                "occurrence": "once",
                "payload": {"kind": "integer", "value": 7},
            }
        ]
        history = {}
    if name == "required-unresolved":
        wait: dict[str, Any] = {
            "node": "decide",
            "scope": [],
            "work_revision": 1,
            "request_revision": 1,
            "role": "reviewer",
            "assignee": None,
            "due_at": "2026-01-12T12:00:00+00:00",
            "request": {"kind": "text", "value": "Provide the decision."},
            "reviewed": [],
            "schema": {"kind": "integer"},
        }
        key[first] = {"decision": None, "effects": [], "waits": [wait]}
        history = {}
    if name in {"calls-touches", "report-replay", "week-version"}:
        ledger = [
            event("model-1", first, kind="model"),
            event("model-retry", first, kind="model", retry=True),
            event("combined", first, category="external_change_approval"),
            event("business", first, category="business_authority"),
            event("input", "case-00002", category="requested_input"),
            event("compile", None, kind="model", phase="compile"),
            event("question", None, phase="compile", category="compile_clarification"),
            event("program", None, phase="administrative", category="program_approval"),
            event(
                "grant",
                None,
                phase="administrative",
                category="authority_administration",
            ),
            event(
                "revoke",
                None,
                phase="administrative",
                category="authority_administration",
            ),
        ]
        ledger[2]["tags"] = ["case_review", "external_change_approval"]
        ledger.append(dict(ledger[2]))
        if name == "week-version":
            ledger[1] = {
                **ledger[1],
                "at": "2026-01-05T10:00:00+00:00",
                "program": "r2",
                "occurred_at": "2026-01-05T10:00:00+00:00",
                "observed_at": "2026-01-05T10:00:00+00:00",
                "received_at": "2026-01-05T10:00:00+00:00",
                "available_at": "2026-01-05T10:00:00+00:00",
                "effective_date": "2026-01-05",
            }
            ledger[4] = {
                **ledger[4],
                "at": "2026-01-12T10:00:00+00:00",
                "program": "r2",
                "occurred_at": "2026-01-12T10:00:00+00:00",
                "observed_at": "2026-01-12T10:00:00+00:00",
                "received_at": "2026-01-12T10:00:00+00:00",
                "available_at": "2026-01-12T10:00:00+00:00",
                "effective_date": "2026-01-12",
            }
    if name == "no-history-unimplemented":
        history = {}
    context: list[dict[str, Any]] = []
    if name == "arrival-context":
        cases["case-00002"]["opened_at"] = "2026-01-05T10:00:00+00:00"
        context = [
            {
                "source_case": first,
                "value": 9,
                "occurred_at": AT,
                "observed_at": "2026-01-04T11:00:00+00:00",
                "received_at": "2026-01-04T12:00:00+00:00",
                "available_at": "2026-01-04T12:00:00+00:00",
                "effective_date": "2026-01-04",
            },
            {
                "source_case": first,
                "value": 99,
                "occurred_at": AT,
                "observed_at": "2026-01-06T11:00:00+00:00",
                "received_at": "2026-01-06T12:00:00+00:00",
                "available_at": "2026-01-06T12:00:00+00:00",
                "effective_date": "2026-01-04",
            },
        ]
        cases["case-00002"]["inputs"] = observed_inputs(
            context, cases["case-00002"]["opened_at"]
        )
        key["case-00002"] = outcome(9)
        history[first] = outcome(9)
        history["case-00002"] = outcome(9)
    return {
        "execution": canonical(
            {
                "format": "dex-frozen-execution-1",
                "programs": programs,
                "cases": cases,
                "cutoff": CUTOFF,
            }
        ),
        "key": key,
        "history": history,
        "mistakes": mistakes,
        "ledger": ledger,
        "context": context,
        "requests": {
            row["request"]: {
                "id": row["request"],
                "company": row["company"],
                "case_id": row["case_id"],
                "program": row["program"],
                "step": "recorded-parse" if row["phase"] == "runtime" else "compile",
                "work_revision": 1,
                "requested_at": AT,
                "delivered_at": row["available_at"],
                "recording": row["recording"],
            }
            for row in ledger
            if row["kind"] == "model"
        },
    }


def observed_inputs(observations: list[dict[str, Any]], arrival: str) -> list[str]:
    boundary = timestamp(arrival, "arrival")
    permitted = [
        row
        for row in observations
        if all(
            timestamp(row[field], field) <= boundary
            for field in ("observed_at", "received_at", "available_at")
        )
    ]
    latest = max(
        permitted, key=lambda row: timestamp(row["observed_at"], "observed_at")
    )
    return [codec.dumps(p.NamedValue("value", p.IntValue(latest["value"])))]

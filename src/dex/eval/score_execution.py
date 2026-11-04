from typing import Any

from dex import codec
from dex.bundle.learning import validate_view
from dex.bundle.model import Bundle, BundleError
from dex.bundle.projection import LearningView, freeze_cohorts, materialize_learning
from dex.bundle.validation import (
    business_date,
    canonical,
    fields,
    items,
    object_value,
    parse_json,
    timestamp,
)
from dex.core import events as e
from dex.core import language as lang
from dex.core import program as p
from dex.eval.scenario_format import FunctionCommand, Program, SandboxCommand
from dex.eval.scenario_output import encode_core
from dex.eval.scenarios import execute


def execute_frozen(content: bytes) -> dict[str, dict[str, Any]]:
    data = parse_json(content, "frozen_execution")
    fields(data, {"format", "programs", "cases", "cutoff"}, set(), "frozen_execution")
    if data["format"] != "dex-frozen-execution-1":
        raise BundleError("execution_version")
    cutoff = timestamp(data["cutoff"], "cutoff")
    programs: dict[str, Program] = {}
    for name, value in object_value(data["programs"], "programs").items():
        raw = object_value(value, "program")
        fields(raw, {"draft", "sources"}, set(), "program")
        programs[name] = Program(
            name,
            codec.loads(raw["draft"], p.ProgramDraft),
            codec.loads(raw["sources"], p.SourceCatalog),
        )
    actual: dict[str, dict[str, Any]] = {}
    calls: list[FunctionCommand] = []
    call_ids: list[str] = []
    for case_id, value in object_value(data["cases"], "cases").items():
        case = object_value(value, "case")
        fields(
            case,
            {
                "company",
                "cohort",
                "program",
                "opened_at",
                "business_date",
                "inputs",
                "mode",
            },
            set(),
            "execution.case",
        )
        if (
            case["cohort"] not in {"learning", "exam", "scenario"}
            or case["program"] not in programs
        ):
            raise BundleError("execution_identity")
        started = timestamp(case["opened_at"], "opened_at") <= cutoff
        row = {key: case[key] for key in ("company", "cohort", "program", "opened_at")}
        row["execution_activity"] = {
            "logical_invocations": 0,
            "network_calls": 0,
            "retries": 0,
            "human_touches": 0,
        }
        row.update(
            status="completed" if started else "not_started",
            decision=None,
            effects=[],
            waits=[],
        )
        actual[case_id] = row
        if not started:
            continue
        inputs = tuple(
            codec.loads(item, p.NamedValue) for item in items(case["inputs"], "inputs")
        )
        if case["mode"] == "call":
            calls.append(
                FunctionCommand(
                    case["program"], "identity", inputs, lang.DEFAULT_LIMITS
                )
            )
            call_ids.append(case_id)
            continue
        if case["mode"] != "sandbox":
            raise BundleError("execution_mode")
        at = timestamp(case["opened_at"], "opened_at")
        command = SandboxCommand(
            case["program"],
            e.CommandMeta("open-" + case_id, "operator", at, at, 0),
            case_id,
            inputs,
            business_date(case["business_date"], "business_date"),
            e.ActivationBounds(),
            company=e.CompanyContext(
                case["company"], "policy-1", (), (), "records-1", frozenset()
            ),
        )
        result = execute((programs[case["program"]],), (command,), "full")
        observation = result.observations[0]
        if observation.runtime is None or observation.runtime.failure is not None:
            raise BundleError("execution_failed: " + observation.status)
        runtime = result.final_runtime
        root = next(work for work in runtime.work if work.opened.parent is None)
        row["decision"] = (
            encode_core(p.normalized_value(root.completed.value))
            if root.completed is not None
            else None
        )
        row["status"] = "completed" if root.completed is not None else "pending"
        row["effects"] = [
            {
                "operation": effect.revision.ref.key.operation,
                "scope": encode_core(effect.revision.ref.key.scope.parts),
                "occurrence": effect.revision.ref.key.occurrence,
                "payload": encode_core(p.normalized_value(effect.revision.payload)),
            }
            for effect in runtime.effects
            if effect.superseded_by is None
        ]
        row["waits"] = [
            {
                "node": task.ref.work.address.node_id,
                "scope": encode_core(task.ref.work.address.scope),
                "work_revision": task.ref.work.revision,
                "request_revision": task.ref.request_revision,
                "role": task.eligible_role,
                "assignee": task.assignee,
                "due_at": task.due_at.isoformat(),
                "request": encode_core(task.request),
                "schema": encode_core(task.schema),
                "reviewed": [
                    {
                        "address": {
                            "case_id": work.address.case_id,
                            "node_id": work.address.node_id,
                            "scope": encode_core(work.address.scope),
                        },
                        "revision": work.revision,
                    }
                    for work in task.reviewed
                ],
            }
            for task in runtime.tasks
            if task.status == "open"
        ]
    if calls:
        result = execute(tuple(programs.values()), tuple(calls), "changes")
        for case_id, observation in zip(call_ids, result.observations, strict=True):
            if not isinstance(observation.function, lang.FunctionResult):
                raise BundleError("execution_failed: " + observation.status)
            actual[case_id]["decision"] = encode_core(
                p.normalized_value(observation.function.value)
            )
    return actual


def freeze_execution(
    bundle: Bundle, draft: p.ProgramDraft, view: LearningView, cohort: str, cutoff: str
) -> bytes:
    learning = validate_view(view.content)
    if (
        learning["company_id"] != bundle.company_id
        or learning["bundle_id"] != bundle.bundle_id
    ):
        raise BundleError("execution_company_identity")
    if timestamp(learning["as_of"], "as_of") != timestamp(cutoff, "cutoff"):
        raise BundleError("execution_cutoff_conflict")
    if (
        materialize_learning(bundle, timestamp(cutoff, "cutoff")).content
        != view.content
    ):
        raise BundleError("execution_projection_identity")
    cohorts = freeze_cohorts(bundle)
    if cohort not in {"learning", "exam"}:
        raise BundleError("execution_cohort")
    members = cohorts.learning if cohort == "learning" else cohorts.exam
    cases = {
        case.case_id: {
            "company": bundle.company_id,
            "cohort": cohort,
            "program": draft.revision,
            "opened_at": case.opened_at.isoformat(),
            "business_date": case.business_date.isoformat(),
            "inputs": [codec.dumps(value) for value in case.facts],
            "mode": "sandbox",
        }
        for case in bundle.cases
        if case.case_id in members
    }
    return canonical(
        {
            "format": "dex-frozen-execution-1",
            "cutoff": cutoff,
            "programs": {
                draft.revision: {
                    "draft": codec.dumps(draft),
                    "sources": codec.dumps(view.catalog),
                }
            },
            "cases": cases,
        }
    )

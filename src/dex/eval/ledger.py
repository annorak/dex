from collections import Counter
from datetime import timedelta
from statistics import median
from typing import Any

from dex.bundle.model import BundleError
from dex.bundle.validation import (
    business_date,
    canonical,
    fields,
    items,
    object_value,
    text,
    timestamp,
)

METRICS: tuple[str, ...] = (
    "logical_invocations",
    "network_calls",
    "retries",
    "input_tokens",
    "output_tokens",
    "cost_micros",
    "human_touches",
)
CATEGORIES = frozenset(
    {
        "compile_clarification",
        "program_approval",
        "case_review",
        "requested_input",
        "business_authority",
        "external_change_approval",
        "authority_administration",
    }
)


def week(at: str) -> str:
    day = timestamp(at, "event.at").date()
    return (day - timedelta(days=day.weekday())).isoformat()


def validate_ledger(
    raw: list[Any], cases: dict[str, Any], cutoff: str, requests: dict[str, Any]
) -> list[dict[str, Any]]:
    events: dict[tuple[str, str, str], dict[str, Any]] = {}
    end = timestamp(cutoff, "cutoff")
    for source in raw:
        row = object_value(source, "ledger.event")
        fields(
            row,
            {
                "id",
                "company",
                "origin",
                "kind",
                "phase",
                "case_id",
                "program",
                "at",
                "category",
                "tags",
                "actor",
                "request",
                "recording",
                "provenance",
                "occurred_at",
                "observed_at",
                "received_at",
                "available_at",
                "effective_date",
                *METRICS,
            },
            set(),
            "ledger.event",
        )
        for name in ("id", "company", "origin", "program"):
            text(row[name], "ledger." + name)
        at = timestamp(row["at"], "ledger.at")
        if row["provenance"] != "supplied_history":
            raise BundleError("ledger_provenance")
        occurred = timestamp(row["occurred_at"], "occurred_at")
        observed = timestamp(row["observed_at"], "observed_at")
        received = timestamp(row["received_at"], "received_at")
        available = timestamp(row["available_at"], "available_at")
        business_date(row["effective_date"], "effective_date")
        if (
            at != occurred
            or occurred > observed
            or observed > available
            or received > available
        ):
            raise BundleError("ledger_chronology")
        if max(at, observed, received, available) > end:
            raise BundleError("ledger_after_cutoff")
        if row["kind"] not in {"model", "human", "system"} or row["phase"] not in {
            "compile",
            "runtime",
            "administrative",
        }:
            raise BundleError("ledger_kind_or_phase")
        case_id = row["case_id"]
        if case_id is not None:
            if case_id not in cases or cases[case_id]["company"] != row["company"]:
                raise BundleError("ledger_case_identity")
            if at < timestamp(cases[case_id]["opened_at"], "case.opened_at"):
                raise BundleError("ledger_before_case")
        if row["kind"] == "human":
            if row["category"] not in CATEGORIES or row["human_touches"] != 1:
                raise BundleError("ledger_human_category")
            text(row["actor"], "ledger.actor")
        elif row["human_touches"] != 0 or row["category"] is not None:
            raise BundleError("ledger_nonhuman_touch")
        for tag in items(row["tags"], "ledger.tags"):
            text(tag, "ledger.tag")
        for name in METRICS:
            if type(row[name]) is not int or row[name] < 0:
                raise BundleError("ledger_nonnegative_integer: " + name)
        if row["kind"] != "model" and any(row[name] for name in METRICS[:-1]):
            raise BundleError("ledger_nonmodel_call")
        if row["kind"] == "model":
            if row["phase"] == "administrative":
                raise BundleError("ledger_model_phase")
            request_id = text(row["request"], "ledger.request")
            if request_id not in requests:
                raise BundleError("ledger_request_missing")
            request = object_value(requests[request_id], "ledger.request")
            fields(
                request,
                {
                    "id",
                    "company",
                    "case_id",
                    "program",
                    "step",
                    "work_revision",
                    "requested_at",
                    "delivered_at",
                    "recording",
                },
                set(),
                "ledger.request",
            )
            if (
                any(
                    request[key] != row[key]
                    for key in ("company", "case_id", "program", "recording")
                )
                or request["id"] != request_id
            ):
                raise BundleError("ledger_request_identity")
            text(request["step"], "ledger.request.step")
            if (
                type(request["work_revision"]) is not int
                or request["work_revision"] < 1
            ):
                raise BundleError("ledger_work_revision")
            if (
                timestamp(request["requested_at"], "requested_at") > available
                or timestamp(request["delivered_at"], "delivered_at") != available
            ):
                raise BundleError("ledger_response_delivery")
            if (
                row["logical_invocations"] != 1
                or row["network_calls"] > 1
                or row["retries"] > 1
            ):
                raise BundleError("ledger_invocation_count")
            if row["phase"] == "runtime" and (
                case_id is None or row["request"] is None
            ):
                raise BundleError("ledger_runtime_attribution")
            if row["retries"] > row["logical_invocations"]:
                raise BundleError("ledger_retry_count")
            if row["recording"] is not None and row["network_calls"]:
                raise BundleError("ledger_recording_network")
        identity = row["company"], row["origin"], row["id"]
        if identity in events and canonical(events[identity]) != canonical(row):
            raise BundleError("ledger_conflicting_identity")
        events[identity] = row
    return sorted(
        events.values(),
        key=lambda row: (
            timestamp(row["at"], "ledger.at"),
            row["company"],
            row["origin"],
            row["id"],
        ),
    )


def distribution(values: list[int]) -> dict[str, Any]:
    denominator = len(values)
    return {
        "denominator": denominator,
        "total": sum(values),
        "frequencies": {
            str(key): count for key, count in sorted(Counter(values).items())
        },
        "zero_count": values.count(0),
        "zero_share": values.count(0) / denominator if denominator else None,
        "mean": sum(values) / denominator if denominator else None,
        "median": median(values) if values else None,
        "maximum": max(values) if values else None,
    }


def summarize(cases: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    case_totals: dict[str, dict[str, int]] = {
        name: dict.fromkeys(METRICS, 0) for name in cases
    }
    phases: dict[str, dict[str, int]] = {
        name: dict.fromkeys(METRICS, 0)
        for name in ("compile", "runtime", "administrative")
    }
    groups: dict[tuple[str, str], dict[str, dict[str, int]]] = {}
    shared: dict[tuple[str, str], dict[str, int]] = {}
    categories: Counter[str] = Counter()
    for case_id, case in cases.items():
        if case["status"] != "not_started":
            groups.setdefault((week(case["opened_at"]), case["program"]), {})[
                case_id
            ] = dict.fromkeys(METRICS, 0)
    for row in rows:
        key = week(row["at"]), row["program"]
        if row["case_id"] is None:
            bucket = shared.setdefault(key, dict.fromkeys(METRICS, 0))
        else:
            bucket = groups.setdefault(key, {}).setdefault(
                row["case_id"], dict.fromkeys(METRICS, 0)
            )
            for metric in METRICS:
                case_totals[row["case_id"]][metric] += row[metric]
        for metric in METRICS:
            bucket[metric] += row[metric]
            phases[row["phase"]][metric] += row[metric]
        if row["category"] is not None:
            categories[row["category"]] += 1
    cohorts = {
        "all": sorted(cases),
        "started": sorted(
            name for name, row in cases.items() if row["status"] != "not_started"
        ),
        "completed": sorted(
            name for name, row in cases.items() if row["status"] == "completed"
        ),
        "pending": sorted(
            name for name, row in cases.items() if row["status"] == "pending"
        ),
        "not_started": sorted(
            name for name, row in cases.items() if row["status"] == "not_started"
        ),
    }

    def bucket_record(members: dict[str, dict[str, int]]) -> dict[str, Any]:
        return {
            "case_ids": sorted(members),
            "denominator": len(members),
            "metrics": {
                metric: distribution([row[metric] for row in members.values()])
                for metric in METRICS
            },
        }

    weekly: dict[str, dict[str, dict[str, int]]] = {}
    versions: dict[str, dict[str, dict[str, int]]] = {}
    for (event_week, version), members in groups.items():
        for target, label in ((weekly, event_week), (versions, version)):
            aggregate = target.setdefault(label, {})
            for name, totals in members.items():
                bucket = aggregate.setdefault(name, dict.fromkeys(METRICS, 0))
                for metric in METRICS:
                    bucket[metric] += totals[metric]
    return {
        "case_totals": case_totals,
        "phases": phases,
        "human_categories": dict(sorted(categories.items())),
        "cohorts": {
            name: bucket_record({case: case_totals[case] for case in ids})
            for name, ids in cohorts.items()
        },
        "weeks": {
            name: bucket_record(members) for name, members in sorted(weekly.items())
        },
        "versions": {
            name: bucket_record(members) for name, members in sorted(versions.items())
        },
        "week_versions": [
            {"week": key[0], "program": key[1], **bucket_record(members)}
            for key, members in sorted(groups.items())
        ],
        "shared": [
            {"week": key[0], "program": key[1], "totals": totals}
            for key, totals in sorted(shared.items())
        ],
        "bucket_denominator": "Distinct cases with a start or recorded event in the bucket. A zero-activity case belongs to its opening week and initial version.",
        "amortization": None,
    }

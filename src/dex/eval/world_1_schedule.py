from datetime import datetime, timedelta
from typing import Any

READ_OPERATIONS = (
    "parse",
    "resolve",
    "cancellation",
    "duplicate",
    "insurance",
    "approver",
    "dates",
    "snow",
)


def behavior(company: str, operation: str, received: str) -> str:
    if operation == "extract_F4":
        return "recorded-AI" if received < "2026-12-04" else "parser-F4"
    if company == "C1":
        if operation == "duplicate" and received >= "2026-11-01":
            return "posted-R"
        if operation == "approver":
            if received >= "2027-01-01":
                return "dated-Harthmere"
            if received >= "2026-11-16T10:00":
                return "Rillhaven"
        if (
            operation
            in (
                "request_approval",
                "eligibility",
                "schedule_payment",
                "request_service_confirmation",
            )
            and received >= "2027-02-01"
        ):
            return "service-confirmation"
    return "initial"


def schedule(
    company: str, cases: list[dict[str, Any]], key: dict[str, Any]
) -> dict[str, Any]:
    actor = "Iona Vale" if company == "C1" else "Orla Fen"
    events: list[dict[str, Any]] = []
    for case in cases:
        if case["cohort"] != "stream":
            continue
        identity = case["case_id"]
        answer = key[identity]
        review = datetime.fromisoformat(case["chronology"]["values_reviewed_at"])
        operations = [
            "extract_F4"
            if operation == "parse" and case["format"] == "F4"
            else operation
            for operation in READ_OPERATIONS
        ]
        if answer["decision"] == "cancellation":
            operations = ["parse", "cancellation"]
        elif answer["decision"] == "duplicate":
            operations = ["parse", "resolve", "cancellation", "duplicate"]
        produced = [
            {
                "operation": operation,
                "behavior": behavior(company, operation, case["received"]),
                "result_revision": 1,
                "outcome": "mistake"
                if case["issue"] == "review-correction" and operation == "approver"
                else "clean",
            }
            for operation in operations
        ]
        if case["issue"] == "review-correction":
            produced = [
                {**entry, "behavior": "initial"}
                if entry["operation"] == "approver"
                else entry
                for entry in produced
            ]
        events.append(
            {
                "id": identity + "/review-values",
                "case_id": identity,
                "at": review.isoformat(),
                "kind": "proposal_review",
                "proposal_id": identity + "/values/1",
                "actor": actor,
                "expected_revision": 1,
                "reviewed_revision": 1,
                "fields": [
                    "identity",
                    "amount",
                    "posting_month",
                    "due_date",
                    "approver",
                    "holds",
                ],
                "producers": produced,
                "decision": "edit"
                if case["issue"] == "review-correction"
                else "approve",
                "case_received": case["received"],
            }
        )
        for offset, effect in enumerate(answer["effects"], 1):
            at = review + timedelta(seconds=offset)
            operation = effect["operation"]
            if operation == "schedule_payment":
                at = max(
                    at,
                    datetime.fromisoformat(answer["eligible_at"])
                    + timedelta(seconds=20),
                )
            producers = [
                {
                    "operation": operation,
                    "behavior": behavior(company, operation, case["received"]),
                    "result_revision": 1,
                    "outcome": "clean",
                    "credit_after": effect["identity"] + "/confirmed",
                }
            ]
            if operation == "schedule_payment":
                producers.insert(
                    0,
                    {
                        "operation": "eligibility",
                        "behavior": behavior(company, "eligibility", case["received"]),
                        "result_revision": 1,
                        "outcome": "clean",
                    },
                )
            events.append(
                {
                    "id": effect["identity"] + "/review",
                    "case_id": identity,
                    "at": at.isoformat(),
                    "kind": "proposal_review",
                    "proposal_id": effect["identity"],
                    "actor": actor,
                    "expected_revision": 1,
                    "reviewed_revision": 1,
                    "fields": list(effect["payload"]),
                    "producers": producers,
                    "decision": "approve",
                    "case_received": case["received"],
                    "effect": effect,
                    "authority": "exact_change_approval",
                }
            )
            confirmed = at + timedelta(microseconds=1)
            if operation == "record_invoice":
                confirmed = datetime.fromisoformat(
                    case["chronology"]["posted_at"]
                ) + timedelta(microseconds=1)
            events.append(
                {
                    "id": effect["identity"] + "/confirmed",
                    "case_id": identity,
                    "at": confirmed.isoformat(),
                    "kind": "effect_confirmation",
                    "effect_identity": effect["identity"],
                    "operation": operation,
                    "behavior": behavior(company, operation, case["received"]),
                    "result_revision": 1,
                    "human_touch": False,
                }
            )
    events.sort(key=lambda event: (datetime.fromisoformat(event["at"]), event["id"]))
    clean: dict[tuple[str, str], int] = {}
    seen: set[tuple[str, str, str]] = set()
    milestones: list[dict[str, Any]] = []
    eligibility: dict[str, dict[str, Any]] = {}
    ordinal = 0
    cases_by_id = {case["case_id"]: case for case in cases}
    for event in events:
        identity = event["case_id"]
        case = cases_by_id[identity]
        if identity not in eligibility and event["kind"] == "proposal_review":
            dependencies = (
                *(
                    "extract_F4"
                    if operation == "parse" and case["format"] == "F4"
                    else operation
                    for operation in READ_OPERATIONS
                ),
                "record_invoice",
                "request_approval",
                "eligibility",
                "schedule_payment",
            )
            qualified = all(
                clean.get(
                    (operation, behavior(company, operation, case["received"])), 0
                )
                >= 300
                for operation in dependencies
            )
            eligible = (
                event["at"] >= "2026-12-20T08:30:00-05:00"
                and qualified
                and case["amount"] <= 500000
                and case["issue"]
                not in (
                    "expired-certificate",
                    "missing-certificate",
                    "unknown-vendor",
                    "ambiguous-community",
                    "conflicting-amount",
                    "community-not-yet-joined",
                    "unanswered",
                )
            )
            if eligible:
                ordinal += 1
            eligibility[identity] = {
                "assigned_before": event["id"],
                "eligible_ordinal": ordinal if eligible else None,
                "sampled": eligible and ordinal % 20 == 0,
                "requires_review": not eligible or ordinal % 20 == 0,
            }
        review = eligibility[identity]["requires_review"]
        event["sampling"] = eligibility[identity]
        if event["kind"] == "proposal_review":
            event["delivered"] = review
            if not review:
                event["actor"] = None
                if "authority" in event:
                    event["authority"] = company + "-grant"
            credits = (
                [entry for entry in event["producers"] if "credit_after" not in entry]
                if review
                else []
            )
        else:
            credits = (
                [
                    {
                        "operation": event["operation"],
                        "behavior": event["behavior"],
                        "outcome": "clean",
                    }
                ]
                if review
                else []
            )
        for entry in credits:
            counted = (identity, entry["operation"], entry["behavior"])
            if counted in seen:
                continue
            seen.add(counted)
            version = (entry["operation"], entry["behavior"])
            clean[version] = (
                0 if entry["outcome"] == "mistake" else clean.get(version, 0) + 1
            )
            if clean[version] == 300:
                milestones.append(
                    {
                        "operation": version[0],
                        "behavior": version[1],
                        "at": event["at"],
                        "case_id": identity,
                    }
                )
    return {
        "format": "dex-world-1-operation-schedule-1",
        "company": company,
        "events": events,
        "counting_basis": "independent specification operations; actual verified step mapping is unavailable until reference execution",
        "first_300_reviews": milestones,
        "sampling": eligibility,
        "sampled_case_ids": [
            identity for identity, value in eligibility.items() if value["sampled"]
        ],
        "opening_prefix": [
            event for event in events if event["at"] <= "2026-10-02T09:30:00-04:00"
        ],
        "cutoff": "2027-03-31T23:59:59-04:00",
        "event_envelopes_are_executable": False,
    }

from copy import deepcopy
from datetime import date, datetime, time, timedelta
from hashlib import sha256
from typing import Any
from zoneinfo import ZoneInfo

from dex.bundle.validation import canonical

ZONE = ZoneInfo("America/New_York")


def moment(day: date, hour: int, minute: int = 0, second: int = 0) -> str:
    return datetime.combine(day, time(hour, minute, second), ZONE).isoformat()


def expectation(case: dict[str, Any]) -> dict[str, Any]:
    identity = case["case_id"]
    number = int(identity[1:])
    historical = identity.startswith("H")
    local = (number - 1) % 12 + 1
    three_day = local in (2, 6, 10) if historical else number in (2, 6, 10, 14)
    five_day = local in (4, 8, 12) if historical else number in (4, 8, 12, 16)
    days = 3 if three_day else 5 if five_day else 0
    opened = date.fromisoformat(case["opened_at"][:10])
    ready = opened + timedelta(days=days)
    finished = ready + timedelta(days=1)
    shared = historical and local == 6
    changes: list[dict[str, str]] = []
    configuration = {"client_id": case["client_id"], "sites": deepcopy(case["sites"])}
    for index, site in enumerate(configuration["sites"]):
        if shared:
            field, value = (
                "payroll_cutover_date",
                (opened + timedelta(days=14)).isoformat(),
            )
        elif days and index == 0:
            field = "pay_frequency" if "payroll" in site["services"] else "site_contact"
            value = (
                "biweekly" if field == "pay_frequency" else site["site_id"] + "-contact"
            )
        else:
            continue
        site[field] = value
        changes.append({"site_id": site["site_id"], "field": field, "value": value})
    request = identity + "-client-request-v1"
    waits: list[dict[str, Any]] = []
    if days:
        waits.append(
            {
                "request_id": request,
                "request_revision": 1,
                "case_id": identity,
                "client_id": case["client_id"],
                "kind": "client_data",
                "actor": case["sponsor"],
                "issued_at": moment(opened, 10),
                "due_at": moment(opened + timedelta(days=3), 23, 59, 59),
                "overdue_at": moment(opened + timedelta(days=4), 0)
                if five_day
                else None,
                "response_id": identity + "-client-response-v1",
                "responded_at": moment(ready, 9),
                "available_at": moment(ready, 9),
                "requires_existing_request": True,
                "changes": changes,
            }
        )
    branches: list[dict[str, Any]] = []
    for index, site in enumerate(case["sites"]):
        for service in site["services"]:
            affected = days and (
                (shared and service == "payroll")
                or (
                    not shared
                    and index == 0
                    and service
                    == ("payroll" if "payroll" in site["services"] else "benefits")
                )
            )
            branches.append(
                {
                    "site_id": site["site_id"],
                    "service": service,
                    "service_id": site["site_id"] + "-" + service,
                    "employee_ids": [
                        employee["employee_id"] for employee in site["employees"]
                    ],
                    "checked_at": moment(opened, 9),
                    "ready_at": moment(ready, 9) if affected else moment(opened, 9),
                }
            )
    payload_hash = sha256(canonical(configuration)).hexdigest()
    summary = {
        "summary_id": identity + "-summary-v1",
        "revision": 1,
        "ready_at": moment(ready, 10),
        "sha256": payload_hash,
        "configuration": configuration,
    }
    owner = {
        "request_id": identity + "-owner-request-v1",
        "request_revision": 1,
        "requested_at": moment(ready, 10),
        "due_at": moment(finished, 10),
        "decision_id": identity + "-owner-decision-v1",
        "actor": "Mara Tern",
        "role": "service_owner",
        "decision": "authorize",
        "decided_at": moment(finished, 10),
        "available_at": moment(finished, 10),
        "summary_id": summary["summary_id"],
        "summary_revision": 1,
        "summary_sha256": payload_hash,
        "never_automate": True,
        "requires_existing_request": True,
    }
    effect_id = "C3-" + identity + "-activate-1"
    authority = {
        "approval_id": identity + "-exact-change-approval-v1",
        "actor": "Veldren setup operator",
        "role": "setup_operator",
        "approved_at": moment(finished, 11),
        "kind": "exact_change",
        "effect_id": effect_id,
        "effect_revision": 1,
        "payload_sha256": payload_hash,
        "business_decision_id": owner["decision_id"],
        "reviews_producing_steps": True,
        "touches": 1,
    }
    return {
        "decision": "activate_after_authorization",
        "case_id": identity,
        "branches": branches,
        "waits": waits,
        "summary": summary,
        "business_decision": owner,
        "engine_authority": authority,
        "effects": [
            {
                "effect_id": effect_id,
                "revision": 1,
                "operation": "activate_configuration",
                "payload": configuration,
                "payload_sha256": payload_hash,
                "business_decision_id": owner["decision_id"],
                "authority_id": authority["approval_id"],
                "applied_at": moment(finished, 12),
                "confirmation_id": identity + "-setup-confirmation",
            }
        ],
        "completed_at": moment(finished, 12),
        "runtime_model_calls": 0,
    }


def change_fixtures() -> dict[str, Any]:
    return {
        "unfamiliar_status": {
            "case_id": "CHANGE-STATUS",
            "client_id": "CHANGE-STATUS-client",
            "program_version": "veldren-status-candidate-1",
            "roster": [
                {
                    "site_id": "CHANGE-STATUS-site-1",
                    "employee_id": "CHANGE-STATUS-employee-1",
                    "display_name": "Synthetic status colleague",
                    "status": "awaiting_roster_review",
                    "service": "payroll",
                },
                {
                    "site_id": "CHANGE-STATUS-site-2",
                    "employee_id": "CHANGE-STATUS-employee-2",
                    "display_name": "Synthetic ready colleague",
                    "status": "active",
                    "service": "benefits",
                },
            ],
            "request": {
                "request_id": "status-meaning-v1",
                "revision": 1,
                "actor": "Mara Tern",
                "issued_at": "2027-02-01T10:00:00-05:00",
                "due_at": "2027-02-02T10:00:00-05:00",
            },
            "response": {
                "request_id": "status-meaning-v1",
                "revision": 1,
                "actor": "Mara Tern",
                "available_at": "2027-02-02T09:00:00-05:00",
                "meaning": "The employee is active; roster review adds no service restriction.",
            },
            "expected": {
                "pending": ["CHANGE-STATUS-site-1/payroll"],
                "ready": ["CHANGE-STATUS-site-2/benefits"],
                "effects_before_resolution": [],
                "requires": [
                    "delivered_answer_citation",
                    "saved_test",
                    "verification",
                    "program_approval",
                ],
            },
        },
        "changed_summary": {
            "case_id": "CHANGE-SUMMARY",
            "client_id": "CHANGE-SUMMARY-client",
            "program_version": "veldren-summary-candidate-1",
            "summaries": [
                {
                    "summary_id": "changed-summary-v1",
                    "revision": 1,
                    "site_contact": "Synthetic contact one",
                    "ready_at": "2027-02-03T10:00:00-05:00",
                },
                {
                    "summary_id": "changed-summary-v2",
                    "revision": 2,
                    "site_contact": "Synthetic contact two",
                    "ready_at": "2027-02-04T10:30:00-05:00",
                },
            ],
            "decisions": [
                {
                    "request_id": "changed-owner-request-v1",
                    "request_revision": 1,
                    "summary_id": "changed-summary-v1",
                    "summary_revision": 1,
                    "actor": "Mara Tern",
                    "at": "2027-02-04T10:00:00-05:00",
                },
                {
                    "request_id": "changed-owner-request-v2",
                    "request_revision": 1,
                    "summary_id": "changed-summary-v2",
                    "summary_revision": 2,
                    "actor": "Mara Tern",
                    "at": "2027-02-05T10:00:00-05:00",
                },
            ],
            "expected": {
                "old_decision_covers_revision_2": False,
                "effects_before_new_decision": [],
                "new_owner_request_at": "2027-02-04T10:30:00-05:00",
                "exact_change_approval_at": "2027-02-05T11:00:00-05:00",
                "activation_at": "2027-02-05T12:00:00-05:00",
            },
        },
    }


def artifacts(specification: dict[str, Any]) -> dict[str, bytes]:
    cases = specification["cases"]
    key = {case["case_id"]: expectation(case) for case in cases}
    observed = specification["observed"]
    mistakes = {
        identity: {
            "field": "activated_at",
            "observed": action["activated_at"],
            "correct": key[identity]["completed_at"],
        }
        for identity, action in observed.items()
        if action["activated_at"] != key[identity]["completed_at"]
    }
    stream = [f"S{number:03d}" for number in range(1, 17)]
    events: list[dict[str, Any]] = []
    responses: list[dict[str, Any]] = []
    for identity, answer in key.items():
        responses.extend(answer["waits"])
        if identity not in stream:
            continue
        common = {"case_id": identity, "program_version": "veldren-stream-required-1"}
        for wait in answer["waits"]:
            events.append(
                {
                    **common,
                    "id": wait["response_id"],
                    "actor": wait["actor"],
                    "at": wait["responded_at"],
                    "kind": "client_response",
                    "touches": 1,
                    "request_id": wait["request_id"],
                }
            )
            if wait["overdue_at"]:
                events.append(
                    {
                        **common,
                        "id": identity + "-overdue",
                        "actor": "system",
                        "at": wait["overdue_at"],
                        "kind": "overdue_notification",
                        "touches": 0,
                        "request_id": wait["request_id"],
                    }
                )
        owner, authority = answer["business_decision"], answer["engine_authority"]
        events.extend(
            [
                {
                    **common,
                    "id": owner["decision_id"],
                    "actor": owner["actor"],
                    "at": owner["decided_at"],
                    "kind": "business_decision",
                    "touches": 1,
                    "request_id": owner["request_id"],
                    "summary_id": owner["summary_id"],
                },
                {
                    **common,
                    "id": authority["approval_id"],
                    "actor": authority["actor"],
                    "at": authority["approved_at"],
                    "kind": "exact_change_approval",
                    "touches": 1,
                    "effect_id": authority["effect_id"],
                },
                {
                    **common,
                    "id": identity + "-activation",
                    "actor": "synthetic_adapter",
                    "at": answer["completed_at"],
                    "kind": "activation",
                    "touches": 0,
                    "effect_id": authority["effect_id"],
                },
            ]
        )
    events.sort(key=lambda event: (event["at"], event["id"]))
    fixture = {
        **specification,
        "learning": [f"H{number:03d}" for number in range(1, 37)],
        "exam": [f"H{number:03d}" for number in range(37, 49)],
        "stream": stream,
        "hidden_rule_evidence": {
            "learning": ["H006", "H018", "H030"],
            "exam": ["H042"],
        },
        "timezone": "America/New_York",
        "week_start": "Monday",
        "cutoffs": {
            "2027-01-10T23:59:59-05:00": {
                "complete": [
                    "S001",
                    "S002",
                    "S003",
                    "S004",
                    "S005",
                    "S006",
                    "S007",
                    "S009",
                ],
                "waiting": ["S008", "S010"],
                "not_opened": ["S011", "S012", "S013", "S014", "S015", "S016"],
            },
            "2027-01-23T23:59:59-05:00": {
                "complete": stream,
                "waiting": [],
                "not_opened": [],
            },
        },
        "required_outcomes": {
            "historical_mismatches": ["H008", "H019", "H031", "H044"],
            "learning_leftovers": ["H008", "H019", "H031"],
            "exam_mismatches": ["H044"],
            "reference_errors": 0,
            "runtime_model_calls": 0,
            "touches_january_10": 19,
            "touches_final": 40,
            "weekly_touches": {
                "2026-12-28": 2,
                "2027-01-04": 17,
                "2027-01-11": 14,
                "2027-01-18": 7,
            },
            "history_clean_review_credit": 0,
            "trusted_steps": [],
            "authority_mode": "per_change",
            "owner_decision_kind": "human",
        },
        "unimplemented": [
            "reference_execution",
            "compiler",
            "learned_stream",
            "trust_execution",
            "touch_count_execution",
            "UI",
        ],
        "key_construction": "independent specification decisions before reference execution",
    }
    scripts = {
        "delivery": "only to the exact existing request at or after its scheduled delivery",
        "client_responses": responses,
        "owner_decisions": [answer["business_decision"] for answer in key.values()],
        "engine_authority": [answer["engine_authority"] for answer in key.values()],
        "employee_answers": [
            {
                "request_id": "shared-payroll-date-v1",
                "request_revision": 1,
                "requested_at": "2026-10-01T09:00:00-04:00",
                "actor": "Mara Tern",
                "available_at": "2026-10-01T10:00:00-04:00",
                "effective_from": "2025-10-01",
                "evidence_cases": ["H006", "H018", "H030"],
                "source_id": "C3-shared-payroll-confirmation",
                "text": "All of a client's payroll sites must use one client-confirmed payroll cutover date.",
                "requires_existing_request": True,
                "saved_test_requirement": "different initial payroll dates require a client-confirmed shared date; benefits-only sites have no payroll date",
            }
        ],
        "program_approval_requirement": {
            "separate_from_business_decisions": True,
            "requires_complete_verification": True,
            "actor": "Mara Tern",
        },
    }
    passage_map = {
        **{
            f"ONB-1.{number}": {"source": "C3-handbook.md", "section": str(number)}
            for number in range(1, 6)
        },
        **{
            f"ONB-E1.{number}": {
                "source": "C3-service-owner-email.md",
                "section": str(number),
            }
            for number in range(1, 4)
        },
    }
    outputs = {
        "answer-key.json": canonical(key),
        "answer-sheet.json": canonical(observed),
        "mistakes.json": canonical(mistakes),
        "fixture.json": canonical(fixture),
        "response-scripts.json": canonical(scripts),
        "passage-map.json": canonical(passage_map),
        "operation-schedule.json": canonical(
            {"status": "fixture_requirements", "events": events}
        ),
        "change-scenarios.json": canonical(change_fixtures()),
    }
    outputs["manifest.json"] = canonical(
        {
            "format": "dex-world-2-evaluator-1",
            "company": "C3",
            "seed": specification["seed"],
            "generator_version": specification["generator_version"],
            "key_frozen_before_reference_execution": True,
            "reference_programs": [],
            "artifacts": {
                name: sha256(content).hexdigest()
                for name, content in sorted(outputs.items())
            },
        }
    )
    return outputs

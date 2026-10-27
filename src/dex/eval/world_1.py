from datetime import date, datetime, timedelta
from hashlib import sha256
from typing import Any
from zoneinfo import ZoneInfo

from dex.bundle.validation import canonical
from dex.eval.world_1_schedule import schedule


def business_due(start: datetime, days: int = 2) -> datetime:
    current = start
    while days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            days -= 1
    return current


def expectation(case: dict[str, Any]) -> dict[str, Any]:
    company = case["company"]
    arrived = datetime.fromisoformat(case["received"]).astimezone(
        ZoneInfo("America/New_York")
    )
    invoiced = date.fromisoformat(case["invoice_date"])
    amount = case["amount"]
    issue = case["issue"]
    limit = 500000
    if case["community"] == "C1-C03":
        limit = 180000 if arrived.date() >= date(2027, 1, 1) else 150000
    elif case["community"] == "C2-C01":
        limit = 250000
    elif case["community"] == "C1-C09" and arrived.date() >= date(2026, 11, 15):
        limit = 200000
    route = "board" if amount > limit else "manager"
    terminal = (
        issue
        if issue in ("duplicate", "cancellation")
        else "rejected"
        if issue == "rejected"
        else "pending"
        if issue == "unanswered"
        else "scheduled"
    )
    if issue in ("duplicate", "cancellation"):
        return {
            "decision": issue,
            "state": terminal,
            "prior": case["prior"],
            "effects": [],
            "waits": [],
            "approvals": [],
        }
    closing = 5 if company == "C1" else 10
    current_month = arrived.date().replace(day=1)
    previous_month = (current_month - timedelta(days=1)).replace(day=1)
    earliest = previous_month if arrived.day <= closing else current_month
    posting = max(invoiced.replace(day=1), earliest)
    terms = 10 if case["vendor"].endswith("-V02") else 30
    due = invoiced + timedelta(days=terms)
    snow_months = range(4, 11) if company == "C1" else range(5, 10)
    snow = case["work"] == "Snow clearing" and invoiced.month in snow_months
    signer = company == "C2" and amount > 1000000
    service = company == "C1" and arrived.date() >= date(2027, 2, 1) and amount > 250000
    roles = (
        [route]
        + (["finance_signer"] if signer else [])
        + (["community_manager_service"] if service else [])
    )
    waits: list[dict[str, Any]] = []
    response_at = business_due(arrived, 1)
    if issue in ("scheduled", "rejected"):
        response_at = arrived + timedelta(minutes=10)
    if issue == "older-pending":
        response_at = business_due(arrived, 2)
    response_at = min(
        response_at, datetime(2027, 3, 31, 18, tzinfo=ZoneInfo("America/New_York"))
    )
    for index, role in enumerate(roles):
        waits.append(
            {
                "request_id": case["case_id"] + "-" + role,
                "role": role,
                "due_at": business_due(arrived).isoformat(),
                "reviewed_revision": 1,
                "actor": company
                + "-"
                + ("finance" if role == "finance_signer" else role)
                + "-person",
                "decision": None
                if issue == "unanswered"
                else "rejected"
                if issue == "rejected"
                else "approved",
                "responded_at": None
                if issue == "unanswered"
                else (response_at + timedelta(minutes=index)).isoformat(),
                "observed_at": None
                if issue == "unanswered"
                else (response_at + timedelta(minutes=index + 1)).isoformat(),
                "origin": company + "-AP",
            }
        )
    if snow:
        waits.append(
            {
                "request_id": case["case_id"] + "-snow",
                "role": "ap_clerk",
                "actor": "Iona Vale" if company == "C1" else "Orla Fen",
                "due_at": business_due(arrived).isoformat(),
                "responded_at": response_at.isoformat(),
                "decision": "service_confirmed",
                "reviewed_revision": 1,
            }
        )
    if issue in (
        "unknown-vendor",
        "ambiguous-community",
        "conflicting-amount",
        "community-not-yet-joined",
        "expired-certificate",
        "missing-certificate",
    ):
        waits.append(
            {
                "request_id": case["case_id"] + "-resolution",
                "role": "ap_clerk",
                "actor": "Iona Vale" if company == "C1" else "Orla Fen",
                "due_at": business_due(arrived).isoformat(),
                "responded_at": response_at.isoformat(),
                "decision": issue + "-resolved",
                "reviewed_revision": 1,
            }
        )
    resolved_vendor = case["community"] + "-V11" if company == "C1" else "C2-V11"
    resolutions = {
        "unknown-vendor": {
            "vendor_id": resolved_vendor,
            "name": "Juniperfen Works" if company == "C1" else "Kestrelfen Works",
            "action": "add_workspace_identity",
        },
        "ambiguous-community": {"community_id": case["community"]},
        "conflicting-amount": {
            "amount_cents": amount,
            "evidence": case["case_id"] + "-attachment",
        },
        "community-not-yet-joined": {
            "community_id": "C1-C09",
            "available_from": "2026-11-15",
        },
        "expired-certificate": {
            "source": company + "-replacement-certificates",
            "expires": "2027-12-31",
        },
        "missing-certificate": {
            "source": company + "-replacement-certificates",
            "expires": "2027-12-31",
        },
    }
    if issue in resolutions:
        waits[-1]["value"] = resolutions[issue]
    held = issue in ("expired-certificate", "missing-certificate")
    if held:
        replacement_at = (
            "2026-10-02T09:15:00-04:00"
            if case["cohort"] == "shadow"
            else "2026-10-05T09:15:00-04:00"
        )
        waits[-1]["responded_at"] = replacement_at
        waits[-1]["observed_at"] = replacement_at
    for wait in waits:
        if wait.get("responded_at") and "observed_at" not in wait:
            wait["observed_at"] = wait["responded_at"]
    if issue == "community-not-yet-joined":
        waits[-1]["responded_at"] = "2026-11-15T08:00:00-05:00"
        waits[-1]["observed_at"] = "2026-11-15T08:00:00-05:00"
    eligible = max(
        [
            arrived,
            *[
                datetime.fromisoformat(wait["observed_at"])
                for wait in waits
                if wait.get("observed_at")
            ],
        ]
    )
    scheduled = max(due, eligible.date())
    identity = {
        "company": company,
        "case_id": case["case_id"],
        "community": case["community"],
        "vendor": resolved_vendor if issue == "unknown-vendor" else case["vendor"],
        "invoice_number": case["number"].strip(),
        "revision": 1,
    }
    entry = {
        **identity,
        "amount_cents": amount,
        "posting_month": f"{posting.year:04d}-{posting.month:02d}",
        "due_date": due.isoformat(),
        "source": case["case_id"] + "-email",
        "payment_hold_at_receipt": held,
    }
    effects = [
        {
            "identity": case["case_id"] + "/record/1",
            "operation": "record_invoice",
            "payload": entry,
        },
        {
            "identity": case["case_id"] + "/request/1",
            "operation": "request_approval",
            "payload": {
                **identity,
                "amount_cents": amount,
                "roles": [
                    role for role in roles if role != "community_manager_service"
                ],
                "due_at": business_due(arrived).isoformat(),
            },
        },
    ]
    if service:
        effects.append(
            {
                "identity": case["case_id"] + "/service-request/1",
                "operation": "request_service_confirmation",
                "payload": {
                    **identity,
                    "role": "community_manager_service",
                    "due_at": business_due(arrived).isoformat(),
                    "citation": "W1-D5",
                },
            }
        )
    if terminal == "scheduled":
        effects.append(
            {
                "identity": case["case_id"] + "/schedule/1",
                "operation": "schedule_payment",
                "payload": {
                    **identity,
                    "amount_cents": amount,
                    "date": scheduled.isoformat(),
                    "approvals": [
                        wait["request_id"] for wait in waits if wait["role"] in roles
                    ],
                },
            }
        )
    return {
        "decision": route,
        "state": terminal,
        "limit_cents": limit,
        "posting_month": f"{posting.year:04d}-{posting.month:02d}",
        "due_date": due.isoformat(),
        "terms_days": terms,
        "snow_review": snow,
        "second_signer": signer,
        "service_confirmation": service,
        "eligible_at": eligible.isoformat(),
        "insurance_at_receipt": "missing"
        if issue == "missing-certificate"
        else "expired"
        if held
        else "valid",
        "effects": effects,
        "waits": waits,
        "approvals": roles,
    }


def later_events(company: str) -> list[dict[str, Any]]:
    controller = "Elin Voss" if company == "C1" else "Neris Tal"
    events: list[dict[str, Any]] = [
        {
            "id": company + "-shadow",
            "at": "2026-10-01T09:00:00-04:00",
            "kind": "shadow",
            "effects": False,
            "trust": False,
        },
        {
            "id": company + "-review",
            "at": "2026-10-02T08:30:00-04:00",
            "actor": controller,
            "kind": "mode_transition",
            "to": "review",
            "requires": [
                "program_approval",
                "passing_tests",
                "zero_shadow_reference_errors",
            ],
        },
        {
            "id": company + "-grant",
            "at": "2026-12-20T08:30:00-05:00",
            "actor": controller,
            "kind": "standing_authority",
            "company": company,
            "operations": ["record_invoice", "request_approval", "schedule_payment"],
            "amount_limit_cents": 500000,
            "unresolved_hold": False,
            "requires_clean_reviews": 300,
            "revoked": False,
            "expected_revision": 1,
            "stable_operations": [
                "record_invoice",
                "request_approval",
                "schedule_payment",
            ],
            "business_decisions_supplied": False,
        },
    ]
    if company == "C1":
        events.extend(
            [
                {
                    "id": "D1",
                    "at": "2026-10-15T08:00:00-04:00",
                    "kind": "column_rename",
                    "before": "amount_cents",
                    "after": "gross_cents",
                    "behavior_changed": False,
                    "source": "C1-register-2026-10-15",
                },
                {
                    "id": "D2",
                    "at": "2026-11-01T08:00:00-05:00",
                    "kind": "unknown_status",
                    "before": "C",
                    "after": "R",
                    "behavior_changed": True,
                    "source": "C1-register-2026-11-01",
                    "answer": {
                        "id": "W1-D2",
                        "actor": controller,
                        "at": "2026-11-01T08:30:00-05:00",
                        "value": "R means posted",
                    },
                },
                {
                    "id": "D3",
                    "at": "2026-11-15T08:00:00-05:00",
                    "kind": "control_move",
                    "before": "invoice.footer.Schedule payment",
                    "after": "Payments.Schedule payment",
                    "old_position": "Void invoice",
                    "expected_voids": [],
                    "behavior_changed": False,
                },
                {
                    "id": "Rillhaven-join",
                    "at": "2026-11-15T08:00:00-05:00",
                    "kind": "community_join",
                    "community": "C1-C09",
                    "name": "Rillhaven Rise",
                },
                {
                    "id": "Rillhaven-correction",
                    "at": "2026-11-16T10:00:00-05:00",
                    "actor": controller,
                    "kind": "review_correction",
                    "case_id": "C1-S0451",
                    "field": "approver",
                    "before": "manager",
                    "after": "board",
                    "limit_cents": 200000,
                    "effective_from": "2026-11-15",
                    "behavior_changed": True,
                },
                {
                    "id": "F4-parser",
                    "at": "2026-12-04T08:00:00-05:00",
                    "kind": "parser_release",
                    "format": "F4",
                    "actor": controller,
                    "expected_revision": 1,
                    "recorded_ai_cases": ["C1-S0601", "C1-S0602", "C1-S0603"],
                    "requires": [
                        "saved_examples",
                        "schema_checks",
                        "tests",
                        "approval",
                    ],
                    "unchanged_formats": ["F1", "F2", "F3"],
                },
                {
                    "id": "D1-mapping-approval",
                    "at": "2026-10-15T08:15:00-04:00",
                    "actor": controller,
                    "kind": "mapping_approval",
                    "expected_revision": 1,
                    "behavior_changed": False,
                    "requires": ["same_values", "saved_tests"],
                },
                {
                    "id": "D2-mapping-approval",
                    "at": "2026-11-01T08:45:00-05:00",
                    "actor": controller,
                    "kind": "mapping_approval",
                    "expected_revision": 1,
                    "behavior_changed": True,
                    "requires": ["W1-D2", "verification"],
                },
                {
                    "id": "D3-repair-approval",
                    "at": "2026-11-15T08:15:00-05:00",
                    "actor": controller,
                    "kind": "repair_approval",
                    "expected_revision": 1,
                    "behavior_changed": False,
                    "requires": ["sandbox_verification", "zero_voids"],
                },
                {
                    "id": "D4-program-approval",
                    "at": "2026-12-31T16:00:00-05:00",
                    "actor": controller,
                    "kind": "program_approval",
                    "expected_revision": 1,
                    "effective_from": "2027-01-01",
                    "requires": ["passing_checks", "old_case_replay"],
                },
                {
                    "id": "D5-program-approval",
                    "at": "2027-01-31T16:00:00-05:00",
                    "actor": controller,
                    "kind": "program_approval",
                    "expected_revision": 1,
                    "effective_from": "2027-02-01",
                    "requires": ["passing_checks", "old_case_replay"],
                },
                {
                    "id": "D4-notice",
                    "at": "2026-12-15T08:00:00-05:00",
                    "kind": "policy_notice",
                    "effective_from": "2027-01-01",
                    "source": "C1-board-limit-notice.md",
                    "community": "C1-C03",
                    "before_cents": 150000,
                    "after_cents": 180000,
                    "applies_by": "receipt",
                },
                {
                    "id": "D5-notice",
                    "at": "2027-01-15T08:00:00-05:00",
                    "kind": "procedure_notice",
                    "effective_from": "2027-02-01",
                    "source": "C1-service-confirmation.md",
                    "amount_strictly_above_cents": 250000,
                    "role": "community_manager_service",
                    "due_business_days": 2,
                    "applies_by": "receipt",
                },
            ]
        )
    else:
        events.extend(
            [
                {
                    "id": "Fennor-library-approval",
                    "at": "2026-12-31T08:00:00-05:00",
                    "actor": controller,
                    "kind": "library_update_approval",
                    "version": "generalized-F4-2026-12-04",
                    "requires": ["local_verification", "approval"],
                },
                {
                    "id": "Fennor-first-F4",
                    "at": "2027-01-01T09:00:00-05:00",
                    "kind": "format_arrival",
                    "case_id": "C2-S0901",
                    "library_run_runtime_calls": 0,
                },
            ]
        )
    return sorted(events, key=lambda item: (item["at"], item["id"]))


def employee_answers(company: str) -> list[dict[str, Any]]:
    values = (
        [
            ("W1-A1", "Harthmere Court board limit is 150000 cents.", "2025-10-01"),
            ("W1-A2", "Avenreed Grounds terms are ten calendar days.", "2025-10-01"),
            (
                "W1-A3",
                "The previous month remains open through day five.",
                "2025-10-01",
            ),
            (
                "W1-A4",
                "Review eligible snow invoices dated April through October.",
                "2025-10-01",
            ),
        ]
        if company == "C1"
        else [
            ("W1-A5", "Ashmere Park board limit is 250000 cents.", "2025-10-01"),
            ("W1-A6", "Morrowfen Electric terms are ten calendar days.", "2025-10-01"),
            ("W1-A7", "The previous month remains open through day ten.", "2025-10-01"),
            (
                "W1-A8",
                "Above 1000000 cents require a distinct additional finance signer.",
                "2025-10-01",
            ),
            (
                "W1-A9",
                "Review eligible snow invoices dated May through September.",
                "2025-10-01",
            ),
        ]
    )
    return [
        {
            "id": identity,
            "company": company,
            "actor": "Iona Vale" if company == "C1" else "Orla Fen",
            "text": value,
            "effective_from": start,
            "effective_until": None,
            "delivery": "only in response to a matching current task",
            "earliest_answer_at": "2026-10-01T08:00:00-04:00",
        }
        for identity, value, start in values
    ]


def artifacts(specification: dict[str, Any]) -> dict[str, bytes]:
    company = specification["company"]
    cases = specification["cases"]
    key = {item["case_id"]: expectation(item) for item in cases}
    observed = specification["observed"]
    mistakes = {
        identity: {
            "field": "decision",
            "observed": action["decision"],
            "correct": key[identity]["decision"],
        }
        for identity, action in observed.items()
        if action["decision"] != key[identity]["decision"]
    }
    learning = [
        item["case_id"]
        for item in cases
        if item["cohort"] == "history" and item["received"] < "2026-07-01"
    ]
    exam = [
        item["case_id"]
        for item in cases
        if item["cohort"] == "history" and item["received"] >= "2026-07-01"
    ]
    opening = [
        f"{company}-S{number:04d}" for number in range(1, 14 if company == "C1" else 7)
    ]
    operations = schedule(company, cases, key)
    scripts = {
        "employee_answers": employee_answers(company),
        "case_responses": {
            identity: answer["waits"] for identity, answer in key.items()
        },
        "reviews": [
            event
            for event in operations["events"]
            if event["kind"] == "proposal_review"
        ],
        "sampling": {
            "company": company,
            "every": 20,
            "assigned": "before first change",
            "scope": "otherwise review-free cases",
            "all_later_proposals_require_review": True,
        },
        "operation_schedule": "operation-schedule.json",
        "events": later_events(company),
        "opening_prefix": {
            "cutoff": "2026-10-02T09:30:00-04:00",
            "cases": [
                {
                    "case_id": identity,
                    "state": "scheduled"
                    if identity == "C1-S0002"
                    else "rejected"
                    if identity == "C1-S0012"
                    else "duplicate"
                    if identity in ("C1-S0003", "C2-S0004")
                    else "cancellation"
                    if identity == "C1-S0011"
                    else "pending",
                    "actions": [
                        wait
                        for wait in key[identity]["waits"]
                        if wait.get("responded_at")
                        and wait["responded_at"] < "2026-10-02T09:30:00-04:00"
                    ],
                }
                for identity in opening
                if identity in key
            ],
        },
    }
    fixture = {
        **specification,
        "learning": learning,
        "exam": exam,
        "opening": opening,
        "shadow": [item["case_id"] for item in cases if item["cohort"] == "shadow"],
        "stream": [item["case_id"] for item in cases if item["cohort"] == "stream"],
        "cutoff": "2027-03-31T23:59:59-04:00",
        "timezone": "America/New_York",
        "week_start": "Monday",
        "events": later_events(company),
        "unimplemented": [
            "reference_execution",
            "compiler",
            "learned_stream",
            "library_comparison",
            "repair_execution",
            "UI",
        ],
        "key_construction": "specification decisions before reference execution",
    }
    passage_map: dict[str, dict[str, str]] = {}
    groups = (
        [
            ("W1-P1", "procedure.md", ("1.1", "1.2", "1.3")),
            ("W1-P2", "procedure.md", ("2.1", "2.2", "2.3")),
            ("W1-P3", "procedure.md", ("3.1", "3.2", "3.3")),
            ("W1-P4", "procedure.md", ("4.1", "4.2", "4.3", "4.4")),
            ("W1-E1", "controller-email.md", ("1", "2", "3")),
        ]
        if company == "C1"
        else [
            ("F1", "ap-checklist.md", ("1", "2", "3", "4")),
            ("F2", "payables-wiki.md", ("1", "2", "3", "4")),
            ("F3", "controller-email.md", ("1", "2", "3")),
        ]
    )
    for prefix, name, sections in groups:
        for section in sections:
            passage_map[prefix + "." + section.split(".")[-1]] = {
                "source": company + "-" + name,
                "section": section,
            }
    if company == "C1":
        passage_map.update(
            {
                "W1-D4": {"source": "C1-board-limit-notice.md", "section": "1"},
                "W1-D5": {"source": "C1-service-confirmation.md", "section": "1"},
            }
        )
    recordings = [
        {
            "recording_id": item["case_id"] + "-F4-extraction",
            "company": company,
            "case_id": item["case_id"],
            "phase": "runtime",
            "prompt_version": "invoice-extraction-1",
            "schema_version": "invoice-fields-1",
            "available_at": item["received"],
            "model": "synthetic-recording",
            "network_calls": 0,
            "validated_output": {
                field: item[field]
                for field in (
                    "community",
                    "vendor",
                    "number",
                    "invoice_date",
                    "amount",
                    "work",
                )
            },
            "schema": {
                "community": "text",
                "vendor": "text",
                "number": "text",
                "invoice_date": "date",
                "amount": "integer_cents",
                "work": "text",
            },
            "failure": None,
            "input_tokens": 0,
            "output_tokens": 0,
        }
        for item in cases
        if item["case_id"] in ("C1-S0601", "C1-S0602", "C1-S0603")
    ]
    libraries: list[dict[str, Any]] = [
        {
            "version": "generalized-initial",
            "published_at": "2026-09-30T20:00:00-04:00",
            "evidence_cutoff": "2026-06-30T23:59:59-04:00",
            "questions": [
                "Does seasonal work require extra review?",
                "Are any local approval limits lower?",
                "Do any vendors have different payment terms?",
            ],
            "formats": ["F1", "F2", "F3"],
            "local_values": {},
        },
        {
            "version": "generalized-F4-2026-12-04",
            "published_at": "2026-12-04T08:00:00-05:00",
            "formats": ["F4"],
            "checks": ["schema", "company-records", "saved-examples"],
            "local_values": {},
        },
    ]
    outputs = {
        "answer-key.json": canonical(key),
        "answer-sheet.json": canonical(observed),
        "mistakes.json": canonical(mistakes),
        "fixture.json": canonical(fixture),
        "response-scripts.json": canonical(scripts),
        "passage-map.json": canonical(passage_map),
        "ai-extractions.json": canonical(recordings),
        "library-schedule.json": canonical(libraries),
        "operation-schedule.json": canonical(operations),
        "shadow-inputs.json": canonical(specification["shadow_inputs"]),
    }
    outputs["manifest.json"] = canonical(
        {
            "format": "dex-world-1-evaluator-1",
            "company": company,
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

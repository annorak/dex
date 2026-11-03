from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from hashlib import sha256
from typing import Any
from zoneinfo import ZoneInfo

from dex.bundle.model import Bundle
from dex.bundle.reader import admit_bundle
from dex.bundle.validation import canonical
from dex.demo.native import csv_bytes

VERSION = "world-2-1"
PACKETS = ("handbook.md", "service-owner-email.md")
ZONE = ZoneInfo("America/New_York")
INITIAL = "2025-09-30T08:00:00-04:00"
CONFIRMATION_AT = "2026-10-01T10:00:00-04:00"


@dataclass(frozen=True)
class Employee:
    employee_id: str
    display_name: str
    status: str


@dataclass(frozen=True)
class Site:
    site_id: str
    employees: tuple[Employee, ...]
    services: tuple[str, ...]
    fields: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class ClientValue:
    site_id: str
    field: str
    value: str


@dataclass(frozen=True)
class Onboarding:
    case_id: str
    client_id: str
    client_name: str
    sponsor: str
    opened: date
    sites: tuple[Site, ...]
    wait_days: int
    response: tuple[ClientValue, ...]


def at(day: date, hour: int, minute: int = 0, second: int = 0) -> str:
    return datetime.combine(day, time(hour, minute, second), ZONE).isoformat()


def make_cases(seed: int) -> tuple[Onboarding, ...]:
    cases: list[Onboarding] = []
    for cohort, count in (("H", 48), ("S", 16)):
        for number in range(1, count + 1):
            local = (number - 1) % 12 + 1
            month, week = divmod(number - 1, 4)
            opened = (
                date(2025 + (month + 9) // 12, (month + 9) % 12 + 1, 1 + week * 7)
                if cohort == "H"
                else date(2027, 1, number)
            )
            multi = local <= 8 if cohort == "H" else number % 4 != 3
            both = local in (2, 4, 6, 8) if cohort == "H" else number % 4 == 2
            wait = (
                ((3 if local in (2, 6, 10) else 5) if local % 2 == 0 else 0)
                if cohort == "H"
                else (3 if number % 4 == 2 else 5)
                if number % 2 == 0
                else 0
            )
            identity = f"{cohort}{number:03d}"
            services = (
                (("payroll", "benefits"), ("payroll",))
                if both
                else (("payroll",), ("benefits",))
                if multi
                else (("payroll",),)
                if (local in (9, 11) if cohort == "H" else number in (3, 11))
                else (("benefits",),)
            )
            cutover = (opened + timedelta(days=14)).isoformat()
            sites: list[Site] = []
            response: list[ClientValue] = []
            for index, selected in enumerate(services, 1):
                site_id = identity + f"-site-{index}"
                fields: dict[str, str] = {}
                if "payroll" in selected:
                    fields.update(
                        pay_frequency="biweekly", payroll_cutover_date=cutover
                    )
                if "benefits" in selected:
                    fields.update(
                        plan_code="SYNTH-PLAN-A",
                        eligibility_group="standard",
                        site_contact=site_id + "-contact",
                    )
                if cohort == "H" and local == 6:
                    fields["payroll_cutover_date"] = (
                        opened + timedelta(days=14 + index)
                    ).isoformat()
                    response.append(
                        ClientValue(site_id, "payroll_cutover_date", cutover)
                    )
                elif wait and index == 1:
                    missing = (
                        "pay_frequency" if "payroll" in selected else "site_contact"
                    )
                    response.append(ClientValue(site_id, missing, fields.pop(missing)))
                employees = tuple(
                    Employee(
                        site_id + f"-employee-{ordinal}",
                        f"Synthetic colleague {seed}-{number}-{index}-{ordinal}",
                        "active",
                    )
                    for ordinal in (1, 2)
                )
                sites.append(Site(site_id, employees, selected, tuple(fields.items())))
            cases.append(
                Onboarding(
                    identity,
                    identity + "-client",
                    f"Synthetic client {seed}-{identity}",
                    identity + "-sponsor",
                    opened,
                    tuple(sites),
                    wait,
                    tuple(response),
                )
            )
    return tuple(cases)


def records(item: Onboarding) -> dict[str, list[list[str]]]:
    tables = {
        "client": [
            ["case_id", "client_id", "name", "sponsor", "agreement_id"],
            [
                item.case_id,
                item.client_id,
                item.client_name,
                item.sponsor,
                item.case_id + "-agreement",
            ],
        ],
        "sites": [["case_id", "client_id", "site_id"]],
        "employees": [
            ["case_id", "client_id", "site_id", "employee_id", "display_name", "status"]
        ],
        "services": [["case_id", "client_id", "site_id", "service_id", "service"]],
    }
    for site in item.sites:
        tables["sites"].append([item.case_id, item.client_id, site.site_id])
        for employee in site.employees:
            tables["employees"].append(
                [
                    item.case_id,
                    item.client_id,
                    site.site_id,
                    employee.employee_id,
                    employee.display_name,
                    employee.status,
                ]
            )
        for service in site.services:
            tables["services"].append(
                [
                    item.case_id,
                    item.client_id,
                    site.site_id,
                    site.site_id + "-" + service,
                    service,
                ]
            )
            fields = (
                ("pay_frequency", "payroll_cutover_date")
                if service == "payroll"
                else ("plan_code", "eligibility_group", "site_contact")
            )
            table = tables.setdefault(
                service, [["case_id", "client_id", "site_id", *fields]]
            )
            values = dict(site.fields)
            table.append(
                [
                    item.case_id,
                    item.client_id,
                    site.site_id,
                    *(values.get(field, "") for field in fields),
                ]
            )
    return tables


def source(
    manifest: dict[str, Any],
    files: dict[str, bytes],
    identity: str,
    path: str,
    content: bytes,
    available: str,
    *,
    headers: list[str] | None = None,
    occurred: str | None = None,
    effective: str | None = None,
) -> dict[str, str]:
    ref = {"source_id": "C3-" + identity, "revision_id": "v1"}
    descriptor: dict[str, Any] = {
        **ref,
        "path": path,
        "sha256": sha256(content).hexdigest(),
        "media_type": "text/csv" if headers else "text/markdown",
        "origin": {
            "kind": "export",
            "source_system": "Veldren-setup",
            "export_id": identity,
        }
        if headers
        else {"kind": "file", "snapshot": identity},
        "occurred_at": occurred or available,
        "observed_at": available,
        "available_at": available,
    }
    if headers:
        descriptor["mapping"] = {
            "version": "roster-1",
            "confirmed_by": "Iven Sel",
            "confirmed_at": INITIAL,
            "effective_from": "2025-10-01",
            "effective_until": None,
            "columns": [
                {"source": header, "target": header, "kind": "text"}
                for header in headers
            ],
        }
    if effective:
        descriptor["effective_date"] = effective
    files[path] = content
    manifest["sources"].append(descriptor)
    return ref


def deliver(
    manifest: dict[str, Any], identity: str, refs: list[dict[str, str]], when: str
) -> None:
    manifest["deliveries"].append(
        {
            "delivery_id": identity,
            "sources": refs,
            "received_at": when,
            "available_at": when,
            "origin": {"kind": "file", "snapshot": identity},
        }
    )


def observation(
    manifest: dict[str, Any],
    files: dict[str, bytes],
    case: dict[str, Any],
    identity: str,
    actor: str,
    happened: str,
    available: str,
    values: dict[str, str],
) -> None:
    rows = [
        ["case_id", "actor", "occurred_at", *values],
        [case["case_id"], actor, happened, *values.values()],
    ]
    ref = source(
        manifest,
        files,
        identity,
        "history/events/" + identity + ".csv",
        csv_bytes(rows),
        available,
        headers=rows[0],
        occurred=happened,
    )
    deliver(manifest, identity, [ref], available)
    case["observations"].append(
        {
            "observation_id": identity,
            "source": ref,
            "locator": "record:2",
            "actor": actor,
            "occurred_at": happened,
            "observed_at": available,
            "available_at": available,
            "mapping_version": "roster-1",
        }
    )


def site_record(site: Site) -> dict[str, Any]:
    return {
        "site_id": site.site_id,
        "services": list(site.services),
        "employees": [
            {
                "employee_id": employee.employee_id,
                "display_name": employee.display_name,
                "status": employee.status,
            }
            for employee in site.employees
        ],
        **dict(site.fields),
    }


def observed_actions(
    manifest: dict[str, Any],
    files: dict[str, bytes],
    case: dict[str, Any],
    item: Onboarding,
) -> dict[str, Any]:
    ready = item.opened + timedelta(days=item.wait_days)
    owner_day = ready + timedelta(days=1)
    summary = item.case_id + "-summary-v1"
    request = item.case_id + "-client-request-v1"
    configuration: dict[str, Any] = {
        "client_id": item.client_id,
        "sites": [site_record(site) for site in item.sites],
    }
    for change in item.response:
        site = next(
            site for site in configuration["sites"] if site["site_id"] == change.site_id
        )
        site[change.field] = change.value
    payload_hash = sha256(canonical(configuration)).hexdigest()
    owner_request = item.case_id + "-owner-request-v1"
    if item.wait_days:
        observation(
            manifest,
            files,
            case,
            request,
            "Iven Sel",
            at(item.opened, 10),
            at(item.opened, 10),
            {
                "kind": "client_request",
                "request_id": request,
                "request_revision": "1",
                "client_id": item.client_id,
                "fields": canonical(
                    [
                        {"site_id": value.site_id, "field": value.field}
                        for value in item.response
                    ]
                )
                .decode()
                .strip(),
                "due_at": at(item.opened + timedelta(days=3), 23, 59, 59),
            },
        )
        if item.wait_days == 5:
            overdue = at(item.opened + timedelta(days=4), 0)
            observation(
                manifest,
                files,
                case,
                item.case_id + "-overdue",
                "system",
                overdue,
                overdue,
                {
                    "kind": "overdue_notification",
                    "request_id": request,
                    "request_revision": "1",
                    "client_id": item.client_id,
                    "recipient": "Iven Sel",
                },
            )
        for number, value in enumerate(item.response, 1):
            observation(
                manifest,
                files,
                case,
                item.case_id + f"-client-response-{number}",
                item.sponsor,
                at(ready, 9),
                at(ready, 9),
                {
                    "kind": "client_response",
                    "request_id": request,
                    "request_revision": "1",
                    "response_id": item.case_id + "-client-response-v1",
                    "client_id": item.client_id,
                    "site_id": value.site_id,
                    "field": value.field,
                    "value": value.value,
                },
            )
    observation(
        manifest,
        files,
        case,
        item.case_id + "-summary",
        "Iven Sel",
        at(ready, 10),
        at(ready, 10),
        {
            "kind": "owner_request",
            "summary_id": summary,
            "summary_revision": "1",
            "summary_sha256": payload_hash,
            "configuration": canonical(configuration).decode().strip(),
            "request_id": owner_request,
            "request_revision": "1",
            "due_at": at(owner_day, 10),
            "client_id": item.client_id,
        },
    )
    observation(
        manifest,
        files,
        case,
        item.case_id + "-owner",
        "Mara Tern",
        at(owner_day, 10),
        at(owner_day, 10),
        {
            "kind": "business_decision",
            "decision": "authorize",
            "summary_id": summary,
            "summary_revision": "1",
            "summary_sha256": payload_hash,
            "request_id": owner_request,
            "request_revision": "1",
            "decision_id": item.case_id + "-owner-decision-v1",
            "client_id": item.client_id,
        },
    )
    observation(
        manifest,
        files,
        case,
        item.case_id + "-authority",
        "Veldren setup operator",
        at(owner_day, 11),
        at(owner_day, 11),
        {
            "kind": "exact_change_approval",
            "effect_id": "C3-" + item.case_id + "-activate-1",
            "effect_revision": "1",
            "payload_sha256": payload_hash,
            "business_decision_id": item.case_id + "-owner-decision-v1",
            "approval_id": item.case_id + "-exact-change-approval-v1",
        },
    )
    activation_day = (
        ready if item.case_id in ("H008", "H019", "H031", "H044") else owner_day
    )
    activated = at(activation_day, 12)
    observed: dict[str, Any] = {
        "case_id": item.case_id,
        "client_id": item.client_id,
        "actor": "Veldren setup operator",
        "summary_id": summary,
        "activated_at": activated,
        "occurred_at": activated,
        "observed_at": at(owner_day, 13),
        "available_at": at(owner_day, 13),
        "owner_decided_at": at(owner_day, 10),
        "confirmation_id": item.case_id + "-setup-confirmation",
        "payload": configuration,
        "payload_sha256": payload_hash,
    }
    observation(
        manifest,
        files,
        case,
        item.case_id + "-activation",
        observed["actor"],
        activated,
        observed["available_at"],
        {
            "kind": "activation",
            "client_id": item.client_id,
            "summary_id": summary,
            "payload_sha256": payload_hash,
            "configuration": canonical(configuration).decode().strip(),
            "confirmation_id": observed["confirmation_id"],
        },
    )
    return observed


def company_bundle(
    seed: int, packets: dict[str, bytes]
) -> tuple[Bundle, dict[str, Any]]:
    manifest: dict[str, Any] = {
        "format_version": "dex-company-bundle-1",
        "bundle_id": f"world-2-C3-{VERSION}-seed-{seed}",
        "company_id": "C3",
        "sources": [],
        "deliveries": [],
        "recordings": [],
        "cases": [],
        "history": {
            "kind": "interval",
            "start": "2025-10-01T00:00:00-04:00",
            "end": "2026-10-01T00:00:00-04:00",
            "opening_event": "signed_agreement_received",
            "adequacy": {
                "decision": "usable",
                "actor": "Mara Tern",
                "decided_at": "2026-09-30T19:30:00-04:00",
            },
            "cases": [],
        },
    }
    files: dict[str, bytes] = {}
    for name in PACKETS:
        issued = "2025-09-01" if name == "handbook.md" else "2025-09-22"
        ref = source(
            manifest,
            files,
            name,
            "sources/" + name,
            packets[name],
            INITIAL,
            occurred=issued + "T08:00:00-04:00",
            effective=issued,
        )
        deliver(manifest, "packet-" + name, [ref], INITIAL)
    raw_cases: list[dict[str, Any]] = []
    observed: dict[str, Any] = {}
    for item in make_cases(seed):
        opened = at(item.opened, 8)
        inputs: list[dict[str, str]] = []
        facts: list[dict[str, Any]] = []
        for name, rows in records(item).items():
            ref = source(
                manifest,
                files,
                item.case_id + "-" + name,
                f"exports/{item.case_id}/{name}.csv",
                csv_bytes(rows),
                opened,
                headers=rows[0],
            )
            inputs.append(ref)
            for row in range(2, len(rows) + 1):
                facts.append(
                    {
                        "name": f"{name}-{row}",
                        "source": ref,
                        "record": f"record:{row}",
                        "column": "case_id",
                    }
                )
        arrival = item.case_id + "-arrival"
        deliver(manifest, arrival, inputs, opened)
        case: dict[str, Any] = {
            "case_id": item.case_id,
            "delivery_id": arrival,
            "opened_at": opened,
            "business_date": item.opened.isoformat(),
            "inputs": inputs,
            "facts": facts,
            "observations": [],
        }
        historical = item.case_id.startswith("H")
        (manifest["history"]["cases"] if historical else manifest["cases"]).append(case)
        actions = observed_actions(manifest, files, case, item)
        if historical:
            observed[item.case_id] = actions
        raw_cases.append(
            {
                "case_id": item.case_id,
                "client_id": item.client_id,
                "client_name": item.client_name,
                "sponsor": item.sponsor,
                "opened_at": opened,
                "sites": [site_record(site) for site in item.sites],
            }
        )
    question = (
        b"# Shared payroll dates\n\n"
        b"Iven Sel asked Mara Tern on October 1, 2026 at 09:00 America/New_York.\n"
        b"Request: shared-payroll-date-v1. Revision: 1.\n"
        b"H006, H018 and H030 began with different payroll dates at their two sites.\n"
        b"Each client corrected both dates before activation. Is a shared date required?\n"
    )
    answer = (
        b"# Payroll date confirmation\n\n"
        b"Mara Tern answered request shared-payroll-date-v1, revision 1, on October 1, 2026 at 10:00 America/New_York.\n"
        b"All of a client's payroll sites must use one client-confirmed payroll cutover date.\n"
        b"This rule applies from October 1, 2025. Benefits-only sites need no payroll date.\n"
    )
    for identity, content, when in (
        ("shared-payroll-question", question, "2026-10-01T09:00:00-04:00"),
        ("shared-payroll-confirmation", answer, CONFIRMATION_AT),
    ):
        ref = source(
            manifest,
            files,
            identity,
            "sources/" + identity + ".md",
            content,
            when,
            effective="2025-10-01" if identity.endswith("confirmation") else None,
        )
        deliver(manifest, identity, [ref], when)
    files["bundle.json"] = canonical(manifest)
    bundle = admit_bundle(files.__getitem__, lambda: set(files))
    return bundle, {
        "company": "C3",
        "seed": seed,
        "generator_version": VERSION,
        "source_hashes": {name: sha256(packets[name]).hexdigest() for name in PACKETS},
        "cases": raw_cases,
        "observed": observed,
    }

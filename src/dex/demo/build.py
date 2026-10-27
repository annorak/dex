import json
import os
import sys
import tempfile
from base64 import b64encode
from dataclasses import asdict
from datetime import date, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any

from dex.bundle.model import Bundle, BundleError
from dex.bundle.reader import admit_bundle
from dex.bundle.validation import canonical
from dex.bundle.writer import write_bundle
from dex.demo.fixtures import write_world_1_artifacts
from dex.demo.native import XLSX, csv_bytes, pdf_bytes, xlsx_bytes
from dex.demo.world_1 import (
    COMMUNITIES,
    COMPANIES,
    PACKETS,
    VENDORS,
    VERSION,
    Invoice,
    chronology,
    local,
    make_cases,
    vendor_id,
)

INITIAL = "2025-09-30T08:00:00-04:00"


def source(
    manifest: dict[str, Any],
    files: dict[str, bytes],
    identity: str,
    path: str,
    content: bytes,
    media: str,
    at: str,
    **metadata: Any,
) -> dict[str, str]:
    ref = {"source_id": identity, "revision_id": "v1"}
    files[path] = content
    manifest["sources"].append(
        {
            **ref,
            "path": path,
            "media_type": media,
            "sha256": sha256(content).hexdigest(),
            "origin": {
                "kind": "export",
                "export_id": identity,
                "source_system": manifest["company_id"] + "-AP",
            }
            if media in ("text/csv", XLSX)
            else {"kind": "file", "snapshot": identity},
            "occurred_at": at,
            "observed_at": at,
            "available_at": at,
            **metadata,
        }
    )
    return ref


def delivery(
    manifest: dict[str, Any], identity: str, refs: list[dict[str, str]], at: str
) -> None:
    manifest["deliveries"].append(
        {
            "delivery_id": identity,
            "sources": refs,
            "received_at": at,
            "available_at": at,
            "origin": {"kind": "file", "snapshot": identity},
        }
    )


def table_mapping(
    company: str, headers: list[str], at: str = INITIAL
) -> dict[str, Any]:
    columns: list[dict[str, Any]] = []
    for header in headers:
        column: dict[str, Any] = {"source": header, "target": header, "kind": "text"}
        if header in ("amount_cents", "amount", "gross_cents"):
            column.update(
                kind="money", encoding="cents" if company == "C1" else "decimal-dollars"
            )
        if header == "invoice_date":
            column.update(kind="date", encoding="iso" if company == "C1" else "us")
        columns.append(column)
    return {
        "version": "native-1",
        "confirmed_by": "Iona Vale" if company == "C1" else "Orla Fen",
        "confirmed_at": at,
        "effective_from": "2025-01-01",
        "effective_until": None,
        "columns": columns,
    }


def native_date(company: str, value: date) -> str:
    return (
        value.isoformat()
        if company == "C1"
        else f"{value.month:02d}/{value.day:02d}/{value.year:04d}"
    )


def native_amount(company: str, amount: int) -> str:
    return str(amount) if company == "C1" else f"{amount // 100}.{amount % 100:02d}"


def invoice_message(item: Invoice) -> tuple[bytes, bytes | None]:
    fields = [
        ("Company", item.company),
        ("Community", item.community),
        (
            "Vendor",
            item.vendor.rsplit("-", 1)[-1]
            if item.company == "C1" and item.vendor.startswith("C1-")
            else item.vendor,
        ),
        ("Invoice", item.number),
        ("Invoice date", native_date(item.company, item.invoice_date)),
        ("Amount", native_amount(item.company, item.amount)),
        ("Currency", "USD"),
        ("Work", item.work),
    ]
    if item.issue == "ambiguous-community":
        fields[1] = ("Community", "Please confirm which property this work belongs to.")
    subject = (
        "Cancellation " if item.issue == "cancellation" else "Invoice "
    ) + item.number
    day = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[item.received.weekday()]
    month = (
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    )[item.received.month - 1]
    offset = "-0400" if item.received.utcoffset() == timedelta(hours=-4) else "-0500"
    mail_date = f"{day}, {item.received.day:02d} {month} {item.received.year} {item.received.hour:02d}:{item.received.minute:02d}:00 {offset}"
    headers = (
        "From: supplier@example.test\r\nTo: payables@example.test\r\n"
        + "Date: "
        + mail_date
        + "\r\nMessage-ID: <"
        + item.case_id
        + "@example.test>\r\nSubject: "
        + subject
        + "\r\nMIME-Version: 1.0\r\n"
    )
    body = "\n".join(f"{key}: {value}" for key, value in fields)
    media = "text/plain"
    if item.issue == "cancellation":
        body = "We cancel this obligation before entry. No payment is due.\n" + body
    elif item.format == "F2":
        media = "text/html"
        body = (
            "<table>"
            + "".join(
                f"<tr><th>{key}</th><td>{value}</td></tr>" for key, value in fields
            )
            + "</table>"
        )
    elif item.format == "F3" or item.issue == "conflicting-amount":
        attachment = pdf_bytes([f"{key}: {value}" for key, value in fields])
        encoded = b64encode(attachment).decode()
        encoded = "\r\n".join(
            encoded[index : index + 76] for index in range(0, len(encoded), 76)
        )
        boundary = "dex-" + item.case_id
        body = "Invoice attached. Amount: " + native_amount(
            item.company,
            item.amount + (100 if item.issue == "conflicting-amount" else 0),
        )
        content = (
            headers
            + 'Content-Type: multipart/mixed; boundary="'
            + boundary
            + '"\r\n\r\n'
            + "--"
            + boundary
            + "\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n"
            + body
            + "\r\n"
            + "--"
            + boundary
            + '\r\nContent-Type: application/pdf\r\nContent-Disposition: attachment; filename="invoice.pdf"\r\nContent-Transfer-Encoding: base64\r\n\r\n'
            + encoded
            + "\r\n--"
            + boundary
            + "--\r\n"
        )
        return content.encode(), attachment
    elif item.format == "F4":
        body = "REMITTANCE / SERVICE CHARGE\n" + "\n".join(
            f"{value} | {key}" for key, value in reversed(fields)
        )
    return (
        headers + "Content-Type: " + media + "; charset=utf-8\r\n\r\n" + body + "\r\n"
    ).encode(), None


def observed_route(item: Invoice) -> str:
    if item.issue in ("duplicate", "cancellation"):
        return item.issue
    limit = 500000
    if item.community == "C1-C03":
        limit = 150000
    if item.community == "C2-C01":
        limit = 250000
    number = int(item.case_id[-4:])
    month, offset = divmod(number - 1, 300)
    wrong = (
        offset in (20, 21)
        if item.company == "C1"
        else offset == 22 or (offset == 23 and month in (0, 1, 2, 4, 6, 8, 10, 11))
    )
    return "board" if wrong or item.amount > limit else "manager"


def company_bundle(
    company: str, seed: int, packets: dict[str, bytes], cases: tuple[Invoice, ...]
) -> tuple[Bundle, dict[str, Any]]:
    manifest: dict[str, Any] = {
        "format_version": "dex-company-bundle-1",
        "bundle_id": f"world-1-{company}-{VERSION}-seed-{seed}",
        "company_id": company,
        "sources": [],
        "deliveries": [],
        "recordings": [],
        "cases": [],
        "history": {
            "kind": "interval",
            "start": "2025-10-01T00:00:00-04:00",
            "end": "2026-10-01T00:00:00-04:00",
            "opening_event": "invoice_received",
            "adequacy": {
                "decision": "usable",
                "actor": "Elin Voss" if company == "C1" else "Neris Tal",
                "decided_at": "2026-09-30T19:30:00-04:00",
            },
            "cases": [],
        },
    }
    files: dict[str, bytes] = {}
    for name, content in packets.items():
        at, effective = {
            "board-limit-notice.md": ("2026-12-15T08:00:00-05:00", "2027-01-01"),
            "service-confirmation.md": ("2027-01-15T08:00:00-05:00", "2027-02-01"),
        }.get(name, (INITIAL, "2025-10-01"))
        ref = source(
            manifest,
            files,
            company + "-" + name,
            "sources/" + name,
            content,
            "text/markdown",
            at,
            effective_date=effective,
        )
        delivery(manifest, "packet-" + name, [ref], at)
    record_refs = records(manifest, files, company)
    days: dict[date, list[Invoice]] = {}
    for item in cases:
        if item.cohort != "shadow":
            days.setdefault(item.received.date(), []).append(item)
    public_cases: dict[str, dict[str, Any]] = {}
    observed: dict[str, dict[str, Any]] = {}
    for day, arrivals in sorted(days.items()):
        for item in arrivals:
            received = item.received.isoformat()
            message, attachment = invoice_message(item)
            ref = source(
                manifest,
                files,
                item.case_id + "-email",
                f"sources/invoices/{item.case_id}.eml",
                message,
                "message/rfc822",
                received,
            )
            refs = [ref]
            if attachment is not None:
                child = source(
                    manifest,
                    files,
                    item.case_id + "-attachment",
                    f"sources/invoices/{item.case_id}.pdf",
                    attachment,
                    "application/pdf",
                    received,
                    origin={
                        "kind": "attachment",
                        "message": ref,
                        "part": "part:2",
                        "attachment_id": item.case_id + "-invoice",
                    },
                )
                refs.append(child)
            delivery(manifest, item.case_id + "-arrival", refs, received)
            case: dict[str, Any] = {
                "case_id": item.case_id,
                "delivery_id": item.case_id + "-arrival",
                "opened_at": received,
                "business_date": day.isoformat(),
                "inputs": refs,
                "facts": [],
                "observations": [],
            }
            (
                manifest["history"]["cases"]
                if item.cohort == "history"
                else manifest["cases"]
            ).append(case)
            public_cases[item.case_id] = case
        historical = [item for item in arrivals if item.cohort == "history"]
        if historical:
            action_at = local(day, 19).isoformat()
            action_rows = [
                [
                    "case_id",
                    "decision",
                    "actor",
                    "occurred_at",
                    "posting_time",
                    "status",
                    "posting_month",
                    "due_date",
                    "approval_roles",
                    "snow_review",
                    "community",
                    "vendor",
                    "invoice_number",
                ]
            ]
            for item in historical:
                route = observed_route(item)
                happened = (item.received + timedelta(hours=1)).isoformat()
                month = item.received.date().replace(day=1)
                closing = 5 if company == "C1" else 10
                if item.received.day <= closing:
                    month = (month - timedelta(days=1)).replace(day=1)
                posted_month = max(month, item.invoice_date.replace(day=1))
                due = item.invoice_date + timedelta(
                    days=10 if item.vendor.endswith("-V02") else 30
                )
                roles = route + (
                    ";finance_signer"
                    if company == "C2" and item.amount > 1000000
                    else ""
                )
                snow_months = range(4, 11) if company == "C1" else range(5, 10)
                snow = (
                    item.work == "Snow clearing"
                    and item.invoice_date.month in snow_months
                )
                stopped = route in ("duplicate", "cancellation")
                recorded = {
                    "posting_month": ""
                    if stopped
                    else f"{posted_month.year:04d}-{posted_month.month:02d}",
                    "due_date": "" if stopped else native_date(company, due),
                    "approval_roles": "" if stopped else roles,
                    "snow_review": "reviewed"
                    if snow and not stopped
                    else "not_required",
                    "community": item.community,
                    "vendor": item.vendor,
                    "invoice_number": item.number,
                }
                observed[item.case_id] = {
                    "decision": route,
                    "actor": "Iona Vale" if company == "C1" else "Orla Fen",
                    "occurred_at": happened,
                    "observed_at": action_at,
                    "available_at": action_at,
                    **recorded,
                }
                action_rows.append(
                    [
                        item.case_id,
                        route,
                        observed[item.case_id]["actor"],
                        happened,
                        "" if route in ("duplicate", "cancellation") else happened,
                        "" if stopped else "C" if company == "C1" else "A",
                        *recorded.values(),
                    ]
                )
            ref = source(
                manifest,
                files,
                f"{company}-actions-{day}",
                f"history/actions/{day}.csv",
                csv_bytes(action_rows),
                "text/csv",
                action_at,
                mapping=table_mapping(company, action_rows[0]),
            )
            delivery(manifest, f"actions-{day}", [ref], action_at)
            for row, item in enumerate(historical, 2):
                public_cases[item.case_id]["observations"].append(
                    {
                        "observation_id": item.case_id + "-action",
                        "source": ref,
                        "locator": f"record:{row}",
                        **{
                            key: observed[item.case_id][key]
                            for key in (
                                "actor",
                                "occurred_at",
                                "observed_at",
                                "available_at",
                            )
                        },
                        "mapping_version": "native-1",
                    }
                )
    mixed_ids = [f"{company}-H2700", f"{company}-H2701"]
    if all(identity in public_cases for identity in mixed_ids):
        at = "2026-09-30T19:00:00-04:00"
        rows = [["case_id", "decision", "actor"]] + [
            [identity, observed[identity]["decision"], observed[identity]["actor"]]
            for identity in mixed_ids
        ]
        ref = source(
            manifest,
            files,
            company + "-reconciled-actions",
            "history/reconciled-actions.csv",
            csv_bytes(rows),
            "text/csv",
            at,
            mapping=table_mapping(company, rows[0]),
        )
        delivery(manifest, "reconciled-actions", [ref], at)
        for row, identity in enumerate(mixed_ids, 2):
            public_cases[identity]["observations"].append(
                {
                    "observation_id": identity + "-reconciled",
                    "source": ref,
                    "locator": f"record:{row}",
                    "actor": observed[identity]["actor"],
                    "occurred_at": observed[identity]["occurred_at"],
                    "observed_at": at,
                    "available_at": at,
                    "mapping_version": "native-1",
                }
            )
    later_sources(manifest, files, company)
    snapshots(manifest, files, company, cases)
    files["bundle.json"] = canonical(manifest)
    bundle = admit_bundle(files.__getitem__, lambda: set(files))
    shadow_inputs: dict[str, dict[str, str | None]] = {}
    for item in cases:
        if item.cohort == "shadow":
            email, attachment = invoice_message(item)
            shadow_inputs[item.case_id] = {
                "email": email.decode(),
                "attachment_base64": b64encode(attachment).decode()
                if attachment
                else None,
            }
    specification = {
        "company": company,
        "seed": seed,
        "generator_version": VERSION,
        "source_hashes": {
            name: sha256(content).hexdigest()
            for name, content in sorted(packets.items())
        },
        "cases": [
            {
                **asdict(item),
                "received": item.received.isoformat(),
                "invoice_date": item.invoice_date.isoformat(),
                "chronology": chronology(item),
            }
            for item in cases
        ],
        "observed": observed,
        "record_sources": record_refs,
        "shadow_inputs": shadow_inputs,
    }
    return bundle, specification


def records(
    manifest: dict[str, Any], files: dict[str, bytes], company: str
) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    count = 8 if company == "C1" else 6
    for start, end, at, suffix in (
        (1, count + 1, INITIAL, "initial"),
        *([(9, 10, "2026-11-15T08:00:00-05:00", "joined")] if company == "C1" else []),
    ):
        communities = [["community_id", "name"]] + [
            [f"{company}-C{number:02d}", COMMUNITIES[company][number - 1]]
            for number in range(start, end)
        ]
        vendors = [["community_id", "vendor_id", "name", "certificate_expiry"]]
        for number in range(start, end):
            community = f"{company}-C{number:02d}"
            for index, name in enumerate(VENDORS[company], 1):
                vendors.append(
                    [
                        community,
                        vendor_id(company, community, index),
                        name,
                        native_date(company, date(2027, 12, 31)),
                    ]
                )
        if suffix == "initial":
            community = f"{company}-C02"
            vendors.append(
                [
                    community,
                    vendor_id(company, community, 9),
                    "Ivyquill Repairs",
                    native_date(company, date(2026, 9, 30)),
                ]
            )
            vendors.append(
                [
                    community,
                    vendor_id(company, community, 10),
                    "Juniperwell Water" if company == "C1" else "Kestrelmere Water",
                    "",
                ]
            )
        for name, rows in (("communities", communities), ("vendors", vendors)):
            ref = source(
                manifest,
                files,
                f"{company}-{name}-{suffix}",
                f"exports/{name}-{suffix}.xlsx",
                xlsx_bytes(rows),
                XLSX,
                at,
                mapping=table_mapping(company, rows[0], at),
            )
            delivery(manifest, f"{name}-{suffix}", [ref], at)
            refs.append(ref)
    return refs


def later_sources(
    manifest: dict[str, Any], files: dict[str, bytes], company: str
) -> None:
    for at, location, old in (
        (INITIAL, "invoice footer", ""),
        *(
            [
                (
                    "2026-11-15T08:00:00-05:00",
                    "Payments tab",
                    "The invoice footer contains Void invoice.",
                )
            ]
            if company == "C1"
            else []
        ),
    ):
        name = "ap-controls-" + at[:10]
        content = (
            "<html><body><h1>Invoice actions</h1><p>Schedule payment is in the "
            + location
            + ". "
            + old
            + "</p></body></html>"
        ).encode()
        ref = source(
            manifest,
            files,
            company + "-" + name,
            "sources/" + name + ".html",
            content,
            "text/html",
            at,
        )
        delivery(manifest, name, [ref], at)
    at = "2026-10-05T09:15:00-04:00"
    rows = [
        ["vendor", "certificate_id", "effective_from", "expires", "received_at"],
        [
            vendor_id(company, f"{company}-C02", 9),
            company + "-replacement-9",
            native_date(company, date(2026, 10, 1)),
            native_date(company, date(2027, 12, 31)),
            at,
        ],
    ]
    rows.append(
        [
            vendor_id(company, f"{company}-C02", 10),
            company + "-replacement-10",
            native_date(company, date(2026, 10, 1)),
            native_date(company, date(2027, 12, 31)),
            at,
        ]
    )
    ref = source(
        manifest,
        files,
        company + "-replacement-certificates",
        "exports/replacement-certificates.csv",
        csv_bytes(rows),
        "text/csv",
        at,
        mapping=table_mapping(company, rows[0], at),
    )
    delivery(manifest, "replacement-certificates", [ref], at)


def snapshots(
    manifest: dict[str, Any],
    files: dict[str, bytes],
    company: str,
    cases: tuple[Invoice, ...],
) -> None:
    headers = [
        "invoice_id",
        "community",
        "vendor",
        "invoice_number",
        "amount_cents" if company == "C1" else "amount",
        "status",
        "posted_at",
        "voided_at",
    ]
    opening = [
        [
            f"{company}-OPEN-{number:03d}",
            f"{company}-C02",
            vendor_id(company, f"{company}-C02", 1),
            f"OPEN-{number:03d}",
            native_amount(company, 100000),
            ("C" if company == "C1" else "A")
            if number < 3
            else ("V" if company == "C1" else "X"),
            "2025-09-20T10:00:00-04:00",
            "" if number < 3 else "2025-09-25T10:00:00-04:00",
        ]
        for number in ((1, 2, 3, 4, 5) if company == "C1" else (1, 2, 3, 5))
    ]
    ref = source(
        manifest,
        files,
        company + "-opening-register",
        "exports/opening-ap-invoice-register.csv",
        csv_bytes([headers, *opening]),
        "text/csv",
        INITIAL,
        mapping=table_mapping(company, headers),
    )
    delivery(manifest, "opening-register", [ref], INITIAL)
    ledger = list(opening)
    day = date(2026, 10, 1)
    stream = [
        (item, chronology(item)["posted_at"])
        for item in cases
        if item.cohort == "stream"
    ]
    current_headers = list(headers)
    while day <= date(2027, 3, 31):
        if company == "C1" and day >= date(2026, 10, 15):
            current_headers[4] = "gross_cents"
        rows = [list(row) for row in ledger]
        if company == "C1" and day >= date(2026, 11, 1):
            for row in rows:
                if row[5] == "C" and (row[0].endswith("1") or row[0].endswith("3")):
                    row[5] = "R"
        at = local(day, 8).isoformat()
        identity = f"{company}-register-{day}"
        ref = source(
            manifest,
            files,
            identity,
            f"exports/register/{day}/ap-invoice-register.csv",
            csv_bytes([current_headers, *rows]),
            "text/csv",
            at,
            origin={
                "kind": "export",
                "source_system": company + "-AP",
                "export_id": identity + "-daily-postings-and-opening",
            },
        )
        delivery(manifest, identity, [ref], at)
        if company == "C1" and day == date(2026, 10, 15):
            before = source(
                manifest,
                files,
                "C1-register-D1-before",
                "exports/drift/ap-invoice-register-before-D1.csv",
                csv_bytes([headers, *rows]),
                "text/csv",
                "2026-10-15T07:59:00-04:00",
            )
            delivery(manifest, "D1-before", [before], "2026-10-15T07:59:00-04:00")
        ledger = list(opening)
        for item, posted_at in stream:
            if item.issue in ("duplicate", "cancellation"):
                continue
            if posted_at[:10] == day.isoformat():
                ledger.append(
                    [
                        item.case_id,
                        item.community,
                        vendor_id(company, item.community, 11)
                        if item.issue == "unknown-vendor"
                        else item.vendor,
                        item.number,
                        native_amount(company, item.amount),
                        "C" if company == "C1" else "A",
                        posted_at,
                        "",
                    ]
                )
        day += timedelta(days=1)
    at = "2027-03-31T23:59:59-04:00"
    if company == "C1":
        for row in ledger:
            if row[5] == "C" and (row[0].endswith("1") or row[0].endswith("3")):
                row[5] = "R"
    ref = source(
        manifest,
        files,
        company + "-final-postings",
        "exports/final-postings.csv",
        csv_bytes([current_headers, *ledger]),
        "text/csv",
        at,
        origin={
            "kind": "export",
            "source_system": company + "-AP",
            "export_id": company + "-final-day-postings-and-opening",
        },
    )
    delivery(manifest, "final-postings", [ref], at)


def build_world(world: str, seed: int, out: Path) -> dict[str, object]:
    if world != "world-1":
        raise BundleError(
            "world_unavailable: request --world world-1; all-world generation requires M1-12"
        )
    if type(seed) is not int or not 0 <= seed <= 2**63 - 1:
        raise BundleError(
            "invalid_seed: expected an integer from 0 through 9223372036854775807"
        )
    if out.exists() or out.is_symlink():
        raise BundleError("output_exists")
    if not out.parent.is_dir() or any(
        parent.is_symlink() for parent in (out.parent, *out.parent.parents)
    ):
        raise BundleError("output_parent: expected an existing directory")
    packet_root = Path(__file__).resolve().parents[3] / "docs" / "sources"
    try:
        packets = {
            company: {
                name: (packet_root / slug / name).read_bytes() for name in PACKETS[slug]
            }
            for company, slug in COMPANIES.items()
        }
    except OSError as error:
        raise BundleError("source_packet_unavailable: " + str(error)) from error
    with tempfile.TemporaryDirectory(prefix=".dex-world-", dir=out.parent) as temporary:
        staging = Path(temporary) / "collection"
        staging.mkdir()
        entries: list[dict[str, str]] = []
        for company, slug in COMPANIES.items():
            bundle, specification = company_bundle(
                company, seed, packets[company], make_cases(company, seed)
            )
            target = staging / "world-1" / slug
            target.parent.mkdir(exist_ok=True)
            write_bundle(bundle, target)
            write_world_1_artifacts(target, specification)
            entries.append(
                {
                    "path": "world-1/" + slug,
                    "bundle_id": bundle.bundle_id,
                    "company_id": company,
                    "manifest_sha256": sha256(
                        (target / "bundle.json").read_bytes()
                    ).hexdigest(),
                }
            )
        (staging / "collection.json").write_bytes(
            canonical(
                {
                    "format_version": "dex-company-collection-1",
                    "collection_id": f"{VERSION}-seed-{seed}",
                    "bundles": entries,
                }
            )
        )
        for path in staging.rglob("*"):
            if path.is_file() and (
                "eval" in path.relative_to(staging).parts
                or path.name == "collection.json"
            ):
                path.chmod(0o644)
                os.utime(path, (0, 0))
        for path in sorted(
            (path for path in staging.rglob("*") if path.is_dir()), reverse=True
        ):
            path.chmod(0o755)
            os.utime(path, (0, 0))
        staging.chmod(0o755)
        os.utime(staging, (0, 0))
        try:
            out.mkdir()
        except FileExistsError:
            raise BundleError("output_exists") from None
        try:
            staging.rename(out)
        except OSError:
            out.rmdir()
            raise
    return {
        "world": world,
        "seed": seed,
        "generator_version": VERSION,
        "companies": list(COMPANIES),
        "output": str(out),
    }


def run_build(world: str, seed: int, out: Path) -> int:
    try:
        print(canonical(build_world(world, seed, out)).decode(), end="")
        return 0
    except (BundleError, OSError) as error:
        print(
            json.dumps(
                {
                    "format": "dex-demo-error-1",
                    "code": str(error).split(":")[0],
                    "message": str(error),
                }
            ),
            file=sys.stderr,
        )
        return 2

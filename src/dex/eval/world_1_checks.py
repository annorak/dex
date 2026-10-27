import calendar
import csv
import io
import json
import zipfile
from collections import Counter
from datetime import date, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

SNOW = {
    "C1": [142, 1918, 2230, 2566, 2638, 2758, 2938, 3118, 3478],
    "C2": [2760, 2940, 3120, 3480],
}
DUPLICATES = {"C1": [313, 628, 1558, 2248, 2713, 3328], "C2": [391, 897, 2247, 2997]}
VOIDS = {"C1": [898, 3013], "C2": [500]}
PACKET_NAMES = {
    "bramblewick": [
        "procedure.md",
        "controller-email.md",
        "board-limit-notice.md",
        "service-confirmation.md",
    ],
    "fennor": ["ap-checklist.md", "payables-wiki.md", "controller-email.md"],
}
MISTAKES = {
    "C1": [
        21,
        22,
        321,
        322,
        621,
        622,
        921,
        922,
        1221,
        1222,
        1521,
        1522,
        1821,
        1822,
        2121,
        2122,
        2421,
        2422,
        2721,
        2722,
        3021,
        3022,
        3321,
        3322,
    ],
    "C2": [
        23,
        24,
        323,
        324,
        623,
        624,
        923,
        1223,
        1224,
        1523,
        1823,
        1824,
        2123,
        2423,
        2424,
        2723,
        3023,
        3024,
        3323,
        3324,
    ],
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_bytes())


def byte_manifest(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def packet_checks(root: Path, packet_root: Path) -> dict[str, object]:
    count = 0
    for slug, names in PACKET_NAMES.items():
        bundle = root / "world-1" / slug
        public = read_json(bundle / "bundle.json")
        for name in names:
            expected = (packet_root / slug / name).read_bytes()
            actual = (bundle / "sources" / name).read_bytes()
            assert actual == expected, (slug, name)
            descriptor = next(
                item for item in public["sources"] if item["path"] == "sources/" + name
            )
            assert descriptor["sha256"] == sha256(expected).hexdigest()
            expected_at = {
                "board-limit-notice.md": "2026-12-15T08:00:00-05:00",
                "service-confirmation.md": "2027-01-15T08:00:00-05:00",
            }.get(name, "2025-09-30T08:00:00-04:00")
            assert descriptor["available_at"] == expected_at
            delivered = next(
                item
                for item in public["deliveries"]
                if item["delivery_id"] == "packet-" + name
            )
            assert delivered["available_at"] == expected_at
            count += 1
        for path in (bundle / "exports").glob("*.xlsx"):
            with zipfile.ZipFile(path) as archive:
                assert archive.namelist() == sorted(archive.namelist())
                for entry in archive.infolist():
                    assert entry.date_time == (1980, 1, 1, 0, 0, 0)
                    assert entry.create_system == 3
                    assert entry.external_attr == 0o100644 << 16
                    assert not entry.extra and not entry.comment
    return {
        "packet_files": count,
        "future_delivery_exact": True,
        "xlsx_metadata_fixed": True,
    }


def membership_checks(root: Path) -> dict[str, object]:
    for company, slug in (("C1", "bramblewick"), ("C2", "fennor")):
        bundle = root / "world-1" / slug
        public = read_json(bundle / "bundle.json")
        fixture = read_json(bundle / "eval/fixture.json")
        histories = public["history"]["cases"]
        assert [item["case_id"] for item in histories] == [
            f"{company}-H{number:04d}" for number in range(1, 3601)
        ]
        assert fixture["learning"] == [
            f"{company}-H{number:04d}" for number in range(1, 2701)
        ]
        assert fixture["exam"] == [
            f"{company}-H{number:04d}" for number in range(2701, 3601)
        ]
        assert Counter(item["business_date"][:7] for item in histories) == {
            f"{year}-{month:02d}": 300
            for year, months in ((2025, range(10, 13)), (2026, range(1, 10)))
            for month in months
        }
        for month in range(12):
            group = histories[month * 300 : (month + 1) * 300]
            first = date.fromisoformat(group[0]["business_date"])
            days = calendar.monthrange(first.year, first.month)[1]
            previous = None
            for ordinal, item in enumerate(group):
                opened = datetime.fromisoformat(item["opened_at"])
                assert opened.day == 1 + ordinal * days // 300
                assert (
                    opened.utcoffset()
                    == opened.astimezone(ZoneInfo("America/New_York")).utcoffset()
                )
                assert opened.hour == 9
                assert opened.minute == (
                    0
                    if previous is None or previous.day != opened.day
                    else previous.minute + 1
                )
                previous = opened
        assert len(public["cases"]) == 1800
        assert {item["case_id"] for item in public["cases"]}.isdisjoint(
            fixture["shadow"]
        )
    return {
        "histories": [3600, 3600],
        "learning": [2700, 2700],
        "exam": [900, 900],
        "chronology_exact": True,
    }


def mistake_checks(root: Path) -> dict[str, object]:
    totals: list[list[int]] = []
    for company, slug, split in (
        ("C1", "bramblewick", (18, 6)),
        ("C2", "fennor", (15, 5)),
    ):
        bundle = root / "world-1" / slug
        mistakes = read_json(bundle / "eval/mistakes.json")
        key = read_json(bundle / "eval/answer-key.json")
        sheet = read_json(bundle / "eval/answer-sheet.json")
        expected = {f"{company}-H{number:04d}" for number in MISTAKES[company]}
        assert set(mistakes) == expected
        assert {
            identity
            for identity, action in sheet.items()
            if action["decision"] != key[identity]["decision"]
        } == expected
        assert (
            tuple(
                sum(
                    int(identity[-4:]) <= 2700
                    if cohort == 0
                    else int(identity[-4:]) > 2700
                    for identity in mistakes
                )
                for cohort in (0, 1)
            )
            == split
        )
        for identity in expected:
            assert mistakes[identity] == {
                "field": "decision",
                "observed": "board",
                "correct": "manager",
            }
            assert key[identity]["approvals"] == ["manager"]
            assert key[identity]["insurance_at_receipt"] == "valid"
        for path in (bundle / "history/actions").glob("*.csv"):
            for row in csv.DictReader(io.StringIO(path.read_text())):
                assert row["decision"] == sheet[row["case_id"]]["decision"]
                assert row["actor"] == sheet[row["case_id"]]["actor"]
        totals.append(list(split))
    return {"mistake_splits": totals, "exact_ids": True, "observed_separate": True}


def path_checks(root: Path) -> dict[str, object]:
    for company, slug in (("C1", "bramblewick"), ("C2", "fennor")):
        bundle = root / "world-1" / slug
        fixture = read_json(bundle / "eval/fixture.json")
        cases = {item["case_id"]: item for item in fixture["cases"]}
        key = read_json(bundle / "eval/answer-key.json")
        history = {
            identity: answer for identity, answer in key.items() if "-H" in identity
        }
        assert {
            identity
            for identity, answer in history.items()
            if answer.get("snow_review")
        } == {f"{company}-H{n:04d}" for n in SNOW[company]}
        assert {
            identity
            for identity, answer in history.items()
            if answer["decision"] == "duplicate"
        } == {f"{company}-H{n:04d}" for n in DUPLICATES[company]}
        assert {
            identity
            for identity, item in cases.items()
            if "-H" in identity and item["issue"] == "void-only"
        } == {f"{company}-H{n:04d}" for n in VOIDS[company]}
        cancellation: set[str] = {"C1-H2128", "C1-H3208"} if company == "C1" else set()
        assert {
            identity
            for identity, answer in history.items()
            if answer["decision"] == "cancellation"
        } == cancellation
        for identity in cancellation | {
            f"{company}-H{n:04d}" for n in DUPLICATES[company]
        }:
            assert key[identity]["effects"] == [] and key[identity]["waits"] == []
        for number in VOIDS[company]:
            assert key[f"{company}-H{number:04d}"]["state"] == "scheduled"
        pairs = (
            [(598, 628), (2113, 2248), (2668, 2713), (3028, 3328)]
            if company == "C1"
            else [(747, 897), (2734, 2997)]
        )
        for earlier, later in pairs:
            original, resend = (
                cases[f"{company}-H{earlier:04d}"],
                cases[f"{company}-H{later:04d}"],
            )
            assert (
                original["number"] == resend["number"]
                and original["vendor"] == resend["vendor"]
            )
            assert company != "C1" or original["community"] == resend["community"]
            assert datetime.fromisoformat(original["received"]) + timedelta(
                hours=1
            ) < datetime.fromisoformat(resend["received"])
        opening = list(
            csv.DictReader(
                io.StringIO(
                    (bundle / "exports/opening-ap-invoice-register.csv").read_text()
                )
            )
        )
        assert [row["status"] for row in opening] == (
            ["C", "C", "V", "V", "V"] if company == "C1" else ["A", "A", "X", "X"]
        )
        for row in opening:
            assert row["posted_at"] == "2025-09-20T10:00:00-04:00"
            assert row["voided_at"] == (
                "2025-09-25T10:00:00-04:00" if row["status"] in ("V", "X") else ""
            )
        if company == "C1":
            assert [
                date.fromisoformat(cases[f"C1-H{n:04d}"]["invoice_date"]).month
                for n in SNOW[company]
            ] == [10, 4, 5, 6, 6, 7, 7, 8, 9]
            assert cases["C1-H0100"]["number"] == cases["C1-H0101"]["number"]
            assert (
                cases["C1-H0100"]["vendor"].split("-")[-1]
                == cases["C1-H0101"]["vendor"].split("-")[-1]
            )
            assert cases["C1-H0100"]["community"] != cases["C1-H0101"]["community"]
            assert (
                key["C1-H0100"]["decision"] != "duplicate"
                and key["C1-H0101"]["decision"] != "duplicate"
            )
        months = range(4, 11) if company == "C1" else range(5, 10)
        raw = {
            identity
            for identity, item in cases.items()
            if "-H" in identity
            and item["work"] == "Snow clearing"
            and date.fromisoformat(item["invoice_date"]).month in months
        }
        assert raw == {f"{company}-H{n:04d}" for n in SNOW[company]} | cancellation
    return {
        "duplicates": [6, 4],
        "void_only": [2, 1],
        "eligible_snow": [9, 4],
        "cancellations": [2, 0],
    }


def stream_checks(root: Path) -> dict[str, object]:
    for company, slug, opening in (("C1", "bramblewick", 13), ("C2", "fennor", 6)):
        bundle = root / "world-1" / slug
        fixture = read_json(bundle / "eval/fixture.json")
        cases = {item["case_id"]: item for item in fixture["cases"]}
        key = read_json(bundle / "eval/answer-key.json")
        assert fixture["stream"] == [f"{company}-S{n:04d}" for n in range(1, 1801)]
        assert fixture["opening"] == [
            f"{company}-S{n:04d}" for n in range(1, opening + 1)
        ]
        assert fixture["shadow"] == [f"{company}-SH{n:02d}" for n in range(1, 11)]
        for identity in fixture["opening"]:
            assert cases[identity]["received"][:10] == "2026-10-02"
        for identity in fixture["shadow"]:
            assert cases[identity]["received"][:10] == "2026-10-01"
        stream = [cases[identity] for identity in fixture["stream"]]
        assert Counter(item["received"][:7] for item in stream) == {
            month: 300
            for month in (
                "2026-10",
                "2026-11",
                "2026-12",
                "2027-01",
                "2027-02",
                "2027-03",
            )
        }
        for ordinal in range(opening + 1, 301):
            day = 3 + (ordinal - opening - 1) * 29 // (300 - opening)
            assert (
                date.fromisoformat(
                    cases[f"{company}-S{ordinal:04d}"]["received"][:10]
                ).day
                == day
            )
        previous = None
        for number, item in enumerate(stream):
            received = datetime.fromisoformat(item["received"])
            assert (
                received.utcoffset()
                == received.astimezone(ZoneInfo("America/New_York")).utcoffset()
            )
            if number >= 300:
                assert (
                    received.day
                    == 1
                    + (number % 300)
                    * calendar.monthrange(received.year, received.month)[1]
                    // 300
                )
            assert received.hour == 9 and received.minute == (
                previous.minute + 1
                if previous is not None and previous.date() == received.date()
                else 0
            )
            previous = received
        issues = (
            [
                "proposal-review",
                "scheduled",
                "duplicate",
                "void-only",
                "unknown-vendor",
                "ambiguous-community",
                "conflicting-amount",
                "expired-certificate",
                "missing-certificate",
                "snow-review",
                "cancellation",
                "rejected",
                "unanswered",
            ]
            if company == "C1"
            else [
                "ordinary",
                "local-board",
                "second-signer",
                "duplicate",
                "void-only",
                "expired-certificate",
            ]
        )
        assert [cases[identity]["issue"] for identity in fixture["opening"]] == issues
        for identity in fixture["stream"]:
            answer = key[identity]
            for wait in answer["waits"]:
                if wait.get("responded_at"):
                    assert datetime.fromisoformat(
                        wait["responded_at"]
                    ) <= datetime.fromisoformat(wait["due_at"])
                    assert wait["responded_at"] <= "2027-03-31T23:59:59-04:00"
                    assert wait["actor"].startswith(company) or wait["actor"] == (
                        "Iona Vale" if company == "C1" else "Orla Fen"
                    )
                else:
                    assert identity == "C1-S0013"
        pending = {
            identity
            for identity in fixture["stream"]
            if key[identity]["state"] == "pending"
        }
        assert pending == ({"C1-S0013"} if company == "C1" else set())
        events = {item["id"]: item for item in fixture["events"]}
        assert events[company + "-review"]["at"] == "2026-10-02T08:30:00-04:00"
        assert events[company + "-grant"]["at"] == "2026-12-20T08:30:00-05:00"
        assert events[company + "-grant"]["amount_limit_cents"] == 500000
        assert events[company + "-grant"]["business_decisions_supplied"] is False
        if company == "C1":
            worked = cases["C1-S0001"]
            assert (
                worked["community"],
                worked["vendor"],
                worked["number"],
                worked["amount"],
                worked["invoice_date"],
            ) == ("C1-C03", "C1-C03-V07", "AF-11496", 180000, "2026-09-29")
            answer = key["C1-S0001"]
            assert (
                answer["decision"],
                answer["posting_month"],
                answer["due_date"],
            ) == ("board", "2026-09", "2026-10-29")
            assert [effect["operation"] for effect in answer["effects"]] == [
                "record_invoice",
                "request_approval",
                "schedule_payment",
            ]
            assert answer["effects"][-1]["payload"]["date"] == "2026-10-29"
            assert (
                key["C1-S0002"]["decision"] == "manager"
                and key["C1-S0002"]["state"] == "scheduled"
            )
            assert key["C1-S0008"]["insurance_at_receipt"] == "expired"
            assert key["C1-S0009"]["insurance_at_receipt"] == "missing"
            assert key["C1-S0010"]["snow_review"]
            assert key["C1-S0012"]["state"] == "rejected"
            assert [effect["operation"] for effect in key["C1-S0012"]["effects"]] == [
                "record_invoice",
                "request_approval",
            ]
            assert (
                cases["C1-S0451"]["received"][:10] == "2026-11-16"
                and cases["C1-S0451"]["amount"] == 240000
            )
            assert key["C1-S0451"]["decision"] == "board"
            for identity, route in (
                ("C1-S0900", "board"),
                ("C1-S0901", "manager"),
                ("C1-S0902", "board"),
            ):
                assert key[identity]["decision"] == route
            assert not key["C1-S1200"]["service_confirmation"]
            assert key["C1-S1201"]["service_confirmation"]
            assert not key["C1-S1202"]["service_confirmation"]
            assert [
                item["case_id"]
                for item in read_json(bundle / "eval/ai-extractions.json")
            ] == ["C1-S0601", "C1-S0602", "C1-S0603"]
            assert all(
                item["format"] != "F4"
                for item in stream
                if item["received"][:10] < "2026-12-01"
            )
            assert events["D1"]["at"] == "2026-10-15T08:00:00-04:00"
            assert events["D2"]["at"] == "2026-11-01T08:00:00-05:00"
            assert events["D3"]["at"] == "2026-11-15T08:00:00-05:00"
        else:
            assert cases["C2-S0901"]["format"] == "F4"
            assert all(
                item["format"] != "F4"
                for item in stream
                if item["received"][:10] < "2027-01-01"
            )
            assert read_json(bundle / "eval/ai-extractions.json") == []
            waits = key["C2-S0003"]["waits"]
            assert [wait["role"] for wait in waits] == ["board", "finance_signer"]
            assert waits[0]["actor"] != waits[1]["actor"]
        public = read_json(bundle / "bundle.json")
        registers = [
            item
            for item in public["sources"]
            if item["path"].endswith("/ap-invoice-register.csv")
        ]
        assert len(registers) == 182
        for descriptor in registers:
            assert descriptor["available_at"][11:19] == "08:00:00"
            for row in csv.DictReader(
                io.StringIO((bundle / descriptor["path"]).read_text())
            ):
                assert datetime.fromisoformat(
                    row["posted_at"]
                ) < datetime.fromisoformat(descriptor["available_at"])
        if company == "C1":
            before = (
                bundle / "exports/register/2026-10-14/ap-invoice-register.csv"
            ).read_text()
            after = (
                bundle / "exports/register/2026-10-15/ap-invoice-register.csv"
            ).read_text()
            assert before.startswith(
                "invoice_id,community,vendor,invoice_number,amount_cents,"
            )
            assert after.startswith(
                "invoice_id,community,vendor,invoice_number,gross_cents,"
            )
            same_before = (
                bundle / "exports/drift/ap-invoice-register-before-D1.csv"
            ).read_bytes()
            assert (
                same_before.replace(b"amount_cents", b"gross_cents", 1)
                == after.encode()
            )
            statuses = {
                row["status"]
                for row in csv.DictReader(
                    io.StringIO(
                        (
                            bundle
                            / "exports/register/2026-11-01/ap-invoice-register.csv"
                        ).read_text()
                    )
                )
            }
            assert {"C", "R", "V"} <= statuses
        chronology_checks(bundle, cases, key)
    return {
        "stream_cases": [1800, 1800],
        "opening_cases": 19,
        "shadow_cases": [10, 10],
        "dates_exact": True,
    }


def chronology_checks(bundle: Path, cases: dict[str, Any], key: dict[str, Any]) -> None:
    operations = read_json(bundle / "eval/operation-schedule.json")
    events = {event["id"]: event for event in operations["events"]}
    postings: dict[str, dict[str, str]] = {}
    for path in [
        bundle / "exports/opening-ap-invoice-register.csv",
        *sorted((bundle / "exports/register").glob("*/ap-invoice-register.csv")),
        bundle / "exports/final-postings.csv",
    ]:
        for row in csv.DictReader(io.StringIO(path.read_text())):
            postings[row["invoice_id"]] = row
    for path in sorted((bundle / "history/actions").glob("*.csv")):
        for row in csv.DictReader(io.StringIO(path.read_text())):
            if row["posting_time"]:
                postings[row["case_id"]] = {
                    **row,
                    "invoice_id": row["case_id"],
                    "posted_at": row["posting_time"],
                    "voided_at": "",
                }
    for identity, case in cases.items():
        answer = key[identity]
        if case["issue"] == "void-only":
            matching = [
                row
                for row in postings.values()
                if row["vendor"] == case["vendor"]
                and row["invoice_number"].strip() == case["number"].strip()
                and datetime.fromisoformat(row["posted_at"])
                < datetime.fromisoformat(case["received"])
            ]
            assert matching and all(row["status"] in ("V", "X") for row in matching)
            assert answer["state"] == "scheduled"
        if case["issue"] == "unknown-vendor":
            resolution = next(
                wait for wait in answer["waits"] if wait["role"] == "ap_clerk"
            )
            certificate = resolution["value"]["certificate"]
            assert answer["insurance_at_receipt"] == "missing"
            assert certificate["vendor_id"] == resolution["value"]["vendor_id"]
            assert (
                certificate["effective_from"]
                <= case["received"][:10]
                <= certificate["expires"]
            )
            assert certificate["available_at"] == resolution["observed_at"]
            assert datetime.fromisoformat(
                certificate["available_at"]
            ) < datetime.fromisoformat(answer["eligible_at"])
        if case["cohort"] != "stream" or not answer["effects"]:
            continue
        posted = datetime.fromisoformat(postings[identity]["posted_at"])
        authorized = datetime.fromisoformat(events[identity + "/record/1/review"]["at"])
        confirmed = datetime.fromisoformat(
            events[identity + "/record/1/confirmed"]["at"]
        )
        requested = datetime.fromisoformat(
            events[identity + "/request/1/confirmed"]["at"]
        )
        assert authorized < posted < confirmed < requested
        assert postings[identity]["invoice_number"] == case["number"]
        assert postings[identity]["community"] == case["community"]
        request = next(
            effect
            for effect in answer["effects"]
            if effect["operation"] == "request_approval"
        )
        assert request["payload"]["work"] == case["work"]
        assert request["payload"]["due_date"] == answer["due_date"]
        assert request["payload"]["payment_holds"] == (
            [case["issue"]]
            if case["issue"] in ("expired-certificate", "missing-certificate")
            else []
        )
        assert {"work", "due_date", "payment_holds"} <= set(
            events[identity + "/request/1/review"]["fields"]
        )
        for wait in answer["waits"]:
            if wait["role"] == "ap_clerk" or not wait.get("responded_at"):
                continue
            submission = (
                datetime.fromisoformat(
                    events[identity + "/service-request/1/confirmed"]["at"]
                )
                if wait["role"] == "community_manager_service"
                else requested
            )
            assert (
                submission
                < datetime.fromisoformat(wait["responded_at"])
                <= datetime.fromisoformat(wait["observed_at"])
            )
            if answer["state"] == "scheduled":
                assert datetime.fromisoformat(
                    wait["observed_at"]
                ) < datetime.fromisoformat(
                    events[identity + "/schedule/1/review"]["at"]
                )


def key_checks(root: Path) -> dict[str, object]:
    for company, slug in (("C1", "bramblewick"), ("C2", "fennor")):
        bundle = root / "world-1" / slug
        manifest = read_json(bundle / "eval/manifest.json")
        assert manifest["reference_programs"] == []
        assert manifest["key_frozen_before_reference_execution"] is True
        for name, digest in manifest["artifacts"].items():
            assert sha256((bundle / "eval" / name).read_bytes()).hexdigest() == digest
        public = read_json(bundle / "bundle.json")
        assert all(
            not item["path"].startswith("eval/")
            for item in public["sources"] + public["recordings"]
        )
        key = read_json(bundle / "eval/answer-key.json")
        assert len(key) == 5410
        assert key[f"{company}-H0001"]["decision"] == "manager"
        assert key[f"{company}-H0002"]["decision"] == "board"
        assert key[f"{company}-H0003"]["decision"] == "manager"
        assert key[f"{company}-H0004"]["decision"] == "board"
        assert key[f"{company}-H0007"]["terms_days"] == 10
        assert key[f"{company}-H0009"]["posting_month"] == "2025-09"
        if company == "C2":
            assert not key["C2-H0005"]["second_signer"]
            assert key["C2-H0006"]["second_signer"]
        operations = read_json(bundle / "eval/operation-schedule.json")
        events = operations["events"]
        assert events == sorted(
            events, key=lambda event: (datetime.fromisoformat(event["at"]), event["id"])
        )
        assert operations["cutoff"] == "2027-03-31T23:59:59-04:00"
        assert operations["event_envelopes_are_executable"] is False
        assert events[-1]["at"] <= operations["cutoff"]
        for event in events:
            at = datetime.fromisoformat(event["at"])
            assert (
                at.utcoffset()
                == at.astimezone(ZoneInfo("America/New_York")).utcoffset()
            )
            if event["kind"] == "proposal_review":
                assert event["expected_revision"] == event["reviewed_revision"] == 1
                assert event["delivered"] == event["sampling"]["requires_review"]
        ordinals = [
            value["eligible_ordinal"]
            for value in operations["sampling"].values()
            if value["eligible_ordinal"] is not None
        ]
        assert sorted(ordinals) == list(range(1, len(ordinals) + 1))
        assert operations["sampled_case_ids"]
        assert all(
            operations["sampling"][identity]["eligible_ordinal"] % 20 == 0
            for identity in operations["sampled_case_ids"]
        )
        prefix = operations["opening_prefix"]
        if company == "C1":
            assert any(
                event["id"] == "C1-S0002/schedule/1/confirmed" for event in prefix
            )
            assert not any(
                event["case_id"]
                in ("C1-S0001", "C1-S0005", "C1-S0006", "C1-S0007", "C1-S0010")
                for event in prefix
            )
        assert set(read_json(bundle / "eval/shadow-inputs.json")) == {
            f"{company}-SH{number:02d}" for number in range(1, 11)
        }
        scripts = read_json(bundle / "eval/response-scripts.json")
        assert {answer["actor"] for answer in scripts["employee_answers"]} == (
            {"Iona Vale"} if company == "C1" else {"Orla Fen"}
        )
    return {
        "keys_frozen": True,
        "reference_programs": 0,
        "independent_boundary_answers": True,
    }


def variation_checks(first: Path, second: Path) -> dict[str, object]:
    for slug in ("bramblewick", "fennor"):
        left = read_json(first / "world-1" / slug / "eval/fixture.json")
        right = read_json(second / "world-1" / slug / "eval/fixture.json")
        assert left["seed"] == 7 and right["seed"] == 11
        for field in (
            "learning",
            "exam",
            "stream",
            "shadow",
            "opening",
            "events",
            "source_hashes",
        ):
            assert left[field] == right[field]
        a, b = left["cases"], right["cases"]
        assert [
            (item["case_id"], item["received"], item["format"], item["issue"])
            for item in a
        ] == [
            (item["case_id"], item["received"], item["format"], item["issue"])
            for item in b
        ]
        assert any(x["amount"] != y["amount"] for x, y in zip(a, b, strict=True))
    path_checks(second)
    mistake_checks(second)
    stream_checks(second)
    key_checks(second)
    return {"seeds": [7, 11], "permitted_variation": True, "named_sets_unchanged": True}

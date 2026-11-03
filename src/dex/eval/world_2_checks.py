import csv
import io
import json
import os
from collections import Counter
from datetime import date, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any
from unittest.mock import patch

from dex.bundle.model import BundleError
from dex.bundle.projection import decode_learning_view, materialize_learning
from dex.bundle.reader import load_bundle
from dex.bundle.validation import canonical
from dex.eval.world_2 import artifacts


def read_json(path: Path) -> Any:
    return json.loads(path.read_bytes())


def rows(bundle: Path, path: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO((bundle / path).read_text())))


def packet_checks(world: Path, packet_root: Path) -> dict[str, object]:
    bundle = world / "world-2/veldren"
    public = read_json(bundle / "bundle.json")
    fixture = read_json(bundle / "eval/fixture.json")
    for name, issued in (
        ("handbook.md", "2025-09-01"),
        ("service-owner-email.md", "2025-09-22"),
    ):
        content = (packet_root / "veldren" / name).read_bytes()
        assert (bundle / "sources" / name).read_bytes() == content
        assert fixture["source_hashes"][name] == sha256(content).hexdigest()
        assert not any(
            word in content.lower()
            for word in (
                b"shared",
                b"same cutover",
                b"client-confirmed",
                b"onb-",
                b"dex",
            )
        )
        descriptor = next(
            item for item in public["sources"] if item["path"] == "sources/" + name
        )
        assert descriptor["occurred_at"][:10] == issued
        assert descriptor["available_at"] == "2025-09-30T08:00:00-04:00"
    return {"packet_files": 2, "exact_bytes": True, "hidden_rule_absent": True}


def history_checks(world: Path) -> dict[str, object]:
    bundle = world / "world-2/veldren"
    public = read_json(bundle / "bundle.json")
    fixture = read_json(bundle / "eval/fixture.json")
    key = read_json(bundle / "eval/answer-key.json")
    ids = [f"H{number:03d}" for number in range(1, 49)]
    assert [case["case_id"] for case in public["history"]["cases"]] == ids
    assert fixture["learning"] == ids[:36] and fixture["exam"] == ids[36:]
    months = [
        "2025-10",
        "2025-11",
        "2025-12",
        "2026-01",
        "2026-02",
        "2026-03",
        "2026-04",
        "2026-05",
        "2026-06",
        "2026-07",
        "2026-08",
        "2026-09",
    ]
    expected_dates = [
        month + "-" + day for month in months for day in ("01", "08", "15", "22")
    ]
    assert [
        case["opened_at"][:10] for case in public["history"]["cases"]
    ] == expected_dates
    for case in public["history"]["cases"]:
        opened = datetime.fromisoformat(case["opened_at"])
        complete = datetime.fromisoformat(key[case["case_id"]]["completed_at"])
        assert opened.hour == 8 and timedelta(0) < complete - opened < timedelta(days=7)
        assert all(
            datetime.fromisoformat(event["available_at"]).date()
            <= opened.date() + timedelta(days=6)
            for event in case["observations"]
        )
    assert key["H036"]["completed_at"][:10] <= "2026-06-28"
    return {
        "history": ids,
        "learning": ids[:36],
        "exam": ids[36:],
        "chronology_exact": True,
    }


def nested_checks(world: Path) -> dict[str, object]:
    bundle = world / "world-2/veldren"
    fixture = read_json(bundle / "eval/fixture.json")
    key = read_json(bundle / "eval/answer-key.json")
    cases = {case["case_id"]: case for case in fixture["cases"]}
    multi = [
        identity
        for identity, case in cases.items()
        if identity.startswith("H") and len(case["sites"]) == 2
    ]
    both = [
        identity
        for identity, case in cases.items()
        if identity.startswith("H")
        and any(site["services"] == ["payroll", "benefits"] for site in case["sites"])
    ]
    waits = [
        identity
        for identity, answer in key.items()
        if identity.startswith("H") and answer["waits"]
    ]
    expected_multi = [
        f"H{base + local:03d}"
        for base in (0, 12, 24, 36)
        for local in (1, 2, 3, 4, 5, 6, 7, 8)
    ]
    expected_both = [
        f"H{base + local:03d}" for base in (0, 12, 24, 36) for local in (2, 4, 6, 8)
    ]
    expected_waits = [
        f"H{base + local:03d}"
        for base in (0, 12, 24, 36)
        for local in (2, 4, 6, 8, 10, 12)
    ]
    assert multi == expected_multi and both == expected_both and waits == expected_waits
    for identity, case in cases.items():
        local = (int(identity[1:]) - 1) % 12 + 1
        if identity.startswith("H"):
            expected = (
                [["payroll", "benefits"], ["payroll"]]
                if identity in both
                else [["payroll"], ["benefits"]]
                if identity in multi
                else [["payroll"]]
                if local in (9, 11)
                else [["benefits"]]
            )
        else:
            expected = (
                [["payroll", "benefits"], ["payroll"]]
                if identity in ("S002", "S006", "S010", "S014")
                else [["payroll"]]
                if identity in ("S003", "S011")
                else [["benefits"]]
                if identity in ("S007", "S015")
                else [["payroll"], ["benefits"]]
            )
        assert [site["services"] for site in case["sites"]] == expected
        native_services = rows(bundle, f"exports/{identity}/services.csv")
        assert [(row["site_id"], row["service"]) for row in native_services] == [
            (site["site_id"], service)
            for site in case["sites"]
            for service in site["services"]
        ]
        employees = rows(bundle, f"exports/{identity}/employees.csv")
        assert (
            len({row["employee_id"] for row in employees})
            == len(employees)
            == 2 * len(expected)
        )
        assert all(
            row["client_id"] == case["client_id"] and row["case_id"] == identity
            for row in employees
        )
        for site in case["sites"]:
            if "payroll" not in site["services"]:
                assert (
                    "pay_frequency" not in site and "payroll_cutover_date" not in site
                )
            assert [
                row["employee_id"]
                for row in employees
                if row["site_id"] == site["site_id"]
            ] == [employee["employee_id"] for employee in site["employees"]]
    return {
        "multi_site": multi,
        "both_services": both,
        "client_waits": waits,
        "nested_identities_exact": True,
    }


def wait_checks(world: Path) -> dict[str, object]:
    bundle = world / "world-2/veldren"
    fixture = read_json(bundle / "eval/fixture.json")
    key = read_json(bundle / "eval/answer-key.json")
    public = read_json(bundle / "bundle.json")
    descriptors = {source["source_id"]: source for source in public["sources"]}
    three = [f"H{base + local:03d}" for base in (0, 12, 24, 36) for local in (2, 6, 10)]
    five = [f"H{base + local:03d}" for base in (0, 12, 24, 36) for local in (4, 8, 12)]
    source_cases = {
        case["case_id"]: case for case in public["history"]["cases"] + public["cases"]
    }
    for case in fixture["cases"]:
        identity = case["case_id"]
        days = (
            3
            if identity in three + ["S002", "S006", "S010", "S014"]
            else 5
            if identity in five + ["S004", "S008", "S012", "S016"]
            else 0
        )
        waits = key[identity]["waits"]
        assert len(waits) == int(days > 0)
        if not days:
            continue
        wait = waits[0]
        opened = datetime.fromisoformat(case["opened_at"])
        response = datetime.fromisoformat(wait["responded_at"])
        assert (
            response.date() == opened.date() + timedelta(days=days)
            and response.hour == 9
        )
        assert wait["issued_at"] == case["opened_at"].replace("T08:", "T10:")
        assert datetime.fromisoformat(
            wait["due_at"]
        ).date() == opened.date() + timedelta(days=3)
        assert wait["due_at"][11:19] == "23:59:59"
        assert (
            wait["request_id"] == identity + "-client-request-v1"
            and wait["request_revision"] == 1
        )
        assert (
            wait["client_id"] == case["client_id"] and wait["actor"] == case["sponsor"]
        )
        assert (
            wait["requires_existing_request"] is True
            and wait["available_at"] == wait["responded_at"]
        )
        if days == 5:
            overdue = datetime.fromisoformat(wait["overdue_at"])
            assert (
                overdue.date() == opened.date() + timedelta(days=4)
                and overdue.hour == 0
            )
        else:
            assert wait["overdue_at"] is None
        observed = [
            event
            for event in source_cases[identity]["observations"]
            if "-client-response-" in event["observation_id"]
        ]
        actual_changes: list[dict[str, str]] = []
        for event in observed:
            assert event["available_at"] == wait["responded_at"]
            source = descriptors[event["source"]["source_id"]]
            for row in rows(bundle, source["path"]):
                assert (
                    row["request_id"] == wait["request_id"]
                    and row["request_revision"] == "1"
                )
                assert (
                    row["response_id"] == wait["response_id"]
                    and row["client_id"] == case["client_id"]
                )
                actual_changes.append(
                    {name: row[name] for name in ("site_id", "field", "value")}
                )
        assert actual_changes == wait["changes"]
        request_rows = rows(bundle, f"history/events/{wait['request_id']}.csv")
        assert json.loads(request_rows[0]["fields"]) == [
            {name: change[name] for name in ("site_id", "field")}
            for change in wait["changes"]
        ]
    return {
        "three_day_history": three,
        "five_day_history": five,
        "exact_requests_and_responses": True,
    }


def key_checks(world: Path) -> dict[str, object]:
    bundle = world / "world-2/veldren"
    fixture = read_json(bundle / "eval/fixture.json")
    key = read_json(bundle / "eval/answer-key.json")
    mistakes = read_json(bundle / "eval/mistakes.json")
    observed = read_json(bundle / "eval/answer-sheet.json")
    manifest = read_json(bundle / "eval/manifest.json")
    assert sorted(mistakes) == ["H008", "H019", "H031", "H044"]
    assert sorted(
        identity
        for identity in observed
        if observed[identity]["activated_at"] != key[identity]["completed_at"]
    ) == sorted(mistakes)
    for identity in mistakes:
        activation = datetime.fromisoformat(observed[identity]["activated_at"])
        owner = datetime.fromisoformat(observed[identity]["owner_decided_at"])
        assert activation.date() == owner.date() - timedelta(days=1)
        assert (
            activation.date()
            == datetime.fromisoformat(key[identity]["summary"]["ready_at"]).date()
        )
        assert activation.hour == 12
    hidden = ["H006", "H018", "H030", "H042"]
    cases = {case["case_id"]: case for case in fixture["cases"]}
    actual_hidden = [
        identity
        for identity, case in cases.items()
        if len(
            {
                site["payroll_cutover_date"]
                for site in case["sites"]
                if "payroll" in site["services"]
            }
        )
        > 1
    ]
    assert actual_hidden == hidden
    for identity in hidden:
        assert len(key[identity]["waits"][0]["changes"]) == 2
        assert (
            len(
                {
                    site["payroll_cutover_date"]
                    for site in key[identity]["effects"][0]["payload"]["sites"]
                }
            )
            == 1
        )
    script = read_json(bundle / "eval/response-scripts.json")["employee_answers"][0]
    assert script["evidence_cases"] == hidden[:3]
    assert (
        script["effective_from"] == "2025-10-01"
        and script["available_at"] == "2026-10-01T10:00:00-04:00"
    )
    assert (
        manifest["key_frozen_before_reference_execution"] is True
        and manifest["reference_programs"] == []
    )
    for name, digest in manifest["artifacts"].items():
        assert sha256((bundle / "eval" / name).read_bytes()).hexdigest() == digest

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("key construction attempted execution")

    with (
        patch("dex.core.program.verify_program", forbidden),
        patch("dex.core.runtime.decide", forbidden),
        patch("dex.core.runtime.rebuild", forbidden),
        patch("dex.core.language.execute_function", forbidden),
    ):
        assert (
            artifacts(fixture)["answer-key.json"]
            == (bundle / "eval/answer-key.json").read_bytes()
        )
    return {
        "mistakes": sorted(mistakes),
        "learning_evidence": hidden[:3],
        "exam_evidence": hidden[3:],
        "keys_independent_and_frozen": True,
    }


def stream_checks(world: Path) -> dict[str, object]:
    bundle = world / "world-2/veldren"
    fixture = read_json(bundle / "eval/fixture.json")
    key = read_json(bundle / "eval/answer-key.json")
    stream = [case for case in fixture["cases"] if case["case_id"].startswith("S")]
    ids = [f"S{number:03d}" for number in range(1, 17)]
    assert [case["case_id"] for case in stream] == ids
    completions = (2, 6, 4, 10, 6, 10, 8, 14, 10, 14, 12, 18, 14, 18, 16, 22)
    for number, case in enumerate(stream, 1):
        identity = case["case_id"]
        assert case["opened_at"] == f"2027-01-{number:02d}T08:00:00-05:00"
        answer = key[identity]
        day = f"2027-01-{completions[number - 1]:02d}"
        assert answer["completed_at"] == day + "T12:00:00-05:00"
        assert answer["business_decision"]["decided_at"] == day + "T10:00:00-05:00"
        assert answer["engine_authority"]["approved_at"] == day + "T11:00:00-05:00"
        assert answer["business_decision"]["never_automate"] is True
        assert (
            answer["engine_authority"]["payload_sha256"]
            == sha256(canonical(answer["effects"][0]["payload"])).hexdigest()
        )
        assert (
            answer["effects"][0]["authority_id"]
            == answer["engine_authority"]["approval_id"]
        )
        if answer["waits"]:
            assert any(
                branch["site_id"].endswith("-2")
                and branch["ready_at"] == case["opened_at"].replace("T08:", "T09:")
                for branch in answer["branches"]
            )
            assert len(answer["waits"][0]["changes"]) == 1
    cutoff = "2027-01-10T23:59:59-05:00"
    complete = [identity for identity in ids if key[identity]["completed_at"] <= cutoff]
    unopened = [case["case_id"] for case in stream if case["opened_at"] > cutoff]
    pending = [identity for identity in ids if identity not in complete + unopened]
    expected = {
        "complete": ["S001", "S002", "S003", "S004", "S005", "S006", "S007", "S009"],
        "waiting": ["S008", "S010"],
        "not_opened": ["S011", "S012", "S013", "S014", "S015", "S016"],
    }
    assert (
        {"complete": complete, "waiting": pending, "not_opened": unopened}
        == expected
        == fixture["cutoffs"][cutoff]
    )
    assert fixture["cutoffs"]["2027-01-23T23:59:59-05:00"] == {
        "complete": ids,
        "waiting": [],
        "not_opened": [],
    }
    assert key["S016"]["waits"][0]["responded_at"] == "2027-01-21T09:00:00-05:00"
    schedule = read_json(bundle / "eval/operation-schedule.json")
    assert schedule["status"] == "fixture_requirements"
    events = schedule["events"]
    assert sum(event["touches"] for event in events) == 40
    assert sum(event["touches"] for event in events if event["at"] <= cutoff) == 19
    weeks: Counter[str] = Counter()
    for event in events:
        day = date.fromisoformat(event["at"][:10])
        weeks[(day - timedelta(days=day.weekday())).isoformat()] += event["touches"]
    assert dict(weeks) == {
        "2026-12-28": 2,
        "2027-01-04": 17,
        "2027-01-11": 14,
        "2027-01-18": 7,
    }
    assert [
        event["case_id"] for event in events if event["kind"] == "overdue_notification"
    ] == ["S004", "S008", "S012", "S016"]
    assert "reference_execution" in fixture["unimplemented"]
    return {
        "stream": ids,
        "january_10": expected,
        "final_complete": ids,
        "fixture_schedule_exact": True,
        "execution_claimed": False,
    }


def isolation_checks(world: Path) -> dict[str, object]:
    path = world / "world-2/veldren"
    original = os.open

    def guarded(name: Any, *args: Any, **kwargs: Any) -> int:
        if (
            isinstance(name, (str, bytes, Path))
            and "eval" in Path(os.fsdecode(name)).parts
        ):
            raise AssertionError("public validation read evaluator")
        return original(name, *args, **kwargs)

    with patch("os.open", guarded):
        bundle = load_bundle(path)
    view = materialize_learning(
        bundle, datetime.fromisoformat("2026-09-30T23:59:59-04:00")
    )
    data = json.loads(view.content)
    assert [case["case_id"] for case in data["cases"]] == [
        f"H{number:03d}" for number in range(1, 37)
    ]
    forbidden = [f"H{number:03d}".encode() for number in range(37, 49)] + [
        b"answer-key",
        b"mistakes.json",
        b"response-scripts",
        b"ONB-",
        b"shared-payroll-confirmation",
        b"Bramblewick",
        b"Fennor",
        b"C1-",
        b"C2-",
    ]
    assert not any(value in view.content for value in forbidden)
    assert str(world).encode() not in view.content
    assert decode_learning_view(view.content).content == view.content
    try:
        materialize_learning(
            bundle, datetime.fromisoformat("2025-11-10T23:59:59-05:00")
        )
    except BundleError as error:
        assert str(error) == "history_adequacy_unavailable"
    else:
        raise AssertionError("learning admitted before history adequacy")
    assert b"H006-client-response" in view.content
    assert not any(
        f"S{number:03d}-client-response".encode() in view.content
        for number in range(1, 17)
    )
    before = materialize_learning(
        bundle, datetime.fromisoformat("2026-10-01T09:59:59-04:00")
    )
    after = materialize_learning(
        bundle, datetime.fromisoformat("2026-10-01T10:00:00-04:00")
    )
    assert b"C3-shared-payroll-confirmation" not in before.content
    assert (
        b"C3-shared-payroll-confirmation" in after.content
        and b"2025-10-01" in after.content
    )
    for original_file in bundle.originals:
        assert not any(
            value in original_file.content.lower()
            for value in (
                b"social security",
                b"ssn",
                b"bank_account",
                b"medical",
                b"routing_number",
            )
        )
    key_checks(world)
    return {
        "learning_cases": 36,
        "exam_excluded": True,
        "evaluator_excluded": True,
        "future_responses_excluded": True,
        "other_company_excluded": True,
        "self_contained": True,
        "synthetic_only": True,
    }


def variation_checks(first: Path, second: Path) -> dict[str, object]:
    left, right = first / "world-2/veldren", second / "world-2/veldren"
    a, b = read_json(left / "eval/fixture.json"), read_json(right / "eval/fixture.json")
    assert a["seed"] == 7 and b["seed"] == 11
    changed = 0
    derived = 0
    keys = [read_json(root / "eval/answer-key.json") for root in (left, right)]
    for source in read_json(left / "bundle.json")["sources"]:
        path = source["path"]
        old, new = (left / path).read_bytes(), (right / path).read_bytes()
        if old == new:
            continue
        one, two = rows(left, path), rows(right, path)
        if path.startswith("exports/"):
            assert path.endswith(("/client.csv", "/employees.csv"))
            field = "name" if path.endswith("/client.csv") else "display_name"
            assert [row.pop(field) for row in one] != [row.pop(field) for row in two]
            changed += 1
        else:
            assert path.startswith("history/events/") and path.endswith(
                ("-summary.csv", "-owner.csv", "-authority.csv", "-activation.csv")
            )
            assert len(one) == len(two) == 1
            for row, key in zip((one[0], two[0]), keys, strict=True):
                payload = key[row["case_id"]]["effects"][0]["payload"]
                digest = sha256(canonical(payload)).hexdigest()
                field = (
                    "summary_sha256"
                    if path.endswith(("-summary.csv", "-owner.csv"))
                    else "payload_sha256"
                )
                assert row.pop(field) == digest
                if "configuration" in row:
                    configuration = json.loads(row["configuration"])
                    assert configuration == payload
                    for site in configuration["sites"]:
                        for employee in site["employees"]:
                            employee.pop("display_name")
                    row["configuration"] = canonical(configuration).decode()
            derived += 1
        assert one == two
    assert changed == 128 and derived == 256
    for world in (first, second):
        history_checks(world)
        nested_checks(world)
        wait_checks(world)
        key_checks(world)
        stream_checks(world)
    return {"changed_name_exports": changed, "only_permitted_variation": True}


def change_checks(world: Path, name: str) -> dict[str, object]:
    changes = read_json(world / "world-2/veldren/eval/change-scenarios.json")
    fixture = read_json(world / "world-2/veldren/eval/fixture.json")
    assert all(item["case_id"] not in fixture["stream"] for item in changes.values())
    if name == "world2-unfamiliar-status":
        item = changes["unfamiliar_status"]
        assert item["request"]["request_id"] == item["response"]["request_id"]
        assert item["expected"]["pending"] == ["CHANGE-STATUS-site-1/payroll"]
        assert item["expected"]["ready"] == ["CHANGE-STATUS-site-2/benefits"]
        assert item["expected"]["effects_before_resolution"] == []
    else:
        item = changes["changed_summary"]
        assert (
            item["decisions"][0]["summary_revision"] == 1
            and item["decisions"][1]["summary_revision"] == 2
        )
        assert item["expected"]["old_decision_covers_revision_2"] is False
        assert item["expected"]["effects_before_new_decision"] == []
    return {
        "separate_from_stream": True,
        "requirements_preserved": True,
        "execution_claimed": False,
    }

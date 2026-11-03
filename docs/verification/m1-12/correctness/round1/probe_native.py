import argparse
import csv
import io
import json
from collections import Counter
from datetime import date, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo

parser = argparse.ArgumentParser()
parser.add_argument("--bundle", type=Path, required=True)
args = parser.parse_args()
BUNDLE = args.bundle
NY = ZoneInfo("America/New_York")


def read(name):
    return json.loads((BUNDLE / name).read_bytes())


def table(name):
    return list(csv.DictReader(io.StringIO((BUNDLE / name).read_text())))


def timestamp(day, clock):
    return datetime.fromisoformat(str(day) + "T" + clock).replace(tzinfo=NY).isoformat()


manifest = read("bundle.json")
key = read("eval/answer-key.json")
sheet = read("eval/answer-sheet.json")
fixture = read("eval/fixture.json")
sources = {item["source_id"]: item for item in manifest["sources"]}
cases = manifest["history"]["cases"] + manifest["cases"]
assert [case["case_id"] for case in cases] == [
    *[f"H{n:03}" for n in range(1, 49)],
    *[f"S{n:03}" for n in range(1, 17)],
]
assert fixture["learning"] == [f"H{n:03}" for n in range(1, 37)]
assert fixture["exam"] == [f"H{n:03}" for n in range(37, 49)]
mistakes = {"H008", "H019", "H031", "H044"}
hidden = {"H006", "H018", "H030", "H042"}
assert set(read("eval/mistakes.json")) == mistakes
actual_hidden = set()
native_touch_events = []
service_counts = Counter()
for case in cases:
    identity = case["case_id"]
    number = int(identity[1:])
    historical = identity.startswith("H")
    local = (number - 1) % 12 + 1
    if historical:
        month = (number - 1) // 4
        opened = date(2025 + (month + 9) // 12, (month + 9) % 12 + 1, (1, 8, 15, 22)[(number - 1) % 4])
        multi = local <= 8
        both = local in (2, 4, 6, 8)
        days = 3 if local in (2, 6, 10) else 5 if local in (4, 8, 12) else 0
        payroll_single = local in (9, 11)
    else:
        opened = date(2027, 1, number)
        multi = identity not in {"S003", "S007", "S011", "S015"}
        both = identity in {"S002", "S006", "S010", "S014"}
        days = 3 if identity in {"S002", "S006", "S010", "S014"} else 5 if identity in {"S004", "S008", "S012", "S016"} else 0
        payroll_single = identity in {"S003", "S011"}
    expected_services = [("payroll", "benefits"), ("payroll",)] if both else [("payroll",), ("benefits",)] if multi else [("payroll",)] if payroll_single else [("benefits",)]
    assert case["opened_at"] == timestamp(opened, "08:00:00")
    client = table(f"exports/{identity}/client.csv")[0]
    site_rows = table(f"exports/{identity}/sites.csv")
    employee_rows = table(f"exports/{identity}/employees.csv")
    service_rows = table(f"exports/{identity}/services.csv")
    assert len(site_rows) == len(expected_services)
    assert len(employee_rows) == len(set(row["employee_id"] for row in employee_rows))
    assert client["case_id"] == identity and client["agreement_id"] == identity + "-agreement"
    expected_branches = []
    for index, selected in enumerate(expected_services, 1):
        site_id = identity + f"-site-{index}"
        assert site_rows[index - 1] == {"case_id": identity, "client_id": client["client_id"], "site_id": site_id}
        assert [row["service"] for row in service_rows if row["site_id"] == site_id] == list(selected)
        for row in employee_rows:
            assert row["case_id"] == identity and row["client_id"] == client["client_id"]
            assert row["site_id"] in {r["site_id"] for r in site_rows}
        for service in selected:
            source_rows = table(f"exports/{identity}/{service}.csv")
            fields = next(row for row in source_rows if row["site_id"] == site_id)
            if service == "benefits":
                assert not ({"pay_frequency", "payroll_cutover_date"} & fields.keys())
            affected = bool(days and ((identity in hidden and service == "payroll") or (identity not in hidden and index == 1 and service == ("payroll" if "payroll" in selected else "benefits"))))
            ready = opened + timedelta(days=days if affected else 0)
            expected_branches.append((site_id, service, timestamp(ready, "09:00:00")))
    answer = key[identity]
    assert [(b["site_id"], b["service"], b["ready_at"]) for b in answer["branches"]] == expected_branches
    assert all(b["checked_at"] == timestamp(opened, "09:00:00") for b in answer["branches"])
    observed_rows = [table(sources[o["source"]["source_id"]]["path"])[0] for o in case["observations"]]
    by_kind = {}
    for row in observed_rows:
        by_kind.setdefault(row["kind"], []).append(row)
    ready = opened + timedelta(days=days)
    completed = ready + timedelta(days=1)
    assert answer["summary"]["ready_at"] == timestamp(ready, "10:00:00")
    assert answer["completed_at"] == timestamp(completed, "12:00:00")
    assert (completed - opened).days <= 6
    assert len(answer["waits"]) == bool(days)
    if days:
        wait = answer["waits"][0]
        request = by_kind["client_request"][0]
        responses = by_kind["client_response"]
        assert request["request_id"] == wait["request_id"] == identity + "-client-request-v1"
        assert request["request_revision"] == "1" and wait["request_revision"] == 1
        assert request["occurred_at"] == wait["issued_at"] == timestamp(opened, "10:00:00")
        assert request["due_at"] == wait["due_at"] == timestamp(opened + timedelta(days=3), "23:59:59")
        assert wait["responded_at"] == timestamp(ready, "09:00:00")
        assert all(r["request_id"] == request["request_id"] and r["request_revision"] == "1" and r["client_id"] == client["client_id"] and r["actor"] == client["sponsor"] and r["occurred_at"] == wait["responded_at"] for r in responses)
        assert {r["response_id"] for r in responses} == {wait["response_id"]}
        assert [{k: r[k] for k in ("site_id", "field", "value")} for r in responses] == wait["changes"]
        assert json.loads(request["fields"]) == [{k: r[k] for k in ("site_id", "field")} for r in responses]
        assert len(responses) == (2 if identity in hidden else 1)
        assert wait["overdue_at"] == (timestamp(opened + timedelta(days=4), "00:00:00") if days == 5 else None)
    assert len(by_kind.get("overdue_notification", [])) == (days == 5)
    payload = answer["effects"][0]["payload"]
    digest = sha256((json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()).hexdigest()
    owner, authority, effect = answer["business_decision"], answer["engine_authority"], answer["effects"][0]
    assert owner["decided_at"] == timestamp(completed, "10:00:00")
    assert authority["approved_at"] == timestamp(completed, "11:00:00")
    assert owner["never_automate"] and owner["requires_existing_request"]
    assert owner["summary_sha256"] == authority["payload_sha256"] == effect["payload_sha256"] == digest
    assert effect["business_decision_id"] == authority["business_decision_id"] == owner["decision_id"]
    assert effect["authority_id"] == authority["approval_id"] and effect["effect_id"] == authority["effect_id"]
    assert by_kind["business_decision"][0]["summary_sha256"] == by_kind["exact_change_approval"][0]["payload_sha256"] == digest
    assert json.loads(by_kind["owner_request"][0]["configuration"]) == payload
    assert by_kind["activation"][0]["occurred_at"] == timestamp(ready if identity in mistakes else completed, "12:00:00")
    if historical:
        service_counts.update({"multi": multi, "both": both, "wait": bool(days), "wait3": days == 3, "wait5": days == 5})
        assert sheet[identity]["payload"] == payload
        if identity in hidden:
            original_dates = [r["payroll_cutover_date"] for r in table(f"exports/{identity}/payroll.csv")]
            assert len(set(original_dates)) == 2
            assert {s["payroll_cutover_date"] for s in payload["sites"]} == {str(opened + timedelta(days=14))}
            actual_hidden.add(identity)
    else:
        native_touch_events.extend(r for r in observed_rows if r["kind"] in {"business_decision", "exact_change_approval", "client_response"})
assert actual_hidden == hidden
assert service_counts == {"multi": 32, "both": 16, "wait": 24, "wait3": 12, "wait5": 12}
assert len(native_touch_events) == 40
assert sum(r["occurred_at"] < "2027-01-11" for r in native_touch_events) == 19
weeks = Counter()
for row in native_touch_events:
    day = date.fromisoformat(row["occurred_at"][:10])
    weeks[str(day - timedelta(days=day.weekday()))] += 1
assert weeks == {"2026-12-28": 2, "2027-01-04": 17, "2027-01-11": 14, "2027-01-18": 7}
assert [n for n in key if n.startswith("S") and key[n]["completed_at"] < "2027-01-11"] == ["S001", "S002", "S003", "S004", "S005", "S006", "S007", "S009"]
print(json.dumps({"result": "PASS", "native_cases": len(cases), "history_cohorts": dict(service_counts), "hidden": sorted(actual_hidden), "native_stream_touches": len(native_touch_events), "weeks": dict(weeks)}, sort_keys=True))

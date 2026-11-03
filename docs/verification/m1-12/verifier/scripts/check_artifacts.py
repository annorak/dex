"""Independent native-byte and specification readback. No dex imports."""
import argparse
from collections import Counter
from copy import deepcopy
import csv
from datetime import date, datetime, time, timedelta
from hashlib import sha256
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

parser = argparse.ArgumentParser()
parser.add_argument("world", type=Path)
parser.add_argument("--packets", type=Path, required=True)
parser.add_argument("--out", type=Path, required=True)
parser.add_argument("--controls", action="store_true")
args = parser.parse_args()
zone = ZoneInfo("America/New_York")

def read(path):
    return json.loads(path.read_bytes())

def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()

def moment(day, hour, minute=0, second=0):
    return datetime.combine(day, time(hour, minute, second), zone).isoformat()

def equal(actual, expected, label):
    assert actual == expected, (label, actual, expected)

def rows(path):
    with path.open(newline="") as source:
        return list(csv.DictReader(source))

def times(value):
    if isinstance(value, dict):
        for item in value.values():
            times(item)
    elif isinstance(value, list):
        for item in value:
            times(item)
    elif isinstance(value, str) and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d", value):
        parsed = datetime.fromisoformat(value)
        equal(parsed.utcoffset(), parsed.astimezone(zone).utcoffset(), "timezone")

if args.controls:
    for actual, expected, label in (({"x": "a"}, {"x": "b"}, "changed byte"),
                                    ({"a": 1}, {"b": 1}, "changed path"),
                                    (["H001", "H003"], ["H001", "H002"], "swapped membership")):
        try:
            equal(actual, expected, label)
        except AssertionError as error:
            assert error.args[0][0] == label
        else:
            raise AssertionError("comparison control did not fail")
    try:
        rows(args.world / "required-missing-control.csv")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("missing input was accepted")

bundle = args.world / "world-2/veldren"
public = read(bundle / "bundle.json")
fixture = read(bundle / "eval/fixture.json")
key = read(bundle / "eval/answer-key.json")
observed = read(bundle / "eval/answer-sheet.json")
scripts = read(bundle / "eval/response-scripts.json")
schedule = read(bundle / "eval/operation-schedule.json")
manifest = read(bundle / "eval/manifest.json")
history = [f"H{number:03d}" for number in range(1, 49)]
stream = [f"S{number:03d}" for number in range(1, 17)]
equal(fixture["learning"], history[:36], "learning")
equal(fixture["exam"], history[36:], "exam")
equal(fixture["stream"], stream, "stream")
equal(set(key), set(history + stream), "all keys")
equal(set(observed), set(history), "observations")
equal(manifest["key_frozen_before_reference_execution"], True, "frozen key")
equal(manifest["reference_programs"], [], "reference execution absent")
for name, digest in manifest["artifacts"].items():
    equal(sha256((bundle / "eval" / name).read_bytes()).hexdigest(), digest, "eval bytes " + name)
for source in public["sources"]:
    original = (bundle / source["path"]).read_bytes()
    equal(sha256(original).hexdigest(), source["sha256"], "source bytes " + source["source_id"])
    extraction = bundle / source["extraction"]["path"]
    equal(sha256(extraction.read_bytes()).hexdigest(), source["extraction"]["sha256"], "extraction bytes")
    assert not any(word in original.lower() for word in
                   (b"social security", b"ssn", b"bank_account", b"medical", b"routing_number"))
for name, issued in (("handbook.md", "2025-09-01"), ("service-owner-email.md", "2025-09-22")):
    original = (args.packets / "veldren" / name).read_bytes()
    equal((bundle / "sources" / name).read_bytes(), original, "exact packet")
    equal(fixture["source_hashes"][name], sha256(original).hexdigest(), "packet pin")
    descriptor = next(source for source in public["sources"] if source["path"] == "sources/" + name)
    equal(descriptor["occurred_at"][:10], issued, "packet issuance")
    assert not any(word in original.lower() for word in (b"shared", b"same cutover", b"client-confirmed", b"onb-", b"dex"))

cases = {case["case_id"]: case for case in fixture["cases"]}
equal(set(cases), set(history + stream), "case identities")
members = {"multi": [], "both": [], "three": [], "five": []}
mistakes = {"H008", "H019", "H031", "H044"}
for identity in history + stream:
    case, answer = cases[identity], key[identity]
    number = int(identity[1:])
    historical = identity.startswith("H")
    local = (number - 1) % 12 + 1
    if historical:
        month = (number - 1) // 4 + 9
        opened = date(2025 + month // 12, month % 12 + 1, (1, 8, 15, 22)[(number - 1) % 4])
        multi = local <= 8
        both = local in (2, 4, 6, 8)
        wait = 3 if local in (2, 6, 10) else 5 if local in (4, 8, 12) else 0
    else:
        opened = date(2027, 1, number)
        multi = number not in (3, 7, 11, 15)
        both = number in (2, 6, 10, 14)
        wait = 3 if number in (2, 6, 10, 14) else 5 if number in (4, 8, 12, 16) else 0
    ready, finish = opened + timedelta(days=wait), opened + timedelta(days=wait + 1)
    equal(case["opened_at"], moment(opened, 8), identity + " opening")
    equal(len(case["sites"]), 2 if multi else 1, identity + " site count")
    if historical:
        for name, applies in (("multi", multi), ("both", both), ("three", wait == 3), ("five", wait == 5)):
            if applies:
                members[name].append(identity)
    expected_services = [["payroll", "benefits"], ["payroll"]] if both else (
        [["payroll"], ["benefits"]] if multi else [["payroll"]] if number % 4 in (1, 3) and historical or not historical and number in (3, 11) else [["benefits"]])
    equal([site["services"] for site in case["sites"]], expected_services, identity + " services")
    client = rows(bundle / "exports" / identity / "client.csv")
    equal(client, [{"case_id": identity, "client_id": case["client_id"], "name": case["client_name"],
                    "sponsor": case["sponsor"], "agreement_id": identity + "-agreement"}], identity + " native client")
    employees = rows(bundle / "exports" / identity / "employees.csv")
    expected_employees = []
    for site in case["sites"]:
        assert len(site["employees"]) == 2
        for employee in site["employees"]:
            expected_employees.append({"case_id": identity, "client_id": case["client_id"],
                                       "site_id": site["site_id"], **employee})
        if "payroll" not in site["services"]:
            assert "payroll_cutover_date" not in site and "pay_frequency" not in site
    equal(employees, expected_employees, identity + " native employees")
    payload = {"client_id": case["client_id"], "sites": deepcopy(case["sites"])}
    shared = historical and local == 6
    changes = []
    for index, site in enumerate(payload["sites"]):
        if shared:
            field, value = "payroll_cutover_date", (opened + timedelta(days=14)).isoformat()
        elif wait and index == 0:
            field = "pay_frequency" if "payroll" in site["services"] else "site_contact"
            value = "biweekly" if field == "pay_frequency" else site["site_id"] + "-contact"
        else:
            continue
        site[field] = value
        changes.append({"site_id": site["site_id"], "field": field, "value": value})
    digest = sha256(canonical(payload)).hexdigest()
    equal(answer["summary"]["configuration"], payload, identity + " configuration")
    equal(answer["summary"]["ready_at"], moment(ready, 10), identity + " summary time")
    equal(answer["summary"]["sha256"], digest, identity + " summary hash")
    owner, authority = answer["business_decision"], answer["engine_authority"]
    equal(owner["decided_at"], moment(finish, 10), identity + " owner")
    equal(owner["requested_at"], moment(ready, 10), identity + " owner request")
    assert owner["never_automate"] and owner["requires_existing_request"]
    equal(owner["summary_sha256"], digest, identity + " exact decision")
    equal(authority["approved_at"], moment(finish, 11), identity + " authority")
    equal(authority["payload_sha256"], digest, identity + " exact authority")
    equal(authority["business_decision_id"], owner["decision_id"], identity + " decision identity")
    equal(answer["effects"][0]["payload"], payload, identity + " effect payload")
    equal(answer["effects"][0]["payload_sha256"], digest, identity + " effect hash")
    equal(answer["effects"][0]["authority_id"], authority["approval_id"], identity + " authority identity")
    equal(answer["completed_at"], moment(finish, 12), identity + " activation")
    equal(answer["effects"][0]["applied_at"], moment(finish, 12), identity + " applied")
    equal(len(answer["waits"]), 1 if wait else 0, identity + " wait count")
    if wait:
        request = answer["waits"][0]
        equal(request["request_id"], identity + "-client-request-v1", identity + " request")
        equal(request["request_revision"], 1, identity + " revision")
        equal(request["issued_at"], moment(opened, 10), identity + " issued")
        equal(request["due_at"], moment(opened + timedelta(days=3), 23, 59, 59), identity + " due")
        equal(request["overdue_at"], moment(opened + timedelta(days=4), 0) if wait == 5 else None, identity + " overdue")
        equal(request["responded_at"], moment(ready, 9), identity + " responded")
        equal(request["available_at"], moment(ready, 9), identity + " available")
        equal(request["changes"], changes, identity + " response values")
        assert request["requires_existing_request"]
        equal(next(item for item in scripts["client_responses"] if item["case_id"] == identity), request, identity + " scripted request")
    expected_branches = [(site["site_id"], service) for site in case["sites"] for service in site["services"]]
    equal([(item["site_id"], item["service"]) for item in answer["branches"]], expected_branches, identity + " branches")
    for branch in answer["branches"]:
        equal(branch["checked_at"], moment(opened, 9), identity + " checked")
        if not wait:
            equal(branch["ready_at"], moment(opened, 9), identity + " independent readiness")
    if not historical and wait:
        assert any(branch["ready_at"] == moment(opened, 9) for branch in answer["branches"])
    if historical:
        equal(observed[identity]["activated_at"], moment(ready if identity in mistakes else finish, 12), identity + " observed activation")
        assert (finish - opened).days <= 6
    equal(answer["runtime_model_calls"], 0, identity + " runtime calls")
equal([len(members[name]) for name in ("multi", "both", "three", "five")], [32, 16, 12, 12], "cohort counts")
equal(set(read(bundle / "eval/mistakes.json")), mistakes, "mistake identities")
equal(fixture["hidden_rule_evidence"], {"learning": ["H006", "H018", "H030"], "exam": ["H042"]}, "hidden evidence")
equal(schedule["status"], "fixture_requirements", "fixture only")
weekly = Counter()
for event in schedule["events"]:
    when = datetime.fromisoformat(event["at"])
    monday = when.date() - timedelta(days=when.weekday())
    weekly[monday.isoformat()] += event["touches"]
equal(dict(weekly), {"2026-12-28": 2, "2027-01-04": 17, "2027-01-11": 14, "2027-01-18": 7}, "weekly touches")
equal(sum(event["touches"] for event in schedule["events"]), 40, "all touches")
equal(sum(event["touches"] for event in schedule["events"] if event["at"] < "2027-01-11"), 19, "cutoff touches")
for document in (public, fixture, key, scripts, schedule):
    times(document)
summary = {"history": history, "learning": history[:36], "exam": history[36:], "stream": stream,
           "memberships": members, "mistakes": sorted(mistakes), "key_count": len(key),
           "native_sources": len(public["sources"]), "weekly_touches": dict(weekly),
           "runtime_calls": 0, "execution_claimed": False, "controls": args.controls}
assert not args.out.exists(), args.out
args.out.write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary))

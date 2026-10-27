import argparse
import calendar
import csv
from datetime import date, datetime, timedelta
from hashlib import sha256
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument("world", type=Path)
parser.add_argument("--packets", type=Path, required=True)
parser.add_argument("--repeat", type=Path)
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()
summary = {}
zone = ZoneInfo("America/New_York")

def read(path):
    return json.loads(path.read_bytes())

def manifest(root):
    return {str(path.relative_to(root)): sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*")) if path.is_file()}

def timestamp(value):
    parsed = datetime.fromisoformat(value)
    assert parsed.utcoffset() == parsed.astimezone(zone).utcoffset(), value
    return parsed

def check_times(value):
    if isinstance(value, dict):
        for child in value.values():
            check_times(child)
    elif isinstance(value, list):
        for child in value:
            check_times(child)
    elif isinstance(value, str) and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?[+-]\d\d:\d\d", value):
        timestamp(value)

collection = read(args.world / "collection.json")
assert [(entry["company_id"], entry["path"]) for entry in collection["bundles"]] == [
    ("C1", "world-1/bramblewick"), ("C2", "world-1/fennor")]
packets = {
    "bramblewick": ["procedure.md", "controller-email.md", "board-limit-notice.md", "service-confirmation.md"],
    "fennor": ["ap-checklist.md", "payables-wiki.md", "controller-email.md"],
}
snow = {"C1": {142: 10, 1918: 4, 2230: 5, 2566: 6, 2638: 6, 2758: 7, 2938: 7, 3118: 8, 3478: 9},
        "C2": {2760: 7, 2940: 7, 3120: 8, 3480: 9}}
duplicates = {"C1": {313, 628, 1558, 2248, 2713, 3328}, "C2": {391, 897, 2247, 2997}}
voids = {"C1": {898, 3013}, "C2": {500}}
for company, slug in (("C1", "bramblewick"), ("C2", "fennor")):
    root = args.world / "world-1" / slug
    public = read(root / "bundle.json")
    fixture = read(root / "eval/fixture.json")
    key = read(root / "eval/answer-key.json")
    observed = read(root / "eval/answer-sheet.json")
    scripts = read(root / "eval/response-scripts.json")
    cases = {item["case_id"]: item for item in fixture["cases"]}
    assert len(cases) == len(key) == 5410
    assert fixture["learning"] == [f"{company}-H{n:04d}" for n in range(1, 2701)]
    assert fixture["exam"] == [f"{company}-H{n:04d}" for n in range(2701, 3601)]
    assert fixture["stream"] == [f"{company}-S{n:04d}" for n in range(1, 1801)]
    assert fixture["shadow"] == [f"{company}-SH{n:02d}" for n in range(1, 11)]
    assert len(public["history"]["cases"]) == 3600 and len(public["cases"]) == 1800
    assert fixture["timezone"] == "America/New_York" and fixture["week_start"] == "Monday"
    assert fixture["cutoff"] == "2027-03-31T23:59:59-04:00"
    for cohort, start, count in (("H", (2025, 10), 3600), ("S", (2026, 10), 1800)):
        last = None
        for n in range(1, count + 1):
            item = cases[f"{company}-{cohort}{n:04d}"]
            when = timestamp(item["received"])
            month_index, ordinal = divmod(n - 1, 300)
            year = start[0] + (start[1] - 1 + month_index) // 12
            month = (start[1] - 1 + month_index) % 12 + 1
            opening = 13 if company == "C1" else 6
            day = 1 + ordinal * calendar.monthrange(year, month)[1] // 300
            if cohort == "S" and month_index == 0:
                day = 2 if ordinal < opening else 3 + (ordinal - opening) * 29 // (300 - opening)
            assert when.date() == date(year, month, day)
            minute = last.minute + 1 if last and last.date() == when.date() else 0
            assert (when.hour, when.minute, when.second) == (9, minute, 0)
            last = when
    mistake_ids = {f"{company}-H{300*m+ordinal:04d}" for m in range(12)
                   for ordinal in ([21, 22] if company == "C1" else [23] + ([24] if m in (0, 1, 2, 4, 6, 8, 10, 11) else []))}
    assert set(read(root / "eval/mistakes.json")) == mistake_ids
    assert {identity for identity in observed if observed[identity]["decision"] != key[identity]["decision"]} == mistake_ids
    for identity in mistake_ids:
        assert key[identity]["decision"] == "manager" and observed[identity]["decision"] == "board"
        assert key[identity]["approvals"] == ["manager"] and key[identity]["insurance_at_receipt"] == "valid"
    historical = {identity: answer for identity, answer in key.items() if identity.startswith(company + "-H")}
    assert {identity for identity, answer in historical.items() if answer.get("snow_review")} == {f"{company}-H{n:04d}" for n in snow[company]}
    for n, month in snow[company].items():
        assert date.fromisoformat(cases[f"{company}-H{n:04d}"]["invoice_date"]).month == month
    assert {identity for identity, answer in historical.items() if answer["decision"] == "duplicate"} == {f"{company}-H{n:04d}" for n in duplicates[company]}
    cancelled = {"C1-H2128", "C1-H3208"} if company == "C1" else set()
    assert {identity for identity, answer in historical.items() if answer["decision"] == "cancellation"} == cancelled
    for identity in cancelled | {f"{company}-H{n:04d}" for n in duplicates[company]}:
        assert key[identity]["effects"] == [] and key[identity]["waits"] == []
    for n in voids[company]:
        assert key[f"{company}-H{n:04d}"]["state"] == "scheduled"
    for name in packets[slug]:
        original = (args.packets / slug / name).read_bytes()
        assert (root / "sources" / name).read_bytes() == original
        descriptor = next(source for source in public["sources"] if source["path"] == "sources/" + name)
        assert descriptor["sha256"] == sha256(original).hexdigest()
        if name in ("board-limit-notice.md", "service-confirmation.md"):
            assert descriptor["available_at"] == {
                "board-limit-notice.md": "2026-12-15T08:00:00-05:00",
                "service-confirmation.md": "2027-01-15T08:00:00-05:00",
            }[name]
    for source in public["sources"]:
        assert not source["path"].startswith("eval/")
        assert sha256((root / source["path"]).read_bytes()).hexdigest() == source["sha256"]
    for path in root.rglob("*.xlsx"):
        with zipfile.ZipFile(path) as archive:
            assert archive.namelist() == sorted(archive.namelist())
            assert not archive.comment
            for entry in archive.infolist():
                assert entry.date_time == (1980, 1, 1, 0, 0, 0)
                assert entry.external_attr == 0o100644 << 16 and entry.create_system == 3
                assert not entry.extra and not entry.comment
    frozen = read(root / "eval/manifest.json")
    assert frozen["reference_programs"] == [] and frozen["key_frozen_before_reference_execution"] is True
    for name, digest in frozen["artifacts"].items():
        assert sha256((root / "eval" / name).read_bytes()).hexdigest() == digest
    check_times(fixture)
    check_times(key)
    check_times(scripts)
    operations = read(root / "eval/operation-schedule.json")
    check_times(operations)
    assert operations["events"] == sorted(
        operations["events"], key=lambda event: (timestamp(event["at"]), event["id"]))
    events = fixture["events"]
    assert events == sorted(events, key=lambda event: (timestamp(event["at"]), event["id"]))
    assert {identity for identity in fixture["stream"] if key[identity]["state"] == "pending"} == ({"C1-S0013"} if company == "C1" else set())
    register_paths = sorted((root / "exports/register").glob("*/ap-invoice-register.csv"))
    assert len(register_paths) == 182
    for path in register_paths:
        at = datetime.combine(date.fromisoformat(path.parent.name), datetime.min.time(), zone) + timedelta(hours=8)
        rows = list(csv.DictReader(path.read_text().splitlines()))
        for row in rows:
            assert timestamp(row["posted_at"]) < at
            assert row["community"].startswith(company) and row["vendor"].startswith(company)
    if company == "C1":
        answer = key["C1-S0001"]
        assert (answer["decision"], answer["posting_month"], answer["due_date"]) == ("board", "2026-09", "2026-10-29")
        assert [effect["operation"] for effect in answer["effects"]] == ["record_invoice", "request_approval", "schedule_payment"]
        assert answer["effects"][-1]["payload"]["date"] == "2026-10-29"
        assert key["C1-S0002"]["state"] == "scheduled" and key["C1-S0002"]["decision"] == "manager"
        assert key["C1-S0003"]["decision"] == "duplicate" and key["C1-S0004"]["state"] == "scheduled"
        assert key["C1-S0008"]["insurance_at_receipt"] == "expired" and key["C1-S0009"]["insurance_at_receipt"] == "missing"
        assert key["C1-S0010"]["snow_review"] and key["C1-S0011"]["decision"] == "cancellation"
        assert key["C1-S0012"]["state"] == "rejected" and len(key["C1-S0012"]["effects"]) == 2
        assert [item["case_id"] for item in read(root / "eval/ai-extractions.json")] == ["C1-S0601", "C1-S0602", "C1-S0603"]
    else:
        assert key["C2-S0001"]["decision"] == "manager" and key["C2-S0002"]["decision"] == "board"
        assert key["C2-S0003"]["approvals"] == ["board", "finance_signer"]
        assert key["C2-S0003"]["waits"][0]["actor"] != key["C2-S0003"]["waits"][1]["actor"]
        assert key["C2-S0004"]["decision"] == "duplicate" and key["C2-S0005"]["state"] == "scheduled"
        assert key["C2-S0006"]["insurance_at_receipt"] == "expired"
        assert read(root / "eval/ai-extractions.json") == []
    summary[company] = {"history": 3600, "learning": 2700, "exam": 900, "stream": 1800, "shadow": 10, "registers": 182, "sources": len(public["sources"])}
files = manifest(args.world)
if args.repeat:
    assert files == manifest(args.repeat), "complete path/byte manifests differ"
summary["files"] = len(files)
summary["bytes"] = sum(path.stat().st_size for path in args.world.rglob("*") if path.is_file())
summary["repeat_identical"] = bool(args.repeat)
args.out.write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, sort_keys=True))

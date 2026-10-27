import argparse
import csv
from datetime import datetime, timedelta
from hashlib import sha256
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--evidence", type=Path, required=True)
args = parser.parse_args()
evidence = args.evidence
live = evidence / "live"

def read(path):
    return json.loads(path.read_bytes())

def manifest(root):
    return {str(path.relative_to(root)): sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*")) if path.is_file()}

reference = {7: manifest(live / "seed7-a"), 11: manifest(live / "seed11-a")}
assert reference[7].keys() == reference[11].keys()
assert reference[7] != reference[11]
outcomes = {}
for lane in ("packets", "membership", "mistakes", "paths", "stream", "key", "seed-variation"):
    actual = read(live / lane / "actual.json")
    expected = read(live / lane / "expected.json")
    assert all(expected["matches"].values()) and expected["matches"]
    assert actual["observed"] == expected["expected"]
    assert manifest(live / lane / "world") == reference[7], lane
    if lane == "seed-variation":
        assert manifest(live / lane / "seed11") == reference[11]
    outcomes[lane] = {"exact_expected": True, "complete_world_identical": True}

postings = {}
for company, slug in (("C1", "bramblewick"), ("C2", "fennor")):
    root = live / "seed7-a/world-1" / slug
    bundle = read(root / "bundle.json")
    final = next(source for source in bundle["sources"] if source["source_id"] == company + "-final-postings")
    assert final["path"] == "exports/final-postings.csv"
    assert all(final[field] == "2027-03-31T23:59:59-04:00"
               for field in ("available_at", "occurred_at", "observed_at"))
    register_sources = [source for source in bundle["sources"] if source["path"].startswith("exports/register/")]
    assert len(register_sources) == 182
    posted = {}
    for source in [*register_sources, final]:
        delivered = datetime.fromisoformat(source["available_at"])
        rows = list(csv.DictReader((root / source["path"]).read_text().splitlines()))
        for row in rows:
            if not row["invoice_id"].startswith(company + "-S"):
                continue
            when = datetime.fromisoformat(row["posted_at"])
            assert when <= delivered
            expected_day = delivered.date() if source == final else delivered.date() - timedelta(days=1)
            assert when.date() == expected_day
            assert row["invoice_id"] not in posted, row["invoice_id"]
            posted[row["invoice_id"]] = row
    excluded = {3, 11} if company == "C1" else {4}
    assert set(posted) == {f"{company}-S{index:04d}" for index in range(1, 1801) if index not in excluded}
    assert company + "-S1800" in posted
    postings[company] = {"retained_daily_exports": 182, "stream_postings": len(posted),
                        "final_day_persisted": True, "receipt_times_exact": True}

controls = {"evaluator": "evaluator", "original-root": "original_root", "network": "network"}
for name, kind in controls.items():
    audit = read(evidence / f"control-{name}-audit.json")
    assert audit["hook_loaded"] and len(audit["attempts"]) == 1
    assert audit["attempts"][0]["kind"] == kind
    receipt = (evidence / f"control-{name}.txt").read_text()
    assert '"exit_status": 1' in receipt
for path in evidence.glob("*-audit.json"):
    if path.name.startswith(("control-", "refusal-")):
        continue
    audit = read(path)
    assert audit["hook_loaded"] and audit["attempts"] == [], path.name
summary = {"scenarios": outcomes, "postings": postings,
           "audit_controls_pass": True, "seed_variation_changes_bytes": True,
           "baseline_files": len(reference[7])}
(evidence / "untimed-readback.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, sort_keys=True))

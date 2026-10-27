"""Freeze and summarize the affected final-fix workload; never remeasure carried work."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument("action", choices=("freeze", "summarize"))
parser.add_argument("--evidence", type=Path, required=True)
parser.add_argument("--previous", type=Path, required=True)
parser.add_argument("--checkouts", type=Path, required=True)
args = parser.parse_args()
root = args.evidence / "performance"
prior_root = args.previous / "performance"

def read(path):
    return json.loads(path.read_bytes())

def digest(path):
    return sha256(path.read_bytes()).hexdigest()

def git(checkout, *command):
    return subprocess.check_output(["git", "-C", str(checkout), *command], text=True).strip()

prior = read(prior_root / "freeze.json")
if args.action == "freeze":
    root.mkdir()
    (root / "outputs").mkdir()
    (root / "transcripts").mkdir()
    tasks = []
    for original in prior["tasks"]:
        if original["workload"] not in ("validation", "absolute-build", "absolute-validation"):
            continue
        task = dict(original)
        if task["workload"] != "validation":
            task["command"] = [part.replace(str(args.previous), str(args.evidence)) for part in task["command"]]
            if "output" in task:
                task["output"] = task["output"].replace(str(args.previous), str(args.evidence))
        tasks.append(task)
    assert len(tasks) == 60
    input_root = prior_root / "inputs"
    actual_inputs = {str(path.relative_to(input_root)): digest(path)
                     for path in sorted(input_root.rglob("*")) if path.is_file()}
    assert actual_inputs == prior["input_bytes"], "Frozen regression input bytes changed."
    head = args.checkouts / "head"
    revisions = {role: git(args.checkouts / role, "rev-parse", "HEAD") for role in prior["revisions"]}
    assert revisions["trunk"] == revisions["parent"] == prior["revisions"]["parent"]
    assert not git(head, "status", "--porcelain")
    tracked = git(head, "ls-files").splitlines()
    tools = dict(prior["tools"])
    tools[str(Path(__file__))] = digest(Path(__file__))
    tools[str(args.evidence / "scripts/check_performance_artifacts.py")] = digest(args.evidence / "scripts/check_performance_artifacts.py")
    freeze = {"revisions": revisions, "tools": tools,
              "head_tracked_bytes": {name: digest(head / name) for name in tracked if (head / name).is_file()},
              "input_root": str(prior_root / "inputs"), "input_bytes": prior["input_bytes"],
              "method": prior["method"], "tasks": tasks,
              "environment": {"utc": datetime.now(timezone.utc).isoformat(), "load_average": os.getloadavg(),
                              "cpu_count": os.cpu_count(), "platform": platform.platform(), "python": sys.version},
              "carried": {"prior_freeze": str(prior_root / "freeze.json"), "prior_summary": str(prior_root / "performance-summary.json"),
                          "proof": str(args.evidence / "carry-forward.json"),
                          "startup": "Exact startup source and dependency bytes unchanged; CLI exits before bundle imports.",
                          "unsupported": "Same exact trunk and dependency commits; original actual refusals retained.",
                          "prior_failure": "Sample 4 build plus validation 45.042089291 seconds exceeded 45; preserved."}}
    (root / "freeze.json").write_text(json.dumps(freeze, indent=2) + "\n")
    (root / "samples.json").write_text("[]\n")
    print(json.dumps({"tasks": len(tasks), "revisions": revisions,
                      "freeze_sha256": digest(root / "freeze.json"), "input_root": freeze["input_root"]}, sort_keys=True))
    sys.exit(0)

freeze = read(root / "freeze.json")
results = read(root / "samples.json")
assert len(results) == len(freeze["tasks"]) == 60
failures = []
for result in results:
    measure = result["measurement"]
    if measure is None or not measure["clock_valid"] or measure["exit_status"] != 0 or result["recorder_exit"] != 0:
        failures.append({"task": result["task"]["id"], "failure": "invalid or failed measurement"})
comparisons = []
for baseline in ("trunk", "parent"):
    grouped = {}
    for role in (baseline, "head"):
        pairs = []
        for pair in range(1, 6):
            selected = [item["measurement"] for item in results
                        if item["task"].get("workload") == "validation" and item["task"].get("baseline") == baseline
                        and item["task"].get("pair") == pair and item["task"]["role"] == role]
            assert len(selected) == 2 and all(selected)
            pairs.append({"wall": sum(item["wall_seconds"] for item in selected),
                          "rss": max(item["max_rss_bytes"] for item in selected)})
        grouped[role] = pairs
    for metric in ("wall", "rss"):
        base_median = statistics.median(item[metric] for item in grouped[baseline])
        head_median = statistics.median(item[metric] for item in grouped["head"])
        entry = {"workload": "validation", "baseline": baseline, "metric": metric,
                 "baseline_median": base_median, "head_median": head_median,
                 "ratio": head_median / base_median, "passed": head_median / base_median <= 1.20,
                 "samples": grouped}
        comparisons.append(entry)
        if not entry["passed"]:
            failures.append(entry)
absolute = []
for sample in range(1, 6):
    selected = [item for item in results if item["task"].get("sample") == sample]
    builds = [item["measurement"] for item in selected if item["task"]["workload"] == "absolute-build"]
    checks = [item["measurement"] for item in selected if item["task"]["workload"] == "absolute-validation"]
    assert len(builds) == len(checks) == 2
    entry = {"sample": sample, "build_seconds": [item["wall_seconds"] for item in builds],
             "build_validation_seconds": builds[0]["wall_seconds"] + sum(item["wall_seconds"] for item in checks),
             "max_rss_bytes": max(item["max_rss_bytes"] for item in builds + checks)}
    entry["passed"] = max(entry["build_seconds"]) <= 30 and entry["build_validation_seconds"] <= 45 and entry["max_rss_bytes"] <= 1073741824
    absolute.append(entry)
    if not entry["passed"]:
        failures.append(entry)
input_root = Path(freeze["input_root"])
assert {str(path.relative_to(input_root)): digest(path) for path in sorted(input_root.rglob("*")) if path.is_file()} == freeze["input_bytes"]
carried_startup = [item for item in read(prior_root / "performance-summary.json")["comparisons"] if item["workload"] == "startup"]
assert len(carried_startup) == 4 and all(item["passed"] for item in carried_startup)
summary = {"passed": not failures, "failures": failures, "comparisons": comparisons,
           "carried_startup_comparisons": carried_startup, "absolute": absolute, "measurements": 60,
           "freeze_sha256": digest(root / "freeze.json"), "carry_forward": freeze["carried"],
           "prior_failure_preserved": True, "post_measurement_artifact_readback_required": True}
(root / "performance-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, sort_keys=True))
sys.exit(0 if not failures else 1)

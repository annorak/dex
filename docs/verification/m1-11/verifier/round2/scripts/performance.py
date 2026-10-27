"""Frozen serial M1-11 measurements using the preserved recorder and Timer V2."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument("action", choices=("freeze", "run", "summarize"))
parser.add_argument("--evidence", type=Path, required=True)
parser.add_argument("--checkouts", type=Path, required=True)
parser.add_argument("--recorder", type=Path, required=True)
parser.add_argument("--timer", type=Path, required=True)
parser.add_argument("--cache", type=Path, required=True)
parser.add_argument("--input", type=Path, required=True)
args = parser.parse_args()
root = args.evidence / "performance"
freeze_path = root / "freeze.json"
results_path = root / "samples.json"

def read(path):
    return json.loads(path.read_bytes())

def digest(path):
    return sha256(path.read_bytes()).hexdigest()

def manifest(directory):
    return {str(path.relative_to(directory)): digest(path)
            for path in sorted(directory.rglob("*")) if path.is_file()}

def git(checkout, *arguments):
    return subprocess.check_output(["git", "-C", str(checkout), *arguments], text=True).strip()

def host():
    return {"utc": datetime.now(timezone.utc).isoformat(), "load_average": os.getloadavg(),
            "cpu_count": os.cpu_count(), "platform": platform.platform(),
            "python": sys.version,
            "processes": subprocess.run(["pgrep", "-fl", "pytest|dex|uv|bun|make|python"],
                                       capture_output=True, text=True).stdout}

if args.action == "freeze":
    root.mkdir()
    (root / "outputs").mkdir()
    (root / "transcripts").mkdir()
    inputs = root / "inputs"
    shutil.copytree(args.input, inputs / "world")
    frozen_scenarios = inputs / "scenarios"
    frozen_scenarios.mkdir()
    head = args.checkouts / "head"
    for path in sorted((head / "tests/scenarios").glob("world1-*.json")):
        shutil.copyfile(path, frozen_scenarios / path.name)
    revisions = {role: git(args.checkouts / role, "rev-parse", "HEAD")
                 for role in ("trunk", "parent", "head")}
    assert revisions["trunk"] == revisions["parent"]
    assert all(not git(args.checkouts / role, "status", "--porcelain") for role in revisions)
    tasks = []

    def add(identity, role, command, **metadata):
        tasks.append({"id": identity, "role": role, "command": command, **metadata})

    add("cold-trunk-help", "trunk", ["uv", "run", "dex", "--help"], workload="cold-start")
    for baseline in ("trunk", "parent"):
        for pair in range(1, 6):
            order = (baseline, "head") if pair % 2 else ("head", baseline)
            for role in order:
                add(f"startup-{baseline}-{pair}-{role}", role, ["uv", "run", "dex", "--help"],
                    workload="startup", baseline=baseline, pair=pair)
    for role in ("trunk", "parent", "head"):
        destination = root / "outputs" / ("regression-" + role)
        add("01-world1-" + role, role,
            ["uv", "run", "dex", "demo", "build", "--world", "world-1", "--seed", "7", "--out", str(destination)],
            workload="regression-generation", output=str(destination), unsupported=role != "head")
    for baseline in ("trunk", "parent"):
        for pair in range(1, 6):
            order = (baseline, "head") if pair % 2 else ("head", baseline)
            for role in order:
                for company in ("bramblewick", "fennor"):
                    add(f"validation-{baseline}-{pair}-{role}-{company}", role,
                        ["uv", "run", "dex", "bundle", "check", str(inputs / "world/world-1" / company)],
                        workload="validation", baseline=baseline, pair=pair, company=company)
    for sample in range(1, 6):
        first = root / "outputs" / f"sample-{sample}-a"
        second = root / "outputs" / f"sample-{sample}-b"
        add(f"size-{sample}-build-a", "head",
            ["uv", "run", "dex", "demo", "build", "--world", "world-1", "--seed", "7", "--out", str(first)],
            workload="absolute-build", sample=sample, build="a", output=str(first))
        for company in ("bramblewick", "fennor"):
            add(f"size-{sample}-check-{company}", "head",
                ["uv", "run", "dex", "bundle", "check", str(first / "world-1" / company)],
                workload="absolute-validation", sample=sample, company=company)
        add(f"size-{sample}-build-b", "head",
            ["uv", "run", "dex", "demo", "build", "--world", "world-1", "--seed", "7", "--out", str(second)],
            workload="absolute-build", sample=sample, build="b", output=str(second))
    tracked = git(head, "ls-files").splitlines()
    freeze = {"revisions": revisions, "tools": {str(args.recorder): digest(args.recorder), str(args.timer): digest(args.timer),
                                              str(Path(__file__)): digest(Path(__file__))},
              "head_tracked_bytes": {path: digest(head / path) for path in tracked if (head / path).is_file()},
              "input_bytes": manifest(inputs), "environment": host(), "tasks": tasks,
              "method": {"timer": 2, "samples": 5, "alternating_order": True,
                         "generation_seconds": 30, "generation_validation_seconds": 45,
                         "max_rss_bytes": 1073741824, "supported_median_ratio": 1.20,
                         "validation_wall": "sum of both complete public check CLI intervals",
                         "combined_wall": "first complete build plus both public check CLI intervals",
                         "combined_rss": "maximum of the measured command peaks",
                         "manifests": "compared only outside all timed generation intervals",
                         "unsupported": "record actual refusal; exclude from speedup and supported ratios",
                         "sampling": "all frozen samples retained; no replacement measurements"}}
    freeze_path.write_text(json.dumps(freeze, indent=2) + "\n")
    results_path.write_text("[]\n")
    print(json.dumps({"tasks": len(tasks), "revisions": revisions, "input_files": len(freeze["input_bytes"]),
                      "freeze_sha256": digest(freeze_path)}, sort_keys=True))
    sys.exit(0)

freeze = read(freeze_path)
assert all(digest(Path(path)) == expected for path, expected in freeze["tools"].items())
assert all(git(args.checkouts / role, "rev-parse", "HEAD") == revision
           for role, revision in freeze["revisions"].items())
results = read(results_path)
if args.action == "run":
    for task in freeze["tasks"][len(results):]:
        assert len(results) == freeze["tasks"].index(task)
        role = task["role"]
        checkout = args.checkouts / role
        receipt = root / "transcripts" / (task["id"] + ".txt")
        assert not receipt.exists(), "Existing receipt requires explicit recovery; never remeasure."
        before = host()
        print("START " + task["id"], flush=True)
        command = [sys.executable, str(args.recorder), "--cwd", str(checkout), "--out", str(receipt), "--",
                   "env", "UV_CACHE_DIR=" + str(args.cache), "UV_OFFLINE=1",
                   str(checkout / ".venv/bin/python"), str(args.timer), "--", *task["command"]]
        completed = subprocess.run(command, capture_output=True, text=True)
        text = receipt.read_text()
        lines = [line for line in text.splitlines() if line.startswith("MEASUREMENT ")]
        measurement = json.loads(lines[-1].removeprefix("MEASUREMENT ")) if len(lines) == 1 else None
        results.append({"task": task, "measurement": measurement, "recorder_exit": completed.returncode,
                        "receipt": str(receipt), "environment_before": before, "environment_after": host()})
        results_path.write_text(json.dumps(results, indent=2) + "\n")
        print("DONE " + json.dumps({"task": task["id"], "measurement": measurement}, sort_keys=True), flush=True)
    sys.exit(0)

assert len(results) == len(freeze["tasks"]), "All frozen samples must complete."
failures = []
for result in results:
    measure = result["measurement"]
    if measure is None or not measure["clock_valid"]:
        failures.append({"task": result["task"]["id"], "failure": "invalid measurement"})
        continue
    task = result["task"]
    if task.get("unsupported"):
        receipt = Path(result["receipt"]).read_text()
        if measure["exit_status"] != 2 or "invalid choice: 'demo'" not in receipt or Path(task["output"]).exists():
            failures.append({"task": task["id"], "failure": "expected unsupported refusal absent"})
    elif measure["exit_status"] != 0:
        failures.append({"task": task["id"], "failure": "supported command failed"})

comparisons = []
for workload in ("startup", "validation"):
    for baseline in ("trunk", "parent"):
        grouped = {}
        for role in (baseline, "head"):
            values = []
            for pair in range(1, 6):
                selected = [result["measurement"] for result in results
                            if result["task"].get("workload") == workload
                            and result["task"].get("baseline") == baseline
                            and result["task"].get("pair") == pair and result["task"]["role"] == role]
                assert len(selected) == (2 if workload == "validation" else 1) and all(selected)
                values.append({"wall": sum(item["wall_seconds"] for item in selected),
                               "rss": max(item["max_rss_bytes"] for item in selected)})
            grouped[role] = values
        for metric in ("wall", "rss"):
            base_median = statistics.median(item[metric] for item in grouped[baseline])
            head_median = statistics.median(item[metric] for item in grouped["head"])
            ratio = head_median / base_median
            entry = {"workload": workload, "baseline": baseline, "metric": metric,
                     "baseline_median": base_median, "head_median": head_median,
                     "ratio": ratio, "passed": ratio <= 1.20, "samples": grouped}
            comparisons.append(entry)
            if not entry["passed"]:
                failures.append(entry)

absolute = []
for sample in range(1, 6):
    selected = [result for result in results if result["task"].get("sample") == sample]
    builds = [result["measurement"] for result in selected if result["task"]["workload"] == "absolute-build"]
    checks = [result["measurement"] for result in selected if result["task"]["workload"] == "absolute-validation"]
    assert len(builds) == len(checks) == 2
    entry = {"sample": sample, "build_seconds": [item["wall_seconds"] for item in builds],
             "build_validation_seconds": builds[0]["wall_seconds"] + sum(item["wall_seconds"] for item in checks),
             "max_rss_bytes": max(item["max_rss_bytes"] for item in builds + checks)}
    entry["passed"] = (max(entry["build_seconds"]) <= 30 and entry["build_validation_seconds"] <= 45
                       and entry["max_rss_bytes"] <= 1073741824)
    absolute.append(entry)
    if not entry["passed"]:
        failures.append(entry)
assert manifest(root / "inputs") == freeze["input_bytes"], "Frozen inputs changed."
summary = {"passed": not failures, "failures": failures, "comparisons": comparisons, "absolute": absolute,
           "measurements": len(results), "freeze_sha256": digest(freeze_path),
           "historical_m1_10_startup_regression": "FAILED: 21.67 percent against unchanged 20 percent limit",
           "post_measurement_artifact_readback_required": True}
(root / "performance-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, sort_keys=True))
sys.exit(0 if not failures else 1)

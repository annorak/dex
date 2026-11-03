"""Frozen M1-12 CLI measurements. The original recorder and Timer V2 stay unchanged."""
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
parser.add_argument("action", choices=("freeze", "run", "summarize"))
parser.add_argument("--evidence", type=Path, required=True)
parser.add_argument("--checkouts", type=Path, required=True)
parser.add_argument("--recorder", type=Path, required=True)
parser.add_argument("--timer", type=Path, required=True)
parser.add_argument("--cache", type=Path, required=True)
parser.add_argument("--hook", type=Path, required=True)
parser.add_argument("--input", type=Path, required=True)
parser.add_argument("--baseline-revision", required=True)
parser.add_argument("--cpu-idle-authorized", action="store_true")
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
    processes = subprocess.run(["ps", "-axo", "pid,etime,%cpu,command"],
                               capture_output=True, text=True)
    return {"utc": datetime.now(timezone.utc).isoformat(), "load_average": os.getloadavg(),
            "cpu_count": os.cpu_count(), "platform": platform.platform(), "python": sys.version,
            "process_status": processes.returncode, "processes": processes.stdout,
            "process_stderr": processes.stderr}

if args.action == "freeze":
    root.mkdir()
    (root / "outputs").mkdir()
    (root / "transcripts").mkdir()
    revisions = {role: git(args.checkouts / role, "rev-parse", "HEAD")
                 for role in ("trunk", "parent", "head")}
    assert revisions["trunk"] == revisions["parent"]
    assert revisions["parent"] == args.baseline_revision
    assert all(not git(args.checkouts / role, "status", "--porcelain") for role in revisions)
    tasks = []

    def add(identity, role, command, **metadata):
        tasks.append({"id": identity, "role": role, "command": command, **metadata})

    def build(identity, role, selector, output, **metadata):
        command = ["uv", "run", "dex", "demo", "build"]
        if selector is not None:
            command += ["--world", selector]
        add(identity, role, command + ["--seed", "7", "--out", str(output)],
            output=str(output), **metadata)

    add("cold-trunk-help", "trunk", ["uv", "run", "dex", "--help"], workload="cold-start")
    for baseline in ("trunk", "parent"):
        for pair in range(1, 6):
            order = (baseline, "head") if pair % 2 else ("head", baseline)
            for role in order:
                add(f"startup-{baseline}-{pair}-{role}", role, ["uv", "run", "dex", "--help"],
                    workload="startup", baseline=baseline, pair=pair)
    for role in ("trunk", "parent"):
        for selector in (None, "world-2"):
            name = "default" if selector is None else selector
            output = root / "outputs" / f"unsupported-{role}-{name}"
            build(f"unsupported-{role}-{name}", role, selector, output,
                  workload="unsupported", unsupported=True)
    for baseline in ("trunk", "parent"):
        for pair in range(1, 6):
            order = (baseline, "head") if pair % 2 else ("head", baseline)
            for role in order:
                output = root / "outputs" / f"world1-{baseline}-{pair}-{role}"
                common = {"workload": "world1-build-validation", "baseline": baseline, "pair": pair}
                build(f"world1-{baseline}-{pair}-{role}-build", role, "world-1", output,
                      phase="build", **common)
                for company in ("bramblewick", "fennor"):
                    add(f"world1-{baseline}-{pair}-{role}-check-{company}", role,
                        ["uv", "run", "dex", "bundle", "check", str(output / "world-1" / company)],
                        phase="check", company=company, **common)
    for sample in range(1, 6):
        output = root / "outputs" / f"collection-{sample}"
        build(f"collection-{sample}-build", "head", None, output,
              workload="absolute-collection", phase="build", sample=sample)
        for world, company in (("world-1", "bramblewick"), ("world-1", "fennor"), ("world-2", "veldren")):
            add(f"collection-{sample}-check-{company}", "head",
                ["uv", "run", "dex", "bundle", "check", str(output / world / company)],
                workload="absolute-collection", phase="check", sample=sample, company=company)
        output = root / "outputs" / f"world2-{sample}"
        build(f"world2-{sample}-build", "head", "world-2", output,
              workload="absolute-world2", phase="build", sample=sample)
    tools = [args.recorder, args.timer, args.hook / "sitecustomize.py", Path(__file__)]
    frozen = {"revisions": revisions, "tools": {str(path): digest(path) for path in tools},
              "source_bytes": {role: {name: digest(args.checkouts / role / name)
                                     for name in git(args.checkouts / role, "ls-files").splitlines()
                                     if (args.checkouts / role / name).is_file()}
                               for role in revisions},
              "input_path": str(args.input), "input_bytes": manifest(args.input),
              "environment": host(), "tasks": tasks,
              "method": {"timer": 2, "samples": 5, "alternating": True,
                         "collection_seconds": 60, "world2_seconds": 5,
                         "max_rss_bytes": 1073741824, "supported_median_ratio": 1.20,
                         "workload_wall": "sum of complete CLI intervals, including generation and all public checks",
                         "workload_rss": "maximum measured command peak",
                         "input": "seed 7, identical World 1 source packets and declared generator version",
                         "byte_readback": "outside timed intervals; every output fully read afterward",
                         "unsupported": "named refusal, never a speedup",
                         "sampling": "retain every frozen sample and contention record; never replace unchanged measurements"}}
    freeze_path.write_text(json.dumps(frozen, indent=2) + "\n")
    results_path.write_text("[]\n")
    print(json.dumps({"tasks": len(tasks), "revisions": revisions,
                      "input_files": len(frozen["input_bytes"]), "freeze_sha256": digest(freeze_path)}))
    sys.exit(0)

frozen = read(freeze_path)
assert all(digest(Path(path)) == value for path, value in frozen["tools"].items())
assert all(git(args.checkouts / role, "rev-parse", "HEAD") == revision
           for role, revision in frozen["revisions"].items())
assert manifest(args.input) == frozen["input_bytes"], "Frozen input changed."
results = read(results_path)
if args.action == "run":
    assert args.cpu_idle_authorized, "Root CPU-idle authorization is required."
    for task in frozen["tasks"][len(results):]:
        assert len(results) == frozen["tasks"].index(task)
        checkout = args.checkouts / task["role"]
        receipt = root / "transcripts" / (task["id"] + ".txt")
        assert not receipt.exists(), "A receipt already exists. Never silently remeasure."
        before = host()
        print("START " + task["id"], flush=True)
        command = [sys.executable, str(args.recorder), "--cwd", str(checkout), "--out", str(receipt),
                   "--", "env", "UV_CACHE_DIR=" + str(args.cache), "UV_OFFLINE=1",
                   "PYTHONPATH=" + str(args.hook),
                   str(checkout / ".venv/bin/python"), str(args.timer), "--", *task["command"]]
        completed = subprocess.run(command, capture_output=True, text=True)
        lines = [line for line in receipt.read_text().splitlines() if line.startswith("MEASUREMENT ")]
        measurement = json.loads(lines[0].removeprefix("MEASUREMENT ")) if len(lines) == 1 else None
        results.append({"task": task, "measurement": measurement, "recorder_exit": completed.returncode,
                        "receipt": str(receipt), "environment_before": before, "environment_after": host()})
        results_path.write_text(json.dumps(results, indent=2) + "\n")
        print("DONE " + json.dumps({"task": task["id"], "measurement": measurement}), flush=True)
    sys.exit(0)

assert len(results) == len(frozen["tasks"]), "All frozen tasks must finish."
failures = []
for result in results:
    task, measurement = result["task"], result["measurement"]
    if measurement is None or not measurement["clock_valid"]:
        failures.append({"task": task["id"], "failure": "invalid measurement"})
        continue
    if task.get("unsupported"):
        receipt = Path(result["receipt"]).read_text()
        if measurement["exit_status"] != 2 or '"code": "world_unavailable"' not in receipt or Path(task["output"]).exists():
            failures.append({"task": task["id"], "failure": "named unsupported refusal absent"})
    elif measurement["exit_status"] != 0:
        failures.append({"task": task["id"], "failure": "supported command failed"})
    if not task.get("unsupported") and measurement["max_rss_bytes"] > 1073741824:
        failures.append({"task": task["id"], "failure": "supported sample exceeds 1 GiB"})
comparisons = []
for workload, count, phase in (("startup", 1, None), ("world1-build-validation", 3, None),
                               ("world1-build-validation", 1, "build"), ("world1-build-validation", 2, "check")):
    for baseline in ("trunk", "parent"):
        grouped = {}
        for role in (baseline, "head"):
            values = []
            for pair in range(1, 6):
                selected = [r["measurement"] for r in results
                            if r["task"].get("workload") == workload
                            and r["task"].get("baseline") == baseline
                            and r["task"].get("pair") == pair and r["task"]["role"] == role
                            and (phase is None or r["task"].get("phase") == phase)]
                assert len(selected) == count and all(selected)
                values.append({"wall": sum(item["wall_seconds"] for item in selected),
                               "rss": max(item["max_rss_bytes"] for item in selected)})
            grouped[role] = values
        for metric in ("wall", "rss"):
            before = statistics.median(item[metric] for item in grouped[baseline])
            after = statistics.median(item[metric] for item in grouped["head"])
            entry = {"workload": workload, "phase": phase, "baseline": baseline, "metric": metric,
                     "baseline_median": before, "head_median": after,
                     "ratio": after / before, "passed": after / before <= 1.20, "samples": grouped}
            comparisons.append(entry)
            if not entry["passed"]:
                failures.append(entry)
absolute = []
for sample in range(1, 6):
    collection = [r["measurement"] for r in results
                  if r["task"].get("sample") == sample
                  and r["task"]["workload"] == "absolute-collection"]
    world2 = [r["measurement"] for r in results
              if r["task"].get("sample") == sample and r["task"]["workload"] == "absolute-world2"]
    assert len(collection) == 4 and len(world2) == 1 and all(collection + world2)
    entry = {"sample": sample, "collection_seconds": sum(m["wall_seconds"] for m in collection),
             "world2_seconds": world2[0]["wall_seconds"],
             "max_rss_bytes": max(m["max_rss_bytes"] for m in collection + world2)}
    entry["passed"] = (entry["collection_seconds"] <= 60 and entry["world2_seconds"] <= 5
                       and entry["max_rss_bytes"] <= 1073741824)
    absolute.append(entry)
    if not entry["passed"]:
        failures.append(entry)
summary = {"passed": not failures, "failures": failures, "comparisons": comparisons,
           "absolute": absolute, "measurements": len(results), "freeze_sha256": digest(freeze_path),
           "artifact_readback_required": True,
           "preserved_failures": ["M1-11: 45.042089291 seconds against 45",
                                  "M1-10: 21.67 percent against 20 percent"]}
(root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary))
sys.exit(0 if not failures else 1)

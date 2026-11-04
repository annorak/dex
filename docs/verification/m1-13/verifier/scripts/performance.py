"""M1-13 command measurements using the preserved recorder and Timer V2."""

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys


def read(path):
    return json.loads(path.read_bytes())


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def git(checkout, *arguments):
    return subprocess.check_output(["git", "-C", str(checkout), *arguments], text=True).strip()


def host():
    processes = subprocess.run(
        ["ps", "-axo", "pid,etime,%cpu,command"], capture_output=True, text=True
    )
    return {
        "utc": datetime.now(timezone.utc).isoformat(),
        "load_average": os.getloadavg(),
        "cpu_count": os.cpu_count(),
        "platform": platform.platform(),
        "python": sys.version,
        "process_status": processes.returncode,
        "processes": processes.stdout,
        "process_stderr": processes.stderr,
    }


def freeze(args, root):
    root.mkdir()
    for name in ("outputs", "transcripts", "inputs", "audits"):
        (root / name).mkdir()
    revisions = {
        role: git(args.checkouts / role, "rev-parse", "HEAD")
        for role in ("trunk", "parent", "head")
    }
    assert revisions["trunk"] == revisions["parent"] == args.baseline_revision
    assert all(
        not git(args.checkouts / role, "status", "--porcelain") for role in revisions
    )
    inputs = {}
    for name, source in (
        ("score-size-10000.json", args.score_scenario),
        ("language-arithmetic.json", args.regression_scenario),
    ):
        target = root / "inputs" / name
        target.write_bytes(source.read_bytes())
        inputs[name] = digest(target)
    tasks = []

    def add(identity, role, command, **metadata):
        tasks.append({"id": identity, "role": role, "command": command, **metadata})

    add("cold-trunk-help", "trunk", ["uv", "run", "dex", "--help"], workload="cold")
    add(
        "missing-trunk-command", "trunk", ["uv", "run", "dex", "missing-command"],
        workload="unsupported-command", expected_exit=2,
        diagnostic="invalid choice: 'missing-command'",
    )
    for workload in ("startup", "arithmetic"):
        for baseline in ("trunk", "parent"):
            for pair in range(1, 6):
                roles = (baseline, "head") if pair % 2 else ("head", baseline)
                for role in roles:
                    identity = f"{workload}-{baseline}-{pair}-{role}"
                    output = root / "outputs" / identity
                    command = ["uv", "run", "dex", "--help"]
                    if workload == "arithmetic":
                        command = [
                            "uv", "run", "dex", "eval", "--scenario",
                            str(root / "inputs/language-arithmetic.json"),
                            "--out", str(output),
                        ]
                    add(
                        identity, role, command, workload=workload,
                        baseline=baseline, pair=pair,
                        output=str(output) if workload == "arithmetic" else None,
                    )
    for role in ("trunk", "parent"):
        output = root / "outputs" / ("unsupported-" + role)
        add(
            "unsupported-score-" + role, role,
            ["uv", "run", "dex", "eval", "--scenario",
             str(root / "inputs/score-size-10000.json"), "--out", str(output)],
            workload="unsupported-score", expected_exit=2,
            diagnostic='"code": "scenario_error"', output=str(output),
        )
        add(
            "unsupported-report-" + role, role,
            ["uv", "run", "dex", "report", str(output)],
            workload="unsupported-report", expected_exit=2,
            diagnostic="invalid choice: 'report'",
        )
    for sample in range(1, 6):
        output = root / "outputs" / f"score-{sample}"
        for phase, command in (
            ("evaluation", [
                "uv", "run", "dex", "eval", "--scenario",
                str(root / "inputs/score-size-10000.json"), "--out", str(output),
            ]),
            ("report", ["uv", "run", "dex", "report", str(output)]),
        ):
            add(
                f"absolute-{sample}-{phase}", "head", command,
                workload="absolute-score", phase=phase, sample=sample,
                output=str(output),
            )
    tools = (Path(__file__), Path(__file__).with_name("publish_measurements.py"), args.recorder, args.timer, args.hook / "sitecustomize.py")
    frozen = {
        "revisions": revisions,
        "tools": {str(path): digest(path) for path in tools},
        "source_bytes": {
            role: {
                name: digest(args.checkouts / role / name)
                for name in git(args.checkouts / role, "ls-files").splitlines()
                if (args.checkouts / role / name).is_file()
            }
            for role in revisions
        },
        "inputs": inputs,
        "environment": host(),
        "tasks": tasks,
        "method": {
            "timer_version": 2, "samples": 5, "alternating": True,
            "cases": 10000, "ledger_events": 100000,
            "scoring_seconds": 10, "report_seconds": 5,
            "combined_seconds": 20, "peak_rss_bytes": 1073741824,
            "supported_median_ratio": 1.20,
            "combined": "sum of complete evaluation and report command intervals",
            "exclusions": [
                "dependency preparation", "input freezing", "artifact hashing",
                "independent output readback", "profiling",
            ],
            "sampling": "preserve every sample and contention record without replacement",
        },
    }
    (root / "freeze.json").write_text(json.dumps(frozen, indent=2) + "\n")
    (root / "samples.json").write_text("[]\n")
    print(json.dumps({"tasks": len(tasks), "revisions": revisions, "inputs": inputs}))


def run(args, root, frozen):
    assert args.cpu_idle_authorized, "Root must release the CPU-idle barrier."
    results = read(root / "samples.json")
    for task in frozen["tasks"][len(results):]:
        receipt = root / "transcripts" / (task["id"] + ".txt")
        assert not receipt.exists(), "Never replace a preserved sample."
        checkout = args.checkouts / task["role"]
        before = host()
        print("START " + task["id"], flush=True)
        with (root / "STARTS.jsonl").open("a") as starts:
            starts.write(json.dumps({"started_utc": before["utc"],
                "revision": frozen["revisions"][task["role"]], "task": task,
                "receipt": str(receipt)}) + "\n")
        command = [
            sys.executable, str(args.recorder), "--cwd", str(checkout),
            "--out", str(receipt), "--",
            str(checkout / ".venv/bin/python"), str(args.timer), "--",
            "env", "UV_CACHE_DIR=" + str(args.cache), "UV_OFFLINE=1",
            "PYTHONPATH=" + str(args.hook),
            "WORLD1_AUDIT_REPORT=" + str(root / "audits" / (task["id"] + ".json")),
            *task["command"],
        ]
        completed = subprocess.run(command, capture_output=True, text=True)
        text = receipt.read_text()
        lines = [line for line in text.splitlines() if line.startswith("MEASUREMENT ")]
        measurement = json.loads(lines[0][12:]) if len(lines) == 1 else None
        results.append({
            "task": task, "measurement": measurement,
            "recorder_exit": completed.returncode, "receipt": str(receipt),
            "environment_before": before, "environment_after": host(),
        })
        (root / "samples.json").write_text(json.dumps(results, indent=2) + "\n")
        print("DONE " + json.dumps({"id": task["id"], "measurement": measurement}), flush=True)


def verify_arithmetic(output):
    assert sorted(path.name for path in output.iterdir()) == ["actual.json", "expected.json"]
    actual = json.loads((output / "actual.json").read_bytes())
    expected = json.loads((output / "expected.json").read_bytes())
    assert actual["format"] == "dex-eval-actual-2" and actual["detail"] == "full"
    assert actual["scenario_id"] == expected["scenario_id"] == "language-arithmetic"
    assert expected["format"] == "dex-eval-expected-2" and expected["matches"] == [True]
    assert len(actual["observations"]) == len(expected["expected"]) == 1
    observation, answer = actual["observations"][0], expected["expected"][0]
    assert observation["command"] == "call" and observation["program"] == "arithmetic"
    assert observation["status"] == answer["status"] == "function_result"
    assert observation["diagnostics"] == observation["missing_checks"] == []
    assert observation["artifact"] is observation["runtime"] is answer["failure"] is None
    values = {"cents": {"kind": "money_cents", "cents": 1001},
              "days": {"kind": "integer", "value": 2},
              "due": {"kind": "date", "value": "2028-03-01"}}
    for value in (observation["function"]["value"], answer["value"]):
        assert value["kind"] == "record" and value["record"] == "Computed"
        assert len(value["fields"]) == 3
        assert {field["name"]: field["value"] for field in value["fields"]} == values
    return {name: digest(output / name) for name in ("actual.json", "expected.json")}


def verify_work(actual, ledger, score, costs, count=10000):
    case_ids = ["case-" + str(index).zfill(5) for index in range(1, count + 1)]
    assert sorted(actual["cases"]) == score["case_ids"] == case_ids
    assert sorted(score["cases"]) == case_ids
    assert costs["workload"] == {"cases": count, "ledger_events": count * 10}
    assert score["denominator"] == score["historical_denominator"] == count
    assert score["evaluation_status"] == "passed"
    assert score["history_status"] == "measured"
    assert score["reference_errors"] == score["historical_mismatches"] == []
    assert score["required_unresolved"] == score["not_scored"] == score["diagnostics"] == []
    assert score["copied_corrupted_fields"] == 0
    expected_score = {"reference_differences": [], "historical_differences": [],
                      "history_available": True, "required_unresolved": False,
                      "copied_corrupted_fields": []}
    for case_id in case_ids:
        case = actual["cases"][case_id]
        assert case["company"] == "synthetic" and case["program"] == "r1"
        assert case["cohort"] == "scenario" and case["status"] == "completed"
        assert case["decision"] == {"kind": "integer", "value": 7}
        assert case["effects"] == case["waits"] == []
        assert score["cases"][case_id] == expected_score
    assert len(ledger) == count * 10
    assert {row["id"] for row in ledger} == {
        case_id + "-" + str(index) for case_id in case_ids for index in range(10)}
    assert Counter(row["case_id"] for row in ledger) == dict.fromkeys(case_ids, 10)
    assert all(row["id"].rsplit("-", 1)[0] == row["case_id"] for row in ledger)


def summarize(root, frozen, results):
    assert len(results) == len(frozen["tasks"]), "Every frozen sample must finish."
    assert [item["task"] for item in results] == frozen["tasks"]
    failures = []
    for item in results:
        task, value = item["task"], item["measurement"]
        if value is None or not value["clock_valid"] or value["timer_version"] != 2:
            failures.append({"id": task["id"], "failure": "invalid timer"})
            continue
        expected_exit = task.get("expected_exit", 0)
        text = Path(item["receipt"]).read_text()
        if value["exit_status"] != expected_exit or item["recorder_exit"] != expected_exit:
            failures.append({"id": task["id"], "failure": "unexpected exit"})
        if task.get("diagnostic") and task["diagnostic"] not in text:
            failures.append({"id": task["id"], "failure": "named diagnostic absent"})
        if expected_exit:
            if task.get("output") and Path(task["output"]).exists():
                failures.append({"id": task["id"], "failure": "refusal published output"})
        elif value["max_rss_bytes"] > 1073741824:
            failures.append({"id": task["id"], "failure": "peak RSS exceeds 1 GiB"})
        audit_path = root / "audits" / (task["id"] + ".json")
        if audit_path.exists():
            audit = read(audit_path)
            if not audit["hook_loaded"] or audit["attempts"]:
                failures.append({"id": task["id"], "failure": "audit hook violation"})
        else:
            failures.append({"id": task["id"], "failure": "audit record absent"})
    supported_readback = [
        {"id": item["task"]["id"], "artifact_sha256": verify_arithmetic(Path(item["task"]["output"]))}
        for item in results if item["task"].get("workload") == "arithmetic"
    ]
    assert all(row["artifact_sha256"] == supported_readback[0]["artifact_sha256"]
               for row in supported_readback)
    comparisons = []
    for workload in ("startup", "arithmetic"):
        for baseline in ("trunk", "parent"):
            grouped = {
                role: [
                    item["measurement"] for item in results
                    if item["task"].get("workload") == workload
                    and item["task"].get("baseline") == baseline
                    and item["task"]["role"] == role
                ]
                for role in (baseline, "head")
            }
            assert all(len(values) == 5 and all(values) for values in grouped.values())
            for metric in ("wall_seconds", "max_rss_bytes"):
                values = {role: [sample[metric] for sample in group]
                          for role, group in grouped.items()}
                before = statistics.median(values[baseline])
                after = statistics.median(values["head"])
                comparison = {
                    "workload": workload, "baseline": baseline, "metric": metric,
                    "baseline_median": before, "head_median": after,
                    "ratio": after / before, "passed": after / before <= 1.20,
                    "samples": values,
                    "ranges": {role: [min(v), max(v)] for role, v in values.items()},
                }
                comparisons.append(comparison)
                if not comparison["passed"]:
                    failures.append(comparison)
    absolute = []
    for sample in range(1, 6):
        group = {
            item["task"]["phase"]: item for item in results
            if item["task"].get("workload") == "absolute-score"
            and item["task"]["sample"] == sample
        }
        output = Path(group["evaluation"]["task"]["output"])
        costs = read(output / "costs.json")
        actual = read(output / "actual.json")
        ledger = read(output / "ledger.json")["events"]
        score = read(output / "score.json")
        manifest = read(output / "run.json")
        verify_work(actual, ledger, score, costs)
        assert all(digest(output / name) == value for name, value in manifest["artifacts"].items())
        scoring = costs["scoring_ns"] / 1_000_000_000
        report = group["report"]["measurement"]["wall_seconds"]
        combined = group["evaluation"]["measurement"]["wall_seconds"] + report
        measurement = {
            "sample": sample, "scoring_seconds": scoring,
            "report_seconds": report, "combined_seconds": combined,
            "run_identity": manifest["identity"], "cases": 10000, "ledger_events": 100000,
            "passed": scoring <= 10 and report <= 5 and combined <= 20,
        }
        absolute.append(measurement)
        if not measurement["passed"]:
            failures.append(measurement)
    summary = {
        "status": "PASS" if not failures else "FAIL",
        "comparisons": comparisons, "absolute": absolute, "failures": failures,
        "supported_readback": supported_readback,
        "sample_count": len(results), "freeze_sha256": digest(root / "freeze.json"),
    }
    (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return bool(failures)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("freeze", "run", "summarize"))
    for name in ("evidence", "checkouts", "recorder", "timer", "cache", "hook",
                 "score-scenario", "regression-scenario"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--baseline-revision", required=True)
    parser.add_argument("--cpu-idle-authorized", action="store_true")
    args = parser.parse_args()
    root = args.evidence / "performance"
    if args.action == "freeze":
        freeze(args, root)
        return 0
    frozen = read(root / "freeze.json")
    assert all(digest(Path(path)) == value for path, value in frozen["tools"].items())
    assert all(
        git(args.checkouts / role, "rev-parse", "HEAD") == revision
        for role, revision in frozen["revisions"].items()
    )
    assert all(
        not git(args.checkouts / role, "status", "--porcelain")
        for role in frozen["revisions"]
    )
    assert all(
        digest(args.checkouts / role / name) == value
        for role, files in frozen["source_bytes"].items()
        for name, value in files.items()
    )
    assert all(digest(root / "inputs" / name) == value for name, value in frozen["inputs"].items())
    if args.action == "run":
        run(args, root, frozen)
        return 0
    return int(summarize(root, frozen, read(root / "samples.json")))


if __name__ == "__main__":
    raise SystemExit(main())

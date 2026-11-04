"""Publish recorded Timer V2 costs without changing a scored outcome."""

import argparse
from hashlib import sha256
import importlib.util
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_bytes())


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def build_supplement(performance, target, frozen, results, summary):
    manifest = read(target / "run.json")
    workload = read(target / "costs.json")["workload"]
    groups = {}
    for row in results:
        if row["task"].get("workload") == "absolute-score":
            groups.setdefault(row["task"]["sample"], {})[row["task"]["phase"]] = row
    samples = []
    stable = {"freeze.json", "actual.json", "expected.json", "score.json", "ledger.json", "coverage.json"}
    for number, group in sorted(groups.items()):
        assert set(group) == {"evaluation", "report"}
        output = Path(group["evaluation"]["task"]["output"])
        observed = read(output / "run.json")
        costs = read(output / "costs.json")
        assert costs["workload"] == workload
        assert all(observed["artifacts"][name] == manifest["artifacts"][name] for name in stable)
        assert all(digest(output / name) == value for name, value in observed["artifacts"].items())
        for phase in ("evaluation", "report"):
            source = group[phase]
            value = source["measurement"]
            assert value["timer_version"] == 2
            sample = {
                **value, "phase": phase, "sample": number,
                "source_run_identity": observed["identity"],
                "workload": workload, "receipt": source["receipt"],
            }
            if phase == "evaluation":
                sample["scoring_ns"] = costs["scoring_ns"]
                sample["execution_ns"] = costs["execution_ns"]
                sample["persistence_ns"] = costs["persistence_ns"]
                sample["component_exclusions"] = costs["exclusions"]
            samples.append(sample)
        evaluation = group["evaluation"]["measurement"]
        report = group["report"]["measurement"]
        samples.append({
            "phase": "combined", "sample": number,
            "source_run_identity": observed["identity"], "workload": workload,
            "wall_seconds": evaluation["wall_seconds"] + report["wall_seconds"],
            "max_rss_bytes": max(evaluation["max_rss_bytes"], report["max_rss_bytes"]),
            "exit_status": evaluation["exit_status"] or report["exit_status"],
            "clock_valid": evaluation["clock_valid"] and report["clock_valid"],
            "timer_version": 2,
            "aggregation": "Sum of complete evaluation and report command intervals; maximum of their command peaks.",
            "component_receipts": [group[name]["receipt"] for name in ("evaluation", "report")],
        })
    return {
        "format": "dex-measurements-1", "run_identity": manifest["identity"],
        "workload": workload, "samples": samples,
        "exclusions": [
            *frozen["method"]["exclusions"],
            "Internal scoring_ns excludes execution, ledger admission, engine hashing, persistence and report serialization.",
            "Combined cost includes complete evaluation and report process completion.",
            "Recorded activity describes supplied history; current execution activity is reported separately.",
        ],
        "methodology": {
            "publication_script_sha256": digest(Path(__file__)),
            "method": frozen["method"], "revisions": frozen["revisions"],
            "schedule": frozen["tasks"],
            "freeze_sha256": digest(performance / "freeze.json"),
            "sample_records_sha256": digest(performance / "samples.json"),
            "summary_sha256": digest(performance / "summary.json"),
            "gate_status": summary["status"], "gate_failures": summary["failures"],
            "supported_comparisons": summary["comparisons"],
            "cold_and_unsupported": [
                row for row in results
                if row["task"]["workload"] in {"cold", "unsupported-command", "unsupported-score", "unsupported-report"}
            ],
            "environment": frozen["environment"],
            "contention_records": "Every before/after host record remains in the identified samples.json.",
            "scoring_measure": "Recorded costs.scoring_ns for each evaluation, paired with that run's complete Timer V2 interval.",
        },
    }


def main():
    parser = argparse.ArgumentParser()
    for name in ("performance", "run", "checkout", "evidence", "recorder", "cache", "hook", "live-driver"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    frozen = read(args.performance / "freeze.json")
    results = read(args.performance / "samples.json")
    summary = read(args.performance / "summary.json")
    assert summary["freeze_sha256"] == digest(args.performance / "freeze.json")
    assert all(digest(Path(path)) == value for path, value in frozen["tools"].items())
    assert len(results) == len(frozen["tasks"]) == summary["sample_count"]
    assert [row["task"] for row in results] == frozen["tasks"]
    assert frozen["method"]["cases"] == 10000 and frozen["method"]["ledger_events"] == 100000
    assert {row["task"]["sample"] for row in results if row["task"].get("workload") == "absolute-score"} == {1, 2, 3, 4, 5}
    selected = next(row for row in results if row["task"]["id"] == "absolute-1-evaluation")
    assert args.run.resolve() == Path(selected["task"]["output"]).resolve()
    assert read(args.run / "costs.json")["workload"] == {"cases": 10000, "ledger_events": 100000}
    before = {path.name: digest(path) for path in args.run.iterdir()}
    assert "measurements.json" not in before
    supplement = build_supplement(args.performance, args.run, frozen, results, summary)
    assert len(supplement["samples"]) == 15
    raw = (json.dumps(supplement, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode()
    with (args.run / "measurements.json").open("xb") as handle:
        handle.write(raw)
    args.evidence.mkdir()
    spec = importlib.util.spec_from_file_location("live_driver", args.live_driver)
    live = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(live)
    reports = [
        live.record(args, args.checkout, name, ["uv", "run", "dex", "report", str(args.run)], 0)
        for name in ("measured-report", "measured-fresh-report")
    ]
    assert reports[0] == reports[1]
    report = json.loads(reports[0])
    assert report["run_identity"] == supplement["run_identity"]
    assert report["external_measurements"] == {"sha256": sha256(raw).hexdigest(), **supplement}
    assert report["outcome"] == read(args.run / "score.json")
    assert report["cases"] == read(args.run / "actual.json")["cases"]
    assert report["costs"] == read(args.run / "costs.json")
    assert before == {path.name: digest(path) for path in args.run.iterdir() if path.name != "measurements.json"}
    readback = {
        "status": "PASS", "run_identity": supplement["run_identity"],
        "measurement_sha256": sha256(raw).hexdigest(), "samples": len(supplement["samples"]),
        "unchanged_outcome_artifacts": sorted(before),
        "fresh_process_reports_identical": True,
    }
    (args.evidence / "measurement-readback.json").write_text(json.dumps(readback, indent=2) + "\n")
    print(json.dumps(readback, indent=2))


if __name__ == "__main__":
    main()

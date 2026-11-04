"""Real M1-13 CLI lanes with independent persisted-output assertions."""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

LANES = (
    ("correct-history-mistake", "01-score", 0),
    ("copied-mistake", "02-copied", 1),
    ("effect-field", "03-effect", 1),
    ("required-unresolved", "04-unresolved", 1),
    ("key-tamper", "05-key", 1),
    ("arrival-context", "06-context", 0),
    ("calls-touches", "07-ledger", 0),
    ("week-version", "08-buckets", 0),
    ("no-history-unimplemented", "09-coverage", 0),
    ("report-replay", "10-report", 0),
)
METRICS = (
    "logical_invocations", "network_calls", "retries", "input_tokens",
    "output_tokens", "cost_micros", "human_touches",
)


def read(path):
    return json.loads(path.read_bytes())


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def canonical_digest(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
    return sha256(raw.encode()).hexdigest()


def git(checkout, *arguments):
    return subprocess.check_output(["git", "-C", str(checkout), *arguments], text=True).strip()


def record(args, checkout, name, command, expected_exit):
    receipt = args.evidence / (name + ".txt")
    audit = args.evidence / "audits" / (name + ".json")
    audit.parent.mkdir(exist_ok=True)
    child = [
        "env", "UV_CACHE_DIR=" + str(args.cache), "UV_OFFLINE=1",
        "PYTHONPATH=" + str(args.hook), "WORLD1_AUDIT_REPORT=" + str(audit),
        *command,
    ]
    print("START " + name, flush=True)
    with (args.evidence / "STARTS.jsonl").open("a") as starts:
        starts.write(json.dumps({"started_utc": datetime.now(timezone.utc).isoformat(),
            "revision": git(checkout, "rev-parse", "HEAD"), "cwd": str(checkout),
            "name": name, "receipt": str(receipt), "argv": child}) + "\n")
    completed = subprocess.run(
        [sys.executable, str(args.recorder), "--cwd", str(checkout),
         "--out", str(receipt), "--", *child], capture_output=True, text=True
    )
    text = receipt.read_text()
    result = json.loads(text.rsplit("\nRESULT\n", 1)[1])
    assert completed.returncode == result["exit_status"] == expected_exit, text
    assert audit.exists(), "The network audit hook did not produce its record."
    assert read(audit)["hook_loaded"] and read(audit)["attempts"] == []
    print("DONE " + name + " exit " + str(completed.returncode), flush=True)
    return text.split("\nSTDOUT\n", 1)[1].split("\nSTDERR\n", 1)[0]


def assert_distribution(actual, values):
    count = len(values)
    ordered = sorted(values)
    median = (ordered[count // 2] if count % 2 else
              (ordered[count // 2 - 1] + ordered[count // 2]) / 2) if count else None
    frequencies = {str(value): values.count(value) for value in sorted(set(values))}
    assert actual == {
        "denominator": count, "total": sum(values), "frequencies": frequencies,
        "zero_count": values.count(0),
        "zero_share": values.count(0) / count if count else None,
        "mean": sum(values) / count if count else None,
        "median": median, "maximum": max(values) if values else None,
    }


def check_run(name, output, report):
    manifest = read(output / "run.json")
    assert canonical_digest({key: value for key, value in manifest.items() if key != "identity"}) == manifest["identity"]
    assert set(manifest["artifacts"]) == {
        "freeze.json", "actual.json", "expected.json", "score.json",
        "ledger.json", "coverage.json", "costs.json",
    }
    assert all(digest(output / path) == value for path, value in manifest["artifacts"].items())
    actual = read(output / "actual.json")["cases"]
    score = read(output / "score.json")
    frozen = read(output / "freeze.json")
    expected = read(output / "expected.json")
    assert canonical_digest(expected["key"]) == frozen["key_identity"]
    assert canonical_digest(expected["history"]) == frozen["history_identity"]
    assert canonical_digest(frozen["execution"]) == frozen["execution_identity"]
    engine = frozen["engine"]
    assert canonical_digest({key: value for key, value in engine.items() if key != "identity"}) == engine["identity"]
    count = 3 if name in {"calls-touches", "week-version", "report-replay"} else 2 if name in {"required-unresolved", "arrival-context"} else 1
    ids = ["case-" + str(index).zfill(5) for index in range(1, count + 1)]
    assert sorted(actual) == score["case_ids"] == ids
    assert sorted(score["cases"]) == ([] if name == "key-tamper" else ids)
    assert score["denominator"] == count
    assert report["format"] == "dex-report-1"
    assert report["run_identity"] == manifest["identity"]
    assert report["outcome"] == score and report["cases"] == actual
    assert report["identities"] == frozen
    assert report["ledger"]["provenance"] == "supplied_history"
    execution_zero = dict.fromkeys(("logical_invocations", "network_calls", "retries", "human_touches"), 0)
    assert all(row["execution_activity"] == execution_zero for row in actual.values())
    assert report["costs"]["execution_activity"] == execution_zero
    assert set(frozen) >= {
        "engine", "bundle", "evaluator_manifest", "evaluator",
        "execution_identity", "key_identity", "history_identity",
        "cohort", "cutoff", "sources", "recordings",
    }
    first, second = "case-00001", "case-00002"
    if name != "key-tamper":
        expected_errors = [first] if name in {"copied-mistake", "effect-field"} else [second] if name == "required-unresolved" else []
        assert score["reference_errors"] == expected_errors
        assert score["historical_mismatches"] == ([first] if name in {"correct-history-mistake", "arrival-context"} else [])
        assert score["required_unresolved"] == ([second] if name == "required-unresolved" else [])
        assert score["copied_corrupted_fields"] == int(name == "copied-mistake")
    if name == "correct-history-mistake":
        difference = score["cases"][first]["historical_differences"]
        assert len(difference) == 1
        assert (difference[0]["path"], difference[0]["expected"], difference[0]["actual"]) == ("/decision/value", 8, 7)
    if name == "copied-mistake":
        difference = score["cases"][first]["reference_differences"]
        assert len(difference) == 1
        assert (difference[0]["path"], difference[0]["expected"], difference[0]["actual"]) == ("/decision/value", 7, 8)
    if name == "effect-field":
        difference = score["cases"][first]["reference_differences"]
        assert len(difference) == 1
        assert (difference[0]["path"], difference[0]["expected"], difference[0]["actual"]) == ("/effects/0/payload/value", 7, 8)
    if name == "required-unresolved":
        assert actual[first]["status"] == actual[second]["status"] == "pending"
        assert score["cases"][first]["reference_differences"] == []
        assert actual[first]["waits"] == [{"node": "decide", "scope": [], "work_revision": 1,
            "request_revision": 1, "role": "reviewer", "assignee": None,
            "due_at": "2026-01-12T12:00:00+00:00",
            "request": {"kind": "text", "value": "Provide the decision."},
            "reviewed": [], "schema": {"kind": "integer"}}]
        assert actual[second]["decision"] is None
    if name == "key-tamper":
        assert score["evaluation_status"] == "failed"
        assert score["diagnostics"] == ["frozen_key_changed", "frozen_key_missing"]
        assert score["not_scored"] == ids and frozen["execution_performed"] is False
        assert actual[first]["status"] == "not_started"
        assert report["activity"]["cohorts"]["not_started"]["case_ids"] == ids
        assert report["activity"]["cohorts"]["started"]["case_ids"] == []
        checks = score["integrity_checks"]
        assert [row["condition"] for row in checks] == ["changed", "missing"]
        assert all(row["frozen_identity"] == frozen["key_identity"] for row in checks)
        assert checks[0]["observed_identity"] != frozen["key_identity"]
        assert checks[1]["observed_identity"] is None
    if name == "arrival-context":
        assert actual[first]["decision"] == {"kind": "integer", "value": 1}
        assert actual[second]["decision"] == {"kind": "integer", "value": 9}
        context = frozen["observed_context"]
        assert [row["value"] for row in context] == [9, 99]
        assert context[0]["available_at"] == "2026-01-04T12:00:00+00:00"
        assert context[1]["available_at"] == "2026-01-06T12:00:00+00:00"
        assert actual[second]["opened_at"] == "2026-01-05T10:00:00+00:00"
        difference = score["cases"][first]["historical_differences"]
        assert len(difference) == 1
        assert (difference[0]["path"], difference[0]["expected"], difference[0]["actual"]) == ("/decision/value", 9, 1)
    if name == "no-history-unimplemented":
        assert score["historical_denominator"] == 0
        assert score["history_status"] == "unimplemented"
        assert "exam_score" not in score and "replay_score" not in score
    if name in {"calls-touches", "week-version", "report-replay"}:
        check_activity(name, actual, read(output / "ledger.json")["events"], report["activity"])
        assert report["ledger"]["recorded_rows"] == 11
        assert report["ledger"]["distinct_events"] == 10
    return {"fixture": name, "case_ids": ids, "run_identity": manifest["identity"], "status": "PASS"}


def check_coverage(coverage, source):
    assert coverage["source_sha256"] == digest(source)
    requirements = coverage["requirements"]
    assert len({row["id"] for row in requirements}) == len(requirements)
    expected = [line for line in source.read_text().splitlines() if line.strip() and not line.startswith("#")]
    actual = [line for row in requirements for line in row["requirement"].splitlines() if line.strip()]
    assert actual == expected
    assert all(row["status"] in {"implemented", "unimplemented"} for row in requirements)
    assert all(row["evidence"] for row in requirements if row["status"] == "implemented")


def check_activity(name, actual, ledger, activity):
    assert len(ledger) == 11
    distinct = {(row["company"], row["origin"], row["id"]): row for row in ledger}
    assert len(distinct) == 10
    assert set(row["id"] for row in ledger) == {
        "model-1", "model-retry", "combined", "business", "input",
        "compile", "question", "program", "grant", "revoke",
    }
    totals = activity["case_totals"]
    first, second, zero = "case-00001", "case-00002", "case-00003"
    assert sorted(totals) == sorted(actual)
    assert totals[first] == dict(zip(METRICS, (2, 0, 1, 20, 4, 0, 2), strict=True))
    assert totals[second] == dict(zip(METRICS, (0, 0, 0, 0, 0, 0, 1), strict=True))
    assert totals[zero] == dict.fromkeys(METRICS, 0)
    assert activity["phases"]["runtime"] == dict(zip(METRICS, (2, 0, 1, 20, 4, 0, 3), strict=True))
    assert activity["phases"]["compile"] == dict(zip(METRICS, (1, 0, 0, 10, 2, 0, 1), strict=True))
    assert activity["phases"]["administrative"] == dict(zip(METRICS, (0, 0, 0, 0, 0, 0, 3), strict=True))
    assert activity["human_categories"] == {
        "external_change_approval": 1, "business_authority": 1,
        "requested_input": 1, "compile_clarification": 1,
        "program_approval": 1, "authority_administration": 2,
    }
    all_cases = activity["cohorts"]["all"]
    assert all_cases["case_ids"] == [first, second, zero] and all_cases["denominator"] == 3
    assert_distribution(all_cases["metrics"]["logical_invocations"], [2, 0, 0])
    assert_distribution(all_cases["metrics"]["human_touches"], [2, 1, 0])
    assert_distribution(all_cases["metrics"]["network_calls"], [0, 0, 0])
    assert activity["cohorts"]["completed"]["case_ids"] == [first, second, zero]
    assert activity["cohorts"]["pending"]["case_ids"] == []
    if name == "week-version":
        buckets = {(row["week"], row["program"]): row for row in activity["week_versions"]}
        assert set(buckets) == {("2025-12-29", "r1"), ("2026-01-05", "r2"), ("2026-01-12", "r2")}
        assert buckets["2025-12-29", "r1"]["case_ids"] == [first, second, zero]
        assert buckets["2026-01-05", "r2"]["case_ids"] == [first]
        assert buckets["2026-01-12", "r2"]["case_ids"] == [second]
        assert_distribution(buckets["2025-12-29", "r1"]["metrics"]["logical_invocations"], [1, 0, 0])
        assert_distribution(buckets["2025-12-29", "r1"]["metrics"]["human_touches"], [2, 0, 0])
        assert_distribution(buckets["2026-01-05", "r2"]["metrics"]["logical_invocations"], [1])
        assert_distribution(buckets["2026-01-12", "r2"]["metrics"]["human_touches"], [1])
        assert activity["versions"]["r2"]["case_ids"] == [first, second]
    else:
        assert len(activity["week_versions"]) == 1
        assert activity["week_versions"][0]["week"] == "2025-12-29"
        assert activity["week_versions"][0]["program"] == "r1"
    assert len(activity["shared"]) == 1
    assert activity["shared"][0]["totals"] == dict(zip(METRICS, (1, 0, 0, 10, 2, 0, 4), strict=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("freeze", "baselines", "scenarios"))
    for name in ("checkout", "baseline", "evidence", "recorder", "cache", "hook", "acceptance"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if args.action == "freeze":
        args.evidence.mkdir()
        (args.evidence / "inputs").mkdir()
        (args.evidence / "runs").mkdir()
        inputs = {}
        for fixture, _, _ in LANES:
            name = "score-" + fixture + ".json"
            target = args.evidence / "inputs" / name
            target.write_bytes((args.checkout / "tests/scenarios" / name).read_bytes())
            inputs[name] = digest(target)
        assert not git(args.checkout, "status", "--porcelain")
        frozen = {"head": git(args.checkout, "rev-parse", "HEAD"), "baseline": git(args.baseline, "rev-parse", "HEAD"), "inputs": inputs}
        (args.evidence / "live-freeze.json").write_text(json.dumps(frozen, indent=2) + "\n")
        print(json.dumps(frozen))
        return
    frozen = read(args.evidence / "live-freeze.json")
    assert git(args.checkout, "rev-parse", "HEAD") == frozen["head"]
    assert git(args.baseline, "rev-parse", "HEAD") == frozen["baseline"]
    assert not git(args.checkout, "status", "--porcelain")
    assert all(digest(args.evidence / "inputs" / name) == value for name, value in frozen["inputs"].items())
    assert all(digest(args.checkout / "tests/scenarios" / name) == value for name, value in frozen["inputs"].items())
    if args.action == "baselines":
        for role in ("trunk", "parent"):
            output = args.evidence / "runs" / ("baseline-" + role)
            text = record(args, args.baseline, "01-score-" + role, ["uv", "run", "dex", "eval", "--scenario", str(args.evidence / "inputs/score-correct-history-mistake.json"), "--out", str(output)], 2)
            assert '"code": "scenario_error"' in text or "scenario_error" in (args.evidence / ("01-score-" + role + ".txt")).read_text()
            record(args, args.baseline, "01-score-" + role + "-report", ["uv", "run", "dex", "report", str(output)], 2)
            assert "invalid choice: 'report'" in (args.evidence / ("01-score-" + role + "-report.txt")).read_text()
            assert not output.exists()
        return
    outcomes = []
    for fixture, transcript, expected_exit in LANES:
        output = args.evidence / "runs" / ("score-" + fixture)
        record(args, args.checkout, transcript, ["uv", "run", "dex", "eval", "--scenario", "tests/scenarios/score-" + fixture + ".json", "--out", str(output)], expected_exit)
        before = {path.name: digest(path) for path in output.iterdir() if path.is_file()}
        report_text = record(args, args.checkout, transcript + "-report", ["uv", "run", "dex", "report", str(output)], 0)
        report = json.loads(report_text)
        outcomes.append(check_run(fixture, output, report))
        check_coverage(report["acceptance"], args.acceptance)
        if fixture == "report-replay":
            repeated = record(args, args.checkout, transcript + "-fresh-report", ["uv", "run", "dex", "report", str(output)], 0)
            assert repeated == report_text
        assert before == {path.name: digest(path) for path in output.iterdir() if path.is_file()}
    (args.evidence / "live-readback.json").write_text(json.dumps(outcomes, indent=2) + "\n")
    print(json.dumps(outcomes, indent=2))


if __name__ == "__main__":
    main()

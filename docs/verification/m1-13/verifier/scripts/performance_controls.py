"""Synthetic controls for the verifier's unchanged performance limits."""

import argparse
from contextlib import redirect_stdout
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--driver", type=Path, required=True)
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()
spec = importlib.util.spec_from_file_location("performance_driver", args.driver)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
args.out.mkdir()
base = []
for workload in ("startup", "arithmetic"):
    for baseline in ("trunk", "parent"):
        for pair in range(1, 6):
            for role in (baseline, "head"):
                base.append({
                    "task": {"id": f"{workload}-{baseline}-{pair}-{role}",
                             "workload": workload, "baseline": baseline, "pair": pair, "role": role},
                    "measurement": {"wall_seconds": 0.1, "max_rss_bytes": 1000,
                                    "clock_valid": True, "timer_version": 2, "exit_status": 0},
                    "recorder_exit": 0,
                })
for sample in range(1, 6):
    for phase in ("evaluation", "report"):
        base.append({
            "task": {"id": f"absolute-{sample}-{phase}", "workload": "absolute-score",
                     "phase": phase, "sample": sample, "role": "head", "output": "synthetic"},
            "measurement": {"wall_seconds": 0.1, "max_rss_bytes": 1000,
                            "clock_valid": True, "timer_version": 2, "exit_status": 0},
            "recorder_exit": 0,
        })
case_ids = ["case-" + str(index).zfill(5) for index in range(1, 10001)]
actual = {"cases": dict.fromkeys(case_ids, {
    "company": "synthetic", "program": "r1", "cohort": "scenario", "status": "completed",
    "decision": {"kind": "integer", "value": 7}, "effects": [], "waits": []})}
ledger = {"events": [{"id": name + "-" + str(index), "case_id": name}
                     for name in case_ids for index in range(10)]}
score = {"case_ids": case_ids, "denominator": 10000, "historical_denominator": 10000,
         "evaluation_status": "passed", "history_status": "measured", "reference_errors": [],
         "historical_mismatches": [], "required_unresolved": [], "not_scored": [],
         "diagnostics": [], "copied_corrupted_fields": 0,
         "cases": dict.fromkeys(case_ids, {"reference_differences": [], "historical_differences": [],
             "history_available": True, "required_unresolved": False, "copied_corrupted_fields": []})}
original_read = module.read
outcomes = []
values = {"kind": "record", "record": "Computed", "fields": [
    {"name": "cents", "value": {"kind": "money_cents", "cents": 1001}},
    {"name": "days", "value": {"kind": "integer", "value": 2}},
    {"name": "due", "value": {"kind": "date", "value": "2028-03-01"}}]}
arithmetic_actual = {"format": "dex-eval-actual-2", "detail": "full",
    "scenario_id": "language-arithmetic", "observations": [{"command": "call",
    "program": "arithmetic", "status": "function_result", "diagnostics": [],
    "missing_checks": [], "artifact": None, "runtime": None, "function": {"value": values}}]}
arithmetic_expected = {"format": "dex-eval-expected-2", "scenario_id": "language-arithmetic",
    "matches": [True], "expected": [{"status": "function_result", "failure": None, "value": values}]}
for control in ("passing", "scoring", "report", "combined", "rss", "regression", "clock", "exit", "missing-work", "arithmetic-changed", "arithmetic-missing"):
    root = args.out / control
    root.mkdir()
    (root / "audits").mkdir()
    results = deepcopy(base)
    scoring_ns = 1000000
    for row in results:
        name = row["task"]["id"]
        receipt = root / (name + ".txt")
        receipt.write_text("SYNTHETIC CONTROL ONLY\n")
        row["receipt"] = str(receipt)
        (root / "audits" / (name + ".json")).write_text(json.dumps({"hook_loaded": True, "attempts": []}))
        if row["task"]["workload"] == "arithmetic":
            output = root / (name + "-output")
            output.mkdir()
            row["task"]["output"] = str(output)
            (output / "actual.json").write_text(json.dumps(arithmetic_actual))
            (output / "expected.json").write_text(json.dumps(arithmetic_expected))
            if name == "arithmetic-trunk-1-trunk" and control == "arithmetic-changed":
                changed = deepcopy(arithmetic_actual)
                changed["observations"][0]["function"]["value"]["fields"][0]["value"]["cents"] = 1002
                (output / "actual.json").write_text(json.dumps(changed))
            if name == "arithmetic-trunk-1-trunk" and control == "arithmetic-missing":
                (output / "actual.json").unlink()
    if control == "scoring":
        scoring_ns = 11000000000
    if control in {"report", "combined"}:
        selected = next(row for row in results if row["task"]["id"] == ("absolute-1-report" if control == "report" else "absolute-1-evaluation"))
        selected["measurement"]["wall_seconds"] = 6 if control == "report" else 20
    if control == "rss":
        results[0]["measurement"]["max_rss_bytes"] = 1073741825
    if control == "regression":
        for row in results:
            if row["task"].get("workload") == "startup" and row["task"]["role"] == "head":
                row["measurement"]["wall_seconds"] = 0.2
    if control == "clock":
        results[0]["measurement"]["clock_valid"] = False
    if control == "exit":
        results[0]["measurement"]["exit_status"] = results[0]["recorder_exit"] = 2
    frozen = {"tasks": [row["task"] for row in results]}
    (root / "freeze.json").write_text(json.dumps(frozen))
    payloads = {
        "actual.json": actual if control != "missing-work" else {"cases": {name: {} for name in case_ids[:-1]}},
        "ledger.json": ledger, "score.json": score,
        "run.json": {"identity": "synthetic", "artifacts": {}},
        "costs.json": {"workload": {"cases": 10000, "ledger_events": 100000}, "scoring_ns": scoring_ns},
    }
    module.read = lambda path: payloads[path.name] if path.name in payloads else original_read(path)
    caught = None
    with redirect_stdout(io.StringIO()):
        try:
            failed = module.summarize(root, frozen, results)
        except (AssertionError, OSError) as error:
            failed = True
            caught = str(error)
    assert failed == (control != "passing"), control
    outcomes.append({"control": control, "detected_failure": failed, "assertion": caught})
small_ids = case_ids[:2]
small_actual = {"cases": {name: deepcopy(actual["cases"][name]) for name in small_ids}}
small_ledger = deepcopy(ledger["events"][:20])
small_score = deepcopy(score)
small_score.update(case_ids=small_ids, denominator=2, historical_denominator=2,
                   cases={name: deepcopy(score["cases"][name]) for name in small_ids})
small_costs = {"workload": {"cases": 2, "ledger_events": 20}}
for control in ("passing", "literal-case-id", "event-case-count", "one-field-result", "pending-result", "score-error"):
    a, events, s = deepcopy(small_actual), deepcopy(small_ledger), deepcopy(small_score)
    if control == "literal-case-id":
        a["cases"]["case-99999"] = a["cases"].pop(small_ids[1])
        s["case_ids"][1] = "case-99999"
        s["cases"]["case-99999"] = s["cases"].pop(small_ids[1])
    if control == "event-case-count":
        events[0]["case_id"] = small_ids[1]
    if control == "one-field-result":
        a["cases"][small_ids[0]]["decision"]["value"] = 8
    if control == "pending-result":
        a["cases"][small_ids[0]]["status"] = "pending"
    if control == "score-error":
        s["cases"][small_ids[0]]["reference_differences"] = [{"path": "/decision/value"}]
    try:
        module.verify_work(a, events, s, small_costs, count=2)
        caught = False
    except AssertionError:
        caught = True
    assert caught == (control != "passing"), control
    outcomes.append({"control": "small-" + control, "detected_failure": caught})
print(json.dumps({"kind": "synthetic_verifier_controls", "status": "PASS", "controls": outcomes}, indent=2))

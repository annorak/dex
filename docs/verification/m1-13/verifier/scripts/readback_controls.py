"""Seed bad persisted fields to prove the independent live readback rejects them."""

import argparse
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil

parser = argparse.ArgumentParser()
for name in ("run", "report-receipt", "live-driver", "out"):
    parser.add_argument("--" + name, type=Path, required=True)
args = parser.parse_args()
spec = importlib.util.spec_from_file_location("live_driver", args.live_driver)
live = importlib.util.module_from_spec(spec)
spec.loader.exec_module(live)
text = args.report_receipt.read_text()
report = json.loads(text.split("\nSTDOUT\n", 1)[1].split("\nSTDERR\n", 1)[0])
args.out.mkdir()
outcomes = []
for control in ("passing", "run-identity", "missing-case", "changed-field", "denominator", "supporting-difference", "changed-artifact", "missing-artifact", "changed-key"):
    output = args.out / control
    shutil.copytree(args.run, output)
    candidate = deepcopy(report)
    if control == "run-identity":
        candidate["run_identity"] = "synthetic-wrong-identity"
    if control == "missing-case":
        del candidate["cases"]["case-00001"]
    if control == "changed-field":
        candidate["cases"]["case-00001"]["decision"]["value"] = 8
    if control == "denominator":
        candidate["outcome"]["denominator"] = 0
    if control == "supporting-difference":
        candidate["outcome"]["cases"]["case-00001"]["historical_differences"][0]["expected"] = 9
    if control == "changed-artifact":
        path = output / "score.json"
        path.write_bytes(path.read_bytes() + b" ")
    if control == "missing-artifact":
        (output / "actual.json").unlink()
    if control == "changed-key":
        path = output / "expected.json"
        value = json.loads(path.read_bytes())
        value["key"]["case-00001"]["decision"]["value"] = 8
        path.write_text(json.dumps(value))
    detected = False
    try:
        live.check_run("correct-history-mistake", output, candidate)
    except (AssertionError, OSError):
        detected = True
    assert detected == (control != "passing"), control
    outcomes.append({"control": control, "detected_failure": detected})
print(json.dumps({"kind": "synthetic_readback_controls", "status": "PASS", "controls": outcomes}, indent=2))

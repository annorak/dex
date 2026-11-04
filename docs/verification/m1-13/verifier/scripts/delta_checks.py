"""Exact-delta carry proof and real CLI refusals for preserved admission failures."""

import argparse
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess


def read(path):
    return json.loads(path.read_bytes())


def snapshot(root):
    result = {}
    for directory, subdirs, names in os.walk(root):
        for name in sorted(subdirs + names):
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                result[relative] = {"kind": "symlink", "target": os.readlink(path)}
            elif path.is_file():
                result[relative] = {"kind": "file", "sha256": sha256(path.read_bytes()).hexdigest()}
            else:
                result[relative] = {"kind": "directory"}
    return result


def main():
    parser = argparse.ArgumentParser()
    for name in ("checkout", "evidence", "recorder", "cache", "hook", "live-driver",
                 "collection", "prior-live", "preserved-malformed", "acceptance"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--prior-head", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("live_driver", args.live_driver)
    live = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(live)
    args.evidence.mkdir()
    def git(*argv):
        return subprocess.run(["git", *argv], cwd=args.checkout, check=True,
                              capture_output=True, text=True).stdout.strip()
    assert git("rev-parse", "HEAD") == args.head
    assert git("status", "--porcelain") == ""
    changed = git("diff", "--name-only", args.prior_head, args.head).splitlines()
    assert changed == ["src/dex/eval/admission.py", "tests/contracts/test_checks.py",
                       "tests/eval/test_scoring.py"], changed
    source_blobs = {}
    for line in git("ls-tree", "-r", args.head, "src", "pyproject.toml",
                    "uv.lock", "tests/scenarios").splitlines():
        metadata, name = line.split("\t")
        blob = metadata.split()[2]
        prior = git("rev-parse", args.prior_head + ":" + name)
        source_blobs[name] = {"prior": prior, "head": blob, "identical": prior == blob}
        assert prior == blob or name == "src/dex/eval/admission.py", name
    for suffix, transcript, _ in live.LANES:
        prior_run = args.prior_live / "runs" / ("score-" + suffix)
        assert (prior_run / "run.json").is_file(), suffix
        report_receipt = (args.prior_live / (transcript + "-report.txt")).read_text()
        report_text = report_receipt.split("\nSTDOUT\n", 1)[1].split("\nSTDERR\n", 1)[0]
        live.check_run(suffix, prior_run, json.loads(report_text))
    run = args.evidence / "fresh-run"
    live.record(args, args.checkout, "fresh-score",
                ["uv", "run", "dex", "eval", "--scenario",
                 "tests/scenarios/score-correct-history-mistake.json", "--out", str(run)], 0)
    reported = live.record(args, args.checkout, "fresh-report",
                           ["uv", "run", "dex", "report", str(run)], 0)
    again = live.record(args, args.checkout, "fresh-report-again",
                        ["uv", "run", "dex", "report", str(run)], 0)
    assert reported == again
    live.check_run("correct-history-mistake", run, json.loads(reported))
    live.check_coverage(read(run / "coverage.json"), args.acceptance)
    prior = args.prior_live / "runs/score-correct-history-mistake"
    same_artifacts = ["actual.json", "expected.json", "score.json", "ledger.json", "coverage.json"]
    assert all((run / name).read_bytes() == (prior / name).read_bytes() for name in same_artifacts)
    before, after = read(prior / "freeze.json"), read(run / "freeze.json")
    differences = [key for key in before if before[key] != after[key]]
    assert differences == ["evaluator"], differences
    evaluator_before, evaluator_after = before["evaluator"], after["evaluator"]
    artifact_changes = [key for key in evaluator_before
                        if evaluator_before[key] != evaluator_after[key]]
    assert artifact_changes == ["admission.py"], artifact_changes
    carry = {"status": "PASS", "prior_head": args.prior_head, "head": args.head,
             "changed_files": changed, "source_blobs": source_blobs,
             "carried_lanes": [suffix for suffix, _, _ in live.LANES], "same_artifacts": same_artifacts,
             "freeze_differences": differences, "evaluator_artifact_changes": artifact_changes,
             "prior_run_identity": read(prior / "run.json")["identity"],
             "fresh_run_identity": read(run / "run.json")["identity"],
             "engine_identity": after["engine"]["identity"],
             "fresh_process_reports_identical": True}
    (args.evidence / "carry-proof.json").write_text(json.dumps(carry, indent=2) + "\n")
    guard = args.evidence / "guarded"
    guard.mkdir()
    (guard / "sentinel").write_text("preserve\n")
    with sqlite3.connect(guard / "workspace.sqlite") as db:
        db.execute("create table marker (value text not null)")
        db.execute("insert into marker values ('preserve')")
    cases = [
        ("world1-null-effect", "world-1/bramblewick", "answer.effect: expected object"),
        ("world1-null-wait", "world-1/bramblewick", "answer.wait: expected object"),
        ("world1-invalid-response-json", "world-1/bramblewick", "response_scripts: invalid JSON"),
        ("world1-invalid-observed-actor", "world-1/bramblewick", "observed.actor: expected nonempty text"),
        ("world1-unhashable-decision", "world-1/bramblewick", "answer.decision: expected nonempty text"),
        ("world2-null-effect", "world-2/veldren", "answer.effect: expected object"),
        ("world2-null-wait", "world-2/veldren", "answer.wait: expected object"),
        ("world2-invalid-response-json", "world-2/veldren", "response_scripts: invalid JSON"),
        ("world2-invalid-observed-actor", "world-2/veldren", "observed.actor: expected nonempty text"),
        ("world2-null-summary", "world-2/veldren", "answer.summary: expected object"),
    ]
    results = []
    for name, source, diagnostic in cases:
        bundle = guard / name
        shutil.copytree(args.collection.parent / source, bundle)
        preserved = args.preserved_malformed / name
        for path in preserved.iterdir():
            assert path.is_file()
            (bundle / "eval" / path.name).write_bytes(path.read_bytes())
        output = guard / (name + "-run")
        before_state = snapshot(guard)
        live.record(args, args.checkout, "preserved-" + name,
                    ["uv", "run", "dex", "eval", str(bundle),
                     "--reference", "--out", str(output)], 2)
        receipt = (args.evidence / ("preserved-" + name + ".txt")).read_text()
        assert diagnostic in receipt and "Traceback (most recent call last)" not in receipt, receipt
        assert not output.exists()
        after_state = snapshot(guard)
        assert before_state == after_state, name
        row = {"name": name, "diagnostic": diagnostic, "exit_status": 2,
               "state_unchanged": True, "output_absent": True,
               "preserved_evaluator": snapshot(preserved)}
        results.append(row)
        snapshots = args.evidence / "snapshots"
        snapshots.mkdir(exist_ok=True)
        (snapshots / (name + ".json")).write_text(json.dumps({
            "before": before_state, "after": after_state}, indent=2) + "\n")
        (args.evidence / "preserved-refusal-readback.json").write_text(
            json.dumps(results, indent=2) + "\n")
    print(json.dumps({"status": "PASS", "carried_lanes": len(live.LANES),
                      "preserved_cli_refusals": len(results)}, indent=2))


if __name__ == "__main__":
    main()

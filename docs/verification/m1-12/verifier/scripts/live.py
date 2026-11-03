"""Untimed M1-12 CLI lanes. Every child command has its own original-recorder receipt."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument("action", choices=("scenarios", "repeat", "admission", "projections", "refusals"))
parser.add_argument("--checkout", type=Path, required=True)
parser.add_argument("--evidence", type=Path, required=True)
parser.add_argument("--baseline", type=Path, required=True)
parser.add_argument("--recorder", type=Path, required=True)
parser.add_argument("--cache", type=Path, required=True)
parser.add_argument("--hook", type=Path, required=True)
parser.add_argument("--inputs", type=Path)
args = parser.parse_args()
inputs = args.inputs or args.evidence
world = inputs / "demo7-a"
seed11 = inputs / "demo11"
summary = []

def read(path):
    return json.loads(path.read_bytes())

def manifest(root):
    assert root.is_dir(), root
    return {str(path.relative_to(root)): sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*")) if path.is_file() and not path.is_symlink()}

def record(name, command, status=0, diagnostic=None, **environment):
    receipt = args.evidence / (name + ".txt")
    assert not receipt.exists(), receipt
    audit = args.evidence / (name + "-audit.json")
    variables = {"UV_CACHE_DIR": str(args.cache), "UV_OFFLINE": "1", "PYTHONPATH": str(args.hook),
                 "WORLD1_AUDIT_REPORT": str(audit), **environment}
    full = ["env", *(key + "=" + value for key, value in variables.items()), *command]
    result = subprocess.run([sys.executable, str(args.recorder), "--cwd", str(args.checkout),
                             "--out", str(receipt), "--", *full], capture_output=True, text=True)
    saved = receipt.read_text()
    metadata = json.JSONDecoder().raw_decode(saved)[0]
    recorded = json.loads(saved.rsplit("\nRESULT\n", 1)[1])
    assert result.returncode == recorded["exit_status"] == status, (name, saved)
    if diagnostic is not None:
        assert diagnostic in saved, (name, saved)
    hook = read(audit)
    assert hook["hook_loaded"], name
    if not environment.get("WORLD1_MISSING_PACKET"):
        assert not hook["attempts"], (name, hook)
    summary.append({"name": name, "receipt": str(receipt), "revision": metadata["revision"],
                    "status": status, "diagnostic": diagnostic})
    print(json.dumps(summary[-1]), flush=True)
    return saved

if args.action == "scenarios":
    scenarios = args.evidence / "frozen-scenarios"
    scenarios.mkdir()
    names = [
        ("04-packets", "world2-packet-bytes"),
        ("05-history", "world2-history-membership"),
        ("06-nesting", "world2-nested-cohorts"),
        ("07-waits", "world2-wait-schedule"),
        ("08-keys", "world2-mistake-evidence-sets"),
        ("09-stream", "world2-stream-schedule"),
        ("10-isolation", "world2-isolation"),
        ("10-variation", "world2-seed-variation"),
        ("11-status", "world2-unfamiliar-status"),
        ("12-summary", "world2-changed-summary"),
    ]
    before = manifest(world)
    before11 = manifest(seed11)
    for principal, name in names:
        specification = read(args.checkout / "tests/scenarios" / (name + ".json"))
        expected = specification["expected"]
        specification["input_world"] = str(world)
        specification["seed11_world"] = str(seed11)
        source = scenarios / (name + ".json")
        source.write_text(json.dumps(specification, sort_keys=True) + "\n")
        output = args.evidence / ("scenario-" + name)
        record(principal, ["uv", "run", "dex", "eval", "--scenario", str(source), "--out", str(output)])
        actual, saved_expected = read(output / "actual.json"), read(output / "expected.json")
        assert actual["scenario"] == name
        assert actual["observed"] == expected, (name, actual["observed"], expected)
        assert actual["status"] == "fixture_requirements" and actual["execution_claimed"] is False
        assert saved_expected == {"expected": expected, "matches": {key: True for key in expected}}
    assert manifest(world) == before and manifest(seed11) == before11
elif args.action == "repeat":
    target = args.evidence / "demo7-b"
    record("02-repeat", ["uv", "run", "dex", "demo", "build", "--seed", "7", "--out", str(target)])
    first, second = manifest(world), manifest(target)
    assert first == second, {"only_first": sorted(first.keys() - second.keys()),
                             "only_second": sorted(second.keys() - first.keys()),
                             "different": [name for name in first.keys() & second.keys() if first[name] != second[name]]}
    summary.append({"complete_repeat_files": len(first), "identical": True})
elif args.action == "admission":
    for name, relative in (("03-admission", "world-2/veldren"),
                           ("03-admission-bramblewick", "world-1/bramblewick"),
                           ("03-admission-fennor", "world-1/fennor")):
        record(name, ["uv", "run", "dex", "bundle", "check", str(world / relative)], WORLD1_DENY_EVAL="1")
    first, second = manifest(args.baseline / "world-1"), manifest(world / "world-1")
    assert first == second, "World 1 path or byte changed."
    collection = read(world / "collection.json")
    assert [(item["company_id"], item["path"]) for item in collection["bundles"]] == [
        ("C1", "world-1/bramblewick"), ("C2", "world-1/fennor"), ("C3", "world-2/veldren")]
    summary.append({"world1_files": len(first), "identical_to_actual_dependency": True,
                    "collection_companies": ["C1", "C2", "C3"]})
elif args.action == "projections":
    for label, as_of in (("pre-adequacy", "2025-11-10T23:59:59-05:00"),
                         ("before-answer", "2026-10-01T09:59:59-04:00"),
                         ("at-answer", "2026-10-01T10:00:00-04:00")):
        target = args.evidence / ("veldren-" + label + "-view")
        rejected = label == "pre-adequacy"
        record("projection-" + label,
               ["uv", "run", "dex", "bundle", "project", str(world / "world-2/veldren"),
                "--consumer", "learning", "--as-of", as_of, "--out", str(target)],
               status=2 if rejected else 0,
               diagnostic="history_adequacy_unavailable" if rejected else None,
               WORLD1_DENY_EVAL="1")
        if rejected:
            assert not target.exists()
elif args.action == "refusals":
    guarded = args.evidence / "refusal-state"
    guarded.mkdir()
    (guarded / "existing").mkdir()
    (guarded / "existing/keep.txt").write_text("preserve existing state\n")
    (guarded / "existing-file").write_text("preserve file\n")
    database = sqlite3.connect(guarded / "state.sqlite")
    database.execute("create table state (revision integer, value text)")
    database.execute("insert into state values (12, 'preserve')")
    database.commit()
    database.close()
    (guarded / "existing-link").symlink_to(guarded / "existing", target_is_directory=True)
    specifications = args.evidence / "refusal-inputs"
    specifications.mkdir()
    standard = ["uv", "run", "dex", "demo", "build", "--seed", "7"]
    cases = [
        ("selector", standard + ["--world", "unknown", "--out", str(guarded / "invalid-selector")], "world_unavailable", {}),
        ("seed-negative", standard + ["--world", "world-2", "--seed", "-1", "--out", str(guarded / "negative")], "invalid_seed", {}),
        ("seed-overflow", standard + ["--seed", "9223372036854775808", "--out", str(guarded / "overflow")], "invalid_seed", {}),
        ("seed-text", standard + ["--seed", "bad", "--out", str(guarded / "text")], "invalid int value", {}),
        ("existing-directory", standard + ["--out", str(guarded / "existing")], "output_exists", {}),
        ("existing-file", standard + ["--out", str(guarded / "existing-file")], "output_exists", {}),
        ("existing-symlink", standard + ["--out", str(guarded / "existing-link")], "output_exists", {}),
        ("missing-parent", standard + ["--out", str(guarded / "absent/output")], "output_parent", {}),
        ("symlink-parent", standard + ["--out", str(guarded / "existing-link/output")], "output_parent", {}),
        ("missing-packet", standard + ["--out", str(guarded / "missing-packet")], "source_packet_unavailable", {"WORLD1_MISSING_PACKET": "1"}),
    ]
    for name, updates, code in (
        ("unknown-case", {"case": "world2-unknown"}, "world2_unknown_scenario"),
        ("missing-input", {"input_world": str(guarded / "absent")}, "world2_input_unavailable"),
        ("missing-seed11", {"seed11_world": str(guarded / "absent")}, "world2_seed11_unavailable"),
    ):
        specification = read(args.checkout / "tests/scenarios/world2-isolation.json")
        specification.update(input_world=str(world), seed11_world=str(seed11))
        specification.update(updates)
        source = specifications / (name + ".json")
        source.write_text(json.dumps(specification) + "\n")
        cases.append((name, ["uv", "run", "dex", "eval", "--scenario", str(source),
                             "--out", str(guarded / name)], code, {}))
    source = specifications / "valid.json"
    specification = read(args.checkout / "tests/scenarios/world2-history-membership.json")
    specification["input_world"] = str(world)
    source.write_text(json.dumps(specification) + "\n")
    cases.append(("scenario-existing-output", ["uv", "run", "dex", "eval", "--scenario", str(source),
                                               "--out", str(guarded / "existing")], "output_exists", {}))
    for name, command, diagnostic, environment in cases:
        before = manifest(guarded)
        paths_before = {str(path.relative_to(guarded)) for path in guarded.rglob("*")}
        links = {str(p.relative_to(guarded)): str(p.readlink()) for p in guarded.rglob("*") if p.is_symlink()}
        record("refusal-" + name, command, status=2, diagnostic=diagnostic, **environment)
        assert manifest(guarded) == before, name
        assert {str(path.relative_to(guarded)) for path in guarded.rglob("*")} == paths_before, name
        assert {str(p.relative_to(guarded)): str(p.readlink()) for p in guarded.rglob("*") if p.is_symlink()} == links
        with sqlite3.connect(guarded / "state.sqlite") as database:
            assert database.execute("select * from state").fetchall() == [(12, "preserve")]
    summary.append({"named_nonzero_refusals": len(cases), "state_unchanged": True})

output = args.evidence / (args.action + "-summary.json")
assert not output.exists(), output
output.write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps({"action": args.action, "summary": str(output)}))

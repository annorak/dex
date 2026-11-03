"""Read every timed native output after the full frozen schedule finishes."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("--performance", type=Path, required=True)
parser.add_argument("--world1", type=Path, required=True)
parser.add_argument("--collection", type=Path, required=True)
parser.add_argument("--checkouts", type=Path, required=True)
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()

def read(path):
    return json.loads(path.read_bytes())

def manifest(root):
    assert root.is_dir(), root
    assert not any(path.is_symlink() for path in root.rglob("*")), root
    return {str(path.relative_to(root)): sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*")) if path.is_file()}

frozen = read(args.performance / "freeze.json")
samples = read(args.performance / "samples.json")
assert len(samples) == len(frozen["tasks"]) == 110
expected_world1 = manifest(args.world1)
expected_collection = manifest(args.collection)
expected_world2 = manifest(args.collection / "world-2")
assert expected_world1 == frozen["input_bytes"]
assert all(sha256(Path(path).read_bytes()).hexdigest() == digest
           for path, digest in frozen["tools"].items())
for role, revision in frozen["revisions"].items():
    checkout = args.checkouts / role
    assert subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip() == revision
    assert all(sha256((checkout / path).read_bytes()).hexdigest() == digest
               for path, digest in frozen["source_bytes"][role].items())
expected_checks = {}
for world, company in (("world-1", "bramblewick"), ("world-1", "fennor"), ("world-2", "veldren")):
    public = read(args.collection / world / company / "bundle.json")
    expected_checks[company] = {"company_id": public["company_id"],
                                "cases": len(public["cases"]) + len(public["history"]["cases"]),
                                "sources": len(public["sources"]), "deliveries": len(public["deliveries"])}
outputs, checks, unsupported = [], [], []
for result, task in zip(samples, frozen["tasks"], strict=True):
    assert result["task"] == task
    measurement = result["measurement"]
    assert measurement["clock_valid"] and result["recorder_exit"] == measurement["measurement_exit_status"]
    receipt = Path(result["receipt"]).read_text()
    metadata = json.JSONDecoder().raw_decode(receipt)[0]
    assert metadata["revision"] == frozen["revisions"][task["role"]]
    if task.get("unsupported"):
        assert measurement["exit_status"] == 2 and '"code": "world_unavailable"' in receipt
        assert not Path(task["output"]).exists()
        unsupported.append(task["id"])
        continue
    assert measurement["exit_status"] == 0
    assert measurement["max_rss_bytes"] <= 1073741824
    if task.get("phase") == "build":
        output = Path(task["output"])
        if task["workload"] == "world1-build-validation":
            actual = manifest(output)
            assert actual == expected_world1, task["id"]
        elif task["workload"] == "absolute-collection":
            actual = manifest(output)
            assert actual == expected_collection, task["id"]
        else:
            actual = manifest(output / "world-2")
            assert actual == expected_world2, task["id"]
            entries = read(output / "collection.json")["bundles"]
            assert [(entry["company_id"], entry["path"]) for entry in entries] == [("C3", "world-2/veldren")]
            assert set(manifest(output)) == {"collection.json"} | {"world-2/" + name for name in expected_world2}
        outputs.append({"task": task["id"], "files": len(actual), "bytes_identical": True})
    if task.get("phase") == "check":
        stdout = receipt.split("\nSTDOUT\n", 1)[1].split("\nSTDERR\n", 1)[0].strip()
        actual = json.loads(stdout)
        assert actual["format"] == "dex-bundle-check-1"
        expected = expected_checks[task["company"]]
        assert {key: actual[key] for key in expected} == expected, task["id"]
        if task["company"] == "veldren":
            assert actual["unresolved"] == []
        checks.append({"task": task["id"], **expected})
assert len(outputs) == 30 and len(checks) == 55 and len(unsupported) == 4
loads = [environment["load_average"][0] for result in samples
         for environment in (result["environment_before"], result["environment_after"])]
summary = {"complete_outputs": outputs, "public_checks": checks, "unsupported": unsupported,
           "output_count": len(outputs), "check_count": len(checks),
           "all_native_bytes_read_after_timing": True, "input_and_source_bytes_unchanged": True,
           "process_snapshots_complete": all(environment["process_status"] == 0 for result in samples
                                           for environment in (result["environment_before"], result["environment_after"])),
           "one_minute_load_range": [min(loads), max(loads)]}
assert not args.out.exists()
args.out.write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps({"output_count": len(outputs), "check_count": len(checks), "unsupported_count": len(unsupported),
                  "all_bytes_match": True, "process_snapshots_complete": summary["process_snapshots_complete"],
                  "load_range": summary["one_minute_load_range"]}))

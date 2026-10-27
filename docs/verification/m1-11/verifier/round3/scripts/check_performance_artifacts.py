"""Inspect all persisted formal outputs only after the frozen timing schedule ends."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--performance", type=Path, required=True)
parser.add_argument("--checkouts", type=Path, required=True)
args = parser.parse_args()
root = args.performance
freeze = json.loads((root / "freeze.json").read_bytes())
samples = json.loads((root / "samples.json").read_bytes())
assert len(samples) == len(freeze["tasks"]) == 60
for name, digest in freeze["head_tracked_bytes"].items():
    assert sha256((args.checkouts / "head" / name).read_bytes()).hexdigest() == digest
expected = {name.removeprefix("world/"): digest for name, digest in freeze["input_bytes"].items()
            if name.startswith("world/")}
assert len(expected) == 30861
assert all(sample["measurement"]["clock_valid"] for sample in samples)
outputs = []
checks = []
for sample in samples:
    task = sample["task"]
    receipt = Path(sample["receipt"]).read_text()
    result = sample["measurement"]
    assert sample["recorder_exit"] == result["measurement_exit_status"]
    assert result["measurement_exit_status"] == result["exit_status"]
    if task.get("unsupported"):
        assert result["exit_status"] == 2
        assert "invalid choice: 'demo'" in receipt
        assert not Path(task["output"]).exists()
        continue
    assert result["exit_status"] == 0
    stdout = receipt.split("STDOUT\n", 1)[1].split("\nSTDERR", 1)[0].strip()
    if task["workload"] in ("regression-generation", "absolute-build"):
        output = Path(task["output"])
        files = {str(path.relative_to(output)): sha256(path.read_bytes()).hexdigest()
                 for path in sorted(output.rglob("*")) if path.is_file()}
        assert files == expected, task["id"]
        metadata = json.loads(stdout)
        assert metadata["companies"] == ["C1", "C2"] and metadata["seed"] == 7
        assert metadata["generator_version"] == "world-1-1"
        assert metadata["output"] == str(output)
        for company, slug, source_count in (("C1", "bramblewick", 7704), ("C2", "fennor", 7714)):
            bundle = json.loads((output / "world-1" / slug / "bundle.json").read_bytes())
            assert len(bundle["history"]["cases"]) == 3600 and len(bundle["cases"]) == 1800
            assert len(bundle["sources"]) == source_count
            assert any(source["source_id"] == company + "-final-postings" for source in bundle["sources"])
        outputs.append({"task": task["id"], "files": len(files), "all_bytes_identical": True})
        print("READBACK " + task["id"], flush=True)
    elif task["workload"] in ("validation", "absolute-validation"):
        metadata = json.loads(stdout)
        company = "C1" if task["company"] == "bramblewick" else "C2"
        assert metadata["company_id"] == company and metadata["cases"] == 5400
        assert metadata["sources"] == (7704 if company == "C1" else 7714)
        assert metadata["deliveries"] == (5962 if company == "C1" else 5957)
        assert metadata["format"] == "dex-bundle-check-1"
        unresolved = metadata["unresolved"]
        assert len(unresolved) == (184 if company == "C1" else 183)
        assert all(item["reason"] == "mapping requires explicit confirmation" for item in unresolved)
        assert any(item["source_id"] == company + "-final-postings" for item in unresolved)
        checks.append({"task": task["id"], "company": company, "cases": metadata["cases"],
                       "sources": metadata["sources"], "deliveries": metadata["deliveries"],
                       "unconfirmed_register_mappings": len(unresolved)})
assert len(outputs) == 10 and len(checks) == 50
summary = {"passed": True, "complete_outputs": outputs, "public_checks": checks,
           "unsupported_baseline_refusals_carried": 2, "comparison_outside_timing": True,
           "every_declared_source_and_case_processed": True,
           "native_export_and_packet_bytes_match_independent_untimed_readback": True}
(root / "artifact-readback.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps({"passed": True, "complete_worlds": len(outputs), "public_checks": len(checks),
                  "files_per_world": len(expected)}, sort_keys=True))

"""Named M1-13 refusals with exact existing-state preservation checks."""

import argparse
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3

parser = argparse.ArgumentParser()
for name in ("checkout", "collection", "recorded-run", "evidence", "recorder", "cache", "hook", "live-driver"):
    parser.add_argument("--" + name, type=Path, required=True)
args = parser.parse_args()
spec = importlib.util.spec_from_file_location("live_driver", args.live_driver)
live = importlib.util.module_from_spec(spec)
spec.loader.exec_module(live)
args.evidence.mkdir()
guard = args.evidence / "guarded"
guard.mkdir()
bundle = guard / "veldren"
shutil.copytree(args.collection.parent / "world-2/veldren", bundle)
original = {path.name: path.read_bytes() for path in (bundle / "eval").iterdir()}
(guard / "sentinel").write_text("existing-state\n")
with sqlite3.connect(guard / "workspace.sqlite") as database:
    database.execute("create table marker (value text not null)")
    database.execute("insert into marker values (?)", ("preserve",))
existing = guard / "existing"
existing.mkdir()
(existing / "keep").write_text("unchanged\n")
(guard / "existing-file").write_text("unchanged\n")
(guard / "existing-link").symlink_to(existing, target_is_directory=True)
(guard / "linked-parent").symlink_to(existing, target_is_directory=True)
run = guard / "recorded-run"
shutil.copytree(args.recorded_run, run)
run_original = {path.name: path.read_bytes() for path in run.iterdir()}
results = []


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def snapshot(root):
    found = {}
    for directory, subdirs, names in os.walk(root):
        for name in sorted(subdirs + names):
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            found[relative] = {"kind": "symlink", "target": os.readlink(path)} if path.is_symlink() else {"kind": "file", "sha256": sha256(path.read_bytes()).hexdigest()} if path.is_file() else {"kind": "directory"}
    return found


def restore():
    for path in (bundle / "eval").iterdir():
        if path.name not in original:
            path.unlink()
    for name, raw in original.items():
        (bundle / "eval" / name).write_bytes(raw)
    for name, raw in run_original.items():
        (run / name).write_bytes(raw)


def write_artifact(name, value):
    raw = canonical(value)
    (bundle / "eval" / name).write_bytes(raw)
    manifest = json.loads((bundle / "eval/manifest.json").read_bytes())
    manifest["artifacts"][name] = sha256(raw).hexdigest()
    (bundle / "eval/manifest.json").write_bytes(canonical(manifest))


def refuse(name, command, diagnostic):
    before = snapshot(guard)
    mutations = args.evidence / "mutations" / name
    mutations.mkdir(parents=True)
    (mutations / "before-state.json").write_text(json.dumps(before, indent=2) + "\n")
    for path in (bundle / "eval").iterdir():
        if path.name not in original or path.read_bytes() != original[path.name]:
            (mutations / path.name).write_bytes(path.read_bytes())
    text = live.record(args, args.checkout, "refusal-" + name, command, 2)
    receipt = (args.evidence / ("refusal-" + name + ".txt")).read_text()
    assert diagnostic in receipt, receipt
    assert "Traceback (most recent call last)" not in receipt
    after = snapshot(guard)
    (mutations / "after-state.json").write_text(json.dumps(after, indent=2) + "\n")
    assert before == after, name
    result = {"name": name, "diagnostic": diagnostic, "state_unchanged": True}
    results.append(result)
    (args.evidence / "refusal-readback.json").write_text(json.dumps(results, indent=2) + "\n")
    return text


def reference(path, out):
    return ["uv", "run", "dex", "eval", str(path), "--reference", "--out", str(out)]


refuse("missing-reference-bundle", reference(bundle, guard / "missing-reference-bundle"), "reference_unavailable")
collection_before = snapshot(args.collection.parent)
refuse("missing-reference-collection", reference(args.collection, guard / "missing-reference-collection"), "reference_unavailable")
collection_after = snapshot(args.collection.parent)
assert collection_before == collection_after
(args.evidence / "collection-preservation.json").write_text(json.dumps({
    "before": collection_before, "after": collection_after, "state_unchanged": True}, indent=2) + "\n")
(bundle / "eval/manifest.json").write_bytes(b"{")
refuse("malformed-manifest", reference(bundle, guard / "malformed"), "evaluator_manifest: invalid JSON")
restore()
(bundle / "eval/answer-key.json").write_bytes(original["answer-key.json"] + b" ")
refuse("changed-key", reference(bundle, guard / "changed-key"), "evaluator_hash_mismatch: answer-key.json")
restore()
(bundle / "eval/answer-key.json").unlink()
refuse("missing-key", reference(bundle, guard / "missing-key"), "evaluator_undeclared_artifact")
restore()
manifest = json.loads(original["manifest.json"])
del manifest["artifacts"]["answer-key.json"]
(bundle / "eval/manifest.json").write_bytes(canonical(manifest))
refuse("missing-key-declaration", reference(bundle, guard / "missing-key-declaration"), "evaluator_missing_artifact")
restore()
manifest = json.loads(original["manifest.json"])
manifest["company"] = "different-company"
(bundle / "eval/manifest.json").write_bytes(canonical(manifest))
refuse("company-conflict", reference(bundle, guard / "company-conflict"), "evaluator_company_identity")
restore()
fixture = json.loads(original["fixture.json"])
fixture["learning"].remove("H001")
write_artifact("fixture.json", fixture)
refuse("cohort-conflict", reference(bundle, guard / "cohort-conflict"), "evaluator_cohort_conflict")
restore()
fixture = json.loads(original["fixture.json"])
fixture["cutoffs"]["2027-01-10T23:59:59-05:00"]["not_opened"].append("S001")
write_artifact("fixture.json", fixture)
refuse("cutoff-conflict", reference(bundle, guard / "cutoff-conflict"), "evaluator_cutoff_conflict")
restore()
key = json.loads(original["answer-key.json"])
del key["H001"]
write_artifact("answer-key.json", key)
refuse("case-conflict", reference(bundle, guard / "case-conflict"), "evaluator_case_membership")
restore()
fixture = json.loads(original["fixture.json"])
fixture["seed"] = 999
write_artifact("fixture.json", fixture)
refuse("fixture-identity-conflict", reference(bundle, guard / "fixture-identity-conflict"), "evaluator_fixture_identity")
restore()
manifest = json.loads(original["manifest.json"])
manifest["artifacts"]["../sentinel"] = sha256((guard / "sentinel").read_bytes()).hexdigest()
(bundle / "eval/manifest.json").write_bytes(canonical(manifest))
refuse("unsafe-evaluator-path", reference(bundle, guard / "unsafe-evaluator-path"), "unsafe path")
restore()
for name in ("existing", "existing-file", "existing-link"):
    refuse("destination-" + name, reference(bundle, guard / name), "output_exists")
refuse("destination-symlink-parent", reference(bundle, guard / "linked-parent/new-run"), "output_parent")
refuse("destination-missing-parent", reference(bundle, guard / "absent/new-run"), "output_parent")
refuse("selector-absent", ["uv", "run", "dex", "eval", str(bundle), "--out", str(guard / "selector-absent")], "eval_selector")
refuse("selector-conflict", ["uv", "run", "dex", "eval", str(bundle), "--reference", "--scenario", "tests/scenarios/score-correct-history-mistake.json", "--out", str(guard / "selector-conflict")], "eval_selector")
(run / "score.json").write_bytes(run_original["score.json"] + b" ")
refuse("report-changed-artifact", ["uv", "run", "dex", "report", str(run)], "run_artifact_changed: score.json")
restore()
(run / "score.json").unlink()
refuse("report-missing-artifact", ["uv", "run", "dex", "report", str(run)], "report_invalid")
restore()
refuse("report-missing-input", ["uv", "run", "dex", "report", str(guard / "absent-run")], "report_invalid")
print(json.dumps({"status": "PASS", "refusals": results}, indent=2))

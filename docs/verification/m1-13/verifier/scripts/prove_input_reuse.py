"""Prove a preserved M1-12 seed-7 collection is applicable to M1-13."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("--checkout", type=Path, required=True)
parser.add_argument("--input", type=Path, required=True)
parser.add_argument("--previous-product", required=True)
parser.add_argument("--dependency", required=True)
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()


def git(*arguments):
    return subprocess.check_output(["git", "-C", str(args.checkout), *arguments])


def digest(raw):
    return sha256(raw).hexdigest()


def protected(name):
    return name.startswith(("src/dex/demo/", "src/dex/bundle/", "src/dex/core/", "src/dex/workspace", "docs/sources/", "src/dex/eval/world_1", "src/dex/eval/world_2")) or name == "src/dex/codec.py"


names = [name for name in git("ls-tree", "-r", "--name-only", args.dependency).decode().splitlines() if protected(name)]
assert names
source_proof = {}
for name in names:
    previous = git("show", args.previous_product + ":" + name)
    dependency = git("show", args.dependency + ":" + name)
    assert previous == dependency == (args.checkout / name).read_bytes(), name
    source_proof[name] = digest(dependency)
collection = json.loads((args.input / "collection.json").read_bytes())
assert collection["collection_id"] == "demo-collection-1-seed-7"
assert [(row["company_id"], row["path"]) for row in collection["bundles"]] == [
    ("C1", "world-1/bramblewick"), ("C2", "world-1/fennor"), ("C3", "world-2/veldren"),
]
evaluator_proof = {}
for declaration in collection["bundles"]:
    root = args.input / declaration["path"]
    assert digest((root / "bundle.json").read_bytes()) == declaration["manifest_sha256"]
    manifest = json.loads((root / "eval/manifest.json").read_bytes())
    assert manifest["company"] == declaration["company_id"]
    assert manifest["seed"] == 7 and manifest["reference_programs"] == []
    assert manifest["key_frozen_before_reference_execution"] is True
    for name, identity in manifest["artifacts"].items():
        assert name and "/" not in name and "\\" not in name
        assert digest((root / "eval" / name).read_bytes()) == identity
    evaluator_proof[declaration["company_id"]] = digest((root / "eval/manifest.json").read_bytes())
files = {}
for directory, subdirs, filenames in os.walk(args.input):
    assert all(not (Path(directory) / name).is_symlink() for name in subdirs + filenames)
    for name in sorted(filenames):
        path = Path(directory) / name
        files[path.relative_to(args.input).as_posix()] = digest(path.read_bytes())
assert len(files) == 32287
canonical = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
proof = {
    "kind": "preserved_seed7_input_applicability", "status": "PASS",
    "previous_verified_product": args.previous_product, "merged_dependency": args.dependency,
    "current_checkout_head": git("rev-parse", "HEAD").decode().strip(),
    "input": str(args.input), "protected_sources": source_proof,
    "input_files": files, "input_manifest_sha256": digest(canonical(files)),
    "evaluator_manifests": evaluator_proof,
    "scope": "Input reuse for explicit missing-reference refusal; no historical verification is repeated.",
}
args.out.write_text(json.dumps(proof, indent=2) + "\n")
print(json.dumps({
    "status": "PASS", "protected_files": len(source_proof), "input_files": len(files),
    "input_manifest_sha256": proof["input_manifest_sha256"], "companies": sorted(evaluator_proof),
}, sort_keys=True))

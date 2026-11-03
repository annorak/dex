import argparse
import ast
import builtins
import csv
import fcntl
import io
import json
import os
import socket
import subprocess
import tokenize
from contextlib import ExitStack
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

from dex.bundle.model import BundleError
from dex.bundle.projection import (
    EvidenceRef, materialize_learning, read_learning_view,
    serialize_learning_inputs, write_learning_view,
)
from dex.bundle.reader import load_bundle
from dex.bundle.writer import write_bundle
from dex.demo.build import build_world
from dex.eval.world_2 import artifacts

parser = argparse.ArgumentParser()
parser.add_argument("--root", type=Path, required=True)
parser.add_argument("--base", required=True)
parser.add_argument("--head", required=True)
args = parser.parse_args()
HEAD = subprocess.check_output(["git", "rev-parse", "--verify", args.head], text=True).strip()
BASE = subprocess.check_output(["git", "rev-parse", "--verify", args.base], text=True).strip()
ROOT = args.root
ROOT.mkdir()
WORLD = ROOT / "world"
assert subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip() == HEAD

def forbidden(*args, **kwargs):
    raise AssertionError("forbidden execution or network")

with patch.object(socket.socket, "connect", forbidden), patch.object(socket, "create_connection", forbidden):
    build_world("world-2", 7, WORLD)

bundle_path = WORLD / "world-2/veldren"
original_os, original_builtin, original_io = os.open, builtins.open, io.open
attempts = []
def check(name, kwargs, deny_original=False):
    if isinstance(name, int):
        return
    path = Path(os.fsdecode(name))
    if not path.is_absolute() and kwargs.get("dir_fd") is not None:
        parent = fcntl.fcntl(kwargs["dir_fd"], 50, bytes(1024)).split(bytes(1), 1)[0]
        path = Path(os.fsdecode(parent)) / path
    path = path.absolute()
    if "eval" in path.parts:
        attempts.append(str(path))
        raise AssertionError("evaluator read")
    if deny_original and path.is_relative_to(WORLD):
        raise AssertionError("original bundle read")

def guarded_os(name, *args, **kwargs):
    check(name, kwargs)
    return original_os(name, *args, **kwargs)
def guarded_builtin(name, *args, **kwargs):
    check(name, kwargs)
    return original_builtin(name, *args, **kwargs)
def guarded_io(name, *args, **kwargs):
    check(name, kwargs)
    return original_io(name, *args, **kwargs)

with patch("os.open", guarded_os), patch("builtins.open", guarded_builtin), patch("io.open", guarded_io):
    bundle = load_bundle(bundle_path)
    view = materialize_learning(bundle, datetime.fromisoformat("2026-09-30T23:59:59-04:00"))
    before = materialize_learning(bundle, datetime.fromisoformat("2026-10-01T09:59:59-04:00"))
    after = materialize_learning(bundle, datetime.fromisoformat("2026-10-01T10:00:00-04:00"))
assert not attempts
data = json.loads(view.content)
assert [case["case_id"] for case in data["cases"]] == [f"H{n:03d}" for n in range(1, 37)]
for token in [*(f"H{n:03d}".encode() for n in range(37, 49)), b"ONB-", b"answer-key", b"response-scripts", b"C1-", b"C2-", str(WORLD).encode()]:
    assert token not in view.content, token
assert b"shared-payroll-confirmation" not in before.content
assert b"shared-payroll-confirmation" in after.content
confirmation = next(s for s in json.loads(after.content)["sources"] if s["source_id"] == "C3-shared-payroll-confirmation")
assert confirmation["effective_date"] == "2025-10-01"
assert confirmation["available_at"] == "2026-10-01T10:00:00-04:00"
for token in (b"H006-client-response", b"H018-client-response", b"H030-client-response"):
    assert token in view.content
assert all(f"S{n:03d}-client-response".encode() not in view.content for n in range(1, 17))
original_sources = {(s.source_id, s.revision_id): s for s in bundle.sources}
passages = 0
for source in data["sources"]:
    original = original_sources[source["source_id"], source["revision_id"]]
    for mapping in source["passages"]:
        old, new = mapping["original"]["value"], mapping["projected"]["value"]
        assert original.extraction is not None
        assert original.extraction.text[old["start"]:old["end"]] == old["quote"] == new["quote"]
        assert source["extraction"]["value"]["text"][new["start"]:new["end"]] == new["quote"]
        passages += 1
assert passages > 0
manifest = json.loads(bundle.manifest)
descriptors = {s["source_id"]: s for s in manifest["sources"]}
for case in manifest["history"]["cases"]:
    events = case["observations"]
    requests = {}
    for event in events:
        source = descriptors[event["source"]["source_id"]]
        row = next(csv.DictReader(io.StringIO((bundle_path / source["path"]).read_text())))
        assert row["actor"] == event["actor"]
        assert row["occurred_at"] == event["occurred_at"] == source["occurred_at"]
        assert event["observed_at"] == event["available_at"] == source["observed_at"] == source["available_at"]
        delivery = next(d for d in manifest["deliveries"] if event["source"] in d["sources"])
        assert delivery["received_at"] == delivery["available_at"] == event["available_at"]
        if row["kind"] in ("client_request", "owner_request"):
            requests[row["request_id"]] = row
        elif row["kind"] in ("client_response", "business_decision"):
            request = requests[row["request_id"]]
            assert request["request_revision"] == row["request_revision"] == "1"
            assert request["client_id"] == row["client_id"] == case["case_id"] + "-client"
            assert event["occurred_at"] > request["occurred_at"]
            if row["kind"] == "client_response":
                assert {"site_id": row["site_id"], "field": row["field"]} in json.loads(request["fields"])
for destination in ("prompt", "diagnostic", "cache", "training_test", "compiler_recording"):
    for reference in (EvidenceRef("C3", "case", ("H042",)), EvidenceRef("C1", "case", ("H006",)), EvidenceRef("C3", "source", ("C3-shared-payroll-confirmation", "v1"))):
        try:
            serialize_learning_inputs(view, (reference,), destination, "C3")
        except BundleError as error:
            assert str(error) in ("learning_evidence_forbidden", "learning_company")
        else:
            raise AssertionError("restricted evidence serialized")
try:
    serialize_learning_inputs(view, (EvidenceRef("C3", "case", ("H006",)),), "library", "C3")
except BundleError as error:
    assert str(error) == "library_company_evidence"
else:
    raise AssertionError("company evidence reached library")

saved = ROOT / "view"
write_learning_view(after, saved)
def denied_os(name, *args, **kwargs):
    check(name, kwargs, True)
    return original_os(name, *args, **kwargs)
def denied_builtin(name, *args, **kwargs):
    check(name, kwargs, True)
    return original_builtin(name, *args, **kwargs)
def denied_io(name, *args, **kwargs):
    check(name, kwargs, True)
    return original_io(name, *args, **kwargs)
with patch("os.open", denied_os), patch("builtins.open", denied_builtin), patch("io.open", denied_io):
    reopened = read_learning_view(saved)
    assert reopened.content == after.content
    assert reopened.catalog == after.catalog
write_bundle(bundle, ROOT / "roundtrip")
roundtrip = load_bundle(ROOT / "roundtrip")
assert roundtrip == bundle
fixture = json.loads((bundle_path / "eval/fixture.json").read_bytes())
key = (bundle_path / "eval/answer-key.json").read_bytes()
with ExitStack() as stack:
    for name in ("dex.core.program.verify_program", "dex.core.runtime.decide", "dex.core.runtime.rebuild", "dex.core.language.execute_function"):
        stack.enter_context(patch(name, forbidden))
    assert artifacts(fixture)["answer-key.json"] == key
    fixture["observed"]["H008"]["activated_at"] = "2099-01-01T00:00:00-05:00"
    assert artifacts(fixture)["answer-key.json"] == key
protected = [
    "src/dex/core", "src/dex/workspace.py", "src/dex/workspace_command.py",
    "src/dex/verification.py", "src/dex/recordings.py", "src/dex/bundle",
    "scripts/import_contracts.py", "scripts/check_core.py",
]
for path in protected:
    assert subprocess.check_output(["git", "diff", BASE, HEAD, "--", path]) == b"", path
changed = subprocess.check_output(["git", "diff", "--name-only", BASE, HEAD, "--", "src"], text=True).splitlines()
comments = []
for name in changed:
    if name.endswith(".py"):
        with tokenize.open(name) as stream:
            tokens = tokenize.generate_tokens(stream.readline)
            comments += [(name, t.start[0], t.string) for t in tokens if t.type == tokenize.COMMENT]
assert comments == []
for name in changed:
    if name.startswith("src/dex/demo/") and name != "src/dex/demo/fixtures.py":
        tree = ast.parse(Path(name).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("dex.eval"), name
            if isinstance(node, ast.Import):
                assert all(not n.name.startswith("dex.eval") for n in node.names), name
print(json.dumps({
    "head": HEAD, "base": BASE, "public_evaluator_reads": attempts,
    "learning_cases": len(data["cases"]), "verified_passages": passages,
    "guarded_reopen": True, "roundtrip_exact": True,
    "key_independent": True, "restricted_destinations_rejected": True,
    "protected_code_unchanged": protected, "new_product_comments": comments,
}, indent=2))

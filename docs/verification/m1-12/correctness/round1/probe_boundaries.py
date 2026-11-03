import argparse
import io
import json
import subprocess
import tokenize
from copy import deepcopy
from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

from dex.bundle.model import BundleError
from dex.demo.build import build_world
from dex.eval.world_2 import artifacts

parser = argparse.ArgumentParser()
parser.add_argument("--root", type=Path, required=True)
parser.add_argument("--packets", type=Path, required=True)
parser.add_argument("--base", required=True)
parser.add_argument("--head", required=True)
args = parser.parse_args()
ROOT = args.root
BUNDLE = ROOT / "world/world-2/veldren"
BASE = subprocess.check_output(["git", "rev-parse", "--verify", args.base], text=True).strip()
HEAD = subprocess.check_output(["git", "rev-parse", "--verify", args.head], text=True).strip()
assert subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip() == HEAD
assert not subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()
diff = subprocess.check_output(["git", "diff", BASE, HEAD])
patch_id = subprocess.check_output(["git", "patch-id", "--stable"], input=diff).decode().split()[0]
manifest = json.loads((BUNDLE / "bundle.json").read_bytes())
fixture = json.loads((BUNDLE / "eval/fixture.json").read_bytes())
sources = {s["source_id"]: s for s in manifest["sources"]}
for filename in ("handbook.md", "service-owner-email.md"):
    original = args.packets / filename
    content = original.read_bytes()
    assert (BUNDLE / "sources" / filename).read_bytes() == content
    assert fixture["source_hashes"][filename] == sha256(content).hexdigest()
    assert not any(term in content.lower() for term in (b"shared", b"client-confirmed", b"onb-", b"dex"))
question = (BUNDLE / sources["C3-shared-payroll-question"]["path"]).read_text()
answer = sources["C3-shared-payroll-confirmation"]
assert all(case in question for case in ("H006", "H018", "H030")) and "H042" not in question
assert answer["effective_date"] == "2025-10-01"
assert answer["available_at"] == "2026-10-01T10:00:00-04:00"
changes = json.loads((BUNDLE / "eval/change-scenarios.json").read_bytes())
assert set(changes) == {"unfamiliar_status", "changed_summary"}
assert all(c["case_id"] not in fixture["stream"] for c in changes.values())
status = changes["unfamiliar_status"]
issued = datetime.fromisoformat(status["request"]["issued_at"])
due = datetime.fromisoformat(status["request"]["due_at"])
response = datetime.fromisoformat(status["response"]["available_at"])
assert due - issued == timedelta(days=1) and issued < response <= due
assert status["request"]["request_id"] == status["response"]["request_id"]
assert status["request"]["revision"] == status["response"]["revision"] == 1
assert status["response"]["actor"] == "Mara Tern"
assert status["expected"]["pending"] == ["CHANGE-STATUS-site-1/payroll"]
assert status["expected"]["ready"] == ["CHANGE-STATUS-site-2/benefits"]
assert status["expected"]["effects_before_resolution"] == []
assert set(status["expected"]["requires"]) == {"delivered_answer_citation", "saved_test", "verification", "program_approval"}
changed = changes["changed_summary"]
first, second = changed["summaries"]
old, new = changed["decisions"]
expected = changed["expected"]
assert first["ready_at"] < old["at"] < second["ready_at"] < new["at"] < expected["exact_change_approval_at"] < expected["activation_at"]
assert old["summary_id"] == first["summary_id"] and new["summary_id"] == second["summary_id"]
assert old["summary_revision"] == first["revision"] == 1
assert new["summary_revision"] == second["revision"] == 2
assert first["site_contact"] != second["site_contact"]
assert expected["old_decision_covers_revision_2"] is False
assert expected["effects_before_new_decision"] == []
assert expected["new_owner_request_at"] == second["ready_at"]
original_key = (BUNDLE / "eval/answer-key.json").read_bytes()
altered = deepcopy(fixture)
altered["observed"] = {}
with patch("dex.core.program.verify_program", side_effect=AssertionError("candidate verification called")), patch("dex.core.runtime.decide", side_effect=AssertionError("candidate execution called")), patch("dex.core.runtime.rebuild", side_effect=AssertionError("candidate replay called")), patch("dex.core.language.execute_function", side_effect=AssertionError("candidate function called")):
    assert artifacts(altered)["answer-key.json"] == original_key
parent = ROOT / "late-staging-failure"
parent.mkdir()
sentinel = parent / "keep"
sentinel.write_bytes(b"prior state")
target = parent / "world"


def fail_after_public_bundle(path, specification):
    assert (path / "bundle.json").is_file()
    assert (path / "exports/H001/client.csv").is_file()
    assert not target.exists()
    raise BundleError("review_injected_late_evaluator_failure")


with patch("dex.demo.build.write_world_2_artifacts", fail_after_public_bundle):
    try:
        build_world("world-2", 7, target)
    except BundleError as error:
        assert str(error) == "review_injected_late_evaluator_failure"
    else:
        raise AssertionError("late failure was swallowed")
assert sentinel.read_bytes() == b"prior state"
assert list(parent.iterdir()) == [sentinel]
files = subprocess.check_output(["git", "diff", "--name-only", BASE, HEAD], text=True).splitlines()
assert not any(name.startswith(("src/dex/core/", "src/dex/bundle/")) for name in files)
comments = []
for name in files:
    if name.endswith(".py"):
        for token in tokenize.generate_tokens(io.StringIO(Path(name).read_text()).readline):
            if token.type == tokenize.COMMENT:
                comments.append((name, token.start[0], token.string))
print(json.dumps({"result": "PASS", "base": BASE, "head": HEAD, "stable_patch_id": patch_id, "packet_bytes": "exact", "standalone_changes": "requirements and chronology valid", "key_independent_of_observed_actions": True, "late_failure": "no publication; sentinel preserved; staging cleaned", "comments_in_changed_python_files": comments}, sort_keys=True))

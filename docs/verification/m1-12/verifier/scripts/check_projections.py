"""Read actual saved learning views with original bundle access denied."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

from dex.bundle.projection import EvidenceRef, read_learning_view, serialize_learning_inputs

parser = argparse.ArgumentParser()
parser.add_argument("--evidence", type=Path, required=True)
parser.add_argument("--world", type=Path, required=True)
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()
summary = {}
for label in ("before-answer", "at-answer"):
    path = args.evidence / ("veldren-" + label + "-view")
    saved = (path / "view.json").read_bytes()
    view = read_learning_view(path)
    content = view.content
    data = json.loads(content)
    assert [case["case_id"] for case in data["cases"]] == [f"H{number:03d}" for number in range(1, 37)]
    identities = set(re.findall(r"\b[HS]\d{3}\b", content.decode()))
    assert identities <= {f"H{number:03d}" for number in range(1, 37)}, identities
    assert str(args.world).encode() not in content
    for forbidden in (b"answer-key", b"answer-sheet", b"mistakes.json", b"response-scripts",
                      b"ONB-", b"Bramblewick", b"Fennor", b"C1-", b"C2-", b"eval/"):
        assert forbidden not in content, forbidden
    assert b"H006-client-response" in content
    assert not any(f"S{number:03d}".encode() in content for number in range(1, 17))
    cutoff = "2026-10-01T09:59:59-04:00" if label == "before-answer" else "2026-10-01T10:00:00-04:00"
    assert all(source["available_at"] <= cutoff for source in data["sources"])
    confirmation = b"C3-shared-payroll-confirmation"
    assert (confirmation in content) == (label == "at-answer")
    if label == "at-answer":
        assert b"2025-10-01" in content
    source = next(item for item in data["sources"] if "H006-client-response" in item["source_id"])
    refs = (EvidenceRef("C3", "source", (source["source_id"], source["revision_id"])),
            EvidenceRef("C3", "case", ("H006",)))
    destinations = {}
    for destination in ("prompt", "diagnostic", "cache", "training_test", "compiler_recording"):
        encoded = serialize_learning_inputs(view, refs, destination, "C3")
        assert b"H006" in encoded
        assert str(args.world).encode() not in encoded
        assert not any(word in encoded for word in (b"H037", b"H042", b"H048", b"S001", b"answer-key", b"ONB-", b"C1-", b"C2-"))
        destinations[destination] = len(encoded)
    assert json.loads(serialize_learning_inputs(view, (), "library", "C3"))["evidence"] == []
    assert (path / "view.json").read_bytes() == saved
    summary[label] = {"learning_cases": 36, "source_count": len(data["sources"]),
                      "confirmation_available": label == "at-answer", "destinations": destinations,
                      "original_root_required": False, "sha256": sha256(saved).hexdigest()}
assert not args.out.exists()
args.out.write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary))

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

from dex.bundle.projection import EvidenceRef, read_learning_view, serialize_learning_inputs

parser = argparse.ArgumentParser()
parser.add_argument("--views", type=Path, required=True)
parser.add_argument("--world", required=True)
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()
summary = {}
for company, slug, employee in (("C1", "bramblewick", "Iona Vale"), ("C2", "fennor", "Orla Fen")):
    path = args.views / (slug + "-view")
    before = (path / "view.json").read_bytes()
    view = read_learning_view(path)
    data = json.loads(view.content)
    assert [item["case_id"] for item in data["cases"]] == [f"{company}-H{n:04d}" for n in range(1, 2701)]
    references = set(re.findall(r"C[12]-[HS]\d{4}", view.content.decode()))
    assert references <= {f"{company}-H{n:04d}" for n in range(1, 2701)}
    assert args.world.encode() not in view.content
    for denied in (b"answer-key", b"mistakes.json", b"response-scripts", b"W1-A", b"board-limit-notice", b"service-confirmation", b"Rillhaven Rise"):
        assert denied not in view.content, denied
    assert all(source["available_at"] < "2026-10-01" for source in data["sources"])
    mixed = next(source for source in data["sources"] if source["source_id"] == company + "-reconciled-actions")
    assert [record["locator"] for record in mixed["records"]] == ["record:2"]
    extraction = mixed["extraction"]["value"]
    assert extraction["text"] == company + "-H2700\nmanager\n" + employee + "\n"
    for passage in mixed["passages"]:
        original = passage["original"]["value"]
        projected = passage["projected"]["value"]
        assert original["quote"] == projected["quote"]
        assert projected["quote"] == extraction["text"][projected["start"]:projected["end"]]
        assert original["pin"]["original_sha256"] == projected["pin"]["original_sha256"]
        assert original["pin"]["extraction"] != projected["pin"]["extraction"]
        assert original["locator"].startswith("record:2/")
    refs = (
        EvidenceRef(company, "source", (mixed["source_id"], mixed["revision_id"])),
        EvidenceRef(company, "case", (company + "-H2700",)),
    )
    destinations = {}
    for destination in ("prompt", "diagnostic", "cache", "training_test", "compiler_recording"):
        encoded = serialize_learning_inputs(view, refs, destination, company)
        assert company.encode() + b"-H2700" in encoded
        assert args.world.encode() not in encoded
        assert all(word not in encoded for word in (b"-H2701", b"answer-key", b"mistakes.json"))
        destinations[destination] = len(encoded)
    library = json.loads(serialize_learning_inputs(view, (), "library", company))
    assert library["evidence"] == []
    assert (path / "view.json").read_bytes() == before
    summary[company] = {
        "learning_cases": 2700, "mixed_rows": ["record:2"],
        "destinations": destinations, "original_root_required": False,
        "saved_bytes_unchanged": True, "sha256": sha256(before).hexdigest(),
    }
args.out.write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps({company: {key: value for key, value in result.items() if key != "sha256"}
                  for company, result in summary.items()}, sort_keys=True))

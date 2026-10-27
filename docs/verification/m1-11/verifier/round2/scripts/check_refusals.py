import argparse
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--checkout", type=Path, required=True)
parser.add_argument("--evidence", type=Path, required=True)
parser.add_argument("--recorder", type=Path, required=True)
parser.add_argument("--cache", type=Path, required=True)
args = parser.parse_args()
guard = args.evidence / "live/refusal-state"
guard.mkdir()
existing = guard / "existing"
existing.mkdir()
(existing / "sentinel").write_bytes(b"existing state must survive")
with sqlite3.connect(guard / "workspace.sqlite") as db:
    db.execute("CREATE TABLE sentinel (value TEXT)")
    db.execute("INSERT INTO sentinel VALUES ('unchanged')")
(guard / "file").write_bytes(b"existing destination file")
(guard / "link").symlink_to(existing, target_is_directory=True)

def snapshot(root):
    result = {}
    for path in [root, *sorted(root.rglob("*"))]:
        relative = str(path.relative_to(root))
        stat = path.lstat()
        if path.is_symlink():
            value = ["symlink", str(path.readlink())]
        elif path.is_dir():
            value = ["directory"]
        else:
            value = ["file", sha256(path.read_bytes()).hexdigest()]
        result[relative] = [*value, stat.st_mode, stat.st_mtime_ns]
    return result

fresh = guard / "new"
cases = [
    ("default", ["--seed", "7"], fresh, "world_unavailable", False),
    ("all", ["--world", "all", "--seed", "7"], fresh, "world_unavailable", False),
    ("world2", ["--world", "world-2", "--seed", "7"], fresh, "world_unavailable", False),
    ("negative-seed", ["--world", "world-1", "--seed", "-1"], fresh, "invalid_seed", False),
    ("large-seed", ["--world", "world-1", "--seed", "9223372036854775808"], fresh, "invalid_seed", False),
    ("text-seed", ["--world", "world-1", "--seed", "seven"], fresh, "invalid int value", False),
    ("existing-directory", ["--world", "world-1", "--seed", "7"], existing, "output_exists", False),
    ("existing-file", ["--world", "world-1", "--seed", "7"], guard / "file", "output_exists", False),
    ("existing-symlink", ["--world", "world-1", "--seed", "7"], guard / "link", "output_exists", False),
    ("missing-parent", ["--world", "world-1", "--seed", "7"], guard / "absent/world", "output_parent", False),
    ("file-parent", ["--world", "world-1", "--seed", "7"], guard / "file/world", "output_parent", False),
    ("symlink-parent", ["--world", "world-1", "--seed", "7"], guard / "link/world", "output_parent", False),
    ("missing-packet", ["--world", "world-1", "--seed", "7"], fresh, "source_packet_unavailable", True),
]
results = []
for name, flags, output, reason, missing in cases:
    before = snapshot(guard)
    audit = args.evidence / ("refusal-" + name + "-audit.json")
    command = ["env", "UV_CACHE_DIR=" + str(args.cache), "UV_OFFLINE=1",
        "PYTHONPATH=" + str(args.evidence / "scripts"),
        "WORLD1_AUDIT_REPORT=" + str(audit),
        "WORLD1_MISSING_PACKET=" + ("1" if missing else "0"),
        "uv", "run", "dex", "demo", "build", *flags, "--out", str(output)]
    receipt = args.evidence / ("refusal-" + name + ".txt")
    result = subprocess.run([sys.executable, str(args.recorder),
        "--cwd", str(args.checkout), "--out", str(receipt), "--", *command],
        capture_output=True, text=True)
    assert result.returncode == 2, (name, result.returncode, result.stdout, result.stderr)
    assert reason in result.stderr, (name, result.stderr)
    assert snapshot(guard) == before, name
    control = json.loads(audit.read_bytes())
    assert control["hook_loaded"]
    assert all(item["kind"] == "missing_packet" for item in control["attempts"])
    assert bool(control["attempts"]) == missing
    results.append({"case": name, "exit": result.returncode, "reason": reason, "unchanged": True})
    print(name, reason, "unchanged", flush=True)
with sqlite3.connect(guard / "workspace.sqlite") as db:
    assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert db.execute("SELECT value FROM sentinel").fetchall() == [("unchanged",)]
(args.evidence / "refusal-summary.json").write_text(json.dumps(results, indent=2) + "\n")

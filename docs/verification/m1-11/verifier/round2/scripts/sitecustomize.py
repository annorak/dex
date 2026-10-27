import atexit
import json
import os
from pathlib import Path
import sys

attempts = []
report = os.environ.get("WORLD1_AUDIT_REPORT")
denied_root = os.environ.get("WORLD1_DENY_ROOT", "")
deny_eval = os.environ.get("WORLD1_DENY_EVAL") == "1"
missing_packet = os.environ.get("WORLD1_MISSING_PACKET") == "1"

def audit(event, args):
    if event.startswith("socket."):
        attempts.append({"event": event, "kind": "network"})
        raise RuntimeError("verifier denies model and socket network")
    if event not in ("open", "os.listdir", "os.scandir") or not args:
        return
    path = args[0]
    if not isinstance(path, (str, bytes)):
        return
    path = os.fsdecode(path)
    if missing_packet and path.endswith("procedure.md"):
        attempts.append({"event": event, "kind": "missing_packet", "path": path})
        raise FileNotFoundError("verifier required packet unavailable")
    if denied_root and (path == denied_root or path.startswith(denied_root + "/")):
        attempts.append({"event": event, "kind": "original_root", "path": path})
        raise PermissionError("verifier denies original bundle root")
    if deny_eval and ("eval" in Path(path).parts or Path(path).name in (
        "answer-key.json", "answer-sheet.json", "mistakes.json",
        "fixture.json", "response-scripts.json", "passage-map.json",
        "ai-extractions.json", "library-schedule.json",
    )):
        attempts.append({"event": event, "kind": "evaluator", "path": path})
        raise PermissionError("verifier denies evaluator reads")

def finish():
    if report:
        Path(report).write_text(json.dumps({
            "hook_loaded": True, "deny_eval": deny_eval,
            "deny_root": denied_root, "missing_packet": missing_packet,
            "attempts": attempts,
        }, sort_keys=True) + "\n")

sys.addaudithook(audit)
atexit.register(finish)

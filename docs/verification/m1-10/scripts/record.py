import argparse
import datetime
import json
import pathlib
import shlex
import subprocess
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument("--cwd", required=True)
parser.add_argument("--out", required=True)
parser.add_argument("--timeout", type=float, default=1800)
parser.add_argument("command", nargs=argparse.REMAINDER)
args = parser.parse_args()
command = args.command
if command and command[0] == "--":
    command = command[1:]
if not command:
    parser.error("command required")
output = pathlib.Path(args.out)
output.parent.mkdir(parents=True, exist_ok=True)
with output.open("x") as receipt:
    started = datetime.datetime.now(datetime.timezone.utc)
    revision = worktree = None
    metadata_error = None
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=args.cwd,
            capture_output=True, text=True,
        )
        worktree = subprocess.run(
            ["git", "status", "--porcelain"], cwd=args.cwd,
            capture_output=True, text=True,
        )
    except OSError as error:
        metadata_error = str(error)
    tick = time.monotonic()
    receipt.write(json.dumps({
        "argv": command, "command": shlex.join(command), "cwd": args.cwd,
        "revision": revision.stdout.strip() if revision is not None and revision.returncode == 0 else None,
        "working_tree_status": worktree.stdout.strip() if worktree is not None else None,
        "metadata_error": metadata_error,
        "started_utc": started.isoformat(),
    }, indent=2) + "\n")
    receipt.flush()
    try:
        result = subprocess.run(command, cwd=args.cwd, capture_output=True, timeout=args.timeout)
        stdout, stderr, status = result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired as error:
        stdout, stderr, status = error.stdout or b"", error.stderr or b"", 124
        stderr += b"\nRECEIPT_TIMEOUT\n"
    except OSError as error:
        stdout, stderr, status = b"", str(error).encode(), 127
    receipt.write("\nSTDOUT\n" + stdout.decode("utf-8", errors="replace"))
    receipt.write("\nSTDERR\n" + stderr.decode("utf-8", errors="replace"))
    receipt.write("\nRESULT\n" + json.dumps({
        "exit_status": status, "wall_seconds": time.monotonic() - tick,
        "finished_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }) + "\n")
print(f"{output}: exit {status}")
sys.stdout.buffer.write(stdout)
sys.stderr.buffer.write(stderr)
sys.exit(status)

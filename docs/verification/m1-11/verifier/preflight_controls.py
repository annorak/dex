import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--checkout", required=True, type=Path)
parser.add_argument("--tools", required=True, type=Path)
parser.add_argument("--out", required=True, type=Path)
args = parser.parse_args()
recorder = args.tools / "record.py"
timer = args.tools / "measure.py"
args.out.mkdir(parents=True, exist_ok=True)

def record(name, command, expected):
    receipt = args.out / (name + ".txt")
    result = subprocess.run([
        sys.executable, str(recorder), "--cwd", str(args.checkout),
        "--out", str(receipt), "--", *command
    ], capture_output=True, text=True)
    print(result.stdout, result.stderr)
    assert result.returncode == expected, (name, result.returncode, expected)
    saved = receipt.read_text()
    metadata = json.JSONDecoder().raw_decode(saved)[0]
    status = json.loads(saved.rsplit("\nRESULT\n", 1)[1])
    assert metadata["revision"] and metadata["argv"] == command
    assert status["exit_status"] == expected
    assert "\nSTDOUT\n" in saved and "\nSTDERR\n" in saved
    return saved

for name, status in (("005-recorder-success", 0), ("006-recorder-nonzero", 7)):
    code = "import sys;print('control stdout');print('control stderr',file=sys.stderr);raise SystemExit(" + str(status) + ")"
    saved = record(name, [sys.executable, "-c", code], status)
    assert "\nSTDOUT\ncontrol stdout\n" in saved
    assert "\nSTDERR\ncontrol stderr\n" in saved

for name, code, status in (
    ("007-timer-success", "print('timer success')", 0),
    ("008-timer-nonzero", "raise SystemExit(7)", 7),
    ("009-timer-allocation", "data=bytearray(64*1024*1024);print(len(data))", 0),
):
    saved = record(name, [sys.executable, str(timer), "--", sys.executable, "-c", code], status)
    measurement = json.loads(saved.split("MEASUREMENT ", 1)[1].splitlines()[0])
    assert measurement["timer_version"] == 2 and measurement["clock_valid"]
    assert measurement["exit_status"] == status
    assert measurement["measurement_exit_status"] == status
    assert measurement["wall_seconds"] > 0 and measurement["max_rss_bytes"] > 0
    if name == "009-timer-allocation":
        assert measurement["max_rss_bytes"] >= 64 * 1024 * 1024

for name, jump, code, expected in (
    ("010-clock-forward", 10_000_000_000, 0, 125),
    ("011-clock-backward", -10_000_000_000, 0, 125),
    ("012-clock-preserve-failure", 10_000_000_000, 7, 7),
):
    command = [str(timer), sys.executable, "-c", "raise SystemExit(" + str(code) + ")"]
    script = "import runpy,sys;from unittest.mock import patch;sys.argv=" + repr(command)
    script += ";patch('time.time_ns',side_effect=" + repr([20_000_000_000, 20_000_000_000 + jump]) + ").start()"
    script += ";runpy.run_path(" + repr(str(timer)) + ",run_name='__main__')"
    saved = record(name, [sys.executable, "-c", script], expected)
    measurement = json.loads(saved.split("MEASUREMENT ", 1)[1].splitlines()[0])
    assert not measurement["clock_valid"]
    assert measurement["measurement_exit_status"] == expected

print(json.dumps({
    "controls": "PASS",
    "recorder_sha256": hashlib.sha256(recorder.read_bytes()).hexdigest(),
    "timer_sha256": hashlib.sha256(timer.read_bytes()).hexdigest(),
    "python": sys.version,
}, indent=2))

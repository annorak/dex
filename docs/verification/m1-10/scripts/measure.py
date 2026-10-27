import argparse
import json
import resource
import subprocess
import sys
from time import perf_counter_ns, time_ns

CLOCK_DRIFT_LIMIT_SECONDS = 0.05

parser = argparse.ArgumentParser()
parser.add_argument("command", nargs=argparse.REMAINDER)
args = parser.parse_args()
command = args.command[1:] if args.command[:1] == ["--"] else args.command
if not command:
    parser.error("A command is required.")
if sys.platform not in {"darwin", "linux"}:
    parser.error("RSS units are defined only for Darwin and Linux.")
started_utc = time_ns()
started = perf_counter_ns()
result = subprocess.run(command, check=False)
finished = perf_counter_ns()
finished_utc = time_ns()
elapsed = (finished - started) / 1_000_000_000
utc_elapsed = (finished_utc - started_utc) / 1_000_000_000
clock_drift = utc_elapsed - elapsed
is_clock_valid = utc_elapsed >= 0 and abs(clock_drift) <= CLOCK_DRIFT_LIMIT_SECONDS
child_exit = result.returncode if result.returncode >= 0 else 128 - result.returncode
measurement_exit = child_exit if child_exit else (0 if is_clock_valid else 125)
usage = resource.getrusage(resource.RUSAGE_CHILDREN)
measurement = {
    "timer_version": 2,
    "command": command,
    "wall_seconds": elapsed,
    "utc_started_ns": started_utc,
    "utc_finished_ns": finished_utc,
    "utc_elapsed_seconds": utc_elapsed,
    "utc_minus_monotonic_seconds": clock_drift,
    "clock_drift_limit_seconds": CLOCK_DRIFT_LIMIT_SECONDS,
    "clock_valid": is_clock_valid,
    "measurement_exit_status": measurement_exit,
    "max_rss_bytes": usage.ru_maxrss * (1 if sys.platform == "darwin" else 1024),
    "user_seconds": usage.ru_utime,
    "system_seconds": usage.ru_stime,
    "exit_status": result.returncode,
    "platform": sys.platform,
    "rss_source": "getrusage(RUSAGE_CHILDREN), one launched command",
}
print("MEASUREMENT " + json.dumps(measurement, sort_keys=True), file=sys.stderr)
sys.exit(measurement_exit)

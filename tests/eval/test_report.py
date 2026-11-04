import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from typing import Any

import pytest

from dex.bundle.model import BundleError
from dex.bundle.validation import canonical
from dex.eval.identity import digest
from dex.eval.ledger import summarize, validate_ledger
from dex.eval.report import report_run
from dex.eval.run_store import read_run, save_run, validate_destination
from dex.eval.score_execution import execute_frozen
from dex.eval.score_fixtures import CUTOFF, fixture
from dex.eval.score_scenarios import evaluate_fixture


def test_recorded_report_is_stable(tmp_path: Path) -> None:
    run = tmp_path / "run"
    evaluate_fixture("report-replay", b"fixture", run)
    first = report_run(run)
    assert report_run(run) == first
    assert first["activity"]["case_totals"]["case-00003"]["human_touches"] == 0
    assert first["ledger"]["recorded_rows"] == 11
    assert first["ledger"]["distinct_events"] == 10
    assert first["activity"]["phases"]["runtime"]["human_touches"] == 3
    assert first["activity"]["phases"]["runtime"]["logical_invocations"] == 2
    assert first["activity"]["phases"]["runtime"]["network_calls"] == 0


def test_week_version_counts_and_zero_denominators(tmp_path: Path) -> None:
    run = tmp_path / "run"
    evaluate_fixture("week-version", b"fixture", run)
    report = report_run(run)
    activity = report["activity"]
    assert activity["versions"]["r1"]["case_ids"] == [
        "case-00001",
        "case-00002",
        "case-00003",
    ]
    assert activity["versions"]["r2"]["case_ids"] == ["case-00001", "case-00002"]
    assert [
        (row["week"], row["program"], row["denominator"])
        for row in activity["week_versions"]
    ] == [("2025-12-29", "r1", 3), ("2026-01-05", "r2", 1), ("2026-01-12", "r2", 1)]
    assert activity["cohorts"]["all"]["metrics"]["human_touches"] == {
        "denominator": 3,
        "total": 3,
        "frequencies": {"0": 1, "1": 1, "2": 1},
        "zero_count": 1,
        "zero_share": 1 / 3,
        "mean": 1,
        "median": 1,
        "maximum": 2,
    }
    assert activity["cohorts"]["pending"]["denominator"] == 0
    assert activity["cohorts"]["pending"]["metrics"]["human_touches"]["mean"] is None
    assert activity["phases"]["compile"]["logical_invocations"] == 1
    assert activity["phases"]["administrative"]["human_touches"] == 3
    assert report["ledger"]["provenance"] == "supplied_history"
    assert report["costs"]["execution_activity"] == {
        "logical_invocations": 0,
        "network_calls": 0,
        "retries": 0,
        "human_touches": 0,
    }


@pytest.mark.parametrize(
    "name, status, ids",
    [
        ("required-unresolved", "pending", ["case-00001", "case-00002"]),
        ("key-tamper", "not_started", ["case-00001"]),
    ],
)
def test_failed_evaluations_keep_all_cases_reportable(
    tmp_path: Path, name: str, status: str, ids: list[str]
) -> None:
    run = tmp_path / "run"
    evaluate_fixture(name, b"fixture", run)
    report = report_run(run)
    assert sorted(report["cases"]) == ids
    assert report["activity"]["cohorts"][status]["case_ids"] == ids
    assert report["outcome"]["evaluation_status"] == "failed"


@pytest.mark.parametrize(
    "mutation, diagnostic",
    [
        ("duplicate", "ledger_conflicting_identity"),
        ("network", "ledger_invocation_count"),
        ("empty_request", "expected nonempty text"),
        ("missing_request", "ledger_request_missing"),
        ("early_delivery", "ledger_response_delivery"),
        ("future", "ledger_after_cutoff"),
        ("company", "ledger_case_identity"),
    ],
)
def test_invalid_ledger_rejected(mutation: str, diagnostic: str) -> None:
    data: dict[str, Any] = fixture("calls-touches")
    cases = execute_frozen(data["execution"])
    events = data["ledger"]
    if mutation == "duplicate":
        events.append({**events[2], "actor": "different"})
    if mutation == "network":
        events[0]["network_calls"] = 100
    if mutation == "empty_request":
        events[0]["request"] = ""
    if mutation == "missing_request":
        data["requests"].clear()
    if mutation == "early_delivery":
        data["requests"][events[0]["request"]]["delivered_at"] = (
            "2026-01-03T00:00:00+00:00"
        )
    if mutation == "future":
        events[0]["available_at"] = "2026-02-01T00:00:00+00:00"
    if mutation == "company":
        events[0]["company"] = "other-company"
    with pytest.raises(BundleError, match=diagnostic):
        validate_ledger(events, cases, CUTOFF, data["requests"])


def test_distinct_action_origin_identity_and_combined_review() -> None:
    data: dict[str, Any] = fixture("calls-touches")
    cases = execute_frozen(data["execution"])
    events = data["ledger"]
    events.append({**events[2], "origin": "second-system"})
    rows = validate_ledger(events, cases, CUTOFF, data["requests"])
    assert len(rows) == 11
    result = summarize(cases, rows)
    assert result["case_totals"]["case-00001"]["human_touches"] == 3
    assert result["human_categories"]["external_change_approval"] == 2


@pytest.mark.parametrize(
    "name",
    [
        "freeze.json",
        "actual.json",
        "expected.json",
        "score.json",
        "ledger.json",
        "coverage.json",
        "costs.json",
    ],
)
@pytest.mark.parametrize("mutation", ["missing", "changed", "symlink"])
def test_recorded_artifact_integrity(tmp_path: Path, name: str, mutation: str) -> None:
    run = tmp_path / "run"
    evaluate_fixture("report-replay", b"fixture", run)
    path = run / name
    content = path.read_bytes()
    if mutation == "changed":
        path.write_bytes(content + b" ")
    else:
        path.unlink()
        if mutation == "symlink":
            target = tmp_path / "outside.json"
            target.write_bytes(content)
            path.symlink_to(target)
    before = {item.name: item.lstat().st_size for item in run.iterdir()}
    with pytest.raises(BundleError):
        report_run(run)
    assert {item.name: item.lstat().st_size for item in run.iterdir()} == before


def test_concurrent_publication_has_one_complete_winner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    barrier = Barrier(2)
    out = tmp_path / "run"

    def synchronized(path: Path) -> None:
        validate_destination(path)
        barrier.wait(timeout=10)

    monkeypatch.setattr("dex.eval.run_store.validate_destination", synchronized)

    def publish(value: int) -> bool:
        try:
            save_run(out, {"value.json": {"value": value}})
            return True
        except BundleError as error:
            assert str(error) == "output_exists"
            return False

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(publish, [1, 2]))
    assert sorted(results) == [False, True]
    _, artifacts = read_run(out)
    assert artifacts["value.json"]["value"] in {1, 2}
    assert sorted(path.name for path in tmp_path.iterdir()) == ["run"]


def test_report_fresh_process_cannot_execute_or_write(tmp_path: Path) -> None:
    run = tmp_path / "run"
    evaluate_fixture("report-replay", b"fixture", run)
    before = {path.name: digest(path.read_bytes()) for path in run.iterdir()}
    script = """
import importlib.abc, os, sys
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in {'dex.eval.admission','dex.eval.scoring','dex.eval.score_execution','dex.eval.score_scenarios','dex.demo'}:
            raise AssertionError('forbidden import: ' + fullname)
sys.meta_path.insert(0, Guard())
def audit(event, args):
    if event.startswith('socket.'):
        raise AssertionError('network')
    if event == 'open' and args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
        raise AssertionError('write')
sys.addaudithook(audit)
from dex.eval.report import run_report
from pathlib import Path
raise SystemExit(run_report(Path(sys.argv[1])))
"""
    commands = [sys.executable, "-B", "-c", script, str(run)]
    first = subprocess.run(commands, capture_output=True, check=True)
    second = subprocess.run(commands, capture_output=True, check=True)
    assert first.stdout == second.stdout == canonical(report_run(run))
    assert {path.name: digest(path.read_bytes()) for path in run.iterdir()} == before


def test_absent_history_stays_unimplemented(tmp_path: Path) -> None:
    run = tmp_path / "run"
    evaluate_fixture("no-history-unimplemented", b"fixture", run)
    report = report_run(run)
    assert report["outcome"]["history_status"] == "unimplemented"
    assert report["outcome"]["historical_denominator"] == 0
    assert all(
        row["status"] == "unimplemented" and row["evidence"] == []
        for row in report["acceptance"]["requirements"]
    )


def test_external_measurements_bind_to_run_and_preserve_failed_samples(
    tmp_path: Path,
) -> None:
    run = tmp_path / "run"
    evaluate_fixture("report-replay", b"fixture", run)
    before = report_run(run)
    measurements = {
        "format": "dex-measurements-1",
        "run_identity": before["run_identity"],
        "workload": before["costs"]["workload"],
        "samples": [
            {
                "phase": "report",
                "wall_seconds": 6.0,
                "max_rss_bytes": 1000,
                "exit_status": 0,
                "clock_valid": True,
                "timer_version": 2,
            }
        ],
        "exclusions": ["Dependency setup"],
        "methodology": "Timer V2; retained failing sample.",
    }
    path = run / "measurements.json"
    path.write_bytes(canonical(measurements))
    after = report_run(run)
    assert after["outcome"] == before["outcome"]
    assert after["external_measurements"]["samples"][0]["wall_seconds"] == 6.0
    measurements["run_identity"] = "wrong"
    path.write_bytes(canonical(measurements))
    with pytest.raises(BundleError, match="measurement_identity"):
        report_run(run)

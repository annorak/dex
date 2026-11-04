import json
import os
import sys
from pathlib import Path
from typing import Any

from dex.bundle.model import BundleError
from dex.bundle.reader import read_file
from dex.bundle.validation import (
    canonical,
    fields,
    items,
    object_value,
    parse_json,
    text,
)
from dex.eval.identity import digest
from dex.eval.ledger import summarize, validate_ledger
from dex.eval.run_store import read_run


def make_report(manifest: dict[str, Any], artifacts: dict[str, Any]) -> dict[str, Any]:
    required = {
        "freeze.json",
        "actual.json",
        "expected.json",
        "score.json",
        "ledger.json",
        "coverage.json",
        "costs.json",
    }
    if set(artifacts) != required:
        raise BundleError("run_artifact_membership")
    cases = object_value(artifacts["actual.json"]["cases"], "recorded.cases")
    frozen = object_value(artifacts["freeze.json"], "recorded.freeze")
    expected = object_value(artifacts["expected.json"]["key"], "recorded.key")
    if (
        sorted(cases) != frozen["cohort"]
        or sorted(cases) != artifacts["score.json"]["case_ids"]
        or cases.keys() != expected.keys()
    ):
        raise BundleError("recorded_case_membership")
    for raw in cases.values():
        case = object_value(raw, "recorded.case")
        fields(
            case,
            {
                "company",
                "cohort",
                "program",
                "opened_at",
                "status",
                "decision",
                "effects",
                "waits",
                "execution_activity",
            },
            set(),
            "recorded.case",
        )
        if case["status"] not in {"completed", "pending", "not_started"}:
            raise BundleError("recorded_case_status")
    rows = validate_ledger(
        artifacts["ledger.json"]["events"],
        cases,
        frozen["cutoff"],
        artifacts["ledger.json"]["requests"],
    )
    return {
        "format": "dex-report-1",
        "run_identity": manifest["identity"],
        "identities": frozen,
        "outcome": artifacts["score.json"],
        "cases": cases,
        "activity": summarize(cases, rows),
        "ledger": {
            "provenance": artifacts["ledger.json"]["provenance"],
            "artifact": "ledger.json",
            "sha256": manifest["artifacts"]["ledger.json"],
            "recorded_rows": len(artifacts["ledger.json"]["events"]),
            "distinct_events": len(rows),
        },
        "acceptance": artifacts["coverage.json"],
        "costs": artifacts["costs.json"],
        "limits": [
            "Synthetic checked execution is not a process reference or learned-stream result.",
            "Fixture requirements are not executed acceptance evidence.",
            "Activity aggregates describe supplied historical ledger records, not current evaluation activity. Current evaluation activity appears under costs.execution_activity.",
        ],
    }


def report_run(path: Path) -> dict[str, Any]:
    manifest, artifacts = read_run(path)
    report = make_report(manifest, artifacts)
    if (path / "measurements.json").exists() or (
        path / "measurements.json"
    ).is_symlink():
        root = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            raw = read_file(root, "measurements.json")
        finally:
            os.close(root)
        measurements = parse_json(raw, "measurements")
        fields(
            measurements,
            {
                "format",
                "run_identity",
                "workload",
                "samples",
                "exclusions",
                "methodology",
            },
            set(),
            "measurements",
        )
        if (
            measurements["format"] != "dex-measurements-1"
            or measurements["run_identity"] != manifest["identity"]
        ):
            raise BundleError("measurement_identity")
        if measurements["workload"] != artifacts["costs.json"]["workload"]:
            raise BundleError("measurement_workload")
        validate_measurements(measurements)
        report["external_measurements"] = {"sha256": digest(raw), **measurements}
    return report


def run_report(path: Path) -> int:
    try:
        sys.stdout.buffer.write(canonical(report_run(path)))
        return 0
    except (OSError, BundleError, KeyError, TypeError) as error:
        print(
            json.dumps(
                {
                    "format": "dex-report-error-1",
                    "code": "report_invalid",
                    "message": str(error),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


def validate_measurements(measurements: dict[str, Any]) -> None:
    samples = items(measurements["samples"], "measurements.samples")
    if not samples:
        raise BundleError("measurement_samples_missing")
    for raw in samples:
        sample = object_value(raw, "measurement.sample")
        if (
            not {
                "phase",
                "wall_seconds",
                "max_rss_bytes",
                "exit_status",
                "clock_valid",
                "timer_version",
            }
            <= sample.keys()
        ):
            raise BundleError("measurement_sample_fields")
        text(sample["phase"], "measurement.phase")
        if (
            type(sample["wall_seconds"]) not in {int, float}
            or sample["wall_seconds"] < 0
        ):
            raise BundleError("measurement_wall_seconds")
        if type(sample["max_rss_bytes"]) is not int or sample["max_rss_bytes"] < 0:
            raise BundleError("measurement_rss")
        if (
            type(sample["exit_status"]) is not int
            or type(sample["clock_valid"]) is not bool
            or sample["timer_version"] != 2
        ):
            raise BundleError("measurement_timer")
    for exclusion in items(measurements["exclusions"], "measurement.exclusions"):
        text(exclusion, "measurement.exclusion")
    if not measurements["methodology"]:
        raise BundleError("measurement_methodology")

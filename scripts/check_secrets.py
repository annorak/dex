"""Scan repository files, or explicitly supplied files, without exposing secrets."""

import json
import os
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[1]
SCANNER_OPTIONS = (
    "--json",
    "--no-verify",
    "--disable-filter",
    "detect_secrets.filters.allowlist.is_line_allowlisted",
    "--disable-filter",
    "detect_secrets.filters.heuristic.is_non_text_file",
    "--disable-filter",
    "detect_secrets.filters.heuristic.is_lock_file",
    "--disable-filter",
    "detect_secrets.filters.heuristic.is_swagger_file",
)


@dataclass(frozen=True, order=True)
class Finding:
    filename: str
    line: int
    detector: str


class CheckError(Exception):
    pass


def get_repository_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if result.returncode or result.stderr:
        raise CheckError("SECRET_INPUT_ERROR: cannot list repository files")
    paths = [
        ROOT / os.fsdecode(filename)
        for filename in result.stdout.split(b"\0")
        if filename
    ]
    return [path for path in paths if path.exists() or path.is_symlink()]


def parse_findings(output: bytes, filenames: set[str]) -> tuple[Finding, ...]:
    document: object = json.loads(output)
    if not isinstance(document, dict):
        raise ValueError
    data = cast(dict[object, object], document)
    results = data.get("results")
    if data.get("version") != "1.5.0" or not isinstance(results, dict):
        raise ValueError
    findings: set[Finding] = set()
    for filename, entries in cast(dict[object, object], results).items():
        if not isinstance(filename, str) or filename not in filenames:
            raise ValueError
        if not isinstance(entries, list) or not entries:
            raise ValueError
        for entry in cast(list[object], entries):
            if not isinstance(entry, dict):
                raise ValueError
            item = cast(dict[object, object], entry)
            detector = item.get("type")
            line = item.get("line_number")
            secret_hash = item.get("hashed_secret")
            if (
                item.get("filename") != filename
                or not isinstance(detector, str)
                or not detector
                or type(line) is not int
                or line < 1
                or not isinstance(secret_hash, str)
                or re.fullmatch(r"[0-9a-f]{40}", secret_hash) is None
                or type(item.get("is_verified")) is not bool
            ):
                raise ValueError
            findings.add(Finding(filename, line, detector))
    if not findings:
        raise ValueError
    return tuple(sorted(findings))


def scan_files(paths: Sequence[Path]) -> tuple[Finding, ...]:
    try:
        installed_version = version("detect-secrets")
    except PackageNotFoundError:
        raise CheckError(
            "SECRET_SCANNER_MISSING: detect-secrets==1.5.0 is required"
        ) from None
    if installed_version != "1.5.0":
        raise CheckError("SECRET_SCANNER_VERSION: detect-secrets==1.5.0 is required")
    files = sorted({path.absolute() for path in paths})
    if any(
        path.is_symlink() or not path.is_file() or "\\" in str(path)
        for path in files
    ):
        raise CheckError(
            "SECRET_INPUT_ERROR: expected regular files without backslashes"
        )
    for path in files:
        try:
            path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            raise CheckError(
                f"SECRET_INPUT_ERROR: cannot read UTF-8 text {json.dumps(str(path))}"
            ) from None
    if not files:
        return ()
    filenames = {str(path) for path in files}
    result = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-m",
            "detect_secrets.pre_commit_hook",
            *SCANNER_OPTIONS,
            "--",
            *sorted(filenames),
        ],
        cwd=ROOT,
        capture_output=True,
        timeout=120,
        check=False,
    )
    if result.stderr or result.returncode not in (0, 1):
        raise CheckError("SECRET_SCANNER_ERROR: scanner failed")
    if result.returncode == 0:
        if result.stdout:
            raise CheckError("SECRET_SCANNER_ERROR: unexpected output")
        return ()
    try:
        return parse_findings(result.stdout, filenames)
    except (ValueError, UnicodeError):
        raise CheckError("SECRET_SCANNER_ERROR: invalid findings output") from None


def main(argv: Sequence[str]) -> int:
    try:
        paths = (
            [Path(argument) for argument in argv] if argv else get_repository_files()
        )
        findings = scan_files(paths)
    except CheckError as error:
        print(str(error), file=sys.stderr)
        return 2
    except (OSError, subprocess.TimeoutExpired):
        print("SECRET_SCANNER_ERROR: cannot complete scan", file=sys.stderr)
        return 2
    for finding in findings:
        print(
            f"SECRET_FOUND {json.dumps(finding.filename)}:{finding.line}: "
            f"{json.dumps(finding.detector)}"
        )
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

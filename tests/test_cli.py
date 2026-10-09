import subprocess
import sys
from pathlib import Path

import pytest


def run_cli(argv: tuple[str, ...], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", "-m", "dex", *argv],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )


@pytest.mark.parametrize(
    "argv",
    [
        ("--help",),
        ("run", "--help"),
        ("measure", "--help"),
        ("verify-package", "--help"),
    ],
)
def test_help(argv: tuple[str, ...], tmp_path: Path) -> None:
    result = run_cli(argv, tmp_path)

    assert result.returncode == 0
    assert "usage:" in result.stdout
    assert result.stderr == ""


@pytest.mark.parametrize(
    ("argv", "command"),
    [
        (("run",), "run"),
        (("measure",), "measure"),
        (("verify-package", "./handoff"), "verify-package"),
    ],
)
def test_unimplemented_command(
    argv: tuple[str, ...], command: str, tmp_path: Path
) -> None:
    result = run_cli(argv, tmp_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == f"dex: {command} is not implemented yet\n"
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "argv",
    [
        (),
        ("unknown",),
        ("verify-package",),
        ("run", "--unknown"),
        ("measure", "extra"),
        ("verify-package", "./handoff", "extra"),
    ],
)
def test_invalid_arguments(argv: tuple[str, ...], tmp_path: Path) -> None:
    result = run_cli(argv, tmp_path)

    assert result.returncode == 2
    assert result.stdout == ""
    assert "error:" in result.stderr

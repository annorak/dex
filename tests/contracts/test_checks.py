import os
import secrets
import shlex
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

ROOT = Path(__file__).resolve().parents[2]
CHECK_CORE = ROOT / "scripts/check_core.py"
CHECK_SECRETS = ROOT / "scripts/check_secrets.py"


def assert_result(
    result: subprocess.CompletedProcess[str],
    expected_returncode: int,
    diagnostic: str | None = None,
) -> None:
    print(f"$ {shlex.join(result.args)}")
    print(result.stdout, end="")
    print(result.stderr, end="")
    print(f"exit: {result.returncode}")
    assert result.returncode == expected_returncode
    if diagnostic is not None:
        assert diagnostic in result.stdout + result.stderr


def run_check(
    command: Sequence[str | Path],
    *,
    cwd: Path,
    expected_returncode: int,
    diagnostic: str | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [str(argument) for argument in command],
        cwd=cwd,
        env=os.environ | {"PYTHONDONTWRITEBYTECODE": "1"} | (env or {}),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert_result(result, expected_returncode, diagnostic)
    return result


def _write_import_packages(root: Path, modules: dict[str, str]) -> None:
    for module, source in modules.items():
        parts = module.split(".")
        for depth in range(1, len(parts) + 1):
            initializer = root.joinpath(*parts[:depth], "__init__.py")
            initializer.parent.mkdir(parents=True, exist_ok=True)
            initializer.touch(exist_ok=True)
        root.joinpath(*parts, "__init__.py").write_text(source, encoding="utf-8")


def _lint_imports(
    root: Path, expected_returncode: int, diagnostic: str | None = None
) -> None:
    run_check(
        [
            Path(sys.executable).with_name("lint-imports"),
            "--config",
            ROOT / "pyproject.toml",
            "--no-cache",
            "--no-logo",
        ],
        cwd=root,
        expected_returncode=expected_returncode,
        diagnostic=diagnostic,
        env={"PYTHONPATH": str(ROOT)},
    )


def _import_round_trip(
    root: Path,
    modules: dict[str, str],
    changed: str,
    planted: str,
    diagnostic: str,
) -> None:
    _write_import_packages(root, modules)
    initializer = root.joinpath(*changed.split("."), "__init__.py")
    original = modules[changed]
    _lint_imports(root, 0)
    try:
        initializer.write_text(planted, encoding="utf-8")
        _lint_imports(root, 1, diagnostic)
    finally:
        initializer.write_text(original, encoding="utf-8")
        _lint_imports(root, 0)


@pytest.mark.parametrize(
    "source",
    [
        "dex",
        "dex.core.step",
        "dex.oak.compiler",
        "dex.runtime.runner",
        "dex.adapters.connector",
        "dex.unlisted.nested",
        "dex.cli.child",
    ],
)
@pytest.mark.parametrize("target", ["dex.eval.keys", "dex.demo.world"])
def test_direct_import_protected_code(
    tmp_path: Path, source: str, target: str
) -> None:
    _import_round_trip(
        tmp_path,
        {source: "import datetime\n", target: ""},
        source,
        f"import {target}\n",
        f"DEX-IMPORT-ISOLATION: {source} -> {target}",
    )


@pytest.mark.parametrize(
    "source", ["dex.demo", "dex.demo.worker", "dex.demo.fixtures.child"]
)
def test_direct_import_evaluator_requires_exact_fixture(
    tmp_path: Path, source: str
) -> None:
    _import_round_trip(
        tmp_path,
        {source: "", "dex.eval.keys": ""},
        source,
        "import dex.eval.keys\n",
        f"DEX-FIXTURE-IMPORT: {source} -> dex.eval.keys",
    )


@pytest.mark.parametrize(
    "source", ["dex.demo.worker", "dex.demo.fixtures", "dex.demo.fixtures.child"]
)
@pytest.mark.parametrize("target", ["dex.cli", "dex.cli.child"])
def test_direct_import_demo_cannot_use_cli(
    tmp_path: Path, source: str, target: str
) -> None:
    _import_round_trip(
        tmp_path,
        {source: "", target: ""},
        source,
        f"import {target}\n",
        f"DEX-DEMO-CLI: {source} -> {target}",
    )


@pytest.mark.parametrize("bridge", ["dex.bridge", "dex.cli"])
@pytest.mark.parametrize("target", ["dex.eval.keys", "dex.demo.world"])
def test_indirect_import_including_cli(
    tmp_path: Path, bridge: str, target: str
) -> None:
    _import_round_trip(
        tmp_path,
        {"dex.worker": f"import {bridge}\n", bridge: "", target: ""},
        bridge,
        f"import {target}\n",
        f"DEX-IMPORT-ISOLATION: dex.worker -> {bridge} -> {target}",
    )


@pytest.mark.parametrize(
    ("source", "target", "planted", "rule"),
    [
        (
            "dex.worker", "dex.eval.keys",
            "from ..eval import keys\n", "DEX-IMPORT-ISOLATION",
        ),
        (
            "dex.demo.worker", "dex.eval.keys",
            "from ...eval import keys\n", "DEX-FIXTURE-IMPORT",
        ),
        (
            "dex.core.step", "dex.runtime",
            "from ... import runtime\n", "DEX-CORE-IMPORT",
        ),
    ],
)
def test_direct_import_relative_and_core_import(
    tmp_path: Path, source: str, target: str, planted: str, rule: str
) -> None:
    _import_round_trip(
        tmp_path,
        {source: "", target: ""},
        source,
        planted,
        f"{rule}: {source} -> {target}",
    )


@pytest.mark.parametrize("target", ["pytest", "dex.runtime", "dex.cli"])
def test_core_import_external_or_noncore(tmp_path: Path, target: str) -> None:
    modules = {"dex.core.step": "import datetime\n"}
    if target.startswith("dex."):
        modules[target] = ""
    _import_round_trip(
        tmp_path,
        modules,
        "dex.core.step",
        f"import {target}\n",
        f"DEX-CORE-IMPORT: dex.core.step -> {target}",
    )


@pytest.mark.parametrize("target", ["pytest", "dex.runtime", "dex.cli"])
def test_core_import_indirect_import(tmp_path: Path, target: str) -> None:
    modules = {
        "dex.core.step": "import dex.core.values\n",
        "dex.core.values": "import datetime\n",
    }
    if target.startswith("dex."):
        modules[target] = ""
    _import_round_trip(
        tmp_path,
        modules,
        "dex.core.values",
        f"import {target}\n",
        f"DEX-CORE-IMPORT: dex.core.step -> dex.core.values -> {target}",
    )


def test_direct_import_and_core_import_allowed_routes(tmp_path: Path) -> None:
    _write_import_packages(
        tmp_path,
        {
            "dex.cli": "import dex.eval.keys\nimport dex.demo.world\n",
            "dex.demo.fixtures": "from ...eval import keys\n",
            "dex.demo.world": "import dex.core.step\nimport dex.demo.fixtures\n",
            "dex.eval.keys": "import dex.demo.world\n",
            "dex.core.step": "import datetime\nfrom .. import values\n",
            "dex.core.values": "import dataclasses\n",
            "dex.worker": "import pytest\n",
        },
    )
    _lint_imports(tmp_path, 0)


def assert_core_rejection(
    root: Path, source: str, diagnostic: str
) -> subprocess.CompletedProcess[str]:
    root.mkdir()
    path = root / "state.py"
    clean = "case = 1\n"
    path.write_text(clean, encoding="utf-8")
    command = [sys.executable, "-B", CHECK_CORE, root]
    run_check(command, cwd=root.parent, expected_returncode=0)
    try:
        path.write_text(source + "\n", encoding="utf-8")
        return run_check(
            command,
            cwd=root.parent,
            expected_returncode=1,
            diagnostic=diagnostic,
        )
    finally:
        path.write_text(clean, encoding="utf-8")
        run_check(command, cwd=root.parent, expected_returncode=0)


@pytest.mark.parametrize(
    "source",
    [
        "open('unused')",
        "reader = open",
        "print('unused')",
        "reader = input",
        "stop = exit",
        "show = license",
        "show = credits",
        "show = copyright",
        "import pathlib as paths\nvalue = paths.Path('unused')",
        "def consume(stream):\n    return stream.read()",
        "def emit(stream):\n    return stream.write('unused')",
        "import socket as network",
        "def emit(transport):\n    return transport.send(b'unused')",
        "import subprocess as process",
        "from os import system as execute",
    ],
)
def test_core_io(tmp_path: Path, source: str) -> None:
    assert_core_rejection(tmp_path / "core", source, "CORE_IO")


@pytest.mark.parametrize(
    "source",
    [
        "import time as clock",
        "from datetime import date\nvalue = date.today()",
        "import datetime as dt\nclock = dt.date.today",
        "from datetime import date as D\nvalue = D.today()",
        "from datetime import datetime as D\nclock = D.now",
        "from datetime import date as D\nDateType = D\nclock = DateType.today",
        "import datetime as dt\nDateType = dt.date\nclock = DateType.today",
        "from datetime import datetime as D\nclock = D.utcnow",
        "from datetime import date as D\nconvert = D.fromtimestamp",
        "from datetime import datetime as D\nconvert = D.astimezone",
        "from datetime import date as D\nformat_date = D.strftime",
    ],
)
def test_core_clock(tmp_path: Path, source: str) -> None:
    assert_core_rejection(tmp_path / "core", source, "CORE_CLOCK")


@pytest.mark.parametrize(
    "source",
    [
        "import random as generator",
        "from secrets import token_bytes as generate",
        "import uuid",
        "fingerprint = hash",
        "identity = id",
    ],
)
def test_core_randomness(tmp_path: Path, source: str) -> None:
    assert_core_rejection(tmp_path / "core", source, "CORE_RANDOM")


@pytest.mark.parametrize(
    ("source", "diagnostic"),
    [
        ("__import__('os')", "CORE_DYNAMIC"),
        ("load = __import__", "CORE_DYNAMIC"),
        ("import importlib as loader", "CORE_DYNAMIC"),
        ("import builtins", "CORE_DYNAMIC"),
        ("import inspect", "CORE_DYNAMIC"),
        ("import sys", "CORE_DYNAMIC"),
        ("execute = exec", "CORE_DYNAMIC"),
        ("evaluate = eval", "CORE_DYNAMIC"),
        ("build = compile", "CORE_DYNAMIC"),
        (
            "import datetime as dt\nclock = getattr(dt.date, 'today')",
            "CORE_DYNAMIC",
        ),
        ("lookup = globals", "CORE_DYNAMIC"),
        ("namespace = vars", "CORE_DYNAMIC"),
        ("value = callback.__globals__", "CORE_DYNAMIC"),
        ("value = object.__subclasses__", "CORE_DYNAMIC"),
        ("value = __builtins__['open']", "CORE_DYNAMIC"),
        ("from . import __builtins__ as runtime", "CORE_DYNAMIC"),
        ("from dex.core import __builtins__ as runtime", "CORE_DYNAMIC"),
        ("from datetime import *", "CORE_DYNAMIC"),
        ("import datetime as dt\nmodule = dt", "CORE_DYNAMIC"),
        (
            "from collections import abc as contracts\nmodule = contracts",
            "CORE_DYNAMIC",
        ),
        ("import collections.abc\nmodule = collections.abc", "CORE_DYNAMIC"),
        ("import datetime as module\nimport json as module", "CORE_DYNAMIC"),
        ("import dataclasses as records\nmodule = records.sys", "CORE_IMPORT"),
        ("import ast as syntax\nhelper = syntax._Unparser", "CORE_IMPORT"),
        ("from dataclasses import sys as system", "CORE_IMPORT"),
        ("from typing import get_type_hints as resolve", "CORE_IMPORT"),
        ("import typing as types\nresolve = types.get_type_hints", "CORE_DYNAMIC"),
        ("import json\nreader = json.load", "CORE_IMPORT"),
    ],
)
def test_core_randomness_dynamic_escapes(
    tmp_path: Path, source: str, diagnostic: str
) -> None:
    assert_core_rejection(tmp_path / "core", source, diagnostic)


@pytest.mark.parametrize(
    "source", ["import requests", "import decimal", "import dex.adapters"]
)
def test_core_import_rejects_unapproved_modules(tmp_path: Path, source: str) -> None:
    assert_core_rejection(tmp_path / "core", source, "CORE_IMPORT")


@pytest.mark.parametrize(
    "term",
    (
        "invoice invoices vendor vendors community communities HOA AP payable "
        "payables payment payments insurance certificate certificates board signer "
        "signers snow remittance onboarding payroll benefit benefits roster rosters "
        "cutover Bramblewick Fennor Veldren Harthmere Ashmere Rillhaven Avenreed "
        "Morrowfen Asterfen"
    ).split(),
)
def test_core_vocabulary_both_worlds(tmp_path: Path, term: str) -> None:
    assert_core_rejection(tmp_path / "core", f"value = {term!r}", "CORE_VOCABULARY")


@pytest.mark.parametrize(
    "source",
    [
        "invoice_total = 0",
        "class APInvoice:\n    pass",
        "class PayrollRoster:\n    pass",
        "invoice2 = 0",
        "# vendor rule\ncase = 1",
        r"value = '\x69nvoice'",
        "value = 'in' 'voice'",
        "value = 'ｉｎｖｏｉｃｅ'",
        "value = 'C1'",
        "value = 'C2'",
        "value = 'W1-P01'",
        "value = 'w1_e01'",
        "value = 'W1-A01'",
        "value = 'W1-D01'",
        "value = 'ONB-001'",
        "value = 'H001'",
        "value = 'S016'",
        "C1Status = 1",
        "ONBCase = 1",
    ],
)
def test_core_vocabulary_source_forms(tmp_path: Path, source: str) -> None:
    assert_core_rejection(tmp_path / "core", source, "CORE_VOCABULARY")


@pytest.mark.parametrize(
    "relative",
    ["invoice.py", "onboarding/state.py", "Bramblewick/__init__.py"],
)
def test_core_vocabulary_paths(tmp_path: Path, relative: str) -> None:
    root = tmp_path / "core"
    root.mkdir()
    clean = root / "state.py"
    clean.write_text("case = 1\n", encoding="utf-8")
    command = [sys.executable, "-B", CHECK_CORE, root]
    run_check(command, cwd=tmp_path, expected_returncode=0)
    planted = root / relative
    planted.parent.mkdir(parents=True, exist_ok=True)
    clean.rename(planted)
    try:
        run_check(
            command, cwd=tmp_path, expected_returncode=1, diagnostic="CORE_VOCABULARY"
        )
    finally:
        planted.rename(clean)
        run_check(command, cwd=tmp_path, expected_returncode=0)


def test_core_import_and_generic_vocabulary_are_allowed(tmp_path: Path) -> None:
    root = tmp_path / "invoice_vendor" / "core"
    root.mkdir(parents=True)
    (root / "state.py").write_text(
        """\
import ast as syntax
import hashlib
import json
from collections import abc as contracts
from dataclasses import dataclass
from datetime import date as D
from enum import StrEnum
from typing import TypeAlias
from ._internal import _reduce

StepId: TypeAlias = str

@dataclass(frozen=True)
class Event:
    actor: str
    when: D

class State(StrEnum):
    READY = "ready"

def collect(records: contracts.Sequence[Event]) -> tuple[Event, ...]:
    return tuple(records)

def fingerprint(source: str) -> str:
    tree: syntax.AST = syntax.parse(source)
    return hashlib.sha256(json.dumps(source).encode()).hexdigest()

def fields(event):
    return event.trace, event.token, event.types, event.signal

words = "case step event authority approval actor record source company client"
more_words = "employee site service activation money date apartment boardwalk"
raise RuntimeError("the checker must never execute this source")
""",
        encoding="utf-8",
    )
    run_check(
        [sys.executable, "-B", CHECK_CORE, root],
        cwd=tmp_path,
        expected_returncode=0,
    )


def test_core_io_diagnostic_does_not_echo_source(tmp_path: Path) -> None:
    sentinel = "SOURCE_CONTENT_MUST_NOT_APPEAR"
    result = assert_core_rejection(
        tmp_path / "core", f"open({sentinel!r})", "CORE_IO"
    )
    assert sentinel not in result.stdout + result.stderr


@settings(max_examples=12, database=None, derandomize=True, deadline=None)
@given(suffix=st.text(alphabet="xyz", min_size=1, max_size=8), module=st.booleans())
def test_core_clock_aliases_cannot_hide_callable_references(
    suffix: str, module: bool
) -> None:
    alias = f"date_type_{suffix}"
    source = (
        f"import datetime as {alias}\nDateType = {alias}.date\n"
        if module
        else f"from datetime import date as {alias}\nDateType = {alias}\n"
    )
    with TemporaryDirectory(prefix="dex-core-") as temporary:
        assert_core_rejection(
            Path(temporary) / "core",
            source + "clock = DateType.today\n",
            "CORE_CLOCK",
        )


@pytest.mark.parametrize(
    ("filename", "source", "diagnostic"),
    [
        ("missing.py", None, "CORE_INPUT"),
        ("source.txt", "case = 1\n", "CORE_INPUT"),
        ("state.py", "def broken(\n", "CORE_PARSE"),
    ],
)
def test_core_invalid_input_is_not_a_rule_failure(
    tmp_path: Path, filename: str, source: str | None, diagnostic: str
) -> None:
    path = tmp_path / filename
    if source is not None:
        path.write_text(source, encoding="utf-8")
    run_check(
        [sys.executable, "-B", CHECK_CORE, path],
        cwd=tmp_path,
        expected_returncode=2,
        diagnostic=diagnostic,
    )


@pytest.mark.parametrize("filename", ["sample.txt", "uv.lock", "image.svg"])
@pytest.mark.parametrize("suffix", ["", " # pragma: allowlist secret"])
def test_secret_key_is_rejected_without_retention(
    filename: str, suffix: str
) -> None:
    clean = 'mode = "demo"\n'
    with TemporaryDirectory(prefix="dex-secret-") as temporary:
        sample = Path(temporary) / filename
        sample.write_text(clean, encoding="utf-8")
        command = [sys.executable, "-B", str(CHECK_SECRETS), str(sample)]
        run_check(command, cwd=ROOT, expected_returncode=0)
        key = "gh" + "p_" + secrets.token_hex(18)
        try:
            sample.write_text(f'token = "{key}"{suffix}\n', encoding="utf-8")
            result = subprocess.run(
                command,
                cwd=ROOT,
                env=os.environ | {"PYTHONDONTWRITEBYTECODE": "1"},
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            has_leak = key in result.stdout + result.stderr
            repository = subprocess.run(
                [
                    "git",
                    "ls-files",
                    "--cached",
                    "--others",
                    "--exclude-standard",
                    "-z",
                ],
                cwd=ROOT,
                capture_output=True,
                timeout=30,
                check=True,
            )
            repository_paths = [
                ROOT / os.fsdecode(name)
                for name in repository.stdout.split(b"\0")
                if name
            ]
            has_retained_key = any(
                key.encode() in path.read_bytes()
                for path in repository_paths
                if path.is_file() and not path.is_symlink()
            )
        except (OSError, UnicodeError, subprocess.SubprocessError):
            pytest.fail("Could not complete the private secret probe", pytrace=False)
        finally:
            del key
            sample.write_text(clean, encoding="utf-8")
        if has_leak or has_retained_key:
            del result
            pytest.fail(
                "The secret probe exposed or retained its sample", pytrace=False
            )
        assert_result(result, 1, "SECRET_FOUND")
        assert "GitHub Token" in result.stdout
        run_check(command, cwd=ROOT, expected_returncode=0)
    assert not sample.exists()


def test_secret_invalid_encoding_is_an_input_error(tmp_path: Path) -> None:
    sample = tmp_path / "sample.txt"
    sample.write_text("clean\n", encoding="utf-8")
    command = [sys.executable, "-B", CHECK_SECRETS, sample]
    run_check(command, cwd=ROOT, expected_returncode=0)
    try:
        sample.write_bytes(b"\xff")
        run_check(
            command,
            cwd=ROOT,
            expected_returncode=2,
            diagnostic="SECRET_INPUT_ERROR",
        )
    finally:
        sample.write_text("clean\n", encoding="utf-8")
        run_check(command, cwd=ROOT, expected_returncode=0)


def test_secret_missing_tool_is_not_a_finding(tmp_path: Path) -> None:
    sample = tmp_path / "sample.txt"
    sample.write_text("clean\n", encoding="utf-8")
    run_check(
        [sys.executable, "-I", "-S", "-B", CHECK_SECRETS, sample],
        cwd=ROOT,
        expected_returncode=2,
        diagnostic="SECRET_SCANNER_MISSING",
    )


def test_cli_help(tmp_path: Path) -> None:
    run_check(
        [Path(sys.executable).with_name("dex"), "--help"],
        cwd=tmp_path,
        expected_returncode=0,
        diagnostic="usage: dex",
    )


def test_cli_unavailable_commands_fail(tmp_path: Path) -> None:
    run_check(
        [Path(sys.executable).with_name("dex"), "run"],
        cwd=tmp_path,
        expected_returncode=2,
        diagnostic="invalid choice: 'run'",
    )

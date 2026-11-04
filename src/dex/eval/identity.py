import importlib.metadata
import platform
import sys
import tomllib
from hashlib import sha256
from pathlib import Path
from typing import Any

from dex.bundle.validation import canonical


def digest(content: bytes) -> str:
    return sha256(content).hexdigest()


def engine_manifest(package: Path | None = None) -> dict[str, Any]:
    package = Path(__file__).resolve().parents[1] if package is None else package
    shared = {
        "eval/scenarios.py",
        "eval/scenario_format.py",
        "eval/scenario_output.py",
        "eval/score_execution.py",
    }
    files = {
        path.relative_to(package).as_posix(): digest(path.read_bytes())
        for path in sorted(package.rglob("*"))
        if path.is_file()
        and "__pycache__" not in path.parts
        and (
            path.relative_to(package).parts[0] not in {"eval", "demo"}
            or path.relative_to(package).as_posix() in shared
        )
    }
    project = package.parent.parent / "pyproject.toml"
    dependencies = (
        tomllib.loads(project.read_text())["project"]["dependencies"]
        if project.is_file()
        else importlib.metadata.requires("dex") or []
    )
    packages: dict[str, Any] = {}
    for requirement in dependencies:
        name = requirement.split("==")[0]
        distribution = importlib.metadata.distribution(name)
        content = {
            str(item): digest(distribution.locate_file(item).read_bytes())
            for item in distribution.files or ()
            if str(item).endswith((".py", ".so", ".pyd", "METADATA"))
        }
        packages[name] = {"version": distribution.version, "files": content}
    manifest = {
        "format": "dex-engine-content-1",
        "files": files,
        "runtime": {
            "implementation": platform.python_implementation(),
            "python": platform.python_version(),
            "cache_tag": sys.implementation.cache_tag,
            "requirements": sorted(dependencies),
            "dependencies": packages,
        },
        "selection": "All reusable dex files plus the shared scenario execution, parsing, serialization and frozen-input boundaries; evaluator, demo and reference artifacts are separate.",
    }
    return {**manifest, "identity": digest(canonical(manifest))}


def evaluator_manifest() -> dict[str, str]:
    root = Path(__file__).parent
    return {
        path.relative_to(root).as_posix(): digest(path.read_bytes())
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and path.suffix in {".py", ".json", ".md"}
        and "references" not in path.relative_to(root).parts
    }

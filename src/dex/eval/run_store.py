import os
import tempfile
from pathlib import Path
from typing import Any

from dex.bundle.model import BundleError
from dex.bundle.reader import read_file
from dex.bundle.validation import (
    canonical,
    fields,
    object_value,
    parse_json,
    relative_path,
)
from dex.eval.identity import digest


def validate_destination(out: Path) -> None:
    if out.exists() or out.is_symlink():
        raise BundleError("output_exists")
    if not out.parent.is_dir() or any(
        parent.is_symlink() for parent in (out.parent, *out.parent.parents)
    ):
        raise BundleError("output_parent: expected existing non-symlink directory")


def save_run(out: Path, artifacts: dict[str, Any]) -> dict[str, Any]:
    validate_destination(out)
    contents = {name: canonical(value) for name, value in artifacts.items()}
    manifest = {
        "format": "dex-score-run-1",
        "artifacts": {name: digest(raw) for name, raw in contents.items()},
    }
    manifest["identity"] = digest(canonical(manifest))
    contents["run.json"] = canonical(manifest)
    with tempfile.TemporaryDirectory(prefix=".dex-score-", dir=out.parent) as temporary:
        staged = Path(temporary) / "run"
        staged.mkdir()
        for name, raw in contents.items():
            relative_path(name, "run_artifact")
            (staged / name).write_bytes(raw)
        try:
            out.mkdir()
        except FileExistsError:
            raise BundleError("output_exists") from None
        try:
            staged.rename(out)
        except OSError:
            out.rmdir()
            raise
    return manifest


def read_run(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    root = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        manifest = parse_json(read_file(root, "run.json"), "run")
        fields(manifest, {"format", "artifacts", "identity"}, set(), "run")
        if manifest["format"] != "dex-score-run-1":
            raise BundleError("run_version")
        if (
            digest(
                canonical(
                    {
                        name: value
                        for name, value in manifest.items()
                        if name != "identity"
                    }
                )
            )
            != manifest["identity"]
        ):
            raise BundleError("run_identity")
        declarations = object_value(manifest["artifacts"], "run.artifacts")
        if set(os.listdir(root)) - {"run.json", "measurements.json", *declarations}:
            raise BundleError("run_undeclared_files")
        artifacts: dict[str, Any] = {}
        for name, identity in declarations.items():
            relative_path(name, "run_artifact")
            raw = read_file(root, name)
            if digest(raw) != identity:
                raise BundleError("run_artifact_changed: " + name)
            artifacts[name] = parse_json(raw, name)
        return manifest, artifacts
    finally:
        os.close(root)

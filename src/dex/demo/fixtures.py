from pathlib import Path
from typing import Any


def write_world_1_artifacts(path: Path, specification: dict[str, Any]) -> None:
    from dex.eval.world_1 import artifacts

    for name, content in artifacts(specification).items():
        destination = path / "eval" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)

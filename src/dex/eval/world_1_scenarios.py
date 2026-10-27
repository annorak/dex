import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

from dex.bundle.model import BundleError
from dex.bundle.validation import canonical, fields, object_value, parse_json
from dex.demo.build import build_world
from dex.eval.world_1 import artifacts
from dex.eval.world_1_checks import (
    key_checks,
    membership_checks,
    mistake_checks,
    packet_checks,
    path_checks,
    read_json,
    stream_checks,
    variation_checks,
)

NAMES = {
    "world1-packet-bytes",
    "world1-history-membership",
    "world1-mistake-sets",
    "world1-duplicate-snow-sets",
    "world1-stream-opening",
    "world1-key-independence",
    "world1-seed-variation",
}


def prove_key_independence(world: Path) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("fixture key attempted program execution")

    with (
        patch("dex.core.program.verify_program", forbidden),
        patch("dex.core.runtime.decide", forbidden),
        patch("dex.core.runtime.rebuild", forbidden),
        patch("dex.core.language.execute_function", forbidden),
    ):
        for slug in ("bramblewick", "fennor"):
            bundle = world / "world-1" / slug
            fixture = read_json(bundle / "eval/fixture.json")
            recreated = artifacts(fixture)
            assert (
                recreated["answer-key.json"]
                == (bundle / "eval/answer-key.json").read_bytes()
            )


def run_world1_scenario(raw: bytes, out: Path) -> int:
    try:
        specification = parse_json(raw, "world1 scenario")
        fields(
            specification,
            {"format", "scenario_id", "case", "expected"},
            {"input_world", "seed11_world"},
            "world1 scenario",
        )
        name = specification["case"]
        if name not in NAMES:
            raise BundleError("world1_unknown_scenario")
        if out.exists() or out.is_symlink():
            raise BundleError("output_exists")
        expected = object_value(specification["expected"], "expected")
        out.mkdir(parents=True, exist_ok=False)
        world = (
            Path(specification["input_world"])
            if "input_world" in specification
            else out / "world"
        )
        if "input_world" not in specification:
            build_world("world-1", 7, world)
        packet_root = Path(__file__).resolve().parents[3] / "docs/sources"
        if name == "world1-packet-bytes":
            actual = packet_checks(world, packet_root)
        elif name == "world1-history-membership":
            actual = membership_checks(world)
        elif name == "world1-mistake-sets":
            actual = mistake_checks(world)
        elif name == "world1-duplicate-snow-sets":
            actual = path_checks(world)
        elif name == "world1-stream-opening":
            actual = stream_checks(world)
        elif name == "world1-key-independence":
            prove_key_independence(world)
            actual = key_checks(world)
        else:
            seed11 = (
                Path(specification["seed11_world"])
                if "seed11_world" in specification
                else out / "seed11"
            )
            if "seed11_world" not in specification:
                build_world("world-1", 11, seed11)
            actual = variation_checks(world, seed11)
        matches = {key: actual.get(key) == value for key, value in expected.items()}
        (out / "actual.json").write_bytes(
            canonical({"scenario": name, "observed": actual, "input_world": str(world)})
        )
        (out / "expected.json").write_bytes(
            canonical({"expected": expected, "matches": matches})
        )
        print(
            canonical(
                {"scenario": name, "observed": actual, "matches": matches}
            ).decode(),
            end="",
        )
        return 0 if all(matches.values()) else 1
    except (ValueError, OSError, AssertionError) as error:
        print(
            json.dumps(
                {
                    "format": "dex-eval-error-1",
                    "code": "world1_scenario",
                    "message": str(error),
                }
            ),
            file=sys.stderr,
        )
        return 2

import json
import sys
from pathlib import Path
from typing import Any

from dex.bundle.model import BundleError
from dex.bundle.validation import canonical, fields, object_value, parse_json, text
from dex.demo.build import build_world
from dex.eval.world_2_checks import (
    change_checks,
    history_checks,
    isolation_checks,
    key_checks,
    nested_checks,
    packet_checks,
    stream_checks,
    variation_checks,
    wait_checks,
)

NAMES = {
    "world2-packet-bytes",
    "world2-history-membership",
    "world2-nested-cohorts",
    "world2-wait-schedule",
    "world2-mistake-evidence-sets",
    "world2-stream-schedule",
    "world2-isolation",
    "world2-seed-variation",
    "world2-unfamiliar-status",
    "world2-changed-summary",
}


def run_world2_scenario(raw: bytes, out: Path) -> int:
    try:
        specification = parse_json(raw, "world2 scenario")
        fields(
            specification,
            {"format", "scenario_id", "case", "expected"},
            {"input_world", "seed11_world"},
            "world2 scenario",
        )
        name = text(specification["case"], "case")
        if name not in NAMES:
            raise BundleError("world2_unknown_scenario")
        expected = object_value(specification["expected"], "expected")
        if out.exists() or out.is_symlink():
            raise BundleError("output_exists")
        supplied = (
            Path(text(specification["input_world"], "input_world"))
            if "input_world" in specification
            else None
        )
        seed11 = (
            Path(text(specification["seed11_world"], "seed11_world"))
            if "seed11_world" in specification
            else out / "seed11"
        )
        if (
            supplied is not None
            and not (supplied / "world-2/veldren/bundle.json").is_file()
        ):
            raise BundleError("world2_input_unavailable")
        if (
            "seed11_world" in specification
            and not (seed11 / "world-2/veldren/bundle.json").is_file()
        ):
            raise BundleError("world2_seed11_unavailable")
        out.mkdir(parents=True, exist_ok=False)
        world = supplied if supplied is not None else out / "world"
        if supplied is None:
            build_world("world-2", 7, world)
        actual: dict[str, Any]
        if name == "world2-packet-bytes":
            actual = packet_checks(
                world, Path(__file__).resolve().parents[3] / "docs/sources"
            )
        elif name == "world2-history-membership":
            actual = history_checks(world)
        elif name == "world2-nested-cohorts":
            actual = nested_checks(world)
        elif name == "world2-wait-schedule":
            actual = wait_checks(world)
        elif name == "world2-mistake-evidence-sets":
            actual = key_checks(world)
        elif name == "world2-stream-schedule":
            actual = stream_checks(world)
        elif name == "world2-isolation":
            actual = isolation_checks(world)
        elif name == "world2-seed-variation":
            if "seed11_world" not in specification:
                build_world("world-2", 11, seed11)
            actual = variation_checks(world, seed11)
        else:
            actual = change_checks(world, name)
        matches = {key: actual.get(key) == value for key, value in expected.items()}
        (out / "actual.json").write_bytes(
            canonical(
                {
                    "scenario": name,
                    "observed": actual,
                    "input_world": str(world),
                    "status": "fixture_requirements",
                    "execution_claimed": False,
                }
            )
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
                    "code": "world2_scenario",
                    "message": str(error),
                }
            ),
            file=sys.stderr,
        )
        return 2

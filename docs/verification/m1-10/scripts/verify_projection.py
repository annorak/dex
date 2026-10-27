import argparse
import hashlib
import json
import os
import statistics
from pathlib import Path
import subprocess

CUTOFF = "2026-10-01T00:00:00+00:00"
NAMES = [
    "projection-learning", "projection-quarter-boundary", "projection-exam-recording",
    "projection-mixed-export", "projection-future-delivery", "projection-evaluator-leak",
    "projection-root-capability", "projection-derived-leak", "projection-no-history",
    "projection-self-contained",
]
EXPECTED = [
    {"cases": ["learning-case"], "available_only": True},
    {"cases": ["learning-case"], "complete_case_cohort": True},
    {"recordings": ["learn-recording"], "exam_excluded": True},
    {"records": ["record:2"], "original_private": True, "citation_preserved": True},
    {"before": ["learning-case"], "after": ["learning-case", "future-case"], "availability_wins": True},
    {"planted_refusals": 5, "evaluator_excluded": True},
    {"planted_refusals": 2, "root_inaccessible": True},
    {"planted_refusals": 24, "destinations": 6},
    {"no_history": True, "incomplete_preserved": True, "invented_claims": False},
    {"independent": True, "authority_unchanged": True},
]


def input_root(root):
    return Path(config.get("input_root", root / "frozen"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(path):
    if not path.exists() and not path.is_symlink():
        return None
    if path.is_symlink():
        return {"symlink": os.readlink(path)}
    if path.is_file():
        return {"sha256": digest(path)}
    return {str(p.relative_to(path)): snapshot(p) for p in sorted(path.iterdir())}


def save(path, value):
    content = json.dumps(value, indent=2, sort_keys=True) + "\n"
    with path.open("x") as stream:
        stream.write(content)


def receipt(root, checkout, label, command):
    target = root / (label + ".txt")
    result = subprocess.run(
        ["/usr/bin/python3", config["tools"]["recorder"], "--cwd", str(checkout),
         "--out", str(target), "--", *command], check=False,
    )
    text = target.read_text()
    header = json.JSONDecoder().raw_decode(text)[0]
    expected = config["head"] if str(checkout) == config["checkouts"]["head"] else config["base"]
    assert header["revision"] == expected, header
    body = text.split("\nSTDOUT\n", 1)[1]
    stdout, body = body.split("\nSTDERR\n", 1)
    stderr, trailer = body.rsplit("\nRESULT\n", 1)
    status = json.loads(trailer)["exit_status"]
    assert result.returncode == status
    return status, stdout, stderr


def launch(checkout, args, timed=False):
    command = [
        "/usr/bin/env", "-u", "PYTHONPATH", "-u", "VIRTUAL_ENV",
        "UV_OFFLINE=1", "UV_CACHE_DIR=" + config["tools"]["cache"],
        "PATH=" + os.pathsep.join([str(checkout / ".venv/bin"),
                                  str(Path(config["tools"]["uv"]).parent), "/usr/bin", "/bin"]),
    ]
    if timed:
        command += [config["tools"]["python"], config["tools"]["timer"], "--"]
    return command + [config["tools"]["uv"], "run", "--locked", *args]


def check_project(root, checkout, label, argv, workspace, want, reason):
    source = Path(argv[2])
    destination = Path(argv[argv.index("--out") + 1])
    before = {"source": snapshot(source), "workspace": snapshot(workspace),
              "destination": snapshot(destination)}
    status, stdout, stderr = receipt(root, checkout, label, launch(checkout, ["dex", *argv]))
    assert status == want, (label, status, stdout, stderr)
    assert snapshot(source) == before["source"]
    assert snapshot(workspace) == before["workspace"]
    if want:
        assert status != 0 and not stdout
        assert json.loads(stderr)["code"] == reason
        assert snapshot(destination) == before["destination"]
    else:
        assert json.loads(stdout) == {
            "format": "dex-bundle-project-1", "consumer": "learning",
            "as_of": argv[argv.index("--as-of") + 1],
        }
        assert not stderr
        assert sorted(p.name for p in destination.iterdir()) == ["view.json"]
        view = json.loads((destination / "view.json").read_bytes())
        assert view["format_version"] == "dex-learning-view-1"
    save(root / (label + "-state.json"), {"before": before, "after": {
        "source": snapshot(source), "workspace": snapshot(workspace),
        "destination": snapshot(destination),
    }})


def validate_saved(path, scenario, original):
    content = (path / "view.json").read_bytes()
    view = json.loads(content)
    assert set(view) == {"format_version", "consumer", "bundle_id", "company_id",
                         "as_of", "history", "sources", "deliveries", "cases", "recordings"}
    assert all(token not in content for token in [
        b"exam-case", b"exam-only", b"exam-event", b"exam-outcome", b"exam-recording",
        b"compile-aggregate", b"evaluator-only", str(original).encode(),
    ])
    if view["as_of"] < "2027":
        assert b"future-only" not in content and b"future notice" not in content
        assert all(source["source_id"] != "future.txt" for source in view["sources"])
    if scenario != "projection-no-history":
        wanted = ["learning-case", "future-case"] if view["as_of"] >= "2027" else ["learning-case"]
        assert [case["case_id"] for case in view["cases"]] == wanted
    table = next((source for source in view["sources"] if source["source_id"] == "mixed.csv"), None)
    if table:
        wanted = ["record:2", "record:4"] if view["as_of"] >= "2027" else ["record:2"]
        assert [record["locator"] for record in table["records"]] == wanted
        assert "Café 🦉 learning" in json.dumps(table["records"][0]["values"], ensure_ascii=False)
        original_quote = table["passages"][0]["original"]["value"]
        projected = table["passages"][0]["projected"]["value"]
        assert original_quote["quote"] == projected["quote"] == "Café 🦉 learning"
        assert (original_quote["start"], original_quote["end"]) == (6, 21)
        assert (projected["start"], projected["end"]) == (0, 15)
        assert original_quote["pin"] != projected["pin"]
    if scenario == "projection-exam-recording":
        assert [recording["recording_id"] for recording in view["recordings"]] == ["learn-recording"]
    if scenario == "projection-quarter-boundary":
        events = view["cases"][0]["observations"]
        assert [event["observation_id"] for event in events] == ([] if view["as_of"].startswith("2026-07") else ["learn-event"])
    if scenario == "projection-no-history":
        assert view["history"] == {"kind": "none"} or view["history"]["adequacy"]["decision"] == "incomplete"
        assert all(token not in content for token in [b"replay_score", b"exam_score", b"adequate_history"])


def prepare(root, checkout):
    frozen = input_root(root)
    frozen.mkdir()
    code = (
        "from pathlib import Path; from dex.eval.projection_fixture import prepare_size,projection_bundle;"
        "projection_bundle(Path(" + repr(str(frozen / "learning-bundle")) + "));"
        "prepare_size(Path(" + repr(str(frozen / "size-bundle")) + "))"
    )
    command = launch(checkout, [])[:-3] + [str(checkout / ".venv/bin/python"), "-c", code]
    status, _, _ = receipt(root, checkout, "022-prepare-frozen-bundles", command)
    assert status == 0
    for name in NAMES + ["projection-size-10000"]:
        value = json.loads((checkout / "tests/scenarios" / (name + ".json")).read_bytes())
        if name in {"projection-learning", "projection-size-10000"}:
            value["input_bundle"] = str(frozen / ("size-bundle" if name.endswith("10000") else "learning-bundle"))
        save(frozen / (name + ".json"), value)
    config["inputs"] = snapshot(frozen)
    steps = [{"label": "cold-trunk-help", "checkout": "trunk", "kind": "help"}]
    for baseline in ["trunk", "parent"]:
        for pair in range(1, 6):
            sides = [baseline, "head"] if pair % 2 else ["head", baseline]
            for side in sides:
                steps.append({"label": f"startup-{baseline}-pair-{pair}-{side}",
                              "checkout": side, "kind": "help"})
    for baseline in ["trunk", "parent"]:
        for name, bundle in [("projection-learning", "learning-bundle"),
                             ("projection-size-10000", "size-bundle")]:
            steps.append({"label": baseline + "-" + name, "checkout": baseline,
                          "kind": "unsupported-scenario", "scenario": name})
            steps.append({"label": baseline + "-" + name + "-project", "checkout": baseline,
                          "kind": "unsupported-project", "bundle": bundle})
    steps.append({"label": "head-projection-learning", "checkout": "head",
                  "kind": "regression-head", "scenario": "projection-learning"})
    for sample in range(1, 6):
        steps.append({"label": f"size-head-{sample}", "checkout": "head",
                      "kind": "size", "scenario": "projection-size-10000"})
    config["schedule"] = steps
    config["method"] = {
        "timer": config["tools"]["timer"], "timer_sha256": digest(Path(config["tools"]["timer"])),
        "recorder": config["tools"]["recorder"],
        "recorder_sha256": digest(Path(config["tools"]["recorder"])), "cold": "First CLI invocation after dependency setup. OS caches remain.",
        "regression_ceiling": 1.20, "processing_seconds": 10,
        "completion_seconds": 20, "rss_bytes": 536870912,
        "barrier": "Root explicitly releases CPU after both reviewers finish.",
        "samples": "No replacement, discarded, or unrecorded formal sample.",
    }
    proposed = json.dumps(config, indent=2, sort_keys=True) + "\n"
    print("--- /dev/null\n+++ frozen-config.json\n" + "".join("+" + line + "\n" for line in proposed.splitlines()), flush=True)
    save(root / "frozen-config.json", config)


def live(root, checkout):
    results = []
    gates = [] if args.skip_gates else [
        ("023-repository-gates", ["make", "check"]),
        ("024-projection-focused", [config["tools"]["uv"], "run", "--locked", "pytest", "tests/bundle/test_projection.py", "-q"]),
    ]
    for label, command_args in gates:
        command = launch(checkout, [])[:-3] + command_args
        status, _, _ = receipt(root, checkout, label, command)
        assert status == 0
    results.append({"outcome": "repository-gates", "verdict": "PASS"})
    for number, name in enumerate(NAMES, 1):
        if not args.first_lane <= number <= args.last_lane:
            continue
        out = root / "live" / name
        scenario = input_root(root) / (name + ".json")
        label = f"lane-{number:02d}-{name}"
        status, stdout, stderr = receipt(root, checkout, label, launch(
            checkout, ["dex", "eval", "--scenario", str(scenario), "--out", str(out)]))
        assert status == 0 and not stderr, (status, stdout, stderr)
        actual = json.loads((out / "actual.json").read_bytes())
        expected = json.loads((out / "expected.json").read_bytes())
        assert actual["observed"] == EXPECTED[number - 1], actual
        assert expected["expected"] == EXPECTED[number - 1]
        assert expected["matches"] and all(expected["matches"].values())
        assert json.loads(stdout)["observed"] == actual["observed"]
        for index, check in enumerate(actual["checks"], 1):
            assert check["argv"][:3] == ["uv", "run", "dex"]
            check_project(root, checkout, label + f"-emitted-{index}",
                          check["argv"][3:], out / "workspace.sqlite",
                          check["exit_status"], check["reason"])
        for path in sorted(out.glob("*/view.json")):
            validate_saved(path.parent, name, out / "bundle")
        if name == "projection-derived-leak":
            for target in ["prompt", "diagnostic", "cache", "training_test", "compiler_recording"]:
                content = (out / (target + ".json")).read_bytes()
                assert b"learning-case" in content
                assert all(token not in content for token in [b"exam-case", b"future.txt", b"eval/"])
            assert len(json.loads((out / "boundary-refusals.json").read_bytes())) == 24
        results.append({"outcome": name, "verdict": "PASS", "emitted": len(actual["checks"])})
        save(root / (label + "-validated.json"), results[-1])
    save(root / f"live-outcomes-{args.first_lane}-{args.last_lane}.json", results)


def performance(root):
    assert snapshot(input_root(root)) == config["inputs"]
    save(root / "performance-start-state.json", {"inputs": config["inputs"], "head": config["head"]})
    measurements = []
    for step in config["schedule"]:
        checkout = Path(config["checkouts"][step["checkout"]])
        out = root / "performance" / step["label"]
        kind = step["kind"]
        if kind == "help":
            args = ["dex", "--help"]
        elif kind == "unsupported-project":
            args = ["dex", "bundle", "project", str(input_root(root) / step["bundle"]),
                    "--consumer", "learning", "--as-of", CUTOFF, "--out", str(out)]
        else:
            args = ["dex", "eval", "--scenario", str(input_root(root) / (step["scenario"] + ".json")),
                    "--out", str(out)]
        timed = kind in {"help", "size"}
        status, stdout, stderr = receipt(root, checkout, step["label"], launch(checkout, args, timed))
        if kind == "regression-head":
            assert status == 0 and not stderr
            actual = json.loads((out / "actual.json").read_bytes())
            assert actual["observed"] == EXPECTED[0]
            assert all(json.loads((out / "expected.json").read_bytes())["matches"].values())
            validate_saved(out / "view", "projection-learning", input_root(root) / "learning-bundle")
            for index, check in enumerate(actual["checks"], 1):
                check_project(root, checkout, f"regression-head-emitted-{index}",
                              check["argv"][3:], out / "workspace.sqlite", 0, None)
            save(root / "regression-lane1-validated.json", {"outcome": "projection-learning", "verdict": "PASS"})
            continue
        if not timed:
            assert status == 2 and not out.exists(), (step, status, stdout, stderr)
            assert (json.loads(stderr)["code"] == "scenario_error" if kind == "unsupported-scenario" else "invalid choice: 'project'" in stderr), stderr
            continue
        assert status == 0, (step, status, stdout, stderr)
        marker = [line for line in stderr.splitlines() if line.startswith("MEASUREMENT ")]
        assert len(marker) == 1
        measurement = json.loads(marker[0].removeprefix("MEASUREMENT "))
        assert measurement["clock_valid"] and measurement["exit_status"] == 0
        if kind == "size":
            processing = json.loads((out / "timing.json").read_bytes())["processing_seconds"]
            actual = json.loads((out / "actual.json").read_bytes())
            assert actual["observed"]["input_cases"] == 10000
            assert actual["observed"]["learning_cases"] == actual["observed"]["records"] == 8000
            view = json.loads((out / "view/view.json").read_bytes())
            assert [case["case_id"] for case in view["cases"]] == [f"case-{n:05d}" for n in range(8000)]
            assert len(view["sources"][1]["records"]) == 8000
            for n, record in enumerate(view["sources"][1]["records"]):
                assert record["locator"] == f"record:{n + 2}"
                assert f"record-{n:05d}" in json.dumps(record["values"])
            content = (out / "view/view.json").read_bytes()
            assert all(value not in content for value in [b"case-08000", b"record-08000", b"future notice", b"evaluator-only"])
            measurement["processing_seconds"] = processing
        measurements.append({"step": step, "measurement": measurement})
    assert snapshot(input_root(root)) == config["inputs"]
    save(root / "measurements.json", measurements)
    comparisons = {}
    for baseline in ["trunk", "parent"]:
        sides = {}
        for side in [baseline, "head"]:
            rows = [row["measurement"] for row in measurements
                    if row["step"]["label"].startswith("startup-" + baseline + "-")
                    and row["step"]["checkout"] == side]
            assert len(rows) == 5
            sides[side] = {metric: {
                "median": statistics.median(row[metric] for row in rows),
                "min": min(row[metric] for row in rows),
                "max": max(row[metric] for row in rows),
            } for metric in ["wall_seconds", "max_rss_bytes"]}
        ratios = {metric: sides["head"][metric]["median"] / sides[baseline][metric]["median"]
                  for metric in ["wall_seconds", "max_rss_bytes"]}
        comparisons[baseline] = {"sides": sides, "ratios": ratios,
                                 "pass": all(value <= 1.20 for value in ratios.values())}
    sizes = [row["measurement"] for row in measurements if row["step"]["kind"] == "size"]
    assert len(sizes) == 5
    budgets = all(row["processing_seconds"] <= 10 and row["wall_seconds"] <= 20
                  and row["max_rss_bytes"] <= 536870912 for row in sizes)
    save(root / "performance-results.json", {
        "comparisons": comparisons, "absolute_limits_pass": budgets,
        "size_samples": sizes,
        "pass": budgets and all(value["pass"] for value in comparisons.values()),
    })
    for sample in range(1, 6):
        out = root / "performance" / f"size-head-{sample}"
        actual = json.loads((out / "actual.json").read_bytes())
        assert len(actual["checks"]) == 1
        check = actual["checks"][0]
        check_project(root, Path(config["checkouts"]["head"]), f"size-head-{sample}-emitted",
                      check["argv"][3:], out / "workspace.sqlite", 0, None)
    assert budgets and all(value["pass"] for value in comparisons.values())


parser = argparse.ArgumentParser()
modes = parser.add_subparsers(dest="mode", required=True)
prepare_parser = modes.add_parser("prepare")
for option in ["root", "checkout", "trunk", "parent", "cache", "history", "uv", "python"]:
    prepare_parser.add_argument("--" + option, type=Path, required=True)
for option in ["base", "head"]:
    prepare_parser.add_argument("--" + option, required=True)
live_parser = modes.add_parser("live")
live_parser.add_argument("--root", type=Path, required=True)
live_parser.add_argument("--skip-gates", action="store_true")
live_parser.add_argument("--first-lane", type=int, default=1)
live_parser.add_argument("--last-lane", type=int, default=10)
live_parser.add_argument("--config", type=Path)
performance_parser = modes.add_parser("performance")
performance_parser.add_argument("--root", type=Path, required=True)
performance_parser.add_argument("--config", type=Path)
args = parser.parse_args()
root = args.root.resolve()
if args.mode == "prepare":
    config = {"base": args.base, "head": args.head, "checkouts": {
        "head": str(args.checkout.resolve()), "trunk": str(args.trunk.resolve()),
        "parent": str(args.parent.resolve()),
    }, "tools": {
        "python": str(args.python.resolve()), "uv": str(args.uv.resolve()),
        "cache": str(args.cache.resolve()), "recorder": str(args.history.resolve() / "record.py"),
        "timer": str(args.history.resolve() / "measure.py"),
    }}
    prepare(root, args.checkout.resolve())
else:
    config = json.loads((args.config or root / "frozen-config.json").read_bytes())
    assert snapshot(input_root(root)) == config["inputs"]
    if args.mode == "live":
        live(root, Path(config["checkouts"]["head"]))
    else:
        performance(root)

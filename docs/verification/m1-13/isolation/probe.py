import argparse
import builtins
import fcntl
import importlib
import importlib.abc
import io
import json
import os
import shutil
import socket
import subprocess
import sys
from dataclasses import dataclass, replace
from datetime import date, datetime
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch


def digest(raw):
    return sha256(raw).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def tree(path):
    return {item.relative_to(path).as_posix(): digest(item.read_bytes())
            for item in sorted(path.rglob("*")) if item.is_file()}


def revision(repo, expected, allow_dirty):
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, text=True)
    assert head == expected, (head, expected)
    assert allow_dirty or not status, status
    return {"head": head, "working_tree_status": status, "formal": not allow_dirty}


def guarded_report(repo, run):
    blocked = (
        "dex.demo", "dex.eval.admission", "dex.eval.scoring",
        "dex.eval.score_execution", "dex.eval.score_scenarios",
        "dex.eval.score_fixtures", "dex.eval.scenarios",
    )

    class ImportGuard(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if any(fullname == name or fullname.startswith(name + ".") for name in blocked):
                raise AssertionError("report imported forbidden module: " + fullname)
            return None

    run = run.resolve()
    code_roots = tuple(path.resolve() for path in
                       (repo / "src", Path(sys.prefix), Path(sys.base_prefix)))
    opened = []
    original_os, original_builtin, original_io = os.open, builtins.open, io.open

    def check_path(raw, options):
        if isinstance(raw, int):
            return
        path = Path(os.fsdecode(raw))
        if not path.is_absolute() and options.get("dir_fd") is not None:
            descriptor = options["dir_fd"]
            if sys.platform == "darwin":
                parent = fcntl.fcntl(descriptor, 50, bytes(1024)).split(b"\0", 1)[0]
                path = Path(os.fsdecode(parent)) / path
            else:
                path = Path(os.readlink("/proc/self/fd/" + str(descriptor))) / path
        path = path.absolute()
        in_run = path == run or path.is_relative_to(run)
        in_code = path.suffix in {".py", ".pyc", ".so", ".pyd"} and any(
            path.is_relative_to(root) for root in code_roots)
        assert in_run or in_code, "report read outside run/code: " + str(path)
        if in_run:
            opened.append(path.relative_to(run).as_posix())

    def guarded_os(raw, flags, *args, **kwargs):
        check_path(raw, kwargs)
        return original_os(raw, flags, *args, **kwargs)

    def guarded_builtin(raw, *args, **kwargs):
        check_path(raw, kwargs)
        return original_builtin(raw, *args, **kwargs)

    def guarded_io(raw, *args, **kwargs):
        check_path(raw, kwargs)
        return original_io(raw, *args, **kwargs)

    mutations = {
        "os.remove", "os.rename", "os.rmdir", "os.mkdir", "os.link", "os.symlink",
        "os.chmod", "os.chown", "os.truncate", "os.utime", "os.system",
        "os.fork", "os.posix_spawn", "subprocess.Popen",
    }

    def audit(event, args):
        if event.startswith("socket.") or event in mutations:
            raise AssertionError("report attempted forbidden action: " + event)
        if event == "open":
            _, mode, flags = args
            assert not (flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)), "report attempted write"
            assert mode is None or not any(value in mode for value in "wax+"), "report attempted write"

    sys.meta_path.insert(0, ImportGuard())
    sys.addaudithook(audit)
    with patch("os.open", guarded_os), patch("builtins.open", guarded_builtin), patch("io.open", guarded_io):
        controls = (
            lambda: importlib.import_module("dex.eval.scoring"),
            lambda: socket.socket(),
            lambda: builtins.open(run / "forbidden-write", "x"),
            lambda: builtins.open(repo / "pyproject.toml", "rb"),
        )
        for control in controls:
            try:
                control()
            except AssertionError:
                pass
            else:
                raise AssertionError("report guard control did not reject")
        opened.clear()
        from dex.cli import main
        sys.argv = ["dex", "report", str(run)]
        try:
            main()
        finally:
            print(json.dumps({"guarded_run_reads": sorted(set(opened))}), file=sys.stderr)


def report_probe(args):
    before = tree(args.run)
    args.out.mkdir()
    results = []
    for number in (1, 2):
        argv = [sys.executable, "-B", str(Path(__file__).resolve()), "report-child",
                "--repo", str(args.repo), "--head", args.head, "--run", str(args.run)]
        if args.allow_dirty:
            argv.append("--allow-dirty")
        result = subprocess.run(argv, capture_output=True, timeout=30)
        (args.out / f"report-{number}.stdout").write_bytes(result.stdout)
        (args.out / f"report-{number}.stderr").write_bytes(result.stderr)
        write_json(args.out / f"report-{number}.command.json",
                   {"argv": argv, "exit_status": result.returncode})
        results.append(result)
    assert all(result.returncode == 0 for result in results), [
        (result.returncode, result.stderr.decode()) for result in results]
    assert results[0].stdout == results[1].stdout, "fresh report bytes changed"
    assert tree(args.run) == before, "report mutated the run"
    report = json.loads(results[0].stdout)
    summary = {"report_sha256": digest(results[0].stdout),
               "run_identity": report["run_identity"], "fresh_processes": 2,
               "run_files_unchanged": before, "forbidden_imports_network_writes": True}
    write_json(args.out / "result.json", summary)
    return summary


@dataclass
class LocalDistribution:
    root: Path
    version: str
    files: tuple[Path, ...]

    def locate_file(self, item):
        return self.root / item


def identity_probe(args):
    from dex.eval import identity

    args.out.mkdir()
    project = args.out / "snapshot"
    package = project / "src/dex"
    shutil.copytree(args.repo / "src/dex", package, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copyfile(args.repo / "pyproject.toml", project / "pyproject.toml")
    baseline = identity.engine_manifest(package)
    write_json(args.out / "baseline.json", baseline)
    results = {}
    engine_files = (
        "core/runtime.py", "workspace.py", "workspace_command.py", "codec.py",
        "recordings.py", "verification.py", "bundle/history.py", "adapters/__init__.py",
        "eval/scenarios.py", "eval/scenario_format.py", "eval/scenario_output.py",
        "eval/score_execution.py",
    )
    for name in engine_files:
        assert name in baseline["files"], name
        path = package / name
        original = path.read_bytes()
        try:
            path.write_bytes(original + b"\n# independent identity probe\n")
            changed = identity.engine_manifest(package)
            assert changed["identity"] != baseline["identity"], name
            results[name] = changed["identity"]
        finally:
            path.write_bytes(original)
    added = package / "future_engine_helper.py"
    added.write_text("VALUE = 1\n")
    changed = identity.engine_manifest(package)
    assert "future_engine_helper.py" in changed["files"]
    assert changed["identity"] != baseline["identity"]
    results["new_engine_module"] = changed["identity"]
    added.unlink()
    with patch.object(identity, "__file__", str(package / "eval/identity.py")):
        evaluator_before = identity.evaluator_manifest()
        added = package / "eval/independent_evaluator.py"
        added.write_text("VALUE = 1\n")
        assert identity.engine_manifest(package)["identity"] == baseline["identity"]
        assert identity.evaluator_manifest() != evaluator_before
        results["evaluator_separate"] = True
        added.unlink()
        reference = package / "eval/references/independent_reference.py"
        reference.parent.mkdir(exist_ok=True)
        reference.write_text("VALUE = 2\n")
        assert identity.engine_manifest(package)["identity"] == baseline["identity"]
        assert identity.evaluator_manifest() == evaluator_before
        results["reference_separate_sha256"] = digest(reference.read_bytes())
    evidence = project / "evidence.txt"
    evidence.write_text("Independent evidence is outside the engine package.\n")
    assert identity.engine_manifest(package)["identity"] == baseline["identity"]
    results["evidence_separate"] = True
    distributions = {}
    for name, declaration in baseline["runtime"]["dependencies"].items():
        root = args.out / "dependencies" / name
        root.mkdir(parents=True)
        (root / "runtime.py").write_text("VALUE = 1\n")
        (root / "METADATA").write_text("Name: " + name + "\n")
        distributions[name] = LocalDistribution(root, declaration["version"], (Path("runtime.py"), Path("METADATA")))
    with patch.object(identity.importlib.metadata, "distribution", side_effect=distributions.__getitem__):
        dependency_baseline = identity.engine_manifest(package)["identity"]
        for name, distribution in distributions.items():
            path = distribution.root / "runtime.py"
            path.write_text("VALUE = 2\n")
            assert identity.engine_manifest(package)["identity"] != dependency_baseline
            path.write_text("VALUE = 1\n")
            version = distribution.version
            distribution.version = version + ".probe"
            assert identity.engine_manifest(package)["identity"] != dependency_baseline
            distribution.version = version
            assert identity.engine_manifest(package)["identity"] == dependency_baseline
            results["dependency/" + name] = {"content_changes_identity": True, "version_changes_identity": True}
    write_json(args.out / "result.json", results)
    return results


def projection_probe(args):
    from dex.bundle.model import BundleError
    from dex.bundle.projection import (
        EvidenceRef,
        decode_learning_view,
        materialize_learning,
        serialize_learning_inputs,
    )
    from dex.bundle.reader import load_bundle
    from dex.bundle.validation import canonical
    from dex.core import program as p
    from dex.eval.score_execution import execute_frozen, freeze_execution

    def execute_without_files(content):
        with patch("builtins.open", side_effect=AssertionError("execution file open")), \
             patch("io.open", side_effect=AssertionError("execution file open")), \
             patch("os.open", side_effect=AssertionError("execution file open")):
            return execute_frozen(content)

    args.out.mkdir()
    root = args.out / "bundle"
    (root / "sources").mkdir(parents=True)
    (root / "eval").mkdir()
    contents = {
        "guide": b"1. Return the value. Before July 1 use 10; on July 1 use 20.\n",
        "mixed": b"Value\nLEARNING-INPUT\nEXAM-INPUT\nFUTURE-INPUT\n",
        "future": b"FUTURE-NOTICE\n",
        "observation": b"IMPORTED-APPROVAL-ONLY actor=controller complete=true\n",
    }
    initial = "2026-01-01T00:00:00+00:00"
    cutoff = "2026-10-01T00:00:00+00:00"
    sources, refs = [], {}
    for name, content in contents.items():
        refs[name] = {"source_id": name, "revision_id": "r1"}
        path = "sources/" + name + (".csv" if name == "mixed" else ".txt")
        (root / path).write_bytes(content)
        observed = "2026-07-03T00:00:00+00:00" if name == "observation" else initial
        available = {"future": "2027-01-01T00:00:00+00:00",
                     "observation": "2026-07-04T00:00:00+00:00"}.get(name, initial)
        source = {**refs[name], "path": path, "media_type": "text/csv" if name == "mixed" else "text/plain",
                  "sha256": digest(content), "origin": {"kind": "file", "snapshot": "packet"},
                  "observed_at": observed, "available_at": available}
        if name == "mixed":
            source["origin"] = {
                "kind": "export",
                "export_id": "mixed-export",
                "source_system": "fixture-system",
            }
            source["mapping"] = {"version": "m1", "confirmed_by": "employee", "confirmed_at": initial,
                                 "effective_from": "2020-01-01", "effective_until": None,
                                 "columns": [{"source": "Value", "target": "value", "kind": "text"}]}
        sources.append(source)
    deliveries = [{"delivery_id": name + "-delivery", "sources": [refs[name]],
                   "received_at": source["observed_at"], "available_at": source["available_at"],
                   "origin": {"kind": "file", "snapshot": "packet"}}
                  for name, source in zip(contents, sources, strict=True)]
    cases = []
    for name, opened, business, row in (
        ("learning-case", "2026-06-30T23:59:59+00:00", "2026-06-30", 2),
        ("exam-case", "2026-07-01T00:00:00+00:00", "2026-06-30", 3),
        ("future-case", "2027-01-01T00:00:00+00:00", "2027-01-01", 4),
    ):
        cases.append({"case_id": name, "delivery_id": "mixed-delivery", "opened_at": opened,
                      "business_date": business, "inputs": [refs["mixed"]],
                      "facts": [{"name": "value", "source": refs["mixed"], "record": "record:" + str(row), "column": "value"}],
                      "observations": []})
    cases[1]["observations"] = [{"observation_id": "imported-approval", "source": refs["observation"],
                                "locator": "text", "actor": "controller",
                                "occurred_at": "2026-07-02T00:00:00+00:00",
                                "observed_at": "2026-07-03T00:00:00+00:00",
                                "available_at": "2026-07-04T00:00:00+00:00", "mapping_version": "text-1"}]
    manifest = {"format_version": "dex-company-bundle-1", "bundle_id": "isolation-packet",
                "company_id": "isolation-company", "sources": sources, "deliveries": deliveries,
                "history": {"kind": "interval", "start": "2025-10-01T00:00:00+00:00", "end": cutoff,
                            "opening_event": "received", "adequacy": {"decision": "usable", "actor": "employee", "decided_at": initial},
                            "cases": cases[:2]}, "cases": cases[2:], "recordings": []}
    (root / "bundle.json").write_bytes(canonical(manifest))
    (root / "eval/answer-key.json").write_bytes(b'{"expected":"EVALUATOR-SECRET"}\n')
    bundle = load_bundle(root)
    view = materialize_learning(bundle, datetime.fromisoformat(cutoff))
    assert {case["case_id"] for case in json.loads(view.content)["cases"]} == {"learning-case"}
    for marker in (b"EXAM-INPUT", b"FUTURE-INPUT", b"FUTURE-NOTICE", b"EVALUATOR-SECRET", b"IMPORTED-APPROVAL-ONLY"):
        assert marker not in view.content, marker
    source = next(item for item in view.catalog.entries if item.pin.source == "guide")
    section = source.sections[0]
    citation = p.Citation(source.pin, section.name, section.locator, section.start, section.end,
                          source.text[section.start:section.end])
    function = p.FunctionDeclaration("identity", (p.Field("value", p.Scalar.TEXT),), p.Scalar.TEXT,
                                    p.FunctionBody("restricted-1", "return value"),
                                    (p.FunctionTest("saved", (p.NamedValue("value", p.TextValue("checked")),), p.TextValue("checked")),))
    metadata = p.StepMetadata("return", "text-1", "Return the input", (citation,),
                              (p.Binding("value", p.Scalar.TEXT, p.ProgramInputRef("value")),), p.Scalar.TEXT)
    draft = p.ProgramDraft("isolation", "r1", (), (p.Field("value", p.Scalar.TEXT),),
                           p.CodeStep(metadata, "identity"), (function,), (), ())
    frozen = freeze_execution(bundle, draft, view, "exam", cutoff)
    data = json.loads(frozen)
    assert set(data["cases"]) == {"exam-case"}
    assert data["cases"]["exam-case"]["business_date"] == "2026-06-30"
    assert b"EXAM-INPUT" not in data["programs"]["r1"]["sources"].encode()
    for marker in (b"FUTURE-INPUT", b"FUTURE-NOTICE", b"EVALUATOR-SECRET", b"IMPORTED-APPROVAL-ONLY", str(root).encode()):
        assert marker not in frozen, marker
    for destination in ("prompt", "diagnostic", "cache", "training_test", "compiler_recording", "library"):
        try:
            serialize_learning_inputs(view, (EvidenceRef(bundle.company_id, "case", ("exam-case",)),), destination, bundle.company_id)
        except BundleError:
            pass
        else:
            raise AssertionError("exam evidence entered " + destination)
    forged = json.loads(view.content)
    forged["cases"] = []
    forged_view = decode_learning_view(canonical(forged))
    try:
        freeze_execution(bundle, draft, forged_view, "exam", cutoff)
    except BundleError as error:
        assert str(error) == "execution_projection_identity", str(error)
    else:
        raise AssertionError("substituted same-ID view admitted")
    actual = execute_without_files(frozen)
    assert actual["exam-case"]["decision"] == {"kind": "text", "value": "EXAM-INPUT"}
    assert actual["exam-case"]["effects"] == actual["exam-case"]["waits"] == []
    integer_function = replace(function, inputs=(p.Field("value", p.Scalar.INTEGER),), output=p.Scalar.INTEGER,
                               tests=(p.FunctionTest("saved", (p.NamedValue("value", p.IntValue(1)),), p.IntValue(1)),))
    integer_metadata = replace(metadata, behavior_id="date-1", inputs=(p.Binding("value", p.Scalar.INTEGER, p.RuleInputRef("limit", ())),), output=p.Scalar.INTEGER)
    rules = (p.DatedRule("before", "limit", (), date(2020, 1, 1), date(2026, 7, 1), p.Export(p.Scalar.INTEGER, p.Literal(p.IntValue(10))), (citation,)),
             p.DatedRule("after", "limit", (), date(2026, 7, 1), None, p.Export(p.Scalar.INTEGER, p.Literal(p.IntValue(20))), (citation,)))
    dated = replace(draft, revision="r2", root=p.CodeStep(integer_metadata, "identity"), functions=(integer_function,), rules=rules)
    dated_frozen = freeze_execution(bundle, dated, view, "exam", cutoff)
    first = execute_without_files(dated_frozen)["exam-case"]["decision"]
    changed = json.loads(dated_frozen)
    changed["cases"]["exam-case"]["business_date"] = "2026-07-01"
    second = execute_without_files(canonical(changed))["exam-case"]["decision"]
    assert first == {"kind": "integer", "value": 10}, first
    assert second == {"kind": "integer", "value": 20}, second
    (args.out / "learning.json").write_bytes(view.content)
    (args.out / "frozen.json").write_bytes(frozen)
    (args.out / "frozen-dated.json").write_bytes(dated_frozen)
    summary = {"learning_cases": ["learning-case"], "exam_cases": ["exam-case"],
               "business_date_result": first, "changed_date_result": second,
               "same_id_projection_substitution": "rejected", "restricted_learning_destinations": "rejected",
               "imported_approval_effects": [], "input_sha256": digest(frozen)}
    write_json(args.out / "result.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("report", "report-child", "identity", "projection"))
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--run", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    args.repo = args.repo.resolve()
    if args.run is not None:
        args.run = args.run.resolve()
    pin = revision(args.repo, args.head, args.allow_dirty)
    sys.path.insert(0, str(args.repo / "src"))
    sys.dont_write_bytecode = True
    if args.mode == "report-child":
        assert args.run is not None
        guarded_report(args.repo, args.run)
        return
    assert args.out is not None and not args.out.exists()
    if args.mode == "report":
        assert args.run is not None
        result = report_probe(args)
    elif args.mode == "identity":
        result = identity_probe(args)
    else:
        result = projection_probe(args)
    print(json.dumps({"revision": pin, "result": result}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

import argparse
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tokenize
from collections import Counter
from pathlib import Path

from probe_contracts import RESULTS, check, exact, rejected


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":")) + "\n").encode()


def mutate_evaluator(source, target, artifact, change):
    shutil.copytree(source, target)
    path = target / artifact
    raw = path.read_bytes()
    value = change(json.loads(raw)) if artifact != "response-scripts.json" else None
    content = canonical(value) if value is not None else b"not JSON\n"
    path.write_bytes(content)
    manifest = json.loads((target / "manifest.json").read_bytes())
    manifest["artifacts"][artifact] = hashlib.sha256(content).hexdigest()
    (target / "manifest.json").write_bytes(canonical(manifest))


def replace_field(field, value):
    def mutate(document):
        document[sorted(document)[0]][field] = value
        return document
    return mutate


def admission_checks(args):
    from dex.bundle.reader import load_bundle
    from dex.eval.admission import load_evaluator

    for world, source in (("world1", args.bramblewick), ("world2", args.veldren)):
        bundle = load_bundle(source)
        check(world + "-valid-evaluator", lambda root=source, admitted=bundle:
              {"artifacts": len(load_evaluator(root / "eval", admitted).artifacts)})
        mutations = [
            ("null-effect", "answer-key.json", replace_field("effects", [None])),
            ("null-wait", "answer-key.json", replace_field("waits", [None])),
            ("invalid-response-json", "response-scripts.json", None),
            ("invalid-observed-actor", "answer-sheet.json",
             replace_field("actor", [])),
        ]
        if world == "world1":
            mutations.append(("unhashable-decision", "answer-key.json",
                              replace_field("decision", [])))
        else:
            mutations.append(("null-summary", "answer-key.json",
                              replace_field("summary", None)))
        for name, artifact, mutation in mutations:
            destination = args.out / (world + "-" + name)
            mutate_evaluator(source / "eval", destination, artifact, mutation)
            check(world + "-" + name, lambda root=destination, admitted=bundle:
                  rejected(lambda: load_evaluator(root, admitted)))


def audit(args):
    from dex.eval.identity import engine_manifest
    from dex.eval.report import report_run

    def comments():
        rows = subprocess.run(
            ["git", "diff", "--name-status", args.base, args.head],
            cwd=args.repo, capture_output=True, text=True, check=True).stdout
        added, removed, files = [], [], []
        for row in rows.splitlines():
            status, name = row.split("\t")
            if not name.endswith(".py"):
                continue
            before = "" if status == "A" else subprocess.run(
                ["git", "show", args.base + ":" + name], cwd=args.repo,
                capture_output=True, text=True, check=True).stdout
            after = (args.repo / name).read_text()
            def tokens(source):
                return Counter(token.string for token in
                               tokenize.generate_tokens(io.StringIO(source).readline)
                               if token.type == tokenize.COMMENT)
            old, new = tokens(before), tokens(after)
            added.extend((name, value, count) for value, count in (new - old).items())
            removed.extend((name, value, count) for value, count in (old - new).items())
            files.append(name)
        exact(added, [])
        exact(removed, [])
        return {"python_files": files, "added_comments": added,
                "removed_comments": removed, "suppressions": 0}

    def recorded_values():
        report = report_run(args.recorded_run)
        exact(report["identities"]["engine"]["identity"],
              engine_manifest()["identity"])
        exact(report["outcome"]["evaluation_status"], "failed")
        exact(report["outcome"]["reference_errors"], ["case-00001"])
        exact(report["costs"]["execution_activity"],
              {"logical_invocations": 0, "network_calls": 0,
               "retries": 0, "human_touches": 0})
        original = args.acceptance.read_bytes()
        if (args.repo / "src/dex/eval/acceptance.md").read_bytes() != original:
            raise AssertionError("packaged acceptance source bytes differ")
        coverage = report["acceptance"]
        exact(coverage["source_sha256"], hashlib.sha256(original).hexdigest())
        expected = Counter(line.strip() for line in original.decode().splitlines()
                           if line.strip() and not line.lstrip().startswith("#"))
        actual = Counter(line.strip() for row in coverage["requirements"]
                         for line in row["requirement"].splitlines() if line.strip())
        exact(dict(actual), dict(expected))
        exact(sorted({row["status"] for row in coverage["requirements"]}),
              ["unimplemented"])
        return {"acceptance_blocks": len(coverage["requirements"]),
                "all_source_lines_accounted": True, "current_activity": 0,
                "engine_identity": report["identities"]["engine"]["identity"]}

    check("no-comments-and-suppressions", comments)
    check("recorded-outcomes-identity-coverage", recorded_values)


def main():
    parser = argparse.ArgumentParser()
    for name in ("repo", "out", "bramblewick", "veldren", "acceptance", "recorded-run"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--head", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--section", choices=("audit", "admission", "all"), default="all")
    args = parser.parse_args()
    exact(subprocess.run(["git", "rev-parse", "HEAD"], cwd=args.repo,
                        capture_output=True, text=True, check=True).stdout.strip(),
          args.head)
    exact(subprocess.run(["git", "status", "--porcelain"], cwd=args.repo,
                        capture_output=True, text=True, check=True).stdout, "")
    args.out.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(args.repo / "src"))
    if args.section in ("audit", "all"):
        audit(args)
    if args.section in ("admission", "all"):
        admission_checks(args)
    result = {"head": args.head, "base": args.base, "checks": RESULTS,
              "failed": [row["name"] for row in RESULTS if row["status"] == "failed"]}
    (args.out / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return int(bool(result["failed"]))


if __name__ == "__main__":
    raise SystemExit(main())

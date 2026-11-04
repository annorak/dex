import argparse
import hashlib
import io
import json
import subprocess
import sys
import tokenize
from collections import Counter
from datetime import datetime
from pathlib import Path

from probe_contracts import RESULTS, check, exact, rejected


def snapshot(root):
    return {path.relative_to(root).as_posix():
            hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*")) if path.is_file()}


def admission(args):
    from dex.bundle.reader import load_bundle
    from dex.eval.admission import load_evaluator

    for world, original in (("world1", args.bramblewick), ("world2", args.veldren)):
        bundle = load_bundle(original)

        def valid(root=original, admitted=bundle):
            before = snapshot(root / "eval")
            result = load_evaluator(root / "eval", admitted)
            exact(snapshot(root / "eval"), before)
            return {"artifacts": len(result.artifacts), "input_unchanged": True}

        check(world + "-valid-original", valid)
        conditions = [
            ("null-effect", "answer.effect: expected object"),
            ("null-wait", "answer.wait: expected object"),
            ("invalid-response-json", "response_scripts: invalid JSON"),
            ("invalid-observed-actor", "observed.actor: expected nonempty text"),
        ]
        conditions.append(
            ("unhashable-decision", "answer.decision: expected nonempty text")
            if world == "world1" else ("null-summary", "answer.summary: expected object"))
        for name, diagnostic in conditions:
            root = args.prior / "boundaries" / (world + "-" + name)

            def invalid(source=root, admitted=bundle, expected=diagnostic):
                before = snapshot(source)
                result = rejected(lambda: load_evaluator(source, admitted))
                if not result["diagnostic"].startswith(expected):
                    raise AssertionError(f"expected {expected!r}; observed {result!r}")
                exact(snapshot(source), before)
                return {**result, "input_unchanged": True,
                        "preserved_files": len(before)}

            check(world + "-" + name, invalid)


def applicability(args):
    from dex.eval.identity import engine_manifest

    def git(*arguments):
        return subprocess.run(["git", *arguments], cwd=args.repo,
                              capture_output=True, text=True, check=True).stdout

    def blobs(revision):
        return {row.split("\t", 1)[1]: row.split()[2]
                for row in git("ls-tree", "-r", revision, "src").splitlines()}

    before, after = blobs(args.before), blobs(args.head)
    allowed = {"src/dex/eval/admission.py", "tests/eval/test_scoring.py",
               "tests/contracts/test_checks.py"}
    exact(sorted(git("diff", "--name-only", args.before, args.head).splitlines()),
          sorted(allowed))
    equal = {name: identity for name, identity in before.items()
             if name != "src/dex/eval/admission.py"}
    exact({name: identity for name, identity in after.items()
           if name != "src/dex/eval/admission.py"}, equal)
    prior = json.loads((args.prior / "cli-cache-access/copied-run/freeze.json").read_bytes())
    exact(engine_manifest()["identity"], prior["engine"]["identity"])
    comments_added, comments_removed = [], []
    for name in sorted(allowed):
        def comments(source):
            return Counter(token.string for token in
                           tokenize.generate_tokens(io.StringIO(source).readline)
                           if token.type == tokenize.COMMENT)
        old = comments(git("show", args.before + ":" + name))
        new = comments((args.repo / name).read_text())
        comments_added.extend((name, text, count)
                              for text, count in (new - old).items())
        comments_removed.extend((name, text, count)
                                for text, count in (old - new).items())
    exact(comments_added, [])
    exact(comments_removed, [])
    return {"changed_files": sorted(allowed), "unchanged_source_blobs": equal,
            "engine_identity": prior["engine"]["identity"],
            "comments_added": comments_added, "comments_removed": comments_removed,
            "carried_evidence": ["round1/002-contracts.txt",
                                "round1/005-engine-corrected.txt",
                                "round1/007-cli-cache-access.txt",
                                "round1/010-readback-corrected.txt"],
            "isolation_applicability": "All prior isolation execution, projection, report and identity implementation blobs remain unchanged."}


def trail(args):
    rows = args.trail.read_text().splitlines()
    exact(rows[0].split("\t"), ["ts", "phase", "decision", "why", "evidence", "result"])
    previous = None
    pointers, receipts = 0, 0
    for ordinal, raw in enumerate(rows[1:], 2):
        row = raw.split("\t")
        exact(len(row), 6)
        logged = datetime.fromisoformat(row[0])
        if logged.utcoffset() is None or previous is not None and logged < previous:
            raise AssertionError(f"invalid logging time at row {ordinal}")
        previous = logged
        if not all(row):
            raise AssertionError(f"empty trail field at row {ordinal}")
        for reference in row[4].split(";"):
            path = Path(reference)
            if not path.is_absolute():
                path = args.trail.parent / path
            if not path.exists():
                raise AssertionError(f"missing evidence at row {ordinal}: {reference}")
            pointers += 1
            if path.suffix == ".txt":
                content = path.read_text()
                if "\nRESULT\n" in content:
                    result = json.loads(content.split("\nRESULT\n", 1)[1])
                    if datetime.fromisoformat(result["finished_utc"]) > logged:
                        raise AssertionError(f"receipt postdates row {ordinal}")
                    receipts += 1
    return {"rows": len(rows) - 1, "resolved_pointers": pointers,
            "timed_receipts": receipts,
            "sha256": hashlib.sha256(args.trail.read_bytes()).hexdigest(),
            "scope": "Format, evidence resolution and receipt chronology; not a full transcript or model-family audit."}


def main():
    parser = argparse.ArgumentParser()
    for name in ("repo", "out", "prior", "bramblewick", "veldren", "trail"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("base", "before", "head"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    exact(subprocess.run(["git", "rev-parse", "HEAD"], cwd=args.repo,
                        capture_output=True, text=True, check=True).stdout.strip(),
          args.head)
    exact(subprocess.run(["git", "status", "--porcelain"], cwd=args.repo,
                        capture_output=True, text=True, check=True).stdout, "")
    args.out.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(args.repo / "src"))
    check("unchanged-blobs-engine-and-comments", lambda: applicability(args))
    admission(args)
    check("isolation-trail-spot-audit", lambda: trail(args))
    result = {"base": args.base, "before": args.before, "head": args.head,
              "checks": RESULTS,
              "failed": [row["name"] for row in RESULTS if row["status"] == "failed"]}
    (args.out / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return int(bool(result["failed"]))


if __name__ == "__main__":
    raise SystemExit(main())

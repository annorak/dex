import argparse
import copy
import json
import subprocess
import sys
import traceback
from dataclasses import replace
from pathlib import Path

METRICS = ("logical_invocations", "network_calls", "retries", "input_tokens",
           "output_tokens", "cost_micros", "human_touches")
SUNDAY = "2026-01-04T23:30:00-05:00"
MONDAY = "2026-01-05T12:00:00-05:00"
NEXT_MONDAY = "2026-01-12T12:00:00-05:00"
CUTOFF = "2026-01-20T23:59:59-05:00"
RESULTS = []


def exact(actual, expected):
    if json.dumps(actual, sort_keys=True) != json.dumps(expected, sort_keys=True):
        raise AssertionError(f"expected {expected!r}; observed {actual!r}")
    return actual


def check(name, action):
    try:
        observed = action()
    except Exception as error:
        RESULTS.append({"name": name, "status": "failed",
                        "error": f"{type(error).__name__}: {error}",
                        "traceback": traceback.format_exc()})
    else:
        RESULTS.append({"name": name, "status": "passed", "observed": observed})


def rejected(action):
    from dex.bundle.model import BundleError
    from dex.eval.scenario_format import ScenarioError

    try:
        action()
    except (BundleError, ScenarioError) as error:
        return {"exception": type(error).__name__, "diagnostic": str(error)}
    raise AssertionError("invalid input was accepted")


def number(value):
    return {"kind": "integer", "value": value}


def outcome(value=7):
    return {"decision": None if value is None else number(value),
            "effects": [], "waits": []}


def effect(value=7):
    return {"operation": "publish", "scope": [], "occurrence": "once",
            "payload": number(value)}


def wait():
    return {"node": "decision", "scope": [], "work_revision": 1,
            "request_revision": 1, "role": "reviewer", "assignee": None,
            "due_at": NEXT_MONDAY, "request": {"kind": "text", "value": "Decide."},
            "reviewed": [], "schema": {"kind": "integer"}}


def field_diff(path, expected, actual, expected_present=True, actual_present=True):
    return {"path": path, "expected_present": expected_present,
            "actual_present": actual_present, "expected": expected, "actual": actual}


def outcome_checks():
    from dex.eval.scoring import differences, freeze_answers, score_cases

    samples = [
        ("scalar-type", True, 1, [field_diff("", True, 1)]),
        ("list-assignment", [1, 2], [2, 1],
         [field_diff("/0", 1, 2), field_diff("/1", 2, 1)]),
        ("missing-null", {"x": None}, {},
         [field_diff("/x", None, None, actual_present=False)]),
        ("extra-null", {}, {"x": None},
         [field_diff("/x", None, None, expected_present=False)]),
        ("list-missing", [1, None], [1],
         [field_diff("/1", None, None, actual_present=False)]),
        ("escaped-pointer", {"a/b~c": 7}, {"a/b~c": 8},
         [field_diff("/a~1b~0c", 7, 8)]),
    ]
    for name, expected, actual, expected_diff in samples:
        check(name, lambda e=expected, a=actual, d=expected_diff:
              exact(differences(e, a), d))

    def correct_history():
        scored = score_cases({"case": outcome()}, {"case": outcome()},
                             {"case": outcome(8)}, {"case": ["/decision/value"]})
        return exact({name: scored[name] for name in
                      ("reference_errors", "historical_mismatches",
                       "required_unresolved", "copied_corrupted_fields")},
                     {"reference_errors": [], "historical_mismatches": ["case"],
                      "required_unresolved": [], "copied_corrupted_fields": 0})

    def copied_fields():
        key, historical = outcome(), outcome(8)
        key["effects"], historical["effects"] = [effect()], [effect(9)]
        scored = score_cases({"case": historical}, {"case": key},
                             {"case": historical},
                             {"case": ["/decision/value", "/effects/0/payload/value"]})
        exact(scored["copied_corrupted_fields"], 2)
        exact(scored["historical_mismatches"], [])
        exact(scored["reference_errors"], ["case"])
        return exact(scored["cases"]["case"]["reference_differences"],
                     [field_diff("/decision/value", 7, 8),
                      field_diff("/effects/0/payload/value", 7, 9)])

    def missing_case():
        scored = score_cases({}, {"case": outcome()}, {}, {})
        exact(scored["denominator"], 1)
        exact(scored["reference_errors"], ["case"])
        exact(scored["required_unresolved"], ["case"])
        return exact(scored["cases"]["case"]["reference_differences"],
                     [field_diff("", outcome(), None, actual_present=False)])

    def expected_wait():
        pending = outcome(None)
        pending["waits"] = [wait()]
        scored = score_cases({"case": pending}, {"case": pending}, {}, {})
        exact(scored["reference_errors"], [])
        exact(scored["required_unresolved"], [])
        return scored["cases"]["case"]

    def null_required():
        scored = score_cases({"case": outcome(None)}, {"case": outcome()}, {}, {})
        exact(scored["reference_errors"], ["case"])
        return exact(scored["required_unresolved"], ["case"])

    def changed_wait():
        expected = outcome(None)
        expected["waits"] = [wait()]
        actual = copy.deepcopy(expected)
        actual["waits"][0]["due_at"] = MONDAY
        scored = score_cases({"case": actual}, {"case": expected}, {}, {})
        exact(scored["reference_errors"], ["case"])
        return exact(scored["cases"]["case"]["reference_differences"],
                     [field_diff("/waits/0/due_at", NEXT_MONDAY, MONDAY)])

    def changed_wait_schema():
        expected = {**outcome(None), "waits": [wait()]}
        actual = copy.deepcopy(expected)
        actual["waits"][0]["schema"] = {"kind": "text"}
        scored = score_cases({"case": actual}, {"case": expected}, {}, {})
        exact(scored["reference_errors"], ["case"])
        return exact(scored["cases"]["case"]["reference_differences"],
                     [field_diff("/waits/0/schema/kind", "integer", "text")])

    def reviewed_wait():
        pending = {**outcome(None), "waits": [wait()]}
        pending["waits"][0]["reviewed"] = [
            {"address": {"case_id": "case", "node_id": "producer", "scope": []},
             "revision": 1}]
        scored = score_cases({"case": pending}, {"case": pending}, {}, {})
        return exact(scored["reference_errors"], [])

    check("correct-history-mistake", correct_history)
    check("two-copied-fields", copied_fields)
    check("missing-case-presence", missing_case)
    check("expected-wait-correct", expected_wait)
    check("null-required-result", null_required)
    check("changed-wait-field", changed_wait)
    check("changed-wait-output-schema", changed_wait_schema)
    check("plain-reviewed-work-references", reviewed_wait)
    check("duplicate-corruption-rejected", lambda: rejected(lambda:
          score_cases({"case": outcome(8)}, {"case": outcome()},
                      {"case": outcome(8)},
                      {"case": ["/decision/value", "/decision/value"]})))
    malformed = {
        "missing-effects": {"decision": number(7), "waits": []},
        "untyped-decision": {"decision": 7, "effects": [], "waits": []},
        "invalid-effect-scope": {**outcome(), "effects": [{**effect(), "scope": "bad"}]},
        "empty-effect-operation": {**outcome(), "effects": [{**effect(), "operation": ""}]},
        "zero-wait-revision": {**outcome(None), "waits": [{**wait(), "request_revision": 0}]},
        "invalid-wait-scope": {**outcome(None), "waits": [{**wait(), "scope": "bad"}]},
        "missing-wait-schema": {**outcome(None), "waits": [
            {key: value for key, value in wait().items() if key != "schema"}]},
        "zero-reviewed-revision": {**outcome(None), "waits": [{**wait(), "reviewed": [
            {"address": {"case_id": "case", "node_id": "producer", "scope": []},
             "revision": 0}]}]},
    }
    for name, invalid in malformed.items():
        check(name, lambda row=invalid: rejected(lambda:
              freeze_answers({"case": row}, {}, {})))


def ledger_event(identity, case_id, *, company="company-a", origin="dex",
                 program="r1", at=SUNDAY, kind="human", phase="runtime",
                 category="case_review"):
    return {"id": identity, "company": company, "origin": origin, "kind": kind,
            "phase": phase, "case_id": case_id, "program": program, "at": at,
            "category": category if kind == "human" else None, "tags": [],
            "actor": "reviewer" if kind == "human" else None,
            "request": None, "recording": None, "provenance": "supplied_history",
            "occurred_at": at, "observed_at": at, "received_at": at,
            "available_at": at, "effective_date": at[:10],
            **{name: int(name == "human_touches" and kind == "human")
               for name in METRICS}}


def ledger_inputs():
    cases = {name: {"company": company, "program": "r1", "opened_at": SUNDAY,
                    "status": status}
             for name, company, status in
             (("a", "company-a", "completed"), ("b", "company-b", "pending"),
              ("zero", "company-a", "completed"))}
    cases["future"] = {"company": "company-a", "program": "r1",
                       "opened_at": "2026-02-01T00:00:00-05:00",
                       "status": "not_started"}
    combined = ledger_event("same", "a", category="external_change_approval")
    combined["tags"] = ["case_review", "external_change_approval"]
    rows = [combined, copy.deepcopy(combined),
            ledger_event("same", "a", origin="external", program="r2", at=MONDAY,
                         category="business_authority"),
            ledger_event("same", "b", company="company-b", program="r2",
                         at=NEXT_MONDAY, category="requested_input"),
            ledger_event("question", None, at=MONDAY, phase="compile",
                         category="compile_clarification"),
            ledger_event("grant", None, program="r2", at=NEXT_MONDAY,
                         phase="administrative", category="authority_administration")]
    requests = {}
    for identity, case_id, phase, at, recording, retry, tokens, cost in (
        ("call", "a", "runtime", MONDAY, "recording-1", 0, (10, 2), 0),
        ("retry", "a", "runtime", MONDAY, "recording-2", 1, (10, 2), 0),
        ("compile", None, "compile", NEXT_MONDAY, None, 0, (5, 1), 123),
    ):
        row = ledger_event(identity, case_id, program="r2", at=at,
                           kind="model", phase=phase)
        request_id = "request-" + identity
        row.update(request=request_id, recording=recording, logical_invocations=1,
                   network_calls=int(recording is None), retries=retry,
                   input_tokens=tokens[0], output_tokens=tokens[1], cost_micros=cost)
        requests[request_id] = {"id": request_id, "company": "company-a",
                                "case_id": case_id, "program": "r2", "step": "ai",
                                "work_revision": 1, "requested_at": at,
                                "delivered_at": at, "recording": recording}
        rows.append(row)
    return cases, rows, requests


def ledger_checks():
    from dex.eval.ledger import distribution, summarize, validate_ledger

    cases, rows, requests = ledger_inputs()

    def totals():
        distinct = validate_ledger(rows, cases, CUTOFF, requests)
        exact(len(distinct), 8)
        result = summarize(cases, distinct)
        exact(result["case_totals"]["a"]["human_touches"], 2)
        exact(result["case_totals"]["b"]["human_touches"], 1)
        exact(result["case_totals"]["zero"], dict.fromkeys(METRICS, 0))
        exact(result["phases"]["runtime"]["logical_invocations"], 2)
        exact(result["phases"]["runtime"]["network_calls"], 0)
        exact(result["phases"]["runtime"]["retries"], 1)
        exact(result["phases"]["compile"]["logical_invocations"], 1)
        exact(result["phases"]["compile"]["network_calls"], 1)
        exact(result["phases"]["compile"]["cost_micros"], 123)
        exact(result["human_categories"],
              {"external_change_approval": 1, "business_authority": 1,
               "requested_input": 1, "compile_clarification": 1,
               "authority_administration": 1})
        exact(result["cohorts"]["all"]["metrics"]["human_touches"],
              {"denominator": 4, "total": 3, "frequencies": {"0": 2, "1": 1, "2": 1},
               "zero_count": 2, "zero_share": 0.5, "mean": 0.75,
               "median": 0.5, "maximum": 2})
        exact({name: row["case_ids"] for name, row in result["cohorts"].items()},
              {"all": ["a", "b", "future", "zero"], "started": ["a", "b", "zero"],
               "completed": ["a", "zero"], "pending": ["b"], "not_started": ["future"]})
        exact([(row["week"], row["program"], row["case_ids"])
               for row in result["week_versions"]],
              [("2025-12-29", "r1", ["a", "b", "zero"]),
               ("2026-01-05", "r2", ["a"]), ("2026-01-12", "r2", ["b"])])
        exact(result["versions"]["r2"]["metrics"]["human_touches"]["total"], 2)
        exact([(row["week"], row["program"], row["totals"]["human_touches"])
               for row in result["shared"]],
              [("2026-01-05", "r1", 1), ("2026-01-12", "r2", 1)])
        return result

    check("scoped-actions-categories-weeks-versions", totals)
    check("zero-denominator", lambda: exact(
          distribution([]), {"denominator": 0, "total": 0, "frequencies": {},
                             "zero_count": 0, "zero_share": None, "mean": None,
                             "median": None, "maximum": None}))
    human, model = rows[0], rows[6]
    invalid_rows = {
        "negative-count": {**human, "human_touches": -1},
        "boolean-count": {**human, "human_touches": True},
        "two-human-touches": {**human, "human_touches": 2},
        "blank-actor": {**human, "actor": ""},
        "unknown-category": {**human, "category": "poll"},
        "wrong-company": {**human, "company": "company-b"},
        "after-cutoff": {**human, "available_at": "2026-02-01T00:00:00-05:00"},
        "unobserved-occurrence": {**human, "observed_at": "2026-01-04T22:00:00-05:00"},
        "blank-request": {**model, "request": ""},
        "zero-invocation": {**model, "logical_invocations": 0},
        "model-administration": {**model, "phase": "administrative"},
        "recording-network": {**model, "network_calls": 1},
    }
    for name, row in invalid_rows.items():
        check("ledger-" + name, lambda invalid=row: rejected(lambda:
              validate_ledger([invalid], cases, CUTOFF, requests)))
    conflicting = {**human, "actor": "another-reviewer"}
    check("conflicting-action-identity", lambda: rejected(lambda:
          validate_ledger([human, conflicting], cases, CUTOFF, requests)))


def engine_checks(repo):
    from dex.core import language as lang
    from dex.core import program as p
    from dex.core import runtime as r
    from dex.eval.scenario_format import parse_scenario
    from dex.eval.scenarios import execute

    for name, recordings, actions in (
        ("continuation-recorded-ai", 1, 0), ("continuation-invalid-ai", 2, 1),
        ("continuation-redelivery", 0, 1), ("effect-exact-approval", 0, 1),
    ):
        def run(scenario_name=name, expected_recordings=recordings,
                expected_actions=actions):
            source = (repo / "tests/scenarios" / (scenario_name + ".json")).read_bytes()
            scenario = parse_scenario(source)
            result = execute(scenario.programs, scenario.commands, scenario.detail)
            exact(len(result.final_runtime.recordings), expected_recordings)
            exact(len(result.final_runtime.actions), expected_actions)
            exact(result.final_runtime.replay_equal, True)
            if scenario_name == "continuation-redelivery":
                exact(result.observations[2].runtime.events, ())
            if scenario_name == "continuation-recorded-ai":
                supplied = scenario.commands[1]
                repeat = replace(supplied, meta=replace(
                    supplied.meta, command_id="record-redelivery",
                    expected_revision=result.final_runtime.revision))
                replay = execute(scenario.programs, (*scenario.commands, repeat),
                                 scenario.detail)
                exact(len(replay.final_runtime.recordings), 1)
                exact(replay.observations[-1].runtime.events, ())
            reviewed = None
            if scenario_name == "effect-exact-approval":
                entries = []
                for program in scenario.programs:
                    verified = p.verify_program(program.draft, program.sources,
                                                lang.DEFAULT_LIMITS)
                    if isinstance(verified, p.StructuralFailure):
                        raise AssertionError("existing program failed verification")
                    entries.append(r.ArtifactEntry(r.artifact_pin(verified.artifact),
                                                   verified.artifact))
                events = tuple(event for observation in result.observations
                               if observation.runtime is not None
                               for event in observation.runtime.events)
                state = r.rebuild(events, r.ProgramCatalog(tuple(entries)))
                exact(len(state.actions), 1)
                exact(len(state.reviews), 1)
                exact([item.outcome for item in state.reviews.values()], ["clean"])
                reviewed = len(state.reviews)
            return {"recordings": len(result.final_runtime.recordings),
                    "actions": len(result.final_runtime.actions),
                    "reviewed_results": reviewed, "replay_equal": True}
        check("engine-" + name, run)


def cli_checks(repo, out):
    recorder = repo / "docs/verification/m1-10/scripts/record.py"

    def command(ordinal, label, arguments, expected_exit):
        receipt = out / (ordinal + "-" + label + ".txt")
        invocation = [sys.executable, str(recorder), "--cwd", str(repo),
                      "--out", str(receipt), "--", "env",
                      "PYTHONDONTWRITEBYTECODE=1", "UV_OFFLINE=1",
                      "uv", "run", "--locked", "dex", *map(str, arguments)]
        result = subprocess.run(invocation, capture_output=True, text=True, timeout=180)
        if result.returncode != expected_exit:
            raise AssertionError(f"{receipt}: expected exit {expected_exit}; "
                                 f"observed {result.returncode}; {result.stderr}")
        content = receipt.read_text()
        stdout = content.split("\nSTDOUT\n", 1)[1].split("\nSTDERR\n", 1)[0]
        stderr = content.split("\nSTDERR\n", 1)[1].split("\nRESULT\n", 1)[0]
        return stdout, stderr

    def failed_evaluation():
        run = out / "copied-run"
        command("01", "copied", ["eval", "--scenario",
                repo / "tests/scenarios/score-copied-mistake.json", "--out", run], 1)
        scored = json.loads((run / "score.json").read_bytes())
        exact(scored["evaluation_status"], "failed")
        exact(scored["reference_errors"], ["case-00001"])
        exact(scored["copied_corrupted_fields"], 1)
        first, _ = command("02", "failed-report", ["report", run], 0)
        repeated, _ = command("03", "failed-report-fresh", ["report", run], 0)
        exact(first, repeated)
        exact(json.loads(first)["outcome"]["evaluation_status"], "failed")
        return {"saved_failed_evaluation": True, "fresh_reports_equal": True}

    def invalid_input():
        source, run = out / "invalid-scenario.json", out / "invalid-run"
        source.write_text(json.dumps({"format": "dex-score-scenario-1",
                                     "scenario_id": "invalid", "fixture": None}))
        _, stderr = command("04", "invalid", ["eval", "--scenario", source,
                                              "--out", run], 2)
        error = json.loads(stderr)
        exact(error["format"], "dex-eval-error-1")
        exact(run.exists(), False)
        return {"invalid_input_published": False, "diagnostic": error}

    check("saved-failed-evaluation-is-reportable", failed_evaluation)
    check("invalid-input-publishes-nothing", invalid_input)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--head")
    parser.add_argument("--section", choices=("contracts", "engine", "cli", "all"),
                        default="all")
    args = parser.parse_args()
    repo = args.repo.resolve()
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                              capture_output=True, text=True, check=True).stdout.strip()
    if args.head is not None and revision != args.head:
        parser.error(f"expected head {args.head}; observed {revision}")
    status = subprocess.run(["git", "status", "--porcelain"], cwd=repo,
                            capture_output=True, text=True, check=True).stdout
    if args.head is not None and status:
        parser.error("pinned-head run requires a clean worktree")
    args.out.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(repo / "src"))
    if args.section in ("contracts", "all"):
        outcome_checks()
        ledger_checks()
    if args.section in ("engine", "all"):
        engine_checks(repo)
    if args.section in ("cli", "all"):
        cli_checks(repo, args.out)
    report = {"scope": "Independent narrow correctness probes; no formal verdict.",
              "revision": revision, "working_tree_status": status,
              "section": args.section, "checks": RESULTS,
              "failed": [row["name"] for row in RESULTS if row["status"] == "failed"]}
    (args.out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return int(bool(report["failed"]))


if __name__ == "__main__":
    raise SystemExit(main())

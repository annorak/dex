from dataclasses import dataclass
from typing import Any

from dex.bundle.model import BundleError
from dex.bundle.validation import (
    canonical,
    fields,
    items,
    object_value,
    text,
    timestamp,
)
from dex.core import program as p
from dex.eval.scenario_format import (
    Json,
    parse_named_value,
    parse_schema,
    parse_scope,
    parse_value,
    parse_work_revision,
)
from dex.eval.scenario_output import encode_core


@dataclass(frozen=True)
class FrozenAnswers:
    key: bytes
    history: bytes
    mistakes: bytes


def differences(expected: Json, actual: Json, path: str = "") -> list[dict[str, Any]]:
    if isinstance(expected, dict) and isinstance(actual, dict):
        result: list[dict[str, Any]] = []
        for name in sorted(expected.keys() | actual.keys()):
            pointer = path + "/" + name.replace("~", "~0").replace("/", "~1")
            if name not in expected or name not in actual:
                result.append(
                    {
                        "path": pointer,
                        "expected_present": name in expected,
                        "actual_present": name in actual,
                        "expected": expected.get(name),
                        "actual": actual.get(name),
                    }
                )
            else:
                result.extend(differences(expected[name], actual[name], pointer))
        return result
    if isinstance(expected, list) and isinstance(actual, list):
        result = []
        for index in range(max(len(expected), len(actual))):
            pointer = path + "/" + str(index)
            if index >= len(expected) or index >= len(actual):
                result.append(
                    {
                        "path": pointer,
                        "expected_present": index < len(expected),
                        "actual_present": index < len(actual),
                        "expected": expected[index] if index < len(expected) else None,
                        "actual": actual[index] if index < len(actual) else None,
                    }
                )
            else:
                result.extend(differences(expected[index], actual[index], pointer))
        return result
    if type(expected) is not type(actual) or expected != actual:
        return [
            {
                "path": path,
                "expected_present": True,
                "actual_present": True,
                "expected": expected,
                "actual": actual,
            }
        ]
    return []


def score_cases(
    actual: dict[str, dict[str, Any]],
    key: dict[str, dict[str, Any]],
    history: dict[str, dict[str, Any]],
    mistakes: dict[str, list[str]],
) -> dict[str, Any]:
    for pointers in mistakes.values():
        if any(
            not isinstance(pointer, str) or not pointer.startswith("/")
            for pointer in items(pointers, "mistakes")
        ):
            raise BundleError("mistake_pointer")
    for rows in (actual, key, history):
        for row in rows.values():
            validate_outcome(row)
    if not set(history) <= set(key) or not set(mistakes) <= set(history):
        raise BundleError("score_case_membership")
    if set(actual) - set(key):
        raise BundleError("score_unexpected_cases")
    cases: dict[str, Any] = {}
    for case_id, expected in sorted(key.items()):
        found = actual.get(case_id)
        independent = differences(expected, found)
        observed = differences(history[case_id], found) if case_id in history else []
        if found is None:
            independent[0]["actual_present"] = False
            if observed:
                observed[0]["actual_present"] = False
        required_missing = found is None or any(
            not item["actual_present"]
            or item["actual"] is None
            and item["expected"] is not None
            for item in independent
        )
        corruption = (
            {item["path"]: item for item in differences(expected, history[case_id])}
            if case_id in history
            else {}
        )
        if len(mistakes.get(case_id, [])) != len(set(mistakes.get(case_id, []))):
            raise BundleError("mistake_duplicate_field: " + case_id)
        copied: list[dict[str, Any]] = []
        for pointer in mistakes.get(case_id, []):
            if pointer not in corruption:
                raise BundleError("mistake_not_corrupted: " + case_id + pointer)
            if canonical(pointer_value(found, pointer)) == canonical(
                pointer_value(history[case_id], pointer)
            ):
                copied.append(corruption[pointer])
        cases[case_id] = {
            "reference_differences": independent,
            "historical_differences": observed,
            "history_available": case_id in history,
            "required_unresolved": required_missing,
            "copied_corrupted_fields": copied,
        }
    return {
        "denominator": len(key),
        "case_ids": sorted(key),
        "cases": cases,
        "reference_errors": [
            name for name, row in cases.items() if row["reference_differences"]
        ],
        "historical_mismatches": [
            name for name, row in cases.items() if row["historical_differences"]
        ],
        "historical_denominator": len(history),
        "required_unresolved": [
            name for name, row in cases.items() if row["required_unresolved"]
        ],
        "copied_corrupted_fields": sum(
            len(row["copied_corrupted_fields"]) for row in cases.values()
        ),
        "history_status": "measured" if history else "unimplemented",
    }


def freeze_answers(key: object, history: object, mistakes: object) -> FrozenAnswers:
    expected = object_value(key, "answer_key")
    observed = object_value(history, "history")
    errors = object_value(mistakes, "mistakes")
    score_cases({}, expected, observed, errors)
    return FrozenAnswers(canonical(expected), canonical(observed), canonical(errors))


def pointer_value(value: Json, pointer: str) -> tuple[bool, Json]:
    for part in pointer.split("/")[1:]:
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict):
            if part not in value:
                return False, None
            value = value[part]
        elif isinstance(value, list) and part.isdecimal() and int(part) < len(value):
            value = value[int(part)]
        else:
            return False, None
    return True, value


def validate_outcome(raw: object) -> None:
    row = object_value(raw, "outcome")
    fields(row, {"decision", "effects", "waits"}, set(), "outcome")
    values = [] if row["decision"] is None else [row["decision"]]
    for raw_effect in items(row["effects"], "effects"):
        effect = object_value(raw_effect, "effect")
        fields(effect, {"operation", "scope", "occurrence", "payload"}, set(), "effect")
        text(effect["operation"], "effect.operation")
        text(effect["occurrence"], "effect.occurrence")
        for part in items(effect["scope"], "effect.scope"):
            parse_named_value(part)
        values.append(effect["payload"])
    for raw_wait in items(row["waits"], "waits"):
        wait = object_value(raw_wait, "wait")
        fields(
            wait,
            {
                "node",
                "scope",
                "work_revision",
                "request_revision",
                "role",
                "assignee",
                "due_at",
                "request",
                "reviewed",
                "schema",
            },
            set(),
            "wait",
        )
        for name in ("node", "role"):
            text(wait[name], "wait." + name)
        if wait["assignee"] is not None:
            text(wait["assignee"], "wait.assignee")
        for revision in ("work_revision", "request_revision"):
            if type(wait[revision]) is not int or wait[revision] < 1:
                raise BundleError("wait_revision")
        parse_scope(wait["scope"])
        parse_schema(wait["schema"])
        for reviewed in items(wait["reviewed"], "wait.reviewed"):
            if parse_work_revision(reviewed).revision < 1:
                raise BundleError("wait_reviewed_revision")
        timestamp(wait["due_at"], "wait.due_at")
        values.append(wait["request"])
    for value in values:
        if canonical(encode_core(p.normalized_value(parse_value(value)))) != canonical(
            value
        ):
            raise BundleError("outcome_noncanonical_value")

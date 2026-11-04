import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dex.bundle.collection import load_collection
from dex.bundle.model import Bundle, BundleError
from dex.bundle.projection import freeze_cohorts
from dex.bundle.reader import inventory, load_bundle, read_file
from dex.bundle.validation import (
    canonical,
    fields,
    items,
    object_value,
    parse_json,
    relative_path,
    text,
    timestamp,
)
from dex.eval.identity import digest
from dex.eval.run_store import validate_destination


@dataclass(frozen=True)
class EvaluatorInputs:
    bundle: Bundle
    manifest: bytes
    artifacts: tuple[tuple[str, bytes], ...]
    learning: frozenset[str]
    exam: frozenset[str]


def load_evaluator(path: Path, bundle: Bundle) -> EvaluatorInputs:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        raw = read_file(descriptor, "manifest.json")
        manifest = parse_json(raw, "evaluator_manifest")
        fields(
            manifest,
            {
                "format",
                "company",
                "seed",
                "generator_version",
                "key_frozen_before_reference_execution",
                "reference_programs",
                "artifacts",
            },
            set(),
            "evaluator_manifest",
        )
        if text(manifest["format"], "evaluator.format") not in {
            "dex-world-1-evaluator-1",
            "dex-world-2-evaluator-1",
        }:
            raise BundleError("evaluator_version")
        if manifest["company"] != bundle.company_id:
            raise BundleError("evaluator_company_identity")
        if manifest["key_frozen_before_reference_execution"] is not True:
            raise BundleError("evaluator_key_not_frozen")
        if type(manifest["seed"]) is not int:
            raise BundleError("evaluator_seed")
        text(manifest["generator_version"], "evaluator.generator_version")
        references = items(manifest["reference_programs"], "reference_programs")
        declarations = object_value(manifest["artifacts"], "evaluator.artifacts")
        required = {
            "answer-key.json",
            "answer-sheet.json",
            "mistakes.json",
            "fixture.json",
            "response-scripts.json",
        }
        if not required <= declarations.keys():
            raise BundleError("evaluator_missing_artifact")
        for name in declarations:
            relative_path(name, "evaluator.path")
        declared_files = {
            "artifacts/manifest.json",
            *("artifacts/" + name for name in declarations),
        }
        if inventory(descriptor, prefix="artifacts/") != declared_files:
            raise BundleError("evaluator_undeclared_artifact")
        frozen: dict[str, bytes] = {}
        for name, identity in declarations.items():
            relative_path(name, "evaluator.path")
            content = read_file(descriptor, name)
            if digest(content) != identity:
                raise BundleError("evaluator_hash_mismatch: " + name)
            frozen[name] = content
        key = parse_json(frozen["answer-key.json"], "answer_key")
        sheet = parse_json(frozen["answer-sheet.json"], "answer_sheet")
        mistakes = parse_json(frozen["mistakes.json"], "mistakes")
        fixture = parse_json(frozen["fixture.json"], "fixture")
        parse_json(frozen["response-scripts.json"], "response_scripts")
        cohort = freeze_cohorts(bundle)
        declared_cases = {case.case_id for case in bundle.cases}
        shadow = case_ids(fixture.get("shadow", []), "shadow")
        if shadow & declared_cases:
            raise BundleError("evaluator_shadow_membership")
        if (
            set(key) != declared_cases | shadow
            or frozenset(sheet) != cohort.learning | cohort.exam
        ):
            raise BundleError("evaluator_case_membership")
        if not set(mistakes) <= set(sheet):
            raise BundleError("evaluator_mistake_membership")
        if (
            case_ids(fixture["learning"], "learning") != cohort.learning
            or case_ids(fixture["exam"], "exam") != cohort.exam
        ):
            raise BundleError("evaluator_cohort_conflict")
        if (
            fixture["company"] != bundle.company_id
            or fixture["seed"] != manifest["seed"]
            or fixture["generator_version"] != manifest["generator_version"]
        ):
            raise BundleError("evaluator_fixture_identity")
        validate_evaluator_answers(manifest["format"], key, sheet, mistakes)
        validate_fixture(fixture, bundle, shadow)
        if references:
            raise BundleError(
                "reference_unavailable: no checked reference implementation is installed"
            )
        return EvaluatorInputs(
            bundle,
            canonical(manifest),
            tuple(sorted(frozen.items())),
            cohort.learning,
            cohort.exam,
        )
    except KeyError as error:
        raise BundleError("evaluator_missing_field: " + str(error)) from None
    finally:
        os.close(descriptor)


def run_reference(path: Path, out: Path) -> int:
    try:
        validate_destination(out)
        if path.is_dir() and (path / "collection.json").is_file():
            path = path / "collection.json"
        if path.name == "collection.json":
            collection = load_collection(path)
            inputs = tuple(
                load_evaluator(path.parent / relative / "eval", bundle)
                for relative, bundle in collection.bundles
            )
        else:
            bundle = load_bundle(path)
            if not path.is_dir():
                raise BundleError("evaluator_directory_required")
            inputs = (load_evaluator(path / "eval", bundle),)
        raise BundleError(
            "reference_unavailable: "
            + ", ".join(item.bundle.company_id for item in inputs)
        )
    except (OSError, BundleError) as error:
        print(
            json.dumps(
                {
                    "format": "dex-eval-error-1",
                    "code": "reference_unavailable"
                    if str(error).startswith("reference_unavailable")
                    else "evaluator_invalid",
                    "message": str(error),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


def case_ids(raw: object, label: str) -> frozenset[str]:
    values = [text(value, label) for value in items(raw, label)]
    if len(set(values)) != len(values):
        raise BundleError("evaluator_duplicate_case: " + label)
    return frozenset(values)


def validate_fixture(
    fixture: dict[str, object], bundle: Bundle, shadow: frozenset[str]
) -> None:
    public = {source.path: source.sha256 for source in bundle.sources}
    hashes = object_value(fixture["source_hashes"], "fixture.source_hashes")
    for name, identity in hashes.items():
        relative_path(name, "fixture.source_hash")
        if public.get("sources/" + name) != identity:
            raise BundleError("evaluator_source_identity: " + name)
    cases = {case.case_id: case for case in bundle.cases}
    descriptors = [
        object_value(row, "fixture.case")
        for row in items(fixture["cases"], "fixture.cases")
    ]
    declared = [text(row["case_id"], "fixture.case_id") for row in descriptors]
    if len(set(declared)) != len(declared) or set(declared) != cases.keys() | shadow:
        raise BundleError("evaluator_fixture_cases")
    for row in descriptors:
        if row["case_id"] in shadow:
            continue
        opened = row.get("opened_at", row.get("received"))
        if timestamp(opened, "fixture.opened_at") != cases[row["case_id"]].opened_at:
            raise BundleError("evaluator_arrival_conflict")
    stream = case_ids(fixture["stream"], "fixture.stream")
    if stream != frozenset(
        case.case_id for case in bundle.cases if not case.historical
    ):
        raise BundleError("evaluator_stream_conflict")
    if "cutoff" in fixture:
        cutoff = timestamp(fixture["cutoff"], "fixture.cutoff")
        if any(cases[name].opened_at > cutoff for name in stream):
            raise BundleError("evaluator_cutoff_conflict")
    elif "cutoffs" in fixture:
        cutoffs = object_value(fixture["cutoffs"], "fixture.cutoffs")
        if not cutoffs:
            raise BundleError("evaluator_cutoff_conflict")
        for raw, declaration in cutoffs.items():
            cutoff = timestamp(raw, "fixture.cutoff")
            partitions = object_value(declaration, "fixture.cutoff.partitions")
            fields(
                partitions,
                {"complete", "waiting", "not_opened"},
                set(),
                "fixture.cutoff.partitions",
            )
            complete = case_ids(partitions["complete"], "complete")
            waiting = case_ids(partitions["waiting"], "waiting")
            unopened = case_ids(partitions["not_opened"], "not_opened")
            if (
                complete & waiting
                or complete & unopened
                or waiting & unopened
                or complete | waiting | unopened != stream
            ):
                raise BundleError("evaluator_cutoff_conflict")
            if unopened != frozenset(
                name for name in stream if cases[name].opened_at > cutoff
            ):
                raise BundleError("evaluator_cutoff_conflict")
    else:
        raise BundleError("evaluator_cutoff_missing")


def validate_evaluator_answers(
    version: str,
    key: dict[str, object],
    sheet: dict[str, object],
    mistakes: dict[str, object],
) -> None:
    expected_fields = {"decision", "effects", "waits"}
    observed_fields = {"actor", "available_at", "observed_at", "occurred_at"}
    if version == "dex-world-1-evaluator-1":
        expected_fields |= {
            "approvals",
            "due_date",
            "eligible_at",
            "insurance_at_receipt",
            "limit_cents",
            "posting_month",
            "second_signer",
            "service_confirmation",
            "snow_review",
            "state",
            "terms_days",
        }
        observed_fields |= {
            "approval_roles",
            "community",
            "decision",
            "due_date",
            "invoice_number",
            "posting_month",
            "snow_review",
            "vendor",
        }
    else:
        expected_fields |= {
            "branches",
            "business_decision",
            "case_id",
            "completed_at",
            "engine_authority",
            "runtime_model_calls",
            "summary",
        }
        observed_fields |= {
            "activated_at",
            "case_id",
            "client_id",
            "confirmation_id",
            "owner_decided_at",
            "payload",
            "payload_sha256",
            "summary_id",
        }
    for case_id, raw in key.items():
        row = object_value(raw, "evaluator.answer")
        decision = text(row.get("decision"), "answer.decision")
        shape = expected_fields
        if version == "dex-world-1-evaluator-1" and decision in {
            "duplicate",
            "cancellation",
        }:
            shape = {"approvals", "decision", "effects", "prior", "state", "waits"}
        fields(row, shape, set(), "evaluator.answer")
        for raw_effect in items(row["effects"], "answer.effects"):
            effect = object_value(raw_effect, "answer.effect")
            text(effect["operation"], "effect.operation")
            identity = (
                "identity" if version == "dex-world-1-evaluator-1" else "effect_id"
            )
            text(effect[identity], "effect.identity")
            object_value(effect["payload"], "effect.payload")
        for raw_wait in items(row["waits"], "answer.waits"):
            wait = object_value(raw_wait, "answer.wait")
            text(wait["request_id"], "wait.request_id")
            text(wait["actor"], "wait.actor")
            timestamp(wait["due_at"], "wait.due_at")
            for clock in ("responded_at", "observed_at", "available_at"):
                if wait.get(clock) is not None:
                    timestamp(wait[clock], "wait." + clock)
        if version == "dex-world-2-evaluator-1":
            for name in ("summary", "business_decision", "engine_authority"):
                object_value(row[name], "answer." + name)
            for branch in items(row["branches"], "answer.branches"):
                object_value(branch, "answer.branch")
        if "case_id" in row and row["case_id"] != case_id:
            raise BundleError("evaluator_answer_identity")
    for case_id, raw in sheet.items():
        row = object_value(raw, "evaluator.observed")
        fields(row, observed_fields, set(), "evaluator.observed")
        text(row["actor"], "observed.actor")
        for clock in ("available_at", "observed_at", "occurred_at"):
            timestamp(row[clock], "observed." + clock)
        if "case_id" in row and row["case_id"] != case_id:
            raise BundleError("evaluator_observation_identity")
    for raw in mistakes.values():
        row = object_value(raw, "evaluator.mistake")
        fields(row, {"field", "correct", "observed"}, set(), "evaluator.mistake")
        text(row["field"], "mistake.field")
        if canonical(row["correct"]) == canonical(row["observed"]):
            raise BundleError("evaluator_mistake_not_corrupted")

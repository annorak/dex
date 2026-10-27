import json
import os
import tempfile
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

from dex import codec
from dex.bundle.history import source_ref
from dex.bundle.learning import (
    exam_boundary,
    metadata_text,
    recording_is_permitted,
    validate_view,
)
from dex.bundle.model import Bundle, BundleError, Source
from dex.bundle.reader import read_file
from dex.bundle.validation import canonical, parse_json, timestamp
from dex.core import program as p

type Destination = Literal[
    "prompt", "diagnostic", "cache", "training_test", "compiler_recording", "library"
]
DESTINATIONS = frozenset(
    {"prompt", "diagnostic", "cache", "training_test", "compiler_recording", "library"}
)


@dataclass(frozen=True)
class Cohorts:
    learning: frozenset[str]
    exam: frozenset[str]
    history: bytes


@dataclass(frozen=True)
class LearningView:
    content: bytes

    @property
    def catalog(self) -> p.SourceCatalog:
        data = validate_view(self.content)
        return p.SourceCatalog(
            tuple(
                codec.loads(json.dumps(source["extraction"]), p.SourceExtraction)
                for source in data["sources"]
                if source["extraction"] is not None
            )
        )


@dataclass(frozen=True)
class EvidenceRef:
    company_id: str
    kind: Literal["source", "case", "recording"]
    identity: tuple[str, ...]


def freeze_cohorts(bundle: Bundle) -> Cohorts:
    manifest = parse_json(bundle.manifest, "bundle")
    history = manifest["history"]
    if history == {"kind": "none"}:
        return Cohorts(frozenset(), frozenset(), canonical(history))
    end = timestamp(history["end"], "history.end")
    start = timestamp(history["start"], "history.start")
    boundary = exam_boundary(end)
    learning = frozenset(
        case.case_id for case in bundle.cases if start <= case.opened_at < boundary
    )
    exam = frozenset(
        case.case_id
        for case in bundle.cases
        if max(start, boundary) <= case.opened_at < end
    )
    declaration = {key: value for key, value in history.items() if key != "cases"}
    return Cohorts(learning, exam, canonical(declaration))


def _metadata(descriptor: dict[str, Any]) -> dict[str, Any]:
    result = {
        key: descriptor[key]
        for key in (
            "source_id",
            "revision_id",
            "sha256",
            "media_type",
            "observed_at",
            "available_at",
            "occurred_at",
            "effective_date",
        )
        if key in descriptor
    }
    for key in ("source_id", "revision_id"):
        metadata_text(result[key])
    origin = descriptor["origin"]
    result["origin"] = {key: value for key, value in origin.items()}
    for key, value in origin.items():
        if key == "message":
            for identity in value.values():
                metadata_text(identity)
        else:
            metadata_text(value)
    if "mapping" in descriptor:
        mapping = descriptor["mapping"]
        result["mapping"] = {
            key: mapping[key]
            for key in (
                "version",
                "confirmed_by",
                "confirmed_at",
                "effective_from",
                "effective_until",
            )
        }
        metadata_text(mapping["version"])
        metadata_text(mapping["confirmed_by"])
    return result


def _source_view(
    source: Source, descriptor: dict[str, Any], permitted: set[str]
) -> dict[str, Any]:
    extraction = source.extraction if source.unresolved is None else None
    records = [
        record
        for record in source.records
        if record.locator in permitted and source.unresolved is None
    ]
    locators = permitted | {
        locator for record in records for locator in record.native_cells
    }
    if extraction is None:
        sections: tuple[p.Section, ...] = ()
    elif not source.records:
        sections = (
            extraction.sections
            if "*" in permitted
            else tuple(
                section
                for section in extraction.sections
                if section.locator in permitted
            )
        )
    else:
        sections = tuple(
            section for section in extraction.sections if section.locator in locators
        )
    passages: list[dict[str, Any]] = []
    projected: p.SourceExtraction | None = None
    if extraction is not None and sections:
        if sections == extraction.sections:
            projected = extraction
            offsets = [(section.start, section.end) for section in sections]
        else:
            chunks: list[str] = []
            new_sections: list[p.Section] = []
            offsets: list[tuple[int, int]] = []
            position = 0
            for section in sections:
                quote = extraction.text[section.start : section.end]
                chunks.append(quote + "\n")
                offsets.append((position, position + len(quote)))
                new_sections.append(
                    p.Section(
                        section.name, section.locator, position, position + len(quote)
                    )
                )
                position += len(quote) + 1
            content = "".join(chunks)
            identity = sha256(
                canonical(
                    [
                        extraction.pin.extraction,
                        [(section.start, section.end) for section in sections],
                    ]
                )
            ).hexdigest()
            projected = p.SourceExtraction(
                p.SourcePin(
                    source.source_id,
                    source.revision_id,
                    source.sha256,
                    identity,
                    sha256(content.encode()).hexdigest(),
                ),
                content,
                tuple(new_sections),
            )
        for section, (start, end) in zip(sections, offsets, strict=True):
            metadata_text(section.name)
            metadata_text(section.locator)
            original = p.Citation(
                extraction.pin,
                section.name,
                section.locator,
                section.start,
                section.end,
                extraction.text[section.start : section.end],
            )
            current = p.Citation(
                projected.pin, section.name, section.locator, start, end, original.quote
            )
            passages.append(
                {
                    "original": json.loads(codec.dumps(original)),
                    "projected": json.loads(codec.dumps(current)),
                }
            )
    result = _metadata(descriptor)
    result.update(
        extraction=None if projected is None else json.loads(codec.dumps(projected)),
        extractor_version=source.extractor_version,
        unresolved=None if source.unresolved is None else "source content unresolved",
        passages=passages,
        records=[
            {
                "locator": record.locator,
                "values": [json.loads(codec.dumps(value)) for value in record.values],
                "cells": [list(cell) for cell in record.cells],
                "native_cells": list(record.native_cells),
            }
            for record in records
        ],
    )
    return result


def materialize_learning(bundle: Bundle, as_of: datetime) -> LearningView:
    if as_of.utcoffset() is None:
        raise BundleError("as_of: invalid timestamp with UTC offset")
    cohorts = freeze_cohorts(bundle)
    manifest = parse_json(bundle.manifest, "bundle")
    metadata_text(bundle.company_id)
    metadata_text(bundle.bundle_id)
    history = parse_json(cohorts.history, "history")
    if history["kind"] != "none":
        metadata_text(history["opening_event"])
        metadata_text(history["adequacy"]["actor"])
        if timestamp(history["adequacy"]["decided_at"], "adequacy") > as_of:
            raise BundleError("history_adequacy_unavailable")
    sources = {
        (source.source_id, source.revision_id): source for source in bundle.sources
    }
    descriptors = {
        (item["source_id"], item["revision_id"]): item for item in manifest["sources"]
    }
    deliveries = {item.delivery_id: item for item in bundle.deliveries}
    delivered = {
        ref
        for delivery in bundle.deliveries
        if delivery.available_at <= as_of
        for ref in delivery.sources
    }
    available = {
        ref
        for ref, source in sources.items()
        if ref in delivered
        and source.available_at <= as_of
        and (
            "mapping" not in descriptors[ref]
            or timestamp(descriptors[ref]["mapping"]["confirmed_at"], "mapping")
            <= as_of
        )
    }
    raw_cases = [*(manifest["history"].get("cases", [])), *manifest.get("cases", [])]
    permitted_cases = {
        case.case_id
        for case in bundle.cases
        if case.case_id not in cohorts.exam
        and case.opened_at <= as_of
        and deliveries[case.delivery_id].available_at <= as_of
    }
    allowed: dict[tuple[str, str], set[str]] = {ref: set() for ref in sources}
    denied: dict[tuple[str, str], set[str]] = {ref: set() for ref in sources}
    assigned: set[tuple[str, str]] = set()
    for case in raw_cases:
        is_permitted = case["case_id"] in permitted_cases
        selectors: dict[tuple[str, str], set[str]] = {}
        for fact in case["facts"]:
            selectors.setdefault(source_ref(fact["source"], "fact"), set()).add(
                fact["record"]
            )
        for raw_ref in case["inputs"]:
            ref = source_ref(raw_ref, "input")
            assigned.add(ref)
            (allowed if is_permitted else denied)[ref].update(selectors.get(ref, {"*"}))
        for observation in case["observations"]:
            ref = source_ref(observation["source"], "observation")
            assigned.add(ref)
            target = (
                allowed
                if is_permitted
                and timestamp(observation["available_at"], "observation") <= as_of
                else denied
            )
            target[ref].add(observation["locator"])
    aliases: dict[tuple[str, str], list[tuple[str, str]]] = {}
    parents: dict[tuple[str, str], tuple[tuple[str, str], set[str]]] = {}
    children: dict[tuple[str, str], list[tuple[tuple[str, str], set[str]]]] = {}
    for ref, source in sources.items():
        aliases.setdefault((source.sha256, source.extractor_version), []).append(ref)
        if ref not in available:
            denied[ref].add("*")
        origin = descriptors[ref]["origin"]
        if origin["kind"] == "attachment":
            parent = source_ref(origin["message"], "attachment")
            extraction = sources[parent].extraction
            sections: set[str] = (
                set()
                if extraction is None
                else {
                    section.locator
                    for section in extraction.sections
                    if section.locator == origin["part"]
                    or section.locator.startswith(origin["part"] + "/")
                }
            )
            parents[ref] = parent, sections
            children.setdefault(parent, []).append((ref, sections))

    def propagate(exclusions: dict[tuple[str, str], set[str]]) -> None:
        pending = deque(ref for ref in sources if exclusions[ref])

        def restrict(ref: tuple[str, str], selectors: set[str]) -> None:
            if not selectors <= exclusions[ref]:
                exclusions[ref].update(selectors)
                pending.append(ref)

        while pending:
            ref = pending.popleft()
            source = sources[ref]
            for alias in aliases[source.sha256, source.extractor_version]:
                restrict(alias, exclusions[ref])
            if ref in parents:
                parent, sections = parents[ref]
                restrict(parent, sections)
            for child, sections in children.get(ref, []):
                if "*" in exclusions[ref] or sections & exclusions[ref]:
                    restrict(child, {"*"})

    propagate(denied)
    ambiguous = {ref: set[str]() for ref in sources}
    processed: set[str] = set()
    while True:
        restricted_versions: dict[str, set[str]] = {}
        for ref, source in sources.items():
            if source.sha256 not in processed and (denied[ref] or ambiguous[ref]):
                restricted_versions.setdefault(source.sha256, set()).add(
                    source.extractor_version
                )
        if not restricted_versions:
            break
        processed.update(restricted_versions)
        for ref, source in sources.items():
            if source.sha256 in restricted_versions and restricted_versions[
                source.sha256
            ] - {source.extractor_version}:
                ambiguous[ref].add("*")
        propagate(ambiguous)
    for ref in sources:
        denied[ref].update(ambiguous[ref])
    for ref, source in sources.items():
        if ref not in assigned:
            allowed[ref].update(record.locator for record in source.records)
            if not source.records:
                allowed[ref].add("*")
        if ref not in available or "*" in denied[ref]:
            allowed[ref].clear()
            continue
        if source.records:
            candidates = (
                {record.locator for record in source.records}
                if "*" in allowed[ref]
                else allowed[ref]
            )
            forbidden_cells = denied[ref] | {
                locator
                for record in source.records
                if record.locator in denied[ref]
                for locator in record.native_cells
            }
            rows = {
                record.locator
                for record in source.records
                if record.locator in candidates
                and record.locator not in denied[ref]
                and not any(
                    locator in forbidden_cells for locator in record.native_cells
                )
            }
            allowed[ref] = rows | {
                locator
                for record in source.records
                for locator in record.native_cells
                if locator in allowed[ref] and locator not in forbidden_cells
            }
        elif source.extraction is not None and denied[ref]:
            extraction = source.extraction
            forbidden = [
                section
                for section in extraction.sections
                if section.locator in denied[ref]
            ]
            allowed[ref] = {
                section.locator
                for section in extraction.sections
                if ("*" in allowed[ref] or section.locator in allowed[ref])
                and not any(
                    section.start < denied_section.end
                    and denied_section.start < section.end
                    for denied_section in forbidden
                )
            }
    projected_sources = [
        _source_view(source, descriptors[ref], allowed[ref])
        for ref, source in sources.items()
        if allowed[ref]
    ]
    included = {(item["source_id"], item["revision_id"]) for item in projected_sources}
    complete = {
        (item["source_id"], item["revision_id"])
        for item in projected_sources
        if item["extraction"] is not None
        and item["extraction"]
        == json.loads(
            codec.dumps(sources[item["source_id"], item["revision_id"]].extraction)
        )
    }
    projected_cases: list[dict[str, Any]] = []
    for case in raw_cases:
        if case["case_id"] not in permitted_cases:
            continue
        metadata_text(case["case_id"])
        metadata_text(case["delivery_id"])
        facts = [
            fact
            for fact in case["facts"]
            if fact["record"] in allowed[source_ref(fact["source"], "fact")]
        ]
        observations = [
            observation
            for observation in case["observations"]
            if timestamp(observation["available_at"], "observation") <= as_of
            and (
                observation["locator"]
                in allowed[source_ref(observation["source"], "observation")]
                or "*" in allowed[source_ref(observation["source"], "observation")]
            )
        ]
        for observation in observations:
            for key in ("observation_id", "actor", "mapping_version", "locator"):
                metadata_text(observation[key])
        projected_cases.append(
            {
                **{
                    key: case[key]
                    for key in ("case_id", "delivery_id", "opened_at", "business_date")
                },
                "cohort": "learning"
                if case["case_id"] in cohorts.learning
                else "current",
                "inputs": [
                    ref
                    for ref in case["inputs"]
                    if source_ref(ref, "input") in included
                ],
                "facts": facts,
                "observations": observations,
            }
        )
    projected_deliveries: list[dict[str, Any]] = []
    for item in manifest["deliveries"]:
        refs = [
            ref for ref in item["sources"] if source_ref(ref, "delivery") in included
        ]
        if refs and timestamp(item["available_at"], "delivery") <= as_of:
            metadata_text(item["delivery_id"])
            projected_deliveries.append(
                {
                    key: item[key]
                    for key in ("delivery_id", "received_at", "available_at")
                }
                | {"sources": refs}
            )
    originals = {item.path: item.content for item in bundle.originals}
    recordings: list[dict[str, Any]] = []
    for item in manifest["recordings"]:
        refs = {source_ref(ref, "recording") for ref in item["sources"]}
        if (
            timestamp(item["available_at"], "recording") > as_of
            or not refs
            or not refs <= complete
            or item["phase"] == "compile"
            or item["phase"] == "runtime"
            and item["case_id"] not in permitted_cases
            or not recording_is_permitted(item["request"], permitted_cases)
        ):
            continue
        metadata_text(item["recording_id"])
        recordings.append(
            {key: value for key, value in item.items() if key != "path"}
            | {"content": originals[item["path"]].decode("utf-8")}
        )
    data = {
        "format_version": "dex-learning-view-1",
        "consumer": "learning",
        "bundle_id": bundle.bundle_id,
        "company_id": bundle.company_id,
        "as_of": as_of.isoformat(),
        "history": history,
        "sources": projected_sources,
        "deliveries": projected_deliveries,
        "cases": projected_cases,
        "recordings": recordings,
    }
    return decode_learning_view(canonical(data))


def decode_learning_view(content: bytes) -> LearningView:
    return LearningView(canonical(validate_view(content)))


def write_learning_view(view: LearningView, path: Path) -> None:
    validated = decode_learning_view(view.content)
    if path.exists() or path.is_symlink():
        raise BundleError("output_exists")
    with tempfile.TemporaryDirectory(prefix=".dex-view-", dir=path.parent) as staging:
        staged = Path(staging) / "view"
        staged.mkdir()
        (staged / "view.json").write_bytes(validated.content)
        try:
            path.mkdir()
        except FileExistsError:
            raise BundleError("output_exists") from None
        try:
            (staged / "view.json").rename(path / "view.json")
        except OSError:
            path.rmdir()
            raise


def read_learning_view(path: Path) -> LearningView:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        if set(os.listdir(descriptor)) != {"view.json"}:
            raise BundleError("learning_view_files")
        return decode_learning_view(read_file(descriptor, "view.json"))
    finally:
        os.close(descriptor)


def serialize_learning_inputs(
    view: LearningView,
    references: tuple[EvidenceRef, ...],
    destination: Destination,
    company_id: str,
) -> bytes:
    data = validate_view(view.content)
    if destination not in DESTINATIONS:
        raise BundleError("learning_destination")
    if company_id != data["company_id"] or any(
        ref.company_id != company_id for ref in references
    ):
        raise BundleError("learning_company")
    if destination == "library":
        if references:
            raise BundleError("library_company_evidence")
        return canonical(
            {
                "format_version": "dex-learning-inputs-1",
                "destination": destination,
                "evidence": [],
            }
        )
    index: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = {}
    for source in data["sources"]:
        index["source", (source["source_id"], source["revision_id"])] = source
    for case in data["cases"]:
        index["case", (case["case_id"],)] = case
    for recording in data["recordings"]:
        index["recording", (recording["recording_id"],)] = recording
    if any((ref.kind, ref.identity) not in index for ref in references):
        raise BundleError("learning_evidence_forbidden")
    return canonical(
        {
            "format_version": "dex-learning-inputs-1",
            "destination": destination,
            "company_id": company_id,
            "as_of": data["as_of"],
            "evidence": [index[ref.kind, ref.identity] for ref in references],
        }
    )

import json
import re
from datetime import datetime
from hashlib import sha256
from typing import Any, cast

from dex import codec
from dex.bundle.evidence import validate_recordings
from dex.bundle.history import load_cases, source_ref
from dex.bundle.model import BundleError, Delivery, Record, Source
from dex.bundle.provenance import origin
from dex.bundle.validation import (
    business_date,
    canonical,
    fields,
    items,
    object_value,
    parse_json,
    text,
    timestamp,
)
from dex.core import events as e
from dex.core import program as p


def metadata_text(value: object) -> str:
    result = text(value, "projection metadata")
    if (
        result.startswith(("/", "~"))
        or "\\" in result
        or "://" in result
        or "\x00" in result
        or any(part in {".", "..", "eval"} for part in result.split("/"))
    ):
        raise BundleError("projection_metadata_capability")
    return result


def exam_boundary(end: datetime) -> datetime:
    first = end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month = end.year * 12 + end.month - 1 - 3 + (end != first)
    year, zero_month = divmod(month, 12)
    if year < 1:
        raise BundleError("history_interval_too_early")
    return first.replace(year=year, month=zero_month + 1)


def recording_is_permitted(raw: object, cases: set[str]) -> bool:
    request = codec.loads(json.dumps(raw), e.RecordingRequest)
    _metadata(
        [
            request.work.address.node_id,
            request.artifact.program_id,
            request.artifact.revision,
            request.prompt_revision,
            request.record_revision,
        ]
    )
    if request.work.address.case_id not in cases:
        return False
    for item in request.inputs:
        _metadata(list(item.name))
        if isinstance(item.reference, p.ResultRef) and item.producer is None:
            return False
        if item.producer is not None:
            metadata_text(item.producer.node_id)
            if (
                item.producer.case_id not in cases
                or item.producer_revision is None
                or item.producer_revision < 1
            ):
                return False
    return True


def _metadata(value: object) -> None:
    if isinstance(value, dict):
        for key, child in object_value(
            cast(dict[object, object], value), "metadata"
        ).items():
            _metadata(key)
            _metadata(child)
    elif isinstance(value, list):
        for child in items(cast(list[object], value), "metadata"):
            _metadata(child)
    elif isinstance(value, str):
        metadata_text(value)


def _digest(value: object) -> str:
    result = text(value, "digest")
    if re.fullmatch("[0-9a-f]{64}", result) is None:
        raise BundleError("projection_digest")
    return result


def _source(item: dict[str, Any], cutoff: datetime) -> Source:
    fields(
        item,
        {
            "source_id",
            "revision_id",
            "sha256",
            "media_type",
            "observed_at",
            "available_at",
            "origin",
            "extraction",
            "extractor_version",
            "unresolved",
            "passages",
            "records",
        },
        {"occurred_at", "effective_date", "mapping"},
        "projected source",
    )
    _metadata(
        {
            key: value
            for key, value in item.items()
            if key not in {"extraction", "passages", "records", "unresolved"}
        }
    )
    source_id, revision = (
        text(item["source_id"], "source"),
        text(item["revision_id"], "revision"),
    )
    digest = _digest(item["sha256"])
    origin(item["origin"], "source")
    observed, available = (
        timestamp(item["observed_at"], "observed_at"),
        timestamp(item["available_at"], "available_at"),
    )
    if not observed <= available <= cutoff or (
        "occurred_at" in item
        and timestamp(item["occurred_at"], "occurred_at") > observed
    ):
        raise BundleError("projection_source_unavailable")
    if "effective_date" in item:
        business_date(item["effective_date"], "effective_date")
    if "mapping" in item:
        mapping = object_value(item["mapping"], "mapping")
        fields(
            mapping,
            {
                "version",
                "confirmed_by",
                "confirmed_at",
                "effective_from",
                "effective_until",
            },
            set(),
            "mapping",
        )
        if timestamp(mapping["confirmed_at"], "confirmed_at") > cutoff:
            raise BundleError("projection_mapping_unavailable")
        start = business_date(mapping["effective_from"], "effective_from")
        if (
            mapping["effective_until"] is not None
            and business_date(mapping["effective_until"], "effective_until") <= start
        ):
            raise BundleError("projection_mapping_interval")
    if (
        item["unresolved"] is not None
        and item["unresolved"] != "source content unresolved"
    ):
        raise BundleError("projection_unresolved")
    extraction = (
        None
        if item["extraction"] is None
        else codec.loads(json.dumps(item["extraction"]), p.SourceExtraction)
    )
    passages = items(item["passages"], "passages")
    records_raw = items(item["records"], "records")
    if extraction is None:
        if passages or records_raw or item["unresolved"] is None:
            raise BundleError("projection_missing_extraction")
        return Source(
            source_id,
            revision,
            "view.json",
            digest,
            observed,
            available,
            text(item["extractor_version"], "extractor"),
            None,
            item["unresolved"],
        )
    if (
        extraction.pin.source != source_id
        or extraction.pin.revision != revision
        or extraction.pin.original_sha256 != digest
        or extraction.pin.extraction_sha256
        != sha256(extraction.text.encode()).hexdigest()
        or len(passages) != len(extraction.sections)
    ):
        raise BundleError("projection_extraction_identity")
    _digest(extraction.pin.extraction)
    sections = {section.locator: section for section in extraction.sections}
    if len(sections) != len(extraction.sections):
        raise BundleError("projection_section_identity")
    for section, raw in zip(extraction.sections, passages, strict=True):
        _metadata([section.name, section.locator])
        passage = object_value(raw, "passage")
        fields(passage, {"original", "projected"}, set(), "passage")
        original = codec.loads(json.dumps(passage["original"]), p.Citation)
        projected = codec.loads(json.dumps(passage["projected"]), p.Citation)
        if (
            projected.pin != extraction.pin
            or (projected.section, projected.locator, projected.start, projected.end)
            != (section.name, section.locator, section.start, section.end)
            or not 0 <= section.start <= section.end <= len(extraction.text)
            or original.pin.source != source_id
            or original.pin.revision != revision
            or original.pin.original_sha256 != digest
            or original.section != projected.section
            or original.locator != projected.locator
            or original.start < 0
            or original.end - original.start != len(original.quote)
            or original.quote != projected.quote
            or extraction.text[projected.start : projected.end] != projected.quote
        ):
            raise BundleError("projection_citation_mismatch")
        _digest(original.pin.extraction)
        _digest(original.pin.extraction_sha256)
    covered = 0
    for section in sorted(extraction.sections, key=lambda value: value.start):
        if extraction.text[covered : section.start].strip("\n"):
            raise BundleError("projection_uncited_text")
        covered = max(covered, section.end)
    if extraction.text[covered:].strip("\n"):
        raise BundleError("projection_uncited_text")
    records: list[Record] = []
    identities: set[str] = set()
    for raw in records_raw:
        record = object_value(raw, "record")
        fields(record, {"locator", "values", "cells", "native_cells"}, set(), "record")
        locator = text(record["locator"], "locator")
        _metadata(locator)
        if locator in identities:
            raise BundleError("projection_record_identity")
        identities.add(locator)
        values = tuple(
            codec.loads(json.dumps(raw_value), p.NamedValue)
            for raw_value in items(record["values"], "values")
        )
        cells: list[tuple[str, str]] = []
        for raw_cell in items(record["cells"], "cells"):
            pair = items(raw_cell, "cell")
            if len(pair) != 2:
                raise BundleError("projection_cell")
            name, cell_locator = text(pair[0], "name"), text(pair[1], "locator")
            _metadata([name, cell_locator])
            if cell_locator not in sections:
                raise BundleError("projection_cell")
            cells.append((name, cell_locator))
        if [value.name for value in values] != [name for name, _ in cells] or len(
            {value.name for value in values}
        ) != len(values):
            raise BundleError("projection_record_values")
        native_cells = tuple(
            text(value, "native cell")
            for value in items(record["native_cells"], "native cells")
        )
        if (
            len(set(native_cells)) != len(native_cells)
            or not set(native_cells) <= sections.keys()
            or not {cell for _, cell in cells} <= set(native_cells)
        ):
            raise BundleError("projection_native_cells")
        records.append(Record(locator, values, tuple(cells), native_cells))
    return Source(
        source_id,
        revision,
        "view.json",
        digest,
        observed,
        available,
        text(item["extractor_version"], "extractor"),
        extraction,
        item["unresolved"],
        tuple(records),
    )


def validate_view(content: bytes) -> dict[str, Any]:
    data = parse_json(content, "learning view")
    fields(
        data,
        {
            "format_version",
            "consumer",
            "bundle_id",
            "company_id",
            "as_of",
            "history",
            "sources",
            "deliveries",
            "cases",
            "recordings",
        },
        set(),
        "learning view",
    )
    if (
        data["format_version"] != "dex-learning-view-1"
        or data["consumer"] != "learning"
    ):
        raise BundleError("learning_view_format")
    _metadata([text(data["company_id"], "company"), text(data["bundle_id"], "bundle")])
    cutoff = timestamp(data["as_of"], "as_of")
    history = object_value(data["history"], "history")
    _metadata(history)
    if history != {"kind": "none"}:
        fields(
            history,
            {"kind", "start", "end", "opening_event", "adequacy"},
            set(),
            "history",
        )
        adequacy = object_value(history["adequacy"], "adequacy")
        fields(adequacy, {"decision", "actor", "decided_at"}, set(), "adequacy")
        if timestamp(adequacy["decided_at"], "decided_at") > cutoff:
            raise BundleError("history_adequacy_unavailable")
    sources: dict[tuple[str, str], Source] = {}
    for raw_source in items(data["sources"], "sources"):
        source = _source(object_value(raw_source, "source"), cutoff)
        ref = source.source_id, source.revision_id
        if ref in sources:
            raise BundleError("projection_source_identity")
        sources[ref] = source
    deliveries: dict[str, Delivery] = {}
    delivery_raw: dict[str, bytes] = {}
    for raw in items(data["deliveries"], "deliveries"):
        item = object_value(raw, "delivery")
        fields(
            item,
            {"delivery_id", "sources", "received_at", "available_at"},
            set(),
            "delivery",
        )
        _metadata(item)
        identity = text(item["delivery_id"], "delivery")
        refs = tuple(
            source_ref(ref, "delivery") for ref in items(item["sources"], "sources")
        )
        received, available = (
            timestamp(item["received_at"], "received_at"),
            timestamp(item["available_at"], "available_at"),
        )
        if (
            identity in deliveries
            or not refs
            or len(set(refs)) != len(refs)
            or any(ref not in sources for ref in refs)
        ):
            raise BundleError("projection_delivery_identity")
        if not received <= available <= cutoff or any(
            sources[ref].available_at > available for ref in refs
        ):
            raise BundleError("projection_delivery_unavailable")
        deliveries[identity] = Delivery(identity, refs, received, available)
        delivery_raw[identity] = canonical(item)
    historical: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    for raw_case in items(data["cases"], "cases"):
        case = object_value(raw_case, "case")
        fields(
            case,
            {
                "case_id",
                "delivery_id",
                "opened_at",
                "business_date",
                "cohort",
                "inputs",
                "facts",
                "observations",
            },
            set(),
            "case",
        )
        _metadata(case)
        opened = timestamp(case["opened_at"], "opened_at")
        expected = "current"
        if history != {"kind": "none"}:
            start, end = (
                timestamp(history["start"], "history.start"),
                timestamp(history["end"], "history.end"),
            )
            if max(start, exam_boundary(end)) <= opened < end:
                raise BundleError("projection_exam_case")
            if start <= opened < exam_boundary(end):
                expected = "learning"
        if case["cohort"] != expected or opened > cutoff:
            raise BundleError("projection_case_cohort")
        for raw_observation in items(case["observations"], "observations"):
            observation = object_value(raw_observation, "observation")
            if timestamp(observation.get("available_at"), "available_at") > cutoff:
                raise BundleError("projection_observation_unavailable")
        (historical if expected == "learning" else current).append(
            {key: value for key, value in case.items() if key != "cohort"}
        )
    manifest = {
        "history": history
        if history == {"kind": "none"}
        else history | {"cases": historical},
        "cases": current,
        "sources": data["sources"],
    }
    cases = load_cases(manifest, sources, deliveries, delivery_raw)
    permitted_cases = {case.case_id for case in cases}
    recording_descriptors: list[dict[str, Any]] = []
    recording_files: dict[str, bytes] = {}
    for raw_recording in items(data["recordings"], "recordings"):
        item = object_value(raw_recording, "recording")
        if (
            item.get("phase") != "runtime"
            or timestamp(item.get("available_at"), "available_at") > cutoff
        ):
            raise BundleError("projection_recording_provenance")
        content = text(item.get("content"), "recording.content").encode()
        descriptor = {key: value for key, value in item.items() if key != "content"}
        if "path" in descriptor:
            raise BundleError("projection_metadata_capability")
        if not recording_is_permitted(descriptor.get("request"), permitted_cases):
            raise BundleError("projection_recording_lineage")
        _metadata({key: value for key, value in descriptor.items() if key != "request"})
        path = "recordings/" + sha256(content).hexdigest() + ".json"
        descriptor["path"] = path
        recording_descriptors.append(descriptor)
        recording_files[path] = content
    validate_recordings(
        recording_descriptors,
        data["company_id"],
        sources,
        cases,
        recording_files.__getitem__,
    )
    return data

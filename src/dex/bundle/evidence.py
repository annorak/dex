import json
from collections.abc import Callable
from hashlib import sha256

from dex import codec
from dex.bundle.history import source_ref
from dex.bundle.model import BundleError, Case, Source
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
from dex.core import events as e
from dex.recordings import parse_recording, request_digest


def extraction_bytes(source: Source) -> bytes:
    return canonical(
        {
            "format_version": "dex-extraction-1",
            "extractor_version": source.extractor_version,
            "extraction": None
            if source.extraction is None
            else json.loads(codec.dumps(source.extraction)),
            "unresolved": source.unresolved,
            "records": [
                {
                    "locator": record.locator,
                    "values": [
                        json.loads(codec.dumps(value)) for value in record.values
                    ],
                    "cells": [list(cell) for cell in record.cells],
                }
                for record in source.records
            ],
        }
    )


def load_snapshot(
    raw: object, source: Source, read: Callable[[str], bytes]
) -> tuple[str, bytes]:
    descriptor = object_value(raw, "extraction")
    fields(descriptor, {"path", "sha256"}, set(), "extraction")
    path = relative_path(descriptor["path"], "extraction.path")
    if not path.startswith("extractions/"):
        raise BundleError("extraction.path: expected extractions directory")
    content = read(path)
    if sha256(content).hexdigest() != descriptor["sha256"]:
        raise BundleError("extraction.sha256: hash mismatch")
    saved = parse_json(content, path)
    if saved != parse_json(extraction_bytes(source), "extraction"):
        raise BundleError(f"{source.source_id}: immutable extraction mismatch")
    if source.extraction is not None:
        extraction = source.extraction
        names: set[str] = set()
        for section in extraction.sections:
            if section.name in names or not 0 <= section.start <= section.end <= len(
                extraction.text
            ):
                raise BundleError(f"{source.source_id}: invalid extraction sections")
            names.add(section.name)
    return path, content


def validate_recordings(
    raw: object,
    company_id: str,
    sources: dict[tuple[str, str], Source],
    cases: tuple[Case, ...],
    read: Callable[[str], bytes],
) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    identities: set[str] = set()
    case_index = {case.case_id: case for case in cases}
    for value in items(raw, "recordings"):
        item = object_value(value, "recording")
        fields(
            item,
            {
                "recording_id",
                "path",
                "sha256",
                "phase",
                "input_identity",
                "prompt_version",
                "schema_version",
                "request",
                "sources",
                "observed_at",
                "available_at",
            },
            {"case_id", "ai_step", "program_version"},
            "recording",
        )
        identity = text(item["recording_id"], "recording_id")
        path = relative_path(item["path"], identity + ".path")
        if (
            identity in identities
            or path in files
            or not path.startswith("recordings/")
        ):
            raise BundleError(f"{identity}: conflicting recording identity or path")
        identities.add(identity)
        content = read(path)
        if sha256(content).hexdigest() != item["sha256"]:
            raise BundleError(f"{identity}.sha256: hash mismatch")
        request = codec.loads(json.dumps(item["request"]), e.RecordingRequest)
        if (
            request.company_id != company_id
            or item["input_identity"] != request_digest(request)
            or item["prompt_version"] != request.prompt_revision
        ):
            raise BundleError(f"{identity}: recording request identity mismatch")
        text(item["schema_version"], identity + ".schema_version")
        observed = timestamp(item["observed_at"], identity + ".observed_at")
        available = timestamp(item["available_at"], identity + ".available_at")
        refs = tuple(
            source_ref(ref, identity) for ref in items(item["sources"], identity)
        )
        if any(ref not in sources for ref in refs):
            raise BundleError(f"{identity}: missing recording source")
        if observed > available or any(
            sources[ref].available_at > available for ref in refs
        ):
            raise BundleError(f"{identity}: invalid recording chronology")
        phase = item["phase"]
        if phase == "runtime":
            case_id = text(item.get("case_id"), identity + ".case_id")
            if (
                case_id not in case_index
                or request.work.address.case_id != case_id
                or item.get("ai_step") != request.work.address.node_id
                or item.get("program_version") != request.artifact.revision
                or case_index[case_id].opened_at > available
            ):
                raise BundleError(
                    f"{identity}: recording case, step, version or chronology mismatch"
                )
        elif phase != "compile" or any(
            key in item for key in {"case_id", "ai_step", "program_version"}
        ):
            raise BundleError(f"{identity}.phase: invalid recording phase")
        recording = parse_recording(content.decode("utf-8"), request)
        if recording.recording_id != identity:
            raise BundleError(f"{identity}: recording payload identity mismatch")
        if recording.failure == "recording_schema":
            raise BundleError(f"{identity}: invalid recorded output schema")
        files[path] = content
    return files

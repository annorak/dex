from email import policy
from email.parser import BytesParser
from typing import Any

from dex.bundle.formats import XLSX, message_parts
from dex.bundle.history import source_ref
from dex.bundle.model import BundleError
from dex.bundle.validation import fields, object_value, text


def origin(raw: object, label: str) -> dict[str, Any]:
    item = object_value(raw, label + ".origin")
    kind = item.get("kind")
    required = {
        "file": {"kind", "snapshot"},
        "export": {"kind", "export_id", "source_system"},
        "connector": {"kind", "source_system", "cursor"},
        "attachment": {"kind", "message", "part", "attachment_id"},
    }
    if not isinstance(kind, str) or kind not in required:
        raise BundleError(f"{label}.origin: unknown provenance kind")
    fields(item, required[kind], set(), label + ".origin")
    for key in required[kind] - {"message"}:
        text(item[key], label + ".origin." + key)
    if kind == "attachment":
        source_ref(item["message"], label + ".origin.message")
    return item


def validate_origins(descriptors: list[Any], originals: dict[str, bytes]) -> None:
    index = {(item["source_id"], item["revision_id"]): item for item in descriptors}
    for item in descriptors:
        label = item["source_id"]
        provenance = origin(item["origin"], label)
        if item["media_type"] in {"text/csv", XLSX} and provenance["kind"] not in {
            "export",
            "attachment",
        }:
            raise BundleError(
                f"{label}.origin: table requires export and source system provenance"
            )
        if provenance["kind"] != "attachment":
            continue
        parent = index.get(source_ref(provenance["message"], label))
        if parent is None or parent["media_type"] != "message/rfc822":
            raise BundleError(f"{label}.origin: missing parent message")
        message = BytesParser(policy=policy.compat32).parsebytes(
            originals[parent["path"]]
        )
        parts = dict(message_parts(message))
        part = parts.get(provenance["part"])
        if part is None or part.get_payload(decode=True) != originals[item["path"]]:
            raise BundleError(f"{label}.origin: attachment part or bytes mismatch")
        if part.get_content_type() != item["media_type"]:
            raise BundleError(f"{label}.origin: attachment media mismatch")

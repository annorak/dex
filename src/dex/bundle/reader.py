import os
import stat
import zipfile
from collections.abc import Callable
from hashlib import sha256
from pathlib import Path
from typing import BinaryIO

from dex.bundle.evidence import load_snapshot, validate_recordings
from dex.bundle.formats import extract, source_extraction
from dex.bundle.history import load_cases, source_ref
from dex.bundle.model import Bundle, BundleError, Delivery, Original, Source
from dex.bundle.provenance import origin, validate_origins
from dex.bundle.validation import (
    business_date,
    canonical,
    fields,
    items,
    object_value,
    parse_json,
    relative_path,
    text,
    timestamp,
)

MAX_FILE_BYTES = 64 * 1024 * 1024


def read_file(root: int, path: str) -> bytes:
    current = os.dup(root)
    try:
        parts = path.split("/")
        for part in parts[:-1]:
            child = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current
            )
            os.close(current)
            current = child
        descriptor = os.open(
            parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=current
        )
        with os.fdopen(descriptor, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise BundleError(f"{path}: expected regular file")
            raw = stream.read(MAX_FILE_BYTES + 1)
            if len(raw) > MAX_FILE_BYTES:
                raise BundleError(f"{path}: file size limit")
            return raw
    except OSError as error:
        raise BundleError(
            f"{path}: missing, symlink or unreadable file ({error.strerror})"
        ) from None
    finally:
        os.close(current)


def inventory(
    root: int, prefix: str = "", bundles: frozenset[str] = frozenset()
) -> set[str]:
    found: set[str] = set()
    with os.scandir(root) as entries:
        for entry in entries:
            if not prefix and entry.name == "eval":
                continue
            path = prefix + entry.name
            if path in bundles:
                found.add(path)
                continue
            relative_path(path, path)
            if entry.is_symlink():
                raise BundleError(f"{path}: symlink")
            if entry.is_dir(follow_symlinks=False):
                descriptor = os.open(
                    entry.name,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=root,
                )
                try:
                    found.update(inventory(descriptor, path + "/", bundles))
                finally:
                    os.close(descriptor)
            else:
                found.add(path)
    return found


def admit_bundle(
    read: Callable[[str], bytes], public_files: Callable[[], set[str]]
) -> Bundle:
    manifest = parse_json(read("bundle.json"), "bundle.json")
    fields(
        manifest,
        {
            "format_version",
            "bundle_id",
            "company_id",
            "sources",
            "deliveries",
            "history",
            "recordings",
        },
        {"cases"},
        "bundle.json",
    )
    if manifest["format_version"] != "dex-company-bundle-1":
        raise BundleError("format_version: unsupported version")
    bundle_id, company_id = (
        text(manifest["bundle_id"], "bundle_id"),
        text(manifest["company_id"], "company_id"),
    )
    sources: dict[tuple[str, str], Source] = {}
    originals: dict[str, bytes] = {}
    snapshots: dict[str, bytes] = {}
    for raw in items(manifest["sources"], "sources"):
        item = object_value(raw, "source")
        fields(
            item,
            {
                "source_id",
                "revision_id",
                "path",
                "media_type",
                "sha256",
                "origin",
                "observed_at",
                "available_at",
            },
            {"occurred_at", "effective_date", "mapping", "sheet", "extraction"},
            "source",
        )
        key = (
            text(item["source_id"], "source_id"),
            text(item["revision_id"], "revision_id"),
        )
        label = "/".join(key)
        if key in sources:
            raise BundleError(f"{label}: conflicting source identity")
        source_path = relative_path(item["path"], label + ".path")
        if (
            source_path.split("/")[0] not in {"sources", "exports", "history"}
            or source_path in originals
        ):
            raise BundleError(f"{label}.path: conflicting source path")
        raw_bytes = read(source_path)
        digest = sha256(raw_bytes).hexdigest()
        if item["sha256"] != digest:
            raise BundleError(f"{label}.sha256: hash mismatch")
        origin(item["origin"], label)
        observed = timestamp(item["observed_at"], label + ".observed_at")
        available = timestamp(item["available_at"], label + ".available_at")
        if available < observed or (
            "occurred_at" in item
            and timestamp(item["occurred_at"], label + ".occurred_at") > observed
        ):
            raise BundleError(f"{label}: invalid chronology")
        if "effective_date" in item:
            business_date(item["effective_date"], label + ".effective_date")
        extracted = extract(raw_bytes, item, label)
        extraction = source_extraction(key, digest, extracted)
        originals[source_path] = raw_bytes
        sources[key] = Source(
            *key,
            source_path,
            digest,
            observed,
            available,
            extraction,
            extracted.unresolved,
            extracted.records,
        )
        if "extraction" in item:
            snapshot_path, snapshot = load_snapshot(
                item["extraction"], sources[key], read
            )
            if snapshot_path in snapshots:
                raise BundleError(f"{label}: conflicting extraction path")
            snapshots[snapshot_path] = snapshot
    validate_origins(items(manifest["sources"], "sources"), originals)
    deliveries: dict[str, Delivery] = {}
    delivery_raw: dict[str, bytes] = {}
    for raw in items(manifest["deliveries"], "deliveries"):
        item = object_value(raw, "delivery")
        fields(
            item,
            {"delivery_id", "sources", "received_at", "available_at", "origin"},
            set(),
            "delivery",
        )
        identity = text(item["delivery_id"], "delivery_id")
        encoded = canonical(item)
        if identity in delivery_raw:
            if delivery_raw[identity] != encoded:
                raise BundleError(f"{identity}: conflicting delivery identity")
            continue
        refs = tuple(
            source_ref(ref, identity) for ref in items(item["sources"], identity)
        )
        if (
            not refs
            or len(set(refs)) != len(refs)
            or any(ref not in sources for ref in refs)
        ):
            raise BundleError(f"{identity}: invalid source references")
        received = timestamp(item["received_at"], identity + ".received_at")
        available = timestamp(item["available_at"], identity + ".available_at")
        if received > available or any(
            sources[ref].available_at > available for ref in refs
        ):
            raise BundleError(f"{identity}: invalid chronology")
        origin(item["origin"], identity)
        deliveries[identity] = Delivery(identity, refs, received, available)
        delivery_raw[identity] = encoded
    cases = load_cases(manifest, sources, deliveries, delivery_raw)
    originals.update(
        validate_recordings(manifest["recordings"], company_id, sources, cases, read)
    )
    declared = {"bundle.json", *originals, *snapshots}
    actual = public_files()
    if actual != declared:
        raise BundleError(
            "files: undeclared or missing inputs " + repr(sorted(actual ^ declared))
        )
    return Bundle(
        bundle_id,
        company_id,
        canonical(manifest),
        tuple(Original(name, data) for name, data in sorted(originals.items())),
        tuple(sources.values()),
        tuple(deliveries.values()),
        cases,
        tuple(Original(name, data) for name, data in sorted(snapshots.items())),
    )


def _archive(stream: BinaryIO) -> Bundle:
    try:
        with zipfile.ZipFile(stream) as archive:
            members: dict[str, zipfile.ZipInfo] = {}
            total = 0
            for entry in archive.infolist():
                name = entry.filename
                if name == "eval/" or name.startswith("eval/"):
                    continue
                relative_path(name.rstrip("/"), "archive.path")
                if stat.S_ISLNK(entry.external_attr >> 16):
                    raise BundleError(f"{name}: symlink")
                if entry.is_dir():
                    continue
                if name in members or entry.file_size > MAX_FILE_BYTES:
                    raise BundleError(
                        f"{name}: duplicate archive path or file size limit"
                    )
                total += entry.file_size
                if total > 256 * 1024 * 1024:
                    raise BundleError("archive: expanded size limit")
                members[name] = entry

            def read(name: str) -> bytes:
                if name not in members:
                    raise BundleError(f"{name}: missing archive file")
                with archive.open(members[name]) as handle:
                    data = handle.read(MAX_FILE_BYTES + 1)
                if len(data) > MAX_FILE_BYTES:
                    raise BundleError(f"{name}: file size limit")
                return data

            return admit_bundle(read, lambda: set(members))
    except (zipfile.BadZipFile, RuntimeError) as error:
        raise BundleError(f"archive: unreadable ({error})") from None


def load_bundle(path: Path) -> Bundle:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as error:
        raise BundleError(
            f"bundle: missing, symlink or unreadable path ({error.strerror})"
        ) from None
    if stat.S_ISDIR(os.fstat(descriptor).st_mode):
        try:
            return admit_bundle(
                lambda name: read_file(descriptor, name), lambda: inventory(descriptor)
            )
        finally:
            os.close(descriptor)
    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise BundleError("bundle: expected directory or ZIP archive")
    with os.fdopen(descriptor, "rb") as stream:
        return _archive(stream)

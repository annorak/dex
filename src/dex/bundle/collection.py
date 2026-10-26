import os
from dataclasses import dataclass
from functools import partial
from hashlib import sha256
from pathlib import Path
from typing import Any

from dex.bundle.model import Bundle, BundleError
from dex.bundle.reader import admit_bundle, inventory, read_file
from dex.bundle.validation import (
    canonical,
    fields,
    items,
    object_value,
    parse_json,
    relative_path,
    text,
)
from dex.bundle.writer import write_bundle


@dataclass(frozen=True)
class Collection:
    collection_id: str
    manifest: bytes
    bundles: tuple[tuple[str, Bundle], ...]


def load_collection(path: Path) -> Collection:
    root = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        manifest = parse_json(read_file(root, path.name), "collection.json")
        fields(
            manifest,
            {"format_version", "collection_id", "bundles"},
            set(),
            "collection",
        )
        if manifest["format_version"] != "dex-company-collection-1":
            raise BundleError("collection.format_version: unsupported version")
        identity = text(manifest["collection_id"], "collection_id")
        bundles: list[tuple[str, Bundle]] = []
        companies: set[str] = set()
        identities: set[str] = set()
        paths: set[str] = set()
        for raw in items(manifest["bundles"], "bundles"):
            item = object_value(raw, "collection.bundle")
            fields(
                item,
                {"path", "bundle_id", "company_id", "manifest_sha256"},
                set(),
                "collection.bundle",
            )
            relative = relative_path(item["path"], "collection.bundle.path")
            if any(
                relative == old
                or relative.startswith(old + "/")
                or old.startswith(relative + "/")
                for old in paths
            ):
                raise BundleError("collection: conflicting bundle paths")
            paths.add(relative)
            descriptor = os.dup(root)
            try:
                for part in relative.split("/"):
                    child = os.open(
                        part,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                        dir_fd=descriptor,
                    )
                    os.close(descriptor)
                    descriptor = child
                content = read_file(descriptor, "bundle.json")
                if sha256(content).hexdigest() != item["manifest_sha256"]:
                    raise BundleError("collection.manifest_sha256: hash mismatch")
                bundle = admit_bundle(
                    partial(read_file, descriptor), partial(inventory, descriptor)
                )
            finally:
                os.close(descriptor)
            if (
                bundle.company_id != item["company_id"]
                or bundle.bundle_id != item["bundle_id"]
                or bundle.company_id in companies
                or bundle.bundle_id in identities
            ):
                raise BundleError("collection: conflicting company or bundle identity")
            companies.add(bundle.company_id)
            identities.add(bundle.bundle_id)
            bundles.append((relative, bundle))
        if not bundles:
            raise BundleError("collection: no company bundles")
        if inventory(root, bundles=frozenset(paths)) != {path.name, *paths}:
            raise BundleError("collection: undeclared inputs")
        return Collection(identity, canonical(manifest), tuple(bundles))
    finally:
        os.close(root)


def write_collection(collection: Collection, path: Path) -> None:
    if path.exists() or path.is_symlink():
        raise BundleError("output_exists")
    path.mkdir()
    entries: list[dict[str, Any]] = []
    for relative, bundle in collection.bundles:
        destination = path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        write_bundle(bundle, destination)
        entries.append(
            {
                "path": relative,
                "bundle_id": bundle.bundle_id,
                "company_id": bundle.company_id,
                "manifest_sha256": sha256(
                    (destination / "bundle.json").read_bytes()
                ).hexdigest(),
            }
        )
    (path / "collection.json").write_bytes(
        canonical(
            {
                "format_version": "dex-company-collection-1",
                "collection_id": collection.collection_id,
                "bundles": entries,
            }
        )
    )

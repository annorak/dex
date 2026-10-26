import os
import tempfile
import zipfile
from hashlib import sha256
from pathlib import Path

from dex.bundle.evidence import extraction_bytes
from dex.bundle.model import Bundle, BundleError
from dex.bundle.validation import canonical, parse_json


def bundle_files(bundle: Bundle) -> dict[str, bytes]:
    manifest = parse_json(bundle.manifest, "bundle")
    files = {original.path: original.content for original in bundle.originals}
    sources = {
        (source.source_id, source.revision_id): source for source in bundle.sources
    }
    for descriptor in manifest["sources"]:
        source = sources[(descriptor["source_id"], descriptor["revision_id"])]
        content = extraction_bytes(source)
        identity = sha256(canonical([source.source_id, source.revision_id])).hexdigest()
        path = "extractions/" + identity + ".json"
        descriptor["extraction"] = {"path": path, "sha256": sha256(content).hexdigest()}
        files[path] = content
    files["bundle.json"] = canonical(manifest)
    return dict(sorted(files.items()))


def write_bundle(bundle: Bundle, path: Path, *, archive: bool = False) -> None:
    if path.exists() or path.is_symlink():
        raise BundleError("output_exists")
    files = bundle_files(bundle)
    if archive:
        with (
            path.open("xb") as stream,
            zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as output,
        ):
            for name, content in files.items():
                entry = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                entry.create_system = 3
                entry.external_attr = 0o100644 << 16
                entry.compress_type = zipfile.ZIP_STORED
                output.writestr(entry, content)
        return
    with tempfile.TemporaryDirectory(prefix=".dex-bundle-", dir=path.parent) as staging:
        staged = Path(staging) / "bundle"
        staged.mkdir()
        for name, content in files.items():
            destination = staged / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            destination.chmod(0o644)
            os.utime(destination, (0, 0))
        if path.exists() or path.is_symlink():
            raise BundleError("output_exists")
        staged.rename(path)

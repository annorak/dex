import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

from dex import codec
from dex.bundle.model import BundleError
from dex.bundle.reader import load_bundle
from dex.bundle.validation import canonical
from dex.core import events as e
from dex.core import program as p
from dex.core import runtime as r
from dex.workspace import Workspace
from dex.workspace_command import load_session


def check_bundle(path: Path) -> int:
    try:
        if path.name == "collection.json":
            from dex.bundle.collection import load_collection

            collection = load_collection(path)
            print(
                canonical(
                    {
                        "format": "dex-bundle-check-1",
                        "collection_id": collection.collection_id,
                        "companies": [
                            bundle.company_id for _, bundle in collection.bundles
                        ],
                    }
                ).decode(),
                end="",
            )
            return 0
        bundle = load_bundle(path)
        print(
            canonical(
                {
                    "format": "dex-bundle-check-1",
                    "bundle_id": bundle.bundle_id,
                    "company_id": bundle.company_id,
                    "sources": len(bundle.sources),
                    "deliveries": len(bundle.deliveries),
                    "cases": len(bundle.cases),
                    "unresolved": [
                        {"source_id": source.source_id, "reason": source.unresolved}
                        for source in bundle.sources
                        if source.unresolved is not None
                    ],
                }
            ).decode(),
            end="",
        )
        return 0
    except (ValueError, OSError) as error:
        print(
            json.dumps({"format": "dex-bundle-error-1", "code": str(error)}),
            file=sys.stderr,
        )
        return 2


def run_bundle(path: Path, program_path: Path, workspace_path: Path, out: Path) -> int:
    try:
        bundle = load_bundle(path)
        artifact = codec.loads(program_path.read_text(), p.StructuralArtifact)
        pin = r.artifact_pin(artifact)
        session = load_session()
        if bundle.company_id != session.company.company_id:
            raise BundleError("session_company")
        available = {entry.pin: entry for entry in bundle.catalog.entries}
        if any(available.get(entry.pin) != entry for entry in artifact.sources.entries):
            raise BundleError("program_source_evidence")
        cases = tuple(case for case in bundle.cases if not case.historical)
        if not cases:
            raise BundleError("cases: no runnable cases")
        required_sources = {ref for case in cases for ref in case.inputs}
        if any(
            source.unresolved
            for source in bundle.sources
            if (source.source_id, source.revision_id) in required_sources
        ):
            raise BundleError("unresolved_case_evidence")
        if out.exists():
            raise BundleError("output_exists")
        if not workspace_path.is_file():
            raise BundleError(
                "workspace_required: register and approve this program first"
            )
        now = datetime.now(UTC)
        if any(source.available_at > now for source in bundle.sources):
            raise BundleError("source evidence not yet available")
        with Workspace(workspace_path, session, {}) as workspace:
            if workspace.catalog.artifacts.get(pin) != artifact:
                raise BundleError("verified_artifact_hash_mismatch")
            commands = tuple(
                e.StartCase(
                    e.CommandMeta(
                        "run/" + case.case_id,
                        session.actor,
                        case.opened_at,
                        now,
                        workspace.state.revision,
                    ),
                    case.case_id,
                    pin,
                    case.facts,
                    case.business_date,
                    case.delivery_id,
                    case.evidence_sha256,
                    case.delivery_sha256,
                    case.admission_key,
                    tuple(
                        source.extraction.pin
                        for source in bundle.sources
                        if (source.source_id, source.revision_id) in case.inputs
                        and source.extraction is not None
                    ),
                    session.company,
                )
                for case in cases
            )
            result = workspace.start_cases(workspace.state.revision, commands)
            if isinstance(result, r.Refused):
                print(
                    json.dumps(
                        {
                            "format": "dex-run-result-1",
                            "status": "refused",
                            "code": result.code,
                        }
                    ),
                    file=sys.stderr,
                )
                return 1
            succeeded = all(
                workspace.state.cases[case.case_id].status == "succeeded"
                for case in cases
            )
            output = {
                "format": "dex-run-result-1",
                "company_id": bundle.company_id,
                "artifact": json.loads(codec.dumps(pin)),
                "revision": workspace.state.revision,
                "cases": [
                    {
                        "case_id": case.case_id,
                        "status": workspace.state.cases[case.case_id].status,
                        "failure": workspace.state.cases[case.case_id].failure,
                    }
                    for case in cases
                ],
            }
        out.mkdir(parents=True, exist_ok=False)
        (out / "result.json").write_bytes(canonical(output))
        print(canonical(output).decode(), end="")
        return 0 if succeeded else 1
    except (ValueError, OSError, sqlite3.Error) as error:
        print(
            json.dumps({"format": "dex-run-error-1", "code": str(error)}),
            file=sys.stderr,
        )
        return 2

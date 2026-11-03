from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from threading import Barrier
from typing import Any
from unittest.mock import patch

import pytest

from dex.bundle.model import BundleError
from dex.bundle.projection import (
    materialize_learning,
    read_learning_view,
    write_learning_view,
)
from dex.bundle.reader import load_bundle
from dex.bundle.validation import canonical
from dex.demo.build import build_world
from dex.demo.world_1 import Invoice
from dex.demo.world_1 import make_cases as invoice_cases
from dex.eval.scenarios import run_scenario
from dex.eval.world_1_checks import byte_manifest
from dex.eval.world_2 import artifacts, expectation
from dex.eval.world_2_checks import (
    history_checks,
    isolation_checks,
    key_checks,
    nested_checks,
    packet_checks,
    read_json,
    stream_checks,
    variation_checks,
    wait_checks,
)


@pytest.fixture(scope="module")
def world(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("world2") / "world"
    build_world("world-2", 7, path)
    return path


@pytest.fixture(scope="module")
def seed11(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("world2-seed11") / "world"
    build_world("world-2", 11, path)
    return path


def test_exact_packets_and_hidden_rule_absence(world: Path) -> None:
    assert packet_checks(world, Path("docs/sources")) == {
        "packet_files": 2,
        "exact_bytes": True,
        "hidden_rule_absent": True,
    }


def test_exact_history_calendar_and_full_cohorts(world: Path) -> None:
    actual = history_checks(world)
    assert actual["learning"] == [f"H{number:03d}" for number in range(1, 37)]
    assert actual["exam"] == [f"H{number:03d}" for number in range(37, 49)]


def test_exact_overlapping_nested_memberships(world: Path) -> None:
    actual = nested_checks(world)
    assert actual["both_services"] == [
        "H002",
        "H004",
        "H006",
        "H008",
        "H014",
        "H016",
        "H018",
        "H020",
        "H026",
        "H028",
        "H030",
        "H032",
        "H038",
        "H040",
        "H042",
        "H044",
    ]


def test_exact_client_waits_and_public_response_records(world: Path) -> None:
    actual = wait_checks(world)
    assert actual["three_day_history"] == [
        "H002",
        "H006",
        "H010",
        "H014",
        "H018",
        "H022",
        "H026",
        "H030",
        "H034",
        "H038",
        "H042",
        "H046",
    ]


def test_mistakes_hidden_evidence_and_independent_key(world: Path) -> None:
    assert key_checks(world) == {
        "mistakes": ["H008", "H019", "H031", "H044"],
        "learning_evidence": ["H006", "H018", "H030"],
        "exam_evidence": ["H042"],
        "keys_independent_and_frozen": True,
    }


def test_stream_exact_cutoffs_and_fixture_only_outcomes(world: Path) -> None:
    assert stream_checks(world)["january_10"] == {
        "complete": ["S001", "S002", "S003", "S004", "S005", "S006", "S007", "S009"],
        "waiting": ["S008", "S010"],
        "not_opened": ["S011", "S012", "S013", "S014", "S015", "S016"],
    }


def test_public_admission_and_real_learning_boundary(world: Path) -> None:
    actual = isolation_checks(world)
    assert actual["learning_cases"] == 36
    assert all(
        value is True for name, value in actual.items() if name != "learning_cases"
    )


def test_saved_projection_opens_without_original_bundle(
    world: Path, tmp_path: Path
) -> None:
    bundle = load_bundle(world / "world-2/veldren")
    view = materialize_learning(
        bundle, datetime.fromisoformat("2026-10-01T10:00:00-04:00")
    )
    target = tmp_path / "learning"
    write_learning_view(view, target)
    original = Path.read_bytes

    def read(path: Path) -> bytes:
        assert not path.is_relative_to(world)
        return original(path)

    with patch.object(Path, "read_bytes", read):
        assert read_learning_view(target).content == view.content


def test_seed11_only_changes_synthetic_display_names(world: Path, seed11: Path) -> None:
    assert variation_checks(world, seed11) == {
        "changed_name_exports": 128,
        "only_permitted_variation": True,
    }


def test_deterministic_native_exports_and_keys(world: Path, tmp_path: Path) -> None:
    target = tmp_path / "repeat"
    build_world("world-2", 7, target)
    assert byte_manifest(world) == byte_manifest(target)


def test_complete_collection_preserves_world1_and_world2_bytes(
    world: Path, tmp_path: Path
) -> None:
    standalone, collection = tmp_path / "world1", tmp_path / "all"
    build_world("world-1", 7, standalone)
    actual = build_world("all", 7, collection)
    assert actual["companies"] == ["C1", "C2", "C3"]
    assert byte_manifest(standalone / "world-1") == byte_manifest(
        collection / "world-1"
    )
    assert byte_manifest(world / "world-2") == byte_manifest(collection / "world-2")
    manifest = read_json(collection / "collection.json")
    assert [entry["path"] for entry in manifest["bundles"]] == [
        "world-1/bramblewick",
        "world-1/fennor",
        "world-2/veldren",
    ]


def test_independent_five_day_answer_has_exact_authorization_and_payload() -> None:
    case: dict[str, Any] = {
        "case_id": "S004",
        "client_id": "S004-client",
        "client_name": "Synthetic test",
        "sponsor": "S004-sponsor",
        "opened_at": "2027-01-04T08:00:00-05:00",
        "sites": [
            {
                "site_id": "S004-site-1",
                "services": ["payroll"],
                "payroll_cutover_date": "2027-01-18",
                "employees": [
                    {
                        "employee_id": "E1",
                        "display_name": "Synthetic one",
                        "status": "active",
                    }
                ],
            },
            {
                "site_id": "S004-site-2",
                "services": ["benefits"],
                "plan_code": "SYNTH-PLAN-A",
                "eligibility_group": "standard",
                "site_contact": "Contact two",
                "employees": [
                    {
                        "employee_id": "E2",
                        "display_name": "Synthetic two",
                        "status": "active",
                    }
                ],
            },
        ],
    }
    original = deepcopy(case)
    answer = expectation(case)
    wait = answer["waits"][0]
    assert (
        wait["issued_at"],
        wait["due_at"],
        wait["overdue_at"],
        wait["responded_at"],
    ) == (
        "2027-01-04T10:00:00-05:00",
        "2027-01-07T23:59:59-05:00",
        "2027-01-08T00:00:00-05:00",
        "2027-01-09T09:00:00-05:00",
    )
    assert wait["changes"] == [
        {"site_id": "S004-site-1", "field": "pay_frequency", "value": "biweekly"}
    ]
    assert answer["branches"][1]["ready_at"] == "2027-01-04T09:00:00-05:00"
    assert answer["summary"]["ready_at"] == "2027-01-09T10:00:00-05:00"
    assert answer["business_decision"]["decided_at"] == "2027-01-10T10:00:00-05:00"
    assert answer["engine_authority"]["approved_at"] == "2027-01-10T11:00:00-05:00"
    assert answer["effects"][0]["applied_at"] == "2027-01-10T12:00:00-05:00"
    expected = deepcopy(original["sites"])
    expected[0]["pay_frequency"] = "biweekly"
    assert answer["effects"][0]["payload"] == {
        "client_id": "S004-client",
        "sites": expected,
    }
    assert case == original


def test_observed_answer_changes_cannot_change_correct_key(world: Path) -> None:
    fixture = read_json(world / "world-2/veldren/eval/fixture.json")
    original = artifacts(fixture)
    fixture["observed"]["H008"]["activated_at"] = "2025-11-28T12:00:00-05:00"
    changed = artifacts(fixture)
    assert original["answer-key.json"] == changed["answer-key.json"]
    assert original["answer-sheet.json"] != changed["answer-sheet.json"]


@pytest.mark.parametrize(
    "number,observed,correct",
    [
        ("H008", "2025-11-27T12:00:00-05:00", "2025-11-28T12:00:00-05:00"),
        ("H019", "2026-02-15T12:00:00-05:00", "2026-02-16T12:00:00-05:00"),
        ("H031", "2026-05-15T12:00:00-04:00", "2026-05-16T12:00:00-04:00"),
        ("H044", "2026-08-27T12:00:00-04:00", "2026-08-28T12:00:00-04:00"),
    ],
)
def test_independent_observed_premature_activations(
    world: Path, number: str, observed: str, correct: str
) -> None:
    bundle = world / "world-2/veldren"
    assert (
        read_json(bundle / "eval/answer-sheet.json")[number]["activated_at"] == observed
    )
    assert read_json(bundle / "eval/answer-key.json")[number]["completed_at"] == correct


@pytest.mark.parametrize(
    "scenario", sorted(Path("tests/scenarios").glob("world2-*.json")), ids=str
)
def test_fixture_scenario_contracts(
    world: Path, seed11: Path, tmp_path: Path, scenario: Path
) -> None:
    specification = read_json(scenario)
    specification.update(input_world=str(world), seed11_world=str(seed11))
    source = tmp_path / "scenario.json"
    source.write_bytes(canonical(specification))
    assert run_scenario(source, tmp_path / "run") == 0
    actual = read_json(tmp_path / "run/actual.json")
    assert actual["execution_claimed"] is False
    assert all(read_json(tmp_path / "run/expected.json")["matches"].values())


@pytest.mark.parametrize(
    "selector,seed,reason",
    [
        ("unknown", 7, "world_unavailable"),
        ("world-2", -1, "invalid_seed"),
        ("all", 2**63, "invalid_seed"),
        ("world-2", True, "invalid_seed"),
    ],
)
def test_refused_selector_or_seed_preserves_existing_state(
    tmp_path: Path, selector: str, seed: int, reason: str
) -> None:
    target = tmp_path / "keep"
    target.write_bytes(b"existing")
    with pytest.raises(BundleError, match=reason):
        build_world(selector, seed, target)
    assert target.read_bytes() == b"existing" and list(tmp_path.iterdir()) == [target]


@pytest.mark.parametrize("selector", ["world-2", "all"])
@pytest.mark.parametrize("kind", ["directory", "file", "symlink"])
def test_refused_destination_preserves_state(
    tmp_path: Path, selector: str, kind: str
) -> None:
    target = tmp_path / "target"
    if kind == "directory":
        target.mkdir()
        (target / "keep").write_bytes(b"existing")
    elif kind == "file":
        target.write_bytes(b"existing")
    else:
        target.symlink_to("missing")
    before = byte_manifest(tmp_path) if kind != "symlink" else str(target.readlink())
    with pytest.raises(BundleError, match="output_exists"):
        build_world(selector, 7, target)
    assert (
        byte_manifest(tmp_path) if kind != "symlink" else str(target.readlink())
    ) == before


def test_failed_veldren_after_world1_staging_publishes_nothing(tmp_path: Path) -> None:
    seen: list[str] = []

    def small(company: str, seed: int) -> tuple[Invoice, ...]:
        seen.append(company)
        return invoice_cases(company, seed)[:3]

    def fail(seed: int, packets: dict[str, bytes]) -> Any:
        assert seen == ["C1", "C2"]
        assert (
            len(list(tmp_path.glob(".dex-world-*/collection/world-1/*/bundle.json")))
            == 2
        )
        raise BundleError("fixture_invalid_veldren")

    with (
        patch("dex.demo.build.make_cases", small),
        patch("dex.demo.world_2.company_bundle", fail),
    ):
        with pytest.raises(BundleError, match="fixture_invalid_veldren"):
            build_world("all", 7, tmp_path / "collection")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("kind", ["missing", "symlink", "invalid_utf8"])
def test_refused_packet_preserves_existing_state(tmp_path: Path, kind: str) -> None:
    (tmp_path / "keep").write_bytes(b"existing")
    before = byte_manifest(tmp_path)
    read_bytes, is_symlink = Path.read_bytes, Path.is_symlink

    def read(path: Path) -> bytes:
        if path.parts[-2:] == ("veldren", "handbook.md"):
            if kind == "missing":
                raise FileNotFoundError("required Veldren packet missing")
            if kind == "invalid_utf8":
                return b"\xff"
        return read_bytes(path)

    def linked(path: Path) -> bool:
        return (
            kind == "symlink" and path.parts[-2:] == ("veldren", "handbook.md")
        ) or is_symlink(path)

    with (
        patch.object(Path, "read_bytes", read),
        patch.object(Path, "is_symlink", linked),
    ):
        with pytest.raises(BundleError, match="source_packet_unavailable"):
            build_world("world-2", 7, tmp_path / "world")
    assert byte_manifest(tmp_path) == before


@pytest.mark.parametrize("kind", ["missing", "symlink"])
def test_refused_parent_preserves_existing_state(tmp_path: Path, kind: str) -> None:
    parent = tmp_path / "parent"
    (tmp_path / "keep").write_bytes(b"existing")
    if kind == "symlink":
        parent.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(BundleError, match="output_parent"):
        build_world("world-2", 7, parent / "world")
    assert (tmp_path / "keep").read_bytes() == b"existing"
    assert not (parent / "world").exists()
    assert sorted(path.name for path in tmp_path.iterdir()) == (
        ["keep", "parent"] if kind == "symlink" else ["keep"]
    )


def test_publication_conflict_preserves_complete_winner(tmp_path: Path) -> None:
    target = tmp_path / "world"
    barrier = Barrier(2)
    original = Path.mkdir

    def arrive(path: Path, *args: Any, **kwargs: Any) -> None:
        if path == target:
            barrier.wait(timeout=30)
        original(path, *args, **kwargs)

    def build() -> str:
        try:
            build_world("world-2", 7, target)
            return "built"
        except BundleError as error:
            return str(error)

    with (
        patch.object(Path, "mkdir", arrive),
        ThreadPoolExecutor(max_workers=2) as executor,
    ):
        futures = [executor.submit(build) for _ in range(2)]
        assert sorted(future.result(timeout=60) for future in futures) == [
            "built",
            "output_exists",
        ]
    assert len(load_bundle(target / "world-2/veldren").cases) == 64

import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path
from threading import Barrier
from typing import Any
from unittest.mock import patch

import pytest

from dex.bundle.model import BundleError
from dex.bundle.projection import materialize_learning
from dex.bundle.reader import load_bundle
from dex.demo.build import build_world, company_bundle, invoice_message
from dex.demo.native import csv_bytes, xlsx_bytes
from dex.demo.world_1 import PACKETS, Invoice, make_cases
from dex.eval.world_1 import expectation
from dex.eval.world_1_checks import (
    key_checks,
    membership_checks,
    mistake_checks,
    packet_checks,
    path_checks,
    stream_checks,
)
from dex.eval.world_1_scenarios import prove_key_independence


@pytest.fixture(scope="module")
def world(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("world1") / "world"
    build_world("world-1", 7, path)
    return path


def test_exact_packet_bytes_and_container_metadata(world: Path) -> None:
    assert packet_checks(world, Path("docs/sources"))["packet_files"] == 7


def test_exact_history_and_cohort_membership(world: Path) -> None:
    assert membership_checks(world)["chronology_exact"] is True


def test_independent_exact_mistake_sets(world: Path) -> None:
    assert mistake_checks(world)["mistake_splits"] == [[18, 6], [15, 5]]


def test_exact_duplicate_cancellation_and_snow_sets(world: Path) -> None:
    assert path_checks(world)["eligible_snow"] == [9, 4]


def test_opening_and_later_event_dates(world: Path) -> None:
    assert stream_checks(world)["opening_cases"] == 19


def test_key_construction_cannot_execute_programs(world: Path) -> None:
    prove_key_independence(world)
    assert key_checks(world)["keys_frozen"] is True


@pytest.mark.parametrize("slug,company", [("bramblewick", "C1"), ("fennor", "C2")])
def test_public_validation_does_not_open_evaluator(
    world: Path, slug: str, company: str
) -> None:
    original = os.open
    attempted: list[str] = []

    def guarded(path: Any, *args: Any, **kwargs: Any) -> int:
        if (
            isinstance(path, (str, bytes, Path))
            and "eval" in Path(os.fsdecode(path)).parts
        ):
            attempted.append(str(path))
            raise AssertionError("public loader read evaluator")
        return original(path, *args, **kwargs)

    with patch("os.open", guarded):
        bundle = load_bundle(world / "world-1" / slug)
    assert bundle.company_id == company and len(bundle.cases) == 5400
    assert attempted == []


@pytest.mark.parametrize("slug,company", [("bramblewick", "C1"), ("fennor", "C2")])
def test_complete_generated_learning_projection(
    world: Path, slug: str, company: str
) -> None:
    bundle = load_bundle(world / "world-1" / slug)
    view = materialize_learning(
        bundle, datetime.fromisoformat("2026-09-30T23:59:59-04:00")
    )
    data = json.loads(view.content)
    assert [item["case_id"] for item in data["cases"]] == [
        f"{company}-H{n:04d}" for n in range(1, 2701)
    ]
    assert all(
        word not in view.content
        for word in (
            b"-H2701",
            b"-H3600",
            b"answer-key",
            b"mistakes.json",
            b"W1-A",
            b"board-limit-notice",
            b"service-confirmation",
            b"Rillhaven Rise",
        )
    )
    mixed = next(
        source
        for source in data["sources"]
        if source["source_id"] == company + "-reconciled-actions"
    )
    assert b"record:2" in json.dumps(mixed).encode()
    assert b"record:3" not in json.dumps(mixed).encode()
    assert str(world).encode() not in view.content
    assert all(source["available_at"] < "2026-10-01" for source in data["sources"])


def test_native_serialization_is_deterministic() -> None:
    rows = [["Amount", "Date"], ["100.01", "01/02/2026"]]
    assert xlsx_bytes(rows) == xlsx_bytes(rows)
    assert csv_bytes(rows) == b"Amount,Date\n100.01,01/02/2026\n"
    for item in make_cases("C1", 7)[:6]:
        assert invoice_message(item) == invoice_message(item)


def test_seed_changes_permitted_values_only() -> None:
    a, b, repeat = make_cases("C1", 7), make_cases("C1", 11), make_cases("C1", 11)
    assert b == repeat and a != b
    assert [(item.case_id, item.received, item.issue, item.format) for item in a] == [
        (item.case_id, item.received, item.issue, item.format) for item in b
    ]
    assert next(item for item in b if item.case_id == "C1-S0001").amount == 180000


@pytest.mark.parametrize(
    "world_name,seed,reason",
    [
        ("all", 7, "world_unavailable"),
        ("world-2", 7, "world_unavailable"),
        ("world-1", -1, "invalid_seed"),
        ("world-1", 2**63, "invalid_seed"),
    ],
)
def test_invalid_build_preserves_destination(
    tmp_path: Path, world_name: str, seed: int, reason: str
) -> None:
    target = tmp_path / "existing"
    target.mkdir()
    sentinel = target / "keep"
    sentinel.write_bytes(b"preserved")
    with pytest.raises(BundleError, match=reason):
        build_world(world_name, seed, target)
    assert (
        list(target.iterdir()) == [sentinel] and sentinel.read_bytes() == b"preserved"
    )


@pytest.mark.parametrize("kind", ["directory", "file", "symlink"])
def test_existing_destination_refused(tmp_path: Path, kind: str) -> None:
    target = tmp_path / "target"
    if kind == "directory":
        target.mkdir()
    elif kind == "file":
        target.write_bytes(b"existing")
    else:
        target.symlink_to(tmp_path / "absent")
    with pytest.raises(BundleError, match="output_exists"):
        build_world("world-1", 7, target)
    assert target.is_symlink() if kind == "symlink" else target.exists()


def case(**changes: object) -> dict[str, Any]:
    return {
        "case_id": "C1-test",
        "company": "C1",
        "cohort": "stream",
        "received": "2027-01-01T09:00:00-05:00",
        "invoice_date": "2026-12-20",
        "community": "C1-C03",
        "vendor": "C1-C03-V07",
        "number": " 0001-A ",
        "amount": 180000,
        "work": "Maintenance",
        "format": "F1",
        "issue": "",
        "prior": "",
        **changes,
    }


@pytest.mark.parametrize(
    "received,amount,route",
    [
        ("2026-12-31T09:00:00-05:00", 150000, "manager"),
        ("2026-12-31T09:00:00-05:00", 150001, "board"),
        ("2027-01-01T09:00:00-05:00", 180000, "manager"),
        ("2027-01-01T09:00:00-05:00", 180001, "board"),
    ],
)
def test_independent_dated_limit_answers(
    received: str, amount: int, route: str
) -> None:
    assert expectation(case(received=received, amount=amount))["decision"] == route


@pytest.mark.parametrize(
    "received,posting", [("2027-01-05", "2026-12"), ("2027-01-06", "2027-01")]
)
def test_independent_closing_and_late_date_answers(received: str, posting: str) -> None:
    answer = expectation(
        case(received=received + "T09:00:00-05:00", invoice_date="2024-01-01")
    )
    assert answer["posting_month"] == posting
    assert answer["due_date"] == "2024-01-31"


@pytest.mark.parametrize(
    "received,amount,required",
    [
        ("2027-01-31", 250001, False),
        ("2027-02-01", 250000, False),
        ("2027-02-01", 250001, True),
    ],
)
def test_independent_service_boundary_answers(
    received: str, amount: int, required: bool
) -> None:
    assert (
        expectation(case(received=received + "T09:00:00-05:00", amount=amount))[
            "service_confirmation"
        ]
        == required
    )


def test_small_inputs_use_real_admission_and_packets() -> None:
    cases = make_cases("C1", 7)[:3]
    packets = {
        name: (Path("docs/sources/bramblewick") / name).read_bytes()
        for name in PACKETS["bramblewick"]
    }
    bundle, specification = company_bundle("C1", 7, packets, cases)
    assert len(bundle.cases) == 3 and len(specification["cases"]) == 3
    assert bundle.cases[0].business_date == date(2025, 10, 1)


def test_publication_conflict_uses_deterministic_barrier(tmp_path: Path) -> None:
    from dex.demo.world_1 import make_cases as real_cases

    barrier = Barrier(2)
    target = tmp_path / "world"
    original_mkdir = Path.mkdir

    def arrive(path: Path, *args: Any, **kwargs: Any) -> None:
        if path == target:
            barrier.wait(timeout=30)
        original_mkdir(path, *args, **kwargs)

    def build() -> str:
        try:
            build_world("world-1", 7, target)
            return "built"
        except BundleError as error:
            return str(error)

    def small_cases(company: str, seed: int) -> tuple[Invoice, ...]:
        return real_cases(company, seed)[:3]

    with (
        patch("dex.demo.build.make_cases", small_cases),
        patch.object(Path, "mkdir", arrive),
        ThreadPoolExecutor(max_workers=2) as executor,
    ):
        futures = [executor.submit(build), executor.submit(build)]
        assert sorted(future.result(timeout=60) for future in futures) == [
            "built",
            "output_exists",
        ]
    assert load_bundle(target / "world-1/bramblewick").company_id == "C1"
    assert load_bundle(target / "world-1/fennor").company_id == "C2"


def test_second_company_failure_does_not_publish_partial_world(tmp_path: Path) -> None:
    from dex.demo.world_1 import make_cases as real_cases

    def fail_second(company: str, seed: int) -> Any:
        if company == "C2":
            raise BundleError("test_invalid_second_company")
        return real_cases(company, seed)[:3]

    before = tuple(tmp_path.iterdir())
    with (
        patch("dex.demo.build.make_cases", fail_second),
        pytest.raises(BundleError, match="test_invalid_second_company"),
    ):
        build_world("world-1", 7, tmp_path / "world")
    assert tuple(tmp_path.iterdir()) == before


@pytest.mark.parametrize(
    "received,amount,route",
    [
        ("2026-11-14", 200001, "manager"),
        ("2026-11-15", 200000, "manager"),
        ("2026-11-15", 200001, "board"),
    ],
)
def test_rillhaven_receipt_boundaries(received: str, amount: int, route: str) -> None:
    assert (
        expectation(
            case(
                community="C1-C09", received=received + "T09:00:00-05:00", amount=amount
            )
        )["decision"]
        == route
    )


def test_fennor_closing_and_second_signer() -> None:
    first = expectation(
        case(
            company="C2",
            community="C2-C02",
            vendor="C2-V02",
            received="2027-01-10T09:00:00-05:00",
            amount=1000000,
        )
    )
    next_day = expectation(
        case(
            company="C2",
            community="C2-C02",
            vendor="C2-V02",
            received="2027-01-11T09:00:00-05:00",
            amount=1000001,
        )
    )
    assert (first["posting_month"], first["due_date"], first["second_signer"]) == (
        "2026-12",
        "2026-12-30",
        False,
    )
    assert (next_day["posting_month"], next_day["second_signer"]) == ("2027-01", True)
    assert next_day["waits"][0]["actor"] != next_day["waits"][1]["actor"]


def test_opening_native_inputs_leave_questions_unanswered() -> None:
    cases = {item.case_id: item for item in make_cases("C1", 7)}
    unknown, attachment = invoice_message(cases["C1-S0005"])
    unknown += attachment or b""
    ambiguous, _ = invoice_message(cases["C1-S0006"])
    assert b"Juniperfen Works" in unknown and b"-V11" not in unknown
    assert b"confirm which property" in ambiguous and b"C1-C02" not in ambiguous
    assert cases["C1-S0002"].amount == 100000


def test_arrival_sources_do_not_supply_a_parsed_invoice_shortcut(world: Path) -> None:
    for slug in ("bramblewick", "fennor"):
        root = world / "world-1" / slug
        manifest = json.loads((root / "bundle.json").read_bytes())
        sources = {source["source_id"]: source for source in manifest["sources"]}
        for item in [*manifest["history"]["cases"], *manifest["cases"]]:
            assert item["facts"] == []
            assert all(
                sources[ref["source_id"]]["available_at"] == item["opened_at"]
                for ref in item["inputs"]
            )
            assert all(
                sources[ref["source_id"]]["media_type"]
                in ("message/rfc822", "application/pdf")
                for ref in item["inputs"]
            )


def test_mime_policy_preserves_existing_extraction_contract() -> None:
    from email import policy
    from email.parser import BytesParser

    from dex.bundle.formats import extract

    samples = [
        invoice_message(item)[0]
        for company in ("C1", "C2")
        for item in make_cases(company, 7)[:8]
    ]
    samples.extend(
        [
            b"Content-Type: text/plain; charset=utf-8\r\nSubject: =?UTF-8?Q?caf=C3=A9?=\r\n\r\nBody",
            b"Content-Type: text/html; charset=utf-8\r\nContent-Disposition: inline; filename*=utf-8''caf%C3%A9.html\r\n\r\n<b>Body</b>",
            b"Content-Type: multipart/mixed; boundary=absent\r\n\r\nBroken",
            b"Content-Type: text/plain; charset=unknown-charset\r\n\r\nBody",
        ]
    )

    def previous_parser(**kwargs: Any) -> BytesParser:
        return BytesParser(policy=policy.default)

    for raw in samples:
        descriptor = {"path": "source.eml", "media_type": "message/rfc822"}
        current = extract(raw, descriptor, "message")
        with patch("dex.bundle.formats.BytesParser", previous_parser):
            previous = extract(raw, descriptor, "message")
        assert current == previous


def test_history_contains_native_evidence_for_unwritten_policies(world: Path) -> None:
    import csv

    for company, slug, first_due in (
        ("C1", "bramblewick", "2025-10-10"),
        ("C2", "fennor", "10/10/2025"),
    ):
        path = world / "world-1" / slug / "history/actions/2025-10-01.csv"
        rows = {
            row["case_id"]: row for row in csv.DictReader(path.read_text().splitlines())
        }
        assert rows[company + "-H0007"]["due_date"] == first_due
        assert rows[company + "-H0007"]["posting_month"] == "2025-09"
        assert rows[company + "-H0003"]["approval_roles"] == "manager"
        assert rows[company + "-H0004"]["approval_roles"] == "board"
        if company == "C2":
            assert rows["C2-H0006"]["approval_roles"] == "board;finance_signer"


def test_missing_packet_refuses_before_creating_destination(tmp_path: Path) -> None:
    original = Path.read_bytes

    def missing_packet(path: Path) -> bytes:
        if path.name == "procedure.md":
            raise FileNotFoundError("required packet missing")
        return original(path)

    target = tmp_path / "world"
    with (
        patch.object(Path, "read_bytes", missing_packet),
        pytest.raises(BundleError, match="source_packet_unavailable"),
    ):
        build_world("world-1", 7, target)
    assert list(tmp_path.iterdir()) == []

from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from dex.bundle.formats import XLSX
from dex.bundle.model import Bundle, BundleError
from dex.bundle.reader import load_bundle
from dex.core import language as lang
from dex.core import program as p
from dex.eval.bundle_fixture import (
    add_source,
    make_bundle,
    mapping,
    supported_program,
    workbook,
)


def test_equivalent_money_dates_and_status_meanings(tmp_path: Path) -> None:
    bundles: list[Bundle] = []
    for label, row, money, dates in (
        ("iso", "1234,2026-01-02,P", "cents", "iso"),
        ("us", "12.34,01/02/2026,P", "decimal-dollars", "us"),
    ):
        path = tmp_path / label
        manifest = make_bundle(path)
        add_source(
            path,
            manifest,
            "table.csv",
            ("Amount,Date,Status\n" + row + "\n").encode(),
            "text/csv",
            mapping=mapping(money, dates),
        )
        bundles.append(load_bundle(path))
    values = bundles[0].sources[1].records[0].values
    assert values == bundles[1].sources[1].records[0].values
    assert values == (
        p.NamedValue("amount", p.MoneyValue(1234)),
        p.NamedValue("date", p.DateValue(date(2026, 1, 2))),
        p.NamedValue("status", p.TextValue("posted")),
    )
    assert bundles[0].sources[1].records[0].cells[0] == ("amount", "record:2/column:1")


@pytest.mark.parametrize(
    "amount", ["0.001", "1234567890123456789012345678.001", "NaN", "1e-2", "Infinity"]
)
def test_money_never_rounds(tmp_path: Path, amount: str) -> None:
    manifest = make_bundle(tmp_path / "bundle")
    add_source(
        tmp_path / "bundle",
        manifest,
        "table.csv",
        f"Amount,Date,Status\n{amount},2026-01-01,P\n".encode(),
        "text/csv",
        mapping=mapping("decimal-dollars"),
    )
    with pytest.raises(BundleError, match="record:2/Amount"):
        load_bundle(tmp_path / "bundle")


@pytest.mark.parametrize(
    "value", ["2026-02-30", "20260101", "2026-1-1", "2026-01-01T00:00:00", "2026-W01-1"]
)
def test_business_dates_are_strict(tmp_path: Path, value: str) -> None:
    path = tmp_path / "bundle"
    manifest = make_bundle(path)
    add_source(
        path,
        manifest,
        "table.csv",
        f"Amount,Date,Status\n100,{value},P\n".encode(),
        "text/csv",
        mapping=mapping(),
    )
    with pytest.raises(BundleError, match="record:2/Date"):
        load_bundle(path)


def test_xlsx_sheet_selection_preserves_cells(tmp_path: Path) -> None:
    for label, selected, expected in (
        ("default", None, 1234),
        ("selected", "Second", 5678),
    ):
        path = tmp_path / label
        manifest = make_bundle(path)
        options: dict[str, object] = {} if selected is None else {"sheet": selected}
        add_source(
            path,
            manifest,
            "table.xlsx",
            workbook(),
            XLSX,
            mapping=mapping("decimal-dollars", "us"),
            **options,
        )
        source = load_bundle(path).sources[1]
        assert source.records[0].values[0].value == p.MoneyValue(expected)
        assert source.records[0].cells[0][1] == f"sheet:{selected or 'First'}/cell:A2"


def test_unicode_citation_uses_exact_codepoints(tmp_path: Path) -> None:
    path = tmp_path / "bundle"
    make_bundle(path)
    draft, sources = supported_program(path)
    source = sources.entries[0]
    quote = "Café 🦉"
    start = source.text.index(quote)
    citation = p.Citation(source.pin, "all", "text", start, start + len(quote), quote)
    assert isinstance(draft.root, p.CodeStep)
    cited = replace(
        draft,
        root=replace(
            draft.root, metadata=replace(draft.root.metadata, citations=(citation,))
        ),
    )
    assert isinstance(
        p.verify_program(cited, sources, lang.DEFAULT_LIMITS), p.ExecutionPending
    )
    wrong = replace(citation, end=start + len(quote.encode()))
    rejected = replace(
        cited,
        root=replace(
            cited.root, metadata=replace(draft.root.metadata, citations=(wrong,))
        ),
    )
    result = p.verify_program(rejected, sources, lang.DEFAULT_LIMITS)
    assert isinstance(result, p.StructuralFailure)
    assert "citation_quote" in {item.code for item in result.diagnostics}


def test_email_attachment_and_page_provenance(tmp_path: Path) -> None:
    from dex.eval.bundle_scenarios import email_attachments

    actual, _ = email_attachments(tmp_path)
    assert all(actual.values())
    bundle = load_bundle(tmp_path / "bundle")
    assert bundle.sources[4].extraction is not None


def test_unreadable_xlsx_and_image_pdf_stay_unresolved(tmp_path: Path) -> None:
    from dex.eval.bundle_scenarios import xlsx_sheets

    actual, _ = xlsx_sheets(tmp_path)
    assert actual["unreadable_unresolved"] and actual["image_unresolved"]


@pytest.mark.parametrize(
    ("encoding", "raw", "expected"),
    [("excel-1900", "61", date(1900, 3, 1)), ("excel-1904", "0", date(1904, 1, 1))],
)
def test_explicit_excel_date_epochs(
    tmp_path: Path, encoding: str, raw: str, expected: date
) -> None:
    path = tmp_path / "bundle"
    manifest = make_bundle(path)
    add_source(
        path,
        manifest,
        "table.csv",
        f"Amount,Date,Status\n100,{raw},P\n".encode(),
        "text/csv",
        mapping=mapping("cents", encoding),
    )
    assert load_bundle(path).sources[1].records[0].values[1].value == p.DateValue(
        expected
    )

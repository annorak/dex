import csv
import io
import re
import zipfile
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from email import policy
from email.message import Message
from email.parser import BytesParser
from functools import lru_cache
from hashlib import sha256
from html.parser import HTMLParser
from typing import Any, cast
from xml.etree import ElementTree as ET

from dex.bundle.model import BundleError, Record
from dex.bundle.validation import (
    business_date,
    canonical,
    fields,
    items,
    object_value,
    text,
    timestamp,
)
from dex.core import program as p

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
MAX_EXPANDED_BYTES = 64 * 1024 * 1024


class Unreadable(ValueError):
    pass


@dataclass(frozen=True)
class Extraction:
    text: str
    sections: tuple[p.Section, ...]
    records: tuple[Record, ...]
    unresolved: str | None
    version: str


class _HTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.hidden += 1
        if tag in {"p", "div", "br", "li", "tr", "h1", "h2", "h3"} and not self.hidden:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


def _html(raw: bytes, charset: str) -> str:
    parser = _HTML()
    parser.feed(raw.decode(charset))
    parser.close()
    return "".join(parser.parts)


@lru_cache(maxsize=1)
def _pdf(raw: bytes) -> tuple[tuple[str, str], ...]:
    from pypdf import PdfReader
    from pypdf.errors import PyPdfError

    try:
        reader = PdfReader(io.BytesIO(raw), strict=True)
        if reader.is_encrypted:
            raise Unreadable("encrypted PDF")
        result = tuple(
            (f"page:{index}", page.extract_text())
            for index, page in enumerate(reader.pages, 1)
        )
        if not result or any(not content.strip() for _, content in result):
            raise Unreadable(
                "image-only or unreadable PDF page; supply text, OCR is unavailable"
            )
        return result
    except (PyPdfError, ValueError, KeyError, TypeError, RuntimeError) as error:
        raise Unreadable(f"PDF extraction unresolved: {error}") from None


def message_parts(message: Message, prefix: str = "part") -> list[tuple[str, Message]]:
    payload = message.get_payload()
    if isinstance(payload, list):
        result: list[tuple[str, Message]] = []
        for index, child in enumerate(cast(list[object], payload), 1):
            if not isinstance(child, Message):
                raise Unreadable("unreadable multipart email")
            result.extend(message_parts(cast(Message, child), f"{prefix}:{index}"))
        return result
    return [(prefix, message)]


def _email(raw: bytes) -> list[tuple[str, str]]:
    message = BytesParser(policy=policy.compat32).parsebytes(raw)
    if message.defects:
        raise Unreadable("malformed email")
    parts = [
        ("headers", "\n".join(f"{key}: {value}" for key, value in message.raw_items()))
    ]
    for locator, part in message_parts(message):
        payload = part.get_payload(decode=True)
        if not isinstance(payload, bytes) or part.defects:
            raise Unreadable(f"{locator}: unreadable message part")
        media = part.get_content_type()
        if media == "application/vnd.ms-excel" or (
            part.get_filename() or ""
        ).lower().endswith(".xls"):
            raise BundleError(f"{locator}: XLS is unsupported; convert to XLSX or CSV")
        if media == "application/pdf":
            parts.extend(
                (locator + "/" + page, content) for page, content in _pdf(payload)
            )
        elif media == "text/html":
            parts.append(
                (locator, _html(payload, part.get_content_charset() or "utf-8"))
            )
        elif media in {"text/plain", "text/markdown", "text/csv"}:
            parts.append(
                (locator, payload.decode(part.get_content_charset() or "utf-8"))
            )
        else:
            raise Unreadable(f"{locator}: unsupported attachment {media}; supply text")
    return parts


def _xlsx(
    raw: bytes, selected: str | None
) -> tuple[list[list[str]], list[list[str]], str]:
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = archive.infolist()
            if (
                len({entry.filename for entry in members}) != len(members)
                or sum(entry.file_size for entry in members) > MAX_EXPANDED_BYTES
            ):
                raise Unreadable("XLSX container limit or duplicate members")
            workbook = ET.fromstring(archive.read("xl/workbook.xml"))
            sheets = workbook.findall(f"{NS}sheets/{NS}sheet")
            names = [sheet.attrib["name"] for sheet in sheets]
            if not names or len(set(names)) != len(names):
                raise Unreadable("XLSX missing or duplicate sheets")
            chosen = names[0] if selected is None else selected
            if chosen not in names:
                raise BundleError(f"sheet: unknown XLSX sheet {chosen!r}")
            sheet = sheets[names.index(chosen)]
            relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            targets = [
                entry
                for entry in relationships
                if entry.attrib.get("Id") == sheet.attrib[REL]
            ]
            if len(targets) != 1 or targets[0].attrib.get("TargetMode") == "External":
                raise Unreadable("XLSX external or missing sheet relationship")
            target = targets[0].attrib["Target"]
            target = target[1:] if target.startswith("/xl/") else "xl/" + target
            if ".." in target.split("/") or "\\" in target:
                raise Unreadable("XLSX unsafe sheet relationship")
            strings: list[str] = []
            if "xl/sharedStrings.xml" in archive.namelist():
                strings = [
                    "".join(node.itertext())
                    for node in ET.fromstring(archive.read("xl/sharedStrings.xml"))
                ]
            xml = ET.fromstring(archive.read(target))
            rows: list[list[str]] = []
            locators: list[list[str]] = []
            row_ids: set[str] = set()
            for row in xml.findall(f"{NS}sheetData/{NS}row"):
                row_id = row.attrib["r"]
                if row_id in row_ids or re.fullmatch(r"[1-9][0-9]*", row_id) is None:
                    raise Unreadable("XLSX conflicting row identity")
                row_ids.add(row_id)
                values: dict[int, tuple[str, str]] = {}
                for cell in row.findall(f"{NS}c"):
                    address = cell.attrib["r"]
                    match = re.fullmatch(r"([A-Z]+)([1-9][0-9]*)", address)
                    if match is None or cell.find(f"{NS}f") is not None:
                        raise Unreadable(
                            "XLSX invalid cell or formula; supply resolved values"
                        )
                    column = 0
                    for character in match[1]:
                        column = column * 26 + ord(character) - ord("A") + 1
                    if (
                        column > 16384
                        or column in values
                        or match[2] != row.attrib["r"]
                    ):
                        raise Unreadable("XLSX conflicting cell identity")
                    kind = cell.attrib.get("t", "n")
                    value = cell.findtext(f"{NS}v", "")
                    if kind == "s":
                        value = strings[int(value)]
                    elif kind == "inlineStr":
                        value = "".join(
                            node.text or "" for node in cell.findall(f"{NS}is//{NS}t")
                        )
                    elif kind not in {"n", "str", "d", "b"}:
                        raise Unreadable(f"XLSX unsupported cell kind {kind}")
                    values[column] = value, f"sheet:{chosen}/cell:{address}"
                if values:
                    width = max(values)
                    rows.append(
                        [
                            values.get(index, ("", ""))[0]
                            for index in range(1, width + 1)
                        ]
                    )
                    locators.append(
                        [
                            values.get(
                                index,
                                (
                                    "",
                                    f"sheet:{chosen}/row:{row.attrib['r']}/column:{index}",
                                ),
                            )[1]
                            for index in range(1, width + 1)
                        ]
                    )
            return rows, locators, chosen
    except (
        zipfile.BadZipFile,
        ET.ParseError,
        KeyError,
        IndexError,
        ValueError,
        OSError,
        RuntimeError,
    ) as error:
        if isinstance(error, BundleError):
            raise
        raise Unreadable(f"XLSX extraction unresolved: {error}") from None


def _value(raw: str, mapping: dict[str, Any], field: str) -> p.Value:
    kind = mapping["kind"]
    if kind == "text":
        return p.TextValue(raw)
    if kind == "status":
        meanings = object_value(mapping.get("meanings"), field + ".meanings")
        if raw not in meanings:
            raise BundleError(f"{field}: unresolved status meaning {raw!r}")
        return p.TextValue(text(meanings[raw], field + ".meaning"))
    if kind == "date":
        encoding = mapping.get("encoding")
        if encoding in {"excel-1900", "excel-1904"}:
            if re.fullmatch(r"[0-9]{1,7}", raw) is None:
                raise BundleError(f"{field}: invalid Excel business date")
            serial = int(raw)
            if encoding == "excel-1900" and serial in {0, 60}:
                raise BundleError(f"{field}: invalid Excel business date")
            epoch = date(1904, 1, 1) if encoding == "excel-1904" else date(1899, 12, 31)
            try:
                return p.DateValue(
                    epoch
                    + timedelta(
                        days=serial - (encoding == "excel-1900" and serial > 60)
                    )
                )
            except OverflowError:
                raise BundleError(f"{field}: invalid Excel business date") from None
        if encoding == "iso":
            return p.DateValue(business_date(raw, field))
        if encoding == "us" and re.fullmatch(r"\d{2}/\d{2}/\d{4}", raw):
            month, day, year = map(int, raw.split("/"))
            try:
                return p.DateValue(date(year, month, day))
            except ValueError:
                pass
        raise BundleError(f"{field}: invalid business date or encoding")
    if kind in {"integer", "money"}:
        if re.fullmatch(r"[+-]?[0-9]+(?:\.[0-9]+)?", raw) is None or len(raw) > 100:
            raise BundleError(f"{field}: invalid exact number")
        try:
            numerator, denominator = Decimal(raw).as_integer_ratio()
            if kind == "money":
                encoding = mapping.get("encoding")
                if encoding not in {"cents", "decimal-dollars"}:
                    raise BundleError(f"{field}: unknown money encoding")
                if encoding == "decimal-dollars":
                    numerator *= 100
            if numerator % denominator:
                raise BundleError(
                    f"{field}: fractional cents"
                    if kind == "money"
                    else f"{field}: fractional integer"
                )
            return (
                p.MoneyValue(numerator // denominator)
                if kind == "money"
                else p.IntValue(numerator // denominator)
            )
        except InvalidOperation:
            raise BundleError(f"{field}: invalid exact number") from None
    raise BundleError(f"{field}: unknown mapping kind")


def _table(
    raw: bytes, media: str, descriptor: dict[str, Any], label: str
) -> Extraction:
    if media == XLSX:
        selected = descriptor.get("sheet")
        if selected is not None:
            selected = text(selected, label + ".sheet")
        rows, locators, sheet = _xlsx(raw, selected)
        version = "xlsx-xml-1/" + sheet
    else:
        rows = list(
            csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True)
        )
        locators = [
            [f"record:{row_index}/column:{index}" for index in range(1, len(row) + 1)]
            for row_index, row in enumerate(rows, 1)
        ]
        version = "csv-1"
    if (
        not rows
        or len(set(rows[0])) != len(rows[0])
        or any(not name for name in rows[0])
    ):
        raise BundleError(f"{label}: missing or conflicting table columns")
    mapping_raw = descriptor.get("mapping")
    mapping = (
        None if mapping_raw is None else object_value(mapping_raw, label + ".mapping")
    )
    columns: list[dict[str, Any]] = []
    if mapping is not None:
        fields(
            mapping,
            {
                "version",
                "confirmed_by",
                "confirmed_at",
                "effective_from",
                "effective_until",
                "columns",
            },
            set(),
            label + ".mapping",
        )
        text(mapping["version"], label + ".mapping.version")
        text(mapping["confirmed_by"], label + ".mapping.confirmed_by")
        timestamp(mapping["confirmed_at"], label + ".mapping.confirmed_at")
        start = business_date(
            mapping["effective_from"], label + ".mapping.effective_from"
        )
        if (
            mapping["effective_until"] is not None
            and business_date(
                mapping["effective_until"], label + ".mapping.effective_until"
            )
            <= start
        ):
            raise BundleError(f"{label}: invalid mapping interval")
        columns = [
            object_value(value, label + ".mapping.column")
            for value in items(mapping["columns"], label)
        ]
        targets: set[str] = set()
        mapped: set[str] = set()
        for column in columns:
            fields(
                column,
                {"source", "target", "kind"},
                {"encoding", "meanings"},
                label + ".mapping.column",
            )
            kind = text(column["kind"], label + ".mapping.kind")
            if kind not in {"text", "status", "integer", "money", "date"}:
                raise BundleError(f"{label}.mapping.kind: unknown kind")
            required = {"source", "target", "kind"}
            if kind in {"money", "date"}:
                required.add("encoding")
                encoding = text(column.get("encoding"), label + ".mapping.encoding")
                allowed = (
                    {"cents", "decimal-dollars"}
                    if kind == "money"
                    else {"iso", "us", "excel-1900", "excel-1904"}
                )
                if encoding not in allowed:
                    raise BundleError(f"{label}.mapping.encoding: unknown encoding")
            if kind == "status":
                required.add("meanings")
                meanings = object_value(
                    column.get("meanings"), label + ".mapping.meanings"
                )
                if not meanings:
                    raise BundleError(f"{label}.mapping.meanings: empty meanings")
                for meaning in meanings.values():
                    text(meaning, label + ".mapping.meaning")
            fields(column, required, set(), label + ".mapping.column")
            source, target = (
                text(column["source"], label),
                text(column["target"], label),
            )
            if source not in rows[0] or source in mapped or target in targets:
                raise BundleError(f"{label}: conflicting mapping or unknown column")
            mapped.add(source)
            targets.add(target)
        if not columns:
            raise BundleError(f"{label}: empty confirmed mapping")
    pieces: list[str] = []
    sections: list[p.Section] = []
    records: list[Record] = []
    position = 0
    for number, row in enumerate(rows, 1):
        if len(row) != len(rows[0]):
            raise BundleError(f"{label}/record:{number}: table width mismatch")
        for index, value in enumerate(row):
            locator = locators[number - 1][index]
            sections.append(
                p.Section(locator, locator, position, position + len(value))
            )
            pieces.append(value + "\n")
            position += len(value) + 1
        if number > 1:
            values = tuple(
                p.NamedValue(
                    column["target"],
                    _value(
                        row[rows[0].index(column["source"])],
                        column,
                        f"{label}/record:{number}/{column['source']}",
                    ),
                )
                for column in columns
            )
            cells = tuple(
                (
                    column["target"],
                    locators[number - 1][rows[0].index(column["source"])],
                )
                for column in columns
            )
            records.append(
                Record(f"record:{number}", values, cells, tuple(locators[number - 1]))
            )
    return Extraction(
        "".join(pieces),
        tuple(sections),
        tuple(records),
        None if mapping is not None else "mapping requires explicit confirmation",
        version,
    )


def extract(raw: bytes, descriptor: dict[str, Any], label: str) -> Extraction:
    media = text(descriptor["media_type"], label + ".media_type")
    if media == "application/vnd.ms-excel" or descriptor["path"].lower().endswith(
        ".xls"
    ):
        raise BundleError(f"{label}: XLS is unsupported; convert to XLSX or CSV")
    try:
        if media in {"text/csv", XLSX}:
            return _table(raw, media, descriptor, label)
        if media in {"text/plain", "text/markdown"}:
            content = raw.decode("utf-8")
            sections = [p.Section("all", "text", 0, len(content))]
            headings = list(
                re.finditer(
                    r"(?m)^(?:#{1,6}\s+)?([0-9]+(?:\.[0-9]+)*)(?:[.)]|\s)\s*", content
                )
            )
            names: set[str] = set()
            for index, match in enumerate(headings):
                name = match[1]
                if name in names:
                    raise Unreadable("duplicate numbered section")
                names.add(name)
                end = (
                    headings[index + 1].start()
                    if index + 1 < len(headings)
                    else len(content)
                )
                sections.append(p.Section(name, "section:" + name, match.start(), end))
            return Extraction(content, tuple(sections), (), None, "utf8-1")
        if media == "message/rfc822":
            parts = _email(raw)
        elif media == "text/html":
            parts = [("html", _html(raw, "utf-8"))]
        elif media == "application/pdf":
            parts = _pdf(raw)
        else:
            raise Unreadable(f"unsupported media type {media}; supply text")
        pieces: list[str] = []
        sections = list[p.Section]()
        position = 0
        for locator, content in parts:
            sections.append(
                p.Section(locator, locator, position, position + len(content))
            )
            pieces.append(content + "\n")
            position += len(content) + 1
        return Extraction(
            "".join(pieces), tuple(sections), (), None, "mime-pdf-1/pypdf-6.19.0"
        )
    except (UnicodeError, LookupError, csv.Error, Unreadable) as error:
        return Extraction("", (), (), str(error), "unresolved-1")


def source_extraction(
    key: tuple[str, str], digest: str, extraction: Extraction
) -> p.SourceExtraction | None:
    if not extraction.text and extraction.unresolved:
        return None
    identity = sha256(canonical([*key, digest, extraction.version])).hexdigest()
    return p.SourceExtraction(
        p.SourcePin(
            *key,
            digest,
            identity,
            sha256(extraction.text.encode()).hexdigest(),
        ),
        extraction.text,
        extraction.sections,
    )

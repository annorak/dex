import json
import re
from datetime import date, datetime
from pathlib import PurePosixPath
from typing import Any, cast

from dex.bundle.model import BundleError


def canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode()


def object_value(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BundleError(f"{field}: expected object")
    result = cast(dict[object, Any], value)
    if any(type(key) is not str for key in result):
        raise BundleError(f"{field}: expected text keys")
    return cast(dict[str, Any], result)


def items(value: object, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise BundleError(f"{field}: expected array")
    return cast(list[Any], value)


def text(value: object, field: str) -> str:
    if type(value) is not str or not value.strip():
        raise BundleError(f"{field}: expected nonempty text")
    return value


def fields(
    value: dict[str, Any], required: set[str], optional: set[str], field: str
) -> None:
    if not required <= value.keys() or value.keys() - required - optional:
        raise BundleError(f"{field}: missing or unknown fields")


def timestamp(value: object, field: str) -> datetime:
    try:
        result = datetime.fromisoformat(text(value, field))
        if result.utcoffset() is None:
            raise ValueError
        return result
    except ValueError:
        raise BundleError(f"{field}: invalid timestamp with UTC offset") from None


def business_date(value: object, field: str) -> date:
    try:
        raw = text(value, field)
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw) is None:
            raise ValueError
        return date.fromisoformat(raw)
    except ValueError:
        raise BundleError(f"{field}: invalid business date") from None


def relative_path(value: object, field: str) -> str:
    raw = text(value, field)
    path = PurePosixPath(raw)
    if (
        path.is_absolute()
        or "\\" in raw
        or ":" in raw
        or "\x00" in raw
        or any(part in {"", ".", "..", "eval"} for part in raw.split("/"))
    ):
        raise BundleError(f"{field}: unsafe path")
    return raw


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BundleError(f"{key}: duplicate field")
        result[key] = value
    return result


def parse_json(raw: bytes, field: str) -> dict[str, Any]:
    try:
        value: object = json.loads(raw, object_pairs_hook=_pairs)
        canonical(value)
        return object_value(value, field)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise BundleError(f"{field}: invalid JSON ({error})") from None

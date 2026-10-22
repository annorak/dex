import json
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from enum import Enum
from types import UnionType
from typing import (
    Any,
    Literal,
    TypeAliasType,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

from dex.core import authority as a
from dex.core import events as e
from dex.core import language as lang
from dex.core import program as p


class CodecError(ValueError):
    pass


_TYPES: dict[str, type[Any]] = {
    value.__name__: value
    for module in (a, e, lang, p)
    for value in vars(module).values()
    if isinstance(value, type)
    and value.__module__ == module.__name__
    and (is_dataclass(value) or issubclass(value, Enum))
}
_HINTS: dict[type[Any], dict[str, Any]] = {}


def _encode(value: object) -> object:
    if isinstance(value, Enum):
        return {"$enum": type(value).__name__, "value": value.value}
    if value is None or type(value) in (bool, int, str):
        return value
    if isinstance(value, datetime):
        return {"$datetime": value.isoformat()}
    if isinstance(value, date):
        return {"$date": value.isoformat()}
    if isinstance(value, (tuple, frozenset)):
        items = cast(tuple[object, ...] | frozenset[object], value)
        return {
            "$tuple" if isinstance(value, tuple) else "$set": [
                _encode(item)
                for item in (
                    items if isinstance(items, tuple) else sorted(items, key=repr)
                )
            ]
        }
    if (
        is_dataclass(value)
        and not isinstance(value, type)
        and type(value).__name__ in _TYPES
    ):
        return {
            "$type": type(value).__name__,
            **{
                field.name: _encode(getattr(value, field.name))
                for field in fields(value)
            },
        }
    raise CodecError("unsupported_type")


def dumps(value: object) -> str:
    return json.dumps(
        {"format": "dex-typed-1", "value": _encode(value)},
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _matches(value: object, hint: Any) -> bool:
    if isinstance(hint, TypeAliasType):
        return _matches(value, hint.__value__)
    origin, args = get_origin(hint), get_args(hint)
    if origin is Literal:
        return any(type(value) is type(option) and value == option for option in args)
    if origin is UnionType:
        return any(_matches(value, option) for option in args)
    if origin in (tuple, frozenset):
        if type(value) is not origin:
            return False
        items = cast(tuple[object, ...] | frozenset[object], value)
        if origin is frozenset or len(args) == 2 and args[1] is Ellipsis:
            return all(_matches(item, args[0]) for item in items)
        return len(items) == len(args) and all(
            _matches(item, item_hint)
            for item, item_hint in zip(items, args, strict=True)
        )
    return type(value) is hint


def _decode(value: Any, depth: int = 0) -> Any:
    if depth > 160:
        raise CodecError("nesting_limit")
    if value is None or type(value) in (bool, int, str):
        return value
    if not isinstance(value, dict):
        raise CodecError("typed_value")
    value = cast(dict[str, Any], value)
    keys = set(value)
    if keys == {"$datetime"}:
        return datetime.fromisoformat(value["$datetime"])
    if keys == {"$date"}:
        return date.fromisoformat(value["$date"])
    if keys in ({"$tuple"}, {"$set"}):
        tag = next(iter(keys))
        if not isinstance(value[tag], list):
            raise CodecError("typed_collection")
        items = tuple(_decode(item, depth + 1) for item in cast(list[Any], value[tag]))
        if tag == "$set" and len(frozenset(items)) != len(items):
            raise CodecError("duplicate_value")
        return items if tag == "$tuple" else frozenset(items)
    if keys == {"$enum", "value"}:
        cls = _TYPES.get(value["$enum"])
        if cls is None or not issubclass(cls, Enum):
            raise CodecError("unknown_type")
        return cls(value["value"])
    cls = _TYPES.get(value.get("$type", ""))
    if cls is None or not is_dataclass(cls):
        raise CodecError("unknown_type")
    if cls is e.StartSandbox and "review_mode" not in keys:
        value = {**value, "review_mode": "review"}
        keys = set(value)
    if keys != {"$type", *(field.name for field in fields(cls))}:
        raise CodecError("typed_fields")
    hints = _HINTS.get(cls)
    if hints is None:
        hints = get_type_hints(
            cls,
            localns={
                "e": e,
                "p": p,
                "a": a,
                "CheckedFunctions": lang.CheckedFunctions,
                "LanguageFailure": lang.LanguageFailure,
            },
        )
        _HINTS[cls] = hints
    decoded = {name: _decode(value[name], depth + 1) for name in hints}
    if any(not _matches(item, hints[name]) for name, item in decoded.items()):
        raise CodecError("typed_field_type")
    return cls(**decoded)


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CodecError("duplicate_field")
        result[key] = value
    return result


def loads[T](raw: str, expected: type[T]) -> T:
    try:
        value = json.loads(raw, object_pairs_hook=_pairs)
        if not isinstance(value, dict):
            raise CodecError("format_version")
        value = cast(dict[str, Any], value)
        if set(value) != {"format", "value"} or value["format"] != "dex-typed-1":
            raise CodecError("format_version")
        decoded = _decode(value["value"])
        if type(decoded) is not expected:
            raise CodecError("root_type")
        return cast(T, decoded)
    except (TypeError, KeyError, RecursionError) as error:
        raise CodecError("invalid_encoding") from error

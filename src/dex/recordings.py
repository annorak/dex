import json
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import cast

from dex.core import events as e
from dex.core import program as p

type Json = None | bool | int | float | str | list[Json] | dict[str, Json]
MAX_RECORDING_BYTES = 1024 * 1024


class RecordingError(ValueError):
    pass


def request_digest(request: e.RecordingRequest) -> str:
    return sha256(("dex-recording-request-1\n" + repr(request)).encode()).hexdigest()


def _object(value: Json, fields: set[str]) -> dict[str, Json]:
    if not isinstance(value, dict) or value.keys() != fields:
        raise RecordingError("recording_schema")
    return value


def _text(value: Json) -> str:
    if not isinstance(value, str) or not value:
        raise RecordingError("recording_identity")
    return value


def _integer(value: Json) -> int:
    if type(value) is not int:
        raise RecordingError("recording_schema")
    return value


def _decode(value: Json, schema: p.Schema, depth: int = 0) -> p.Value:
    if depth > 48:
        raise RecordingError("recording_schema")
    if schema == p.Scalar.BOOLEAN and type(value) is bool:
        return p.BoolValue(value)
    if schema == p.Scalar.INTEGER:
        return p.IntValue(_integer(value))
    if schema == p.Scalar.MONEY:
        return p.MoneyValue(_integer(value))
    if schema == p.Scalar.TEXT and isinstance(value, str):
        return p.TextValue(value)
    if schema == p.Scalar.DATE and isinstance(value, str):
        try:
            return p.DateValue(date.fromisoformat(value))
        except ValueError as error:
            raise RecordingError("recording_schema") from error
    if isinstance(schema, p.OptionalSchema):
        return (
            p.AbsentValue()
            if value is None
            else p.PresentValue(_decode(value, schema.item, depth + 1))
        )
    if isinstance(schema, p.RecordSchema):
        obj = _object(value, {item.name for item in schema.fields})
        return p.RecordValue(
            schema.name,
            tuple(
                p.NamedValue(item.name, _decode(obj[item.name], item.schema, depth + 1))
                for item in schema.fields
            ),
        )
    if isinstance(schema, p.ReferenceSchema):
        obj = _object(value, {"record", "key_field", "key"})
        if obj["record"] != schema.record or obj["key_field"] != schema.key_field:
            raise RecordingError("recording_schema")
        return p.ResolvedRefValue(schema.record, schema.key_field, _text(obj["key"]))
    if isinstance(schema, p.TaggedSchema):
        obj = _object(value, {"tag", "value"})
        for variant in schema.variants:
            if obj["tag"] == variant.name:
                return p.TaggedValue(
                    variant.name, _decode(obj["value"], variant.schema, depth + 1)
                )
    if isinstance(schema, p.KeyedSchema) and isinstance(value, list):
        entries: list[p.KeyedEntry] = []
        for item in value:
            record = _decode(item, schema.item, depth + 1)
            assert isinstance(record, p.RecordValue)
            key = next(
                field.value for field in record.fields if field.name == schema.key_field
            )
            if not isinstance(key, p.TextValue):
                raise RecordingError("recording_schema")
            entries.append(p.KeyedEntry(key.value, record))
        return p.KeyedValue(tuple(entries))
    raise RecordingError("recording_schema")


def _unique(pairs: list[tuple[str, Json]]) -> dict[str, Json]:
    result: dict[str, Json] = {}
    for key, value in pairs:
        if key in result:
            raise RecordingError("recording_duplicate_field")
        result[key] = value
    return result


def _constant(value: str) -> None:
    raise RecordingError("recording_number")


def parse_recording(text: str, request: e.RecordingRequest) -> e.Recording:
    if len(text.encode()) > MAX_RECORDING_BYTES:
        raise RecordingError("recording_size")
    try:
        raw = cast(
            Json, json.loads(text, object_pairs_hook=_unique, parse_constant=_constant)
        )
    except RecordingError:
        raise
    except (ValueError, RecursionError) as error:
        raise RecordingError("recording_json") from error
    obj = _object(
        raw,
        {
            "format",
            "request_digest",
            "recording_id",
            "model",
            "input_tokens",
            "output_tokens",
            "value",
            "failure",
        },
    )
    if obj["format"] != "dex-recording-1":
        raise RecordingError("recording_version")
    if obj["request_digest"] != request_digest(request):
        raise RecordingError("recording_request")
    recording_id, model = _text(obj["recording_id"]), _text(obj["model"])
    input_tokens, output_tokens = (
        _integer(obj["input_tokens"]),
        _integer(obj["output_tokens"]),
    )
    if min(input_tokens, output_tokens) < 0:
        raise RecordingError("recording_usage")
    failure = None if obj["failure"] is None else _text(obj["failure"])
    if failure is not None and obj["value"] is not None:
        raise RecordingError("recording_content")
    value: p.Value | None = None
    if failure is None:
        try:
            value = _decode(obj["value"], request.schema)
        except RecordingError:
            failure = "recording_schema"
    return e.Recording(
        request, recording_id, model, input_tokens, output_tokens, value, failure
    )


def load_recording(path: Path, request: e.RecordingRequest) -> e.Recording:
    with path.open("rb") as source:
        data = source.read(MAX_RECORDING_BYTES + 1)
    if len(data) > MAX_RECORDING_BYTES:
        raise RecordingError("recording_size")
    try:
        return parse_recording(data.decode("utf-8"), request)
    except UnicodeDecodeError as error:
        raise RecordingError("recording_encoding") from error

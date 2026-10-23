import json
from hashlib import sha256
from typing import Any

from dex.bundle.model import BundleError, Case, Delivery, Source
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


def source_ref(raw: object, field: str) -> tuple[str, str]:
    item = object_value(raw, field)
    fields(item, {"source_id", "revision_id"}, set(), field)
    return text(item["source_id"], field), text(item["revision_id"], field)


def case_facts(
    item: dict[str, Any],
    sources: dict[tuple[str, str], Source],
    refs: tuple[tuple[str, str], ...],
    label: str,
) -> tuple[p.NamedValue, ...]:
    facts: dict[str, p.Value] = {}
    for raw in items(item["facts"], label + ".facts"):
        fact = object_value(raw, label + ".fact")
        fields(fact, {"name", "source", "record", "column"}, set(), label + ".fact")
        name = text(fact["name"], label + ".fact.name")
        ref = source_ref(fact["source"], label + ".fact.source")
        if name in facts or ref not in refs:
            raise BundleError(f"{label}: conflicting fact or missing source")
        source = sources[ref]
        if source.unresolved:
            raise BundleError(f"{label}: unresolved fact source {source.unresolved}")
        record_id, column = text(fact["record"], label), text(fact["column"], label)
        records = {record.locator: record for record in source.records}
        if record_id not in records:
            raise BundleError(f"{label}/{name}: missing record {record_id}")
        values = {value.name: value.value for value in records[record_id].values}
        if column not in values:
            raise BundleError(f"{label}/{name}: missing mapped column {column}")
        facts[name] = values[column]
    return tuple(p.NamedValue(name, value) for name, value in facts.items())


def observations(
    raw: object,
    sources: dict[tuple[str, str], Source],
    deliveries: dict[str, Delivery],
    label: str,
) -> None:
    identities: set[str] = set()
    for value in items(raw, label + ".observations"):
        item = object_value(value, label + ".observation")
        fields(
            item,
            {
                "observation_id",
                "source",
                "locator",
                "actor",
                "occurred_at",
                "observed_at",
                "available_at",
                "mapping_version",
            },
            {"effective_date"},
            label + ".observation",
        )
        identity = text(item["observation_id"], label)
        if identity in identities:
            raise BundleError(f"{label}: conflicting observation identity")
        identities.add(identity)
        ref = source_ref(item["source"], label)
        if ref not in sources:
            raise BundleError(f"{label}: missing observation source")
        source = sources[ref]
        locator = text(item["locator"], label)
        locators = {record.locator for record in source.records}
        if source.extraction is not None:
            locators.update(section.locator for section in source.extraction.sections)
        if locator not in locators:
            raise BundleError(f"{label}: missing observation locator")
        text(item["actor"], label + ".actor")
        text(item["mapping_version"], label + ".mapping_version")
        occurred = timestamp(item["occurred_at"], label + ".occurred_at")
        observed = timestamp(item["observed_at"], label + ".observed_at")
        available = timestamp(item["available_at"], label + ".available_at")
        if (
            not occurred <= observed <= available
            or source.available_at > available
            or source.observed_at > observed
        ):
            raise BundleError(f"{label}: invalid observation chronology")
        if not any(
            ref in delivery.sources and delivery.available_at <= available
            for delivery in deliveries.values()
        ):
            raise BundleError(f"{label}: observation unavailable at delivery")
        if "effective_date" in item:
            business_date(item["effective_date"], label + ".effective_date")


def load_cases(
    manifest: dict[str, Any],
    sources: dict[tuple[str, str], Source],
    deliveries: dict[str, Delivery],
    delivery_raw: dict[str, bytes],
) -> tuple[Case, ...]:
    history = object_value(manifest["history"], "history")
    historical: list[Any] = []
    interval = None
    if history != {"kind": "none"}:
        fields(
            history,
            {"kind", "start", "end", "opening_event", "adequacy", "cases"},
            set(),
            "history",
        )
        if history["kind"] != "interval":
            raise BundleError("history.kind: unknown history declaration")
        start, end = (
            timestamp(history["start"], "history.start"),
            timestamp(history["end"], "history.end"),
        )
        if end <= start:
            raise BundleError("history: invalid interval")
        interval = start, end
        text(history["opening_event"], "history.opening_event")
        adequacy = object_value(history["adequacy"], "history.adequacy")
        fields(adequacy, {"decision", "actor", "decided_at"}, set(), "history.adequacy")
        if text(adequacy["decision"], "history.adequacy.decision") not in {
            "usable",
            "incomplete",
            "unresolved",
        }:
            raise BundleError("history.adequacy: unknown decision")
        text(adequacy["actor"], "history.adequacy.actor")
        timestamp(adequacy["decided_at"], "history.adequacy.decided_at")
        historical = items(history["cases"], "history.cases")
    descriptors = {
        source_ref(
            {key: item[key] for key in ("source_id", "revision_id")}, "source"
        ): item
        for item in manifest["sources"]
    }
    cases: dict[str, Case] = {}
    memberships: set[tuple[str, str]] = set()
    for raw, is_history in [
        *((case, True) for case in historical),
        *((case, False) for case in items(manifest.get("cases", []), "cases")),
    ]:
        item = object_value(raw, "case")
        fields(
            item,
            {
                "case_id",
                "delivery_id",
                "opened_at",
                "business_date",
                "inputs",
                "facts",
                "observations",
            },
            set(),
            "case",
        )
        identity = text(item["case_id"], "case_id")
        delivery_id = text(item["delivery_id"], identity + ".delivery_id")
        if identity in cases or delivery_id not in deliveries:
            raise BundleError(
                f"{identity}: conflicting case or missing delivery identity"
            )
        opened = timestamp(item["opened_at"], identity + ".opened_at")
        if is_history and (interval is None or not interval[0] <= opened < interval[1]):
            raise BundleError(f"{identity}: case outside history interval")
        refs = tuple(
            source_ref(ref, identity) for ref in items(item["inputs"], identity)
        )
        delivery = deliveries[delivery_id]
        if (
            not refs
            or len(set(refs)) != len(refs)
            or any(ref not in delivery.sources for ref in refs)
        ):
            raise BundleError(f"{identity}: invalid input references")
        if delivery.available_at > opened or any(
            sources[ref].available_at > opened for ref in refs
        ):
            raise BundleError(f"{identity}: later evidence cannot enter arrival facts")
        facts = case_facts(item, sources, refs, identity)
        records = sorted(
            {
                (*source_ref(fact["source"], identity), fact["record"])
                for fact in item["facts"]
            }
        )
        members = records or [(*ref, "source") for ref in sorted(refs)]
        admission_keys = tuple(
            sha256(canonical(member)).hexdigest() for member in members
        )
        if any((delivery_id, key) in memberships for key in admission_keys):
            raise BundleError(f"{identity}: delivery already belongs to a case")
        memberships.update((delivery_id, key) for key in admission_keys)
        date = business_date(item["business_date"], identity + ".business_date")
        for ref in refs:
            mapping = descriptors[ref].get("mapping")
            if (
                mapping is not None
                and timestamp(mapping["confirmed_at"], identity) > opened
            ):
                raise BundleError(f"{identity}: mapping was not confirmed at arrival")
            if mapping is not None and (
                date < business_date(mapping["effective_from"], identity)
                or (
                    mapping["effective_until"] is not None
                    and date >= business_date(mapping["effective_until"], identity)
                )
            ):
                raise BundleError(f"{identity}: mapping outside effective interval")
        observations(item["observations"], sources, deliveries, identity)
        evidence = sha256(
            canonical(
                {
                    "case": {
                        key: value
                        for key, value in item.items()
                        if key != "observations"
                    },
                    "delivery": json.loads(delivery_raw[delivery_id]),
                    "hashes": [sources[ref].sha256 for ref in refs],
                }
            )
        ).hexdigest()
        delivery_digest = sha256(
            canonical(
                {
                    "delivery": json.loads(delivery_raw[delivery_id]),
                    "hashes": [sources[ref].sha256 for ref in delivery.sources],
                }
            )
        ).hexdigest()
        cases[identity] = Case(
            identity,
            delivery_id,
            opened,
            date,
            facts,
            evidence,
            delivery_digest,
            admission_keys,
            refs,
            is_history,
        )
    return tuple(cases.values())

from dataclasses import dataclass
from datetime import date, datetime

from dex.core import program as p


class BundleError(ValueError):
    pass


@dataclass(frozen=True)
class Original:
    path: str
    content: bytes


@dataclass(frozen=True)
class Record:
    locator: str
    values: tuple[p.NamedValue, ...]
    cells: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Source:
    source_id: str
    revision_id: str
    path: str
    sha256: str
    observed_at: datetime
    available_at: datetime
    extraction: p.SourceExtraction | None
    unresolved: str | None
    records: tuple[Record, ...] = ()


@dataclass(frozen=True)
class Delivery:
    delivery_id: str
    sources: tuple[tuple[str, str], ...]
    received_at: datetime
    available_at: datetime


@dataclass(frozen=True)
class Case:
    case_id: str
    delivery_id: str
    opened_at: datetime
    business_date: date
    facts: tuple[p.NamedValue, ...]
    evidence_sha256: str
    delivery_sha256: str
    admission_key: str
    inputs: tuple[tuple[str, str], ...]
    historical: bool


@dataclass(frozen=True)
class Bundle:
    bundle_id: str
    company_id: str
    manifest: bytes
    originals: tuple[Original, ...]
    sources: tuple[Source, ...]
    deliveries: tuple[Delivery, ...]
    cases: tuple[Case, ...]
    snapshots: tuple[Original, ...] = ()

    @property
    def catalog(self) -> p.SourceCatalog:
        return p.SourceCatalog(
            tuple(
                source.extraction
                for source in self.sources
                if source.extraction is not None
            )
        )

import calendar
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta
from hashlib import sha256
from zoneinfo import ZoneInfo

VERSION = "world-1-1"
ZONE = ZoneInfo("America/New_York")
PACKETS = {
    "bramblewick": (
        "procedure.md",
        "controller-email.md",
        "board-limit-notice.md",
        "service-confirmation.md",
    ),
    "fennor": ("ap-checklist.md", "payables-wiki.md", "controller-email.md"),
}
COMPANIES = {"C1": "bramblewick", "C2": "fennor"}
COMMUNITIES = {
    "C1": (
        "Alderquill Green",
        "Briarmere Walk",
        "Harthmere Court",
        "Cresswell Mews",
        "Dovewick Grove",
        "Elmshale View",
        "Fernhollow Row",
        "Gorsehaven Place",
        "Rillhaven Rise",
    ),
    "C2": (
        "Ashmere Park",
        "Birchfen Court",
        "Celandine Walk",
        "Darnel Grove",
        "Elderwick Place",
        "Foxmere Row",
    ),
}
VENDORS = {
    "C1": (
        "Briarvale Repairs",
        "Avenreed Grounds",
        "Cressfen Snow",
        "Dovemere Water",
        "Elmquill Services",
        "Fernreed Paint",
        "Asterfen Lighting",
        "Gorsewick Cleaning",
    ),
    "C2": (
        "Alderfen Repairs",
        "Morrowfen Electric",
        "Celandine Snow",
        "Darnelwell Water",
        "Elderquill Services",
        "Foxreed Paint",
        "Glenmere Lighting",
        "Hollowfen Cleaning",
    ),
}


def local(day: date, hour: int = 9, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), ZONE)


@dataclass(frozen=True)
class Invoice:
    case_id: str
    company: str
    cohort: str
    received: datetime
    invoice_date: date
    community: str
    vendor: str
    number: str
    amount: int
    work: str
    format: str
    issue: str = ""
    prior: str = ""


def vendor_id(company: str, community: str, number: int) -> str:
    return f"{community}-V{number:02d}" if company == "C1" else f"C2-V{number:02d}"


def receipt(company: str, cohort: str, number: int) -> datetime:
    if cohort == "shadow":
        return local(date(2026, 10, 1), 9, number - 1)
    month_index, ordinal = divmod(number - 1, 300)
    year, month = divmod(
        (2025 if cohort == "history" else 2026) * 12 + 9 + month_index, 12
    )
    month += 1
    days = calendar.monthrange(year, month)[1]
    opening = 13 if company == "C1" else 6
    if cohort == "stream" and month_index == 0:
        day = (
            2 if ordinal < opening else 3 + (ordinal - opening) * 29 // (300 - opening)
        )
        earlier = sum(
            (2 if prior < opening else 3 + (prior - opening) * 29 // (300 - opening))
            == day
            for prior in range(ordinal)
        )
    else:
        day = 1 + ordinal * days // 300
        earlier = sum(1 + prior * days // 300 == day for prior in range(ordinal))
    return local(date(year, month, day), 9, earlier)


def make_cases(company: str, seed: int) -> tuple[Invoice, ...]:
    cases: list[Invoice] = []
    for cohort, prefix, count in (
        ("history", "H", 3600),
        ("stream", "S", 1800),
        ("shadow", "SH", 10),
    ):
        for number in range(1, count + 1):
            identity = (
                f"{company}-{prefix}{number:04d}"
                if prefix != "SH"
                else f"{company}-SH{number:02d}"
            )
            received = receipt(company, cohort, number)
            community = f"{company}-C{1 + (number % (8 if company == 'C1' else 6)):02d}"
            vendor_number = 1 + number % 8
            digest = sha256(f"{VERSION}/{seed}/{identity}".encode()).digest()
            amount = 20000 + int.from_bytes(digest[:4], "big") % 120000
            invoice_date = received.date() - timedelta(days=3 + digest[4] % 8)
            if cohort == "history" and received.day <= 11:
                invoice_date = received.date().replace(day=1) - timedelta(days=1)
            work = (
                "Snow clearing"
                if invoice_date.month in (11, 12, 1, 2, 3) and number % 19 == 0
                else "Property maintenance"
            )
            invoice = Invoice(
                identity,
                company,
                cohort,
                received,
                invoice_date,
                community,
                vendor_id(company, community, vendor_number),
                f"INV-{prefix}-{number:05d}",
                amount,
                work,
                f"F{1 + number % 3}",
            )
            cases.append(special_case(invoice, number))
    indexed = {item.case_id: item for item in cases}
    for later, earlier in (
        ((628, 598), (2248, 2113), (2713, 2668), (3328, 3028))
        if company == "C1"
        else ((897, 747), (2997, 2734))
    ):
        key, prior = f"{company}-H{later:04d}", indexed[f"{company}-H{earlier:04d}"]
        indexed[key] = replace(
            indexed[key],
            community=prior.community,
            vendor=prior.vendor,
            number=prior.number,
            amount=prior.amount,
            invoice_date=prior.invoice_date,
            work=prior.work,
            issue="duplicate",
            prior=prior.case_id,
        )
    return tuple(indexed[item.case_id] for item in cases)


def special_case(item: Invoice, number: int) -> Invoice:
    company, cohort = item.company, item.cohort
    ordinal = (number - 1) % 300 + 1
    local_community = f"{company}-C03" if company == "C1" else "C2-C01"
    limit = 150000 if company == "C1" else 250000
    if ordinal in (1, 2, 3, 4, 5, 6, 7, 8):
        amount = {
            1: 500000,
            2: 500001,
            3: limit,
            4: limit + 1,
            5: 1000000,
            6: 1000001,
            7: 500001,
            8: 500000,
        }[ordinal]
        community = local_community if ordinal in (3, 4) else f"{company}-C02"
        item = replace(
            item,
            amount=amount,
            community=community,
            vendor=vendor_id(company, community, 2 if ordinal == 7 else 1),
        )
    if ordinal == 9:
        item = replace(
            item,
            invoice_date=item.received.date() - timedelta(days=400),
            work="Property maintenance",
        )
    if cohort == "history":
        month = (number - 1) // 300
        is_mistake = (
            ordinal in (21, 22)
            if company == "C1"
            else ordinal == 23
            or (ordinal == 24 and month in (0, 1, 2, 4, 6, 8, 10, 11))
        )
        if is_mistake:
            community = f"{company}-C02"
            item = replace(
                item,
                community=community,
                vendor=vendor_id(company, community, 1),
                amount=100000,
                work="Property maintenance",
            )
        snow = (
            {142, 1918, 2230, 2566, 2638, 2758, 2938, 3118, 3478}
            if company == "C1"
            else {2760, 2940, 3120, 3480}
        )
        cancellations: set[int] = {2128, 3208} if company == "C1" else set()
        if number in snow | cancellations:
            item = replace(
                item,
                invoice_date=item.received.date(),
                work="Snow clearing",
                amount=100000,
                issue="cancellation" if number in cancellations else "",
                format="F1" if number in cancellations else item.format,
            )
        posted = {313: 1, 1558: 2} if company == "C1" else {391: 1, 2247: 2}
        void = {898: 3, 3013: 4} if company == "C1" else {500: 3}
        if number in posted or number in void:
            record = (posted | void)[number]
            community = f"{company}-C02"
            item = replace(
                item,
                community=community,
                vendor=vendor_id(company, community, 1),
                number=f"OPEN-{record:03d}",
                issue="duplicate" if number in posted else "void-only",
                prior=f"{company}-OPEN-{record:03d}",
                work="Property maintenance",
            )
        if company == "C1" and number in (100, 101):
            community = f"C1-C{1 if number == 100 else 2:02d}"
            item = replace(
                item,
                community=community,
                vendor=vendor_id(company, community, 5),
                number="CROSS-0001",
            )
        return item
    if cohort == "shadow":
        community = f"{company}-C02"
        item = replace(
            item,
            community=community,
            vendor=vendor_id(company, community, 1),
            amount=100000,
        )
        if number in (2, 3):
            item = replace(
                item,
                number=f"OPEN-{1 if number == 2 else 5:03d}",
                prior=f"{company}-OPEN-{1 if number == 2 else 5:03d}",
            )
        if number == 4:
            item = replace(
                item,
                vendor="unresolved:Juniperfen Works"
                if company == "C1"
                else "unresolved:Kestrelfen Works",
            )
        if number in (7, 8):
            item = replace(item, vendor=vendor_id(company, community, number + 2))
        if number == 9:
            item = replace(item, invoice_date=date(2026, 9, 29), work="Snow clearing")
        return replace(
            item,
            issue=(
                "ordinary",
                "duplicate",
                "void-only",
                "unknown-vendor",
                "ambiguous-community",
                "conflicting-amount",
                "expired-certificate",
                "missing-certificate",
                "snow-review",
                "rejected",
            )[number - 1],
        )
    if company == "C1" and number <= 13:
        issues = (
            "proposal-review",
            "scheduled",
            "duplicate",
            "void-only",
            "unknown-vendor",
            "ambiguous-community",
            "conflicting-amount",
            "expired-certificate",
            "missing-certificate",
            "snow-review",
            "cancellation",
            "rejected",
            "unanswered",
        )
        item = replace(item, issue=issues[number - 1])
        if number == 1:
            return replace(
                item,
                community="C1-C03",
                vendor="C1-C03-V07",
                number="AF-11496",
                amount=180000,
                invoice_date=date(2026, 9, 29),
                work="Lighting service",
                format="F1",
            )
        if number in (2, 12):
            item = replace(item, amount=100000, community="C1-C02", vendor="C1-C02-V01")
        if number in (3, 4):
            item = replace(
                item,
                community="C1-C02",
                vendor="C1-C02-V01",
                number=f"OPEN-{1 if number == 3 else 5:03d}",
                prior=f"C1-OPEN-{1 if number == 3 else 5:03d}",
            )
        if number == 10:
            item = replace(item, invoice_date=date(2026, 9, 29), work="Snow clearing")
        if number in (8, 9):
            item = replace(item, community="C1-C02", vendor=f"C1-C02-V{number + 1:02d}")
        if number == 11:
            item = replace(item, format="F1")
        if number == 13:
            item = replace(item, amount=600000)
        if number == 5:
            item = replace(item, vendor="unresolved:Juniperfen Works")
    if company == "C2" and number <= 6:
        item = replace(
            item,
            issue=(
                "ordinary",
                "local-board",
                "second-signer",
                "duplicate",
                "void-only",
                "expired-certificate",
            )[number - 1],
        )
        if number == 2:
            item = replace(item, community="C2-C01", amount=300000)
        if number == 3:
            item = replace(item, amount=1100000)
        if number == 6:
            item = replace(item, vendor="C2-V09")
        if number in (4, 5):
            item = replace(
                item,
                vendor="C2-V01",
                number=f"OPEN-{1 if number == 4 else 5:03d}",
                prior=f"C2-OPEN-{1 if number == 4 else 5:03d}",
            )
    if company == "C1" and number in (431, 441, 442, 451):
        item = replace(
            item,
            community="C1-C09",
            vendor="C1-C09-V01",
            amount={431: 200000, 441: 200000, 442: 199999, 451: 240000}[number],
            issue="community-not-yet-joined"
            if number == 431
            else "review-correction"
            if number == 451
            else "",
        )
    if company == "C1" and number in (900, 901, 902, 1200, 1201, 1202):
        community = "C1-C03" if number <= 902 else "C1-C02"
        item = replace(
            item,
            community=community,
            vendor=vendor_id(company, community, 1),
            amount={
                900: 180000,
                901: 180000,
                902: 180001,
                1200: 250001,
                1201: 250001,
                1202: 250000,
            }[number],
            issue="older-pending" if number in (900, 1200) else "",
        )
    if company == "C1":
        if number in (601, 602, 603) or (
            item.received.date() >= date(2026, 12, 4) and number % 7 == 0
        ):
            item = replace(item, format="F4")
    elif number == 901 or (number > 901 and number % 7 == 0):
        item = replace(item, format="F4")
    return item


def chronology(item: Invoice) -> dict[str, str]:
    review = item.received + timedelta(minutes=20)
    if item.cohort == "history":
        review = item.received + timedelta(hours=1, seconds=-1)
    elif item.issue in ("scheduled", "rejected"):
        review = item.received + timedelta(seconds=30)
    elif item.issue == "proposal-review":
        review = item.received.replace(hour=10, minute=0)
    elif item.issue == "review-correction":
        review = item.received.replace(hour=10, minute=0)
    elif item.issue == "community-not-yet-joined":
        review = local(date(2026, 11, 15), 8) + timedelta(seconds=10)
    elif item.issue in (
        "unknown-vendor",
        "ambiguous-community",
        "conflicting-amount",
        "snow-review",
    ) or (
        item.work == "Snow clearing"
        and item.invoice_date.month
        in (range(4, 11) if item.company == "C1" else range(5, 10))
    ):
        review = item.received + timedelta(days=1)
        while review.weekday() >= 5:
            review += timedelta(days=1)
        review += timedelta(seconds=10)
    return {
        "values_reviewed_at": review.isoformat(),
        "posted_at": (
            review
            + timedelta(seconds=1, microseconds=0 if item.cohort == "history" else 1)
        ).isoformat(),
    }

"""Status logic. Pure functions, no I/O. Rules: docs/DATA_MODEL.md, "Status-regler"."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

FORSINKET = "Forsinket"
TIDLIGERE = "Tidligere"
UAENDRET = "Uændret"
TJEK_MANUELT = "Tjek manuelt"
IKKE_FUNDET = "Ikke fundet"
IKKE_UNDERSTOETTET = "Ikke understøttet"

ALL_STATUSES = (FORSINKET, TIDLIGERE, UAENDRET, TJEK_MANUELT, IKKE_FUNDET, IKKE_UNDERSTOETTET)

# Google Sheets serial dates count days from 1899-12-30.
_SHEETS_EPOCH = date(1899, 12, 30)
_DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%Y")


@dataclass(frozen=True)
class CompareResult:
    diff_days: int | None
    status: str


def parse_date(value: object) -> date | None:
    """Parse a sheet cell or AI value into a date. Returns None for empty or unparseable input."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        if value <= 0:
            return None
        return _SHEETS_EPOCH + timedelta(days=int(value))
    text = str(value).strip()
    if not text:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def compare(
    *,
    supported: bool,
    lookup_failed: bool,
    page_state: str | None,
    new_eta: date | None,
    confidence: str | None,
    current_eta: date | None,
    threshold: int,
) -> CompareResult:
    """Map one lookup to (diff_days, status). Rules are checked in order; first match wins."""
    threshold = max(threshold, 1)

    if not supported:
        return CompareResult(None, IKKE_UNDERSTOETTET)
    if lookup_failed or page_state != "ok":
        return CompareResult(None, IKKE_FUNDET)

    diff = (new_eta - current_eta).days if new_eta and current_eta else None

    if new_eta is None or confidence == "low" or current_eta is None:
        return CompareResult(diff, TJEK_MANUELT)
    if diff >= threshold:
        return CompareResult(diff, FORSINKET)
    if diff <= -threshold:
        return CompareResult(diff, TIDLIGERE)
    return CompareResult(diff, UAENDRET)

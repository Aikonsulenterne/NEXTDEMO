"""Google Sheet as input, output and history. Layout: docs/DATA_MODEL.md."""

import csv
import time
from dataclasses import dataclass
from pathlib import Path

import gspread
import requests
from gspread.utils import ValueInputOption, ValueRenderOption

from .compare import FORSINKET, IKKE_FUNDET, IKKE_UNDERSTOETTET, TIDLIGERE, TJEK_MANUELT

SHIPMENT_HEADERS = [
    "Carrier", "BL", "Current ETA", "Ny ETA", "Forskel (dage)", "Status",
    "Skib", "Destination", "Sidst tjekket", "Note",
]
LOG_HEADERS = [
    "Kørsel", "Carrier", "BL", "Current ETA", "Ny ETA", "Forskel (dage)",
    "Status", "Confidence", "Rådata",
]
CONFIG_TAB = "Config"
MAX_ROWS = 1000

STATUS_COLOURS = {
    FORSINKET: "#F4C7C3",
    TIDLIGERE: "#D9EAD3",
    TJEK_MANUELT: "#FFF2CC",
    IKKE_FUNDET: "#EFEFEF",
    IKKE_UNDERSTOETTET: "#EFEFEF",
}
DELAY_TEXT_COLOUR = "#CC0000"


class SheetError(Exception):
    """Google Sheets failed after retries. The message is Danish."""


@dataclass
class Shipment:
    carrier: str
    bl: str
    current_eta_raw: object
    checked: bool = False


def _rgb(hex_colour: str) -> dict:
    h = hex_colour.lstrip("#")
    return {k: int(h[i:i + 2], 16) / 255 for k, i in (("red", 0), ("green", 2), ("blue", 4))}


def _with_retry(fn, *args, **kwargs):
    """Three attempts with backoff on rate limits, server errors and network errors."""
    delay = 2
    for attempt in range(3):
        try:
            return fn(*args, **kwargs)
        except gspread.exceptions.APIError as exc:
            status = getattr(exc.response, "status_code", 0)
            if status not in (429, 500, 502, 503, 504) or attempt == 2:
                raise SheetError(f"Google Sheets-fejl (HTTP {status}): {exc}") from exc
        except requests.exceptions.RequestException as exc:
            if attempt == 2:
                raise SheetError(f"Ingen forbindelse til Google Sheets: {exc}") from exc
        time.sleep(delay)
        delay *= 2


def safe_text(value: object) -> object:
    """USER_ENTERED would turn text starting with = + - @ into a formula. Page/AI text is untrusted."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@"):
        return "'" + value
    return value


def load_seed(csv_path: Path) -> list[Shipment]:
    with csv_path.open(encoding="utf-8") as f:
        return [
            Shipment(carrier=r["Carrier"].strip(), bl=r["BL"].strip(), current_eta_raw=r["Current ETA"].strip())
            for r in csv.DictReader(f)
            if r.get("BL", "").strip()
        ]


class Sheet:
    def __init__(self, service_account_file: Path, sheet_id: str, tab_shipments: str, tab_log: str):
        if not sheet_id:
            raise SheetError("GOOGLE_SHEET_ID mangler i .env")
        if not service_account_file.exists():
            raise SheetError(f"Service account-nøglen findes ikke: {service_account_file}")
        try:
            client = gspread.service_account(filename=str(service_account_file))
            self.spreadsheet = _with_retry(client.open_by_key, sheet_id)
        except gspread.exceptions.SpreadsheetNotFound as exc:
            raise SheetError("Arket findes ikke, eller det er ikke delt med service account-mailen") from exc
        self.tab_shipments = tab_shipments
        self.tab_log = tab_log

    # --- worksheets -------------------------------------------------------

    def _worksheet(self, title: str, cols: int, create: bool = False) -> gspread.Worksheet | None:
        try:
            return _with_retry(self.spreadsheet.worksheet, title)
        except gspread.exceptions.WorksheetNotFound:
            if not create:
                return None
            return _with_retry(self.spreadsheet.add_worksheet, title=title, rows=MAX_ROWS, cols=cols)

    @property
    def shipments(self) -> gspread.Worksheet:
        ws = self._worksheet(self.tab_shipments, len(SHIPMENT_HEADERS))
        if ws is None:
            raise SheetError(f"Fanen '{self.tab_shipments}' findes ikke. Kør først: python -m eta_tracker setup-sheet")
        return ws

    # --- setup ------------------------------------------------------------

    def setup(self, seed: list[Shipment]) -> int:
        """Create tabs, headers and formatting. Imports seed data only if A2:C is empty. Returns rows imported."""
        ss = self.spreadsheet
        existing = _with_retry(ss.worksheets)
        ship = self._worksheet(self.tab_shipments, len(SHIPMENT_HEADERS))
        if ship is None and len(existing) == 1 and not any(_with_retry(existing[0].get_all_values)):
            ship = existing[0]
            _with_retry(ship.update_title, self.tab_shipments)
        if ship is None:
            ship = self._worksheet(self.tab_shipments, len(SHIPMENT_HEADERS), create=True)
        log = self._worksheet(self.tab_log, len(LOG_HEADERS), create=True)

        _with_retry(ship.update, [SHIPMENT_HEADERS], "A1:J1")
        _with_retry(log.update, [LOG_HEADERS], "A1:I1")

        requests_: list[dict] = [{
            "updateSpreadsheetProperties": {
                "properties": {"locale": "da_DK", "timeZone": "Europe/Copenhagen"},
                "fields": "locale,timeZone",
            }
        }]
        for ws, ncols in ((ship, len(SHIPMENT_HEADERS)), (log, len(LOG_HEADERS))):
            requests_ += [
                {"updateSheetProperties": {
                    "properties": {"sheetId": ws.id, "gridProperties": {"frozenRowCount": 1}},
                    "fields": "gridProperties.frozenRowCount",
                }},
                {"repeatCell": {
                    "range": {"sheetId": ws.id, "startRowIndex": 0, "endRowIndex": 1, "endColumnIndex": ncols},
                    "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                    "fields": "userEnteredFormat.textFormat.bold",
                }},
            ]
        requests_ += [
            _number_format(ship.id, 2, 4, "DATE", "dd-mm-yyyy"),        # C:D
            _number_format(ship.id, 8, 9, "DATE_TIME", "dd-mm-yyyy hh:mm"),  # I
            _number_format(log.id, 0, 1, "DATE_TIME", "dd-mm-yyyy hh:mm"),   # A
            _number_format(log.id, 3, 5, "DATE", "dd-mm-yyyy"),         # D:E
        ]

        # Replace our conditional formatting rules (idempotent re-runs).
        metadata = _with_retry(ss.fetch_sheet_metadata, {"fields": "sheets(properties.sheetId,conditionalFormats)"})
        for s in metadata.get("sheets", []):
            if s["properties"]["sheetId"] == ship.id:
                for _ in s.get("conditionalFormats", []):
                    requests_.append({"deleteConditionalFormatRule": {"sheetId": ship.id, "index": 0}})
        requests_ += _conditional_rules(ship.id)
        _with_retry(ss.batch_update, {"requests": requests_})

        has_data = any(any(str(c).strip() for c in row) for row in _with_retry(ship.get, "A2:C"))
        if has_data or not seed:
            return 0
        rows = [[s.carrier, s.bl, s.current_eta_raw] for s in seed]
        _with_retry(ship.update, rows, f"A2:C{len(rows) + 1}", value_input_option=ValueInputOption.user_entered)
        _with_retry(ship.columns_auto_resize, 0, len(SHIPMENT_HEADERS))
        return len(rows)

    # --- read -------------------------------------------------------------

    def read_shipments(self) -> list[Shipment]:
        rows = _with_retry(self.shipments.get, "A2:J", value_render_option=ValueRenderOption.unformatted)
        result = []
        for row in rows:
            row = list(row) + [""] * (10 - len(row))
            bl = str(row[1]).strip()
            if bl:
                result.append(Shipment(
                    carrier=str(row[0]).strip(), bl=bl, current_eta_raw=row[2],
                    checked=str(row[8]).strip() != "",
                ))
        return result

    def threshold(self) -> int | None:
        """DELAY_THRESHOLD_DAYS from the optional Config tab."""
        ws = self._worksheet(CONFIG_TAB, 2)
        if ws is None:
            return None
        for row in _with_retry(ws.get_all_values):
            if len(row) >= 2 and row[0].strip().upper() == "DELAY_THRESHOLD_DAYS":
                try:
                    return int(str(row[1]).strip())
                except ValueError:
                    return None
        return None

    # --- write ------------------------------------------------------------

    def write_result(self, bl: str, values: list) -> bool:
        """Write D:J for this BL. The row is looked up now, so sorting mid-run is safe. False if BL is gone."""
        ws = self.shipments
        column = _with_retry(ws.col_values, 2)
        target = bl.strip().upper()
        for index, cell in enumerate(column[1:], start=2):
            if str(cell).strip().upper() == target:
                _with_retry(
                    ws.update, [[safe_text(v) for v in values]], f"D{index}:J{index}",
                    value_input_option=ValueInputOption.user_entered,
                )
                return True
        return False

    def append_log(self, rows: list[list]) -> None:
        if not rows:
            return
        ws = self._worksheet(self.tab_log, len(LOG_HEADERS), create=True)
        _with_retry(
            ws.append_rows, [[safe_text(v) for v in r] for r in rows],
            value_input_option=ValueInputOption.user_entered, table_range="A1",
        )

    def reset(self) -> None:
        """Clear the output columns D:J. Never touches A:C or the Log tab."""
        _with_retry(self.shipments.batch_clear, ["D2:J"])


def _number_format(sheet_id: int, start_col: int, end_col: int, kind: str, pattern: str) -> dict:
    return {"repeatCell": {
        "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": MAX_ROWS,
                  "startColumnIndex": start_col, "endColumnIndex": end_col},
        "cell": {"userEnteredFormat": {"numberFormat": {"type": kind, "pattern": pattern}}},
        "fields": "userEnteredFormat.numberFormat",
    }}


def _conditional_rules(sheet_id: int) -> list[dict]:
    def rule(start_col: int, end_col: int, status: str, fmt: dict, index: int) -> dict:
        return {"addConditionalFormatRule": {"index": index, "rule": {
            "ranges": [{"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": MAX_ROWS,
                        "startColumnIndex": start_col, "endColumnIndex": end_col}],
            "booleanRule": {
                "condition": {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": f'=$F2="{status}"'}]},
                "format": fmt,
            },
        }}}

    # First rule wins per cell: the bold red "Forskel" rule goes first, then one rule per status on D:F.
    rules = [rule(4, 5, FORSINKET, {
        "backgroundColor": _rgb(STATUS_COLOURS[FORSINKET]),
        "textFormat": {"bold": True, "foregroundColor": _rgb(DELAY_TEXT_COLOUR)},
    }, 0)]
    for i, (status, colour) in enumerate(STATUS_COLOURS.items(), start=1):
        rules.append(rule(3, 6, status, {"backgroundColor": _rgb(colour)}, i))
    return rules

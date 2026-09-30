"""Orchestrator: sheet -> Apify (carrier data) -> parse/Claude -> compare -> sheet + runs/ (docs/ARCHITECTURE.md)."""

import json
import random
import time
from datetime import datetime

from .apify import Apify, ApifyError
from .carriers import get_carrier
from .compare import IKKE_FUNDET, TJEK_MANUELT, compare, parse_date
from .config import Settings
from .extract import ExtractionError, Extractor
from .replay import load_best, save_results
from .sheet import Sheet, SheetError, Shipment, load_seed
from .ui import RunView, console, summary

REPLAY_PREFIX = "Afspillet: "


def select_shipments(
    shipments: list[Shipment], bls: list[str] | None, skip_checked: bool, limit: int | None
) -> tuple[list[Shipment], list[str]]:
    """Apply --bl (keeps the given order), --skip-checked and --limit. Returns (selected, BLs not found)."""
    missing: list[str] = []
    if bls:
        by_bl = {s.bl.strip().upper(): s for s in shipments}
        selected = []
        for bl in bls:
            match = by_bl.get(bl.strip().upper())
            if match:
                selected.append(match)
            else:
                missing.append(bl.strip())
    else:
        selected = list(shipments)
    if skip_checked:
        selected = [s for s in selected if not s.checked]
    if limit is not None:
        selected = selected[: max(limit, 0)]
    return selected, missing


def _open_sheet(settings: Settings) -> Sheet | None:
    try:
        return Sheet(settings.service_account_file, settings.sheet_id, settings.tab_shipments, settings.tab_log)
    except SheetError as exc:
        console.print(f"[bold red]Google Sheet utilgængeligt:[/] {exc}")
        console.print(f"[yellow]Kører kun i terminalen. BL-liste fra {settings.seed_csv.name}.[/]")
        return None


class _SheetWriter:
    """Writes to the sheet but degrades to terminal-only if Sheets fails mid-run, so the demo never stops."""

    def __init__(self, sheet: Sheet | None):
        self.sheet = sheet

    def write(self, record: dict) -> None:
        if not self.sheet:
            return
        values = [
            record["new_eta"] or "",
            record["diff_days"] if record["diff_days"] is not None else "",
            record["status"],
            record.get("vessel") or "",
            record.get("pod") or "",
            record["checked_at"].replace("T", " "),
            record.get("note") or "",
        ]
        try:
            if not self.sheet.write_result(record["bl"], values):
                console.print(f"[yellow]{record['bl']} findes ikke længere i arket; springer skrivning over.[/]")
        except SheetError as exc:
            self._fail(exc)

    def log(self, rows: list[list]) -> None:
        if self.sheet and rows:
            try:
                self.sheet.append_log(rows)
            except SheetError as exc:
                self._fail(exc)

    def _fail(self, exc: SheetError) -> None:
        console.print(f"[bold red]{exc}[/]\n[yellow]Fortsætter kun i terminalen.[/]")
        self.sheet = None


def run(
    settings: Settings, *, limit: int | None, bls: list[str] | None, skip_checked: bool, replay: bool
) -> None:
    sheet = _open_sheet(settings)
    try:
        shipments = sheet.read_shipments() if sheet else load_seed(settings.seed_csv)
    except SheetError as exc:
        console.print(f"[bold red]{exc}[/]")
        sheet, shipments = None, load_seed(settings.seed_csv)

    selected, missing = select_shipments(shipments, bls, skip_checked, limit)
    for bl in missing:
        console.print(f"[yellow]BL {bl} findes ikke i listen; springer over.[/]")
    if not selected:
        console.print("Ingen BL at slå op.")
        return

    writer = _SheetWriter(sheet)
    if replay:
        _replay(settings, selected, writer)
    else:
        _live(settings, selected, writer)


def _replay(settings: Settings, selected: list[Shipment], writer: _SheetWriter) -> None:
    best = load_best(settings.runs_dir)
    records = []
    with RunView(f"Afspiller seneste gode resultat · {len(selected)} BL", selected) as view:
        for shipment in selected:
            record = best.get(shipment.bl.upper())
            view.working(shipment.bl, "Afspiller …")
            time.sleep(random.uniform(1, 2))
            if not record:
                view.done(_record(shipment, status=IKKE_FUNDET, note="Intet gemt resultat til afspilning"))
                continue
            record = {**record, "note": REPLAY_PREFIX + (record.get("note") or "")}
            writer.write(record)  # original checked_at is kept; no Log row (not a new lookup)
            view.done(record)
            records.append(record)
    summary(records)


def _live(settings: Settings, selected: list[Shipment], writer: _SheetWriter) -> None:
    threshold = settings.delay_threshold_days
    if writer.sheet:
        try:
            threshold = writer.sheet.threshold() or threshold
        except SheetError:
            pass

    run_started = datetime.now().replace(microsecond=0)
    run_ts = run_started.isoformat()
    run_dir = settings.runs_dir / run_started.strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    extractor = Extractor(settings.anthropic_api_key, settings.claude_model) if settings.anthropic_api_key else None
    records: list[dict] = []
    log_rows: list[list] = []

    title = f"ETA-tjek · {len(selected)} BL · forsinket ved ≥ {threshold} dag(e)"
    try:
        with RunView(title, selected) as view:
            data, errors = _fetch_all(settings, selected, view)
            for shipment in selected:
                view.working(shipment.bl, "Sammenligner …")
                try:
                    record = _evaluate(shipment, data, errors, extractor, run_dir, settings.runs_dir, threshold)
                except Exception as exc:  # never crash on one BL
                    record = _record(shipment, status=IKKE_FUNDET, note=f"Uventet fejl: {type(exc).__name__}")

                records.append(record)
                save_results(run_dir, run_ts, records)
                writer.write(record)
                log_rows.append([
                    run_ts.replace("T", " "), record["carrier"], record["bl"], record["current_eta"] or "",
                    record["new_eta"] or "", record["diff_days"] if record["diff_days"] is not None else "",
                    record["status"], record.get("confidence") or "", record.get("evidence") or "",
                ])
                view.done(record)
                time.sleep(settings.reveal_delay_seconds)  # rows appear one by one, for the audience
    except KeyboardInterrupt:
        console.print("[yellow]Afbrudt. Gemmer det, der nåede at blive slået op.[/]")
    finally:
        writer.log(log_rows)
    summary(records)
    if records:
        console.print(f"Rådata gemt i [bold]{run_dir.relative_to(settings.runs_dir.parent)}[/]")


def _fetch_all(settings: Settings, selected: list[Shipment], view) -> tuple[dict[str, dict], dict[str, str]]:
    """One Apify run per carrier. Returns ({BL: raw item}, {carrier code: Danish error})."""
    by_carrier: dict[str, list[Shipment]] = {}
    for shipment in selected:
        carrier = get_carrier(shipment.carrier)
        if carrier:
            by_carrier.setdefault(carrier.code, []).append(shipment)

    data: dict[str, dict] = {}
    errors: dict[str, str] = {}
    try:
        apify = Apify(settings.apify_token, settings.apify_timeout_seconds)
    except ApifyError as exc:
        return data, {code: str(exc) for code in by_carrier}

    for code, shipments in by_carrier.items():
        carrier = get_carrier(code)
        for s in shipments:
            view.working(s.bl, f"Henter fra {carrier.name} …")
        try:
            data.update(apify.track(getattr(settings, carrier.actor_setting), [s.bl for s in shipments]))
        except ApifyError as exc:
            errors[code] = str(exc)
    return data, errors


def _evaluate(shipment, data, errors, extractor, run_dir, runs_dir, threshold) -> dict:
    carrier = get_carrier(shipment.carrier)
    current_eta = parse_date(shipment.current_eta_raw)
    if carrier is None:
        record = _record(shipment, current_eta=current_eta,
                         note=f"Rederi '{shipment.carrier}' understøttes ikke (kun CMA og MSC)")
        return {**record, **_status(False, False, None, None, None, current_eta, threshold)}

    base = _record(shipment, current_eta=current_eta)
    if carrier.code in errors:
        return {**base, **_status(True, True, None, None, None, current_eta, threshold), "note": errors[carrier.code]}

    item = data.get(shipment.bl.strip().upper())
    if item is None:
        return {**base, **_status(True, True, None, None, None, current_eta, threshold),
                "note": f"{carrier.name} returnerede intet for BL'et"}

    evidence = run_dir / f"{shipment.bl}.json"
    evidence.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
    base["evidence"] = str(evidence.relative_to(runs_dir))

    ex = carrier.parse(item)
    if ex is None:
        # Data did not have the expected shape: let Claude read it, like a colleague would.
        if extractor is None:
            return {**base, "status": TJEK_MANUELT, "diff_days": None,
                    "note": "Kunne ikke læse rederiets data (ingen ANTHROPIC_API_KEY)"}
        try:
            ex = extractor.extract(bl=shipment.bl, carrier=carrier.name, text=json.dumps(item, ensure_ascii=False))
        except ExtractionError as exc:
            return {**base, "status": TJEK_MANUELT, "diff_days": None, "note": str(exc)}

    new_eta = ex.eta_date if ex.page_state == "ok" else None
    note = ex.note
    if ex.page_state == "ok" and current_eta is None:
        note = f"Mangler gyldig Current ETA. {note}"
    return {
        **base,
        **_status(True, False, ex.page_state, new_eta, ex.confidence, current_eta, threshold),
        "new_eta": new_eta.isoformat() if new_eta else None,
        "vessel": ex.vessel, "pod": ex.pod, "confidence": ex.confidence,
        "arrived": ex.arrived, "page_state": ex.page_state, "note": note,
    }


def _status(supported, failed, page_state, new_eta, confidence, current_eta, threshold) -> dict:
    result = compare(supported=supported, lookup_failed=failed, page_state=page_state, new_eta=new_eta,
                     confidence=confidence, current_eta=current_eta, threshold=threshold)
    return {"status": result.status, "diff_days": result.diff_days}


def _record(shipment: Shipment, *, current_eta=None, status=None, note="") -> dict:
    current = current_eta or parse_date(shipment.current_eta_raw)
    return {
        "carrier": shipment.carrier, "bl": shipment.bl,
        "current_eta": current.isoformat() if current else None,
        "new_eta": None, "diff_days": None, "status": status,
        "vessel": None, "pod": None, "confidence": None, "arrived": None, "page_state": None,
        "checked_at": datetime.now().replace(microsecond=0).isoformat(),
        "note": note, "evidence": None,
    }

"""Build the dashboard's data.json from raw Apify results.

Input: raw items (as Apify returns them), the baseline list (Carrier, BL, Current ETA) and yesterday's data.json.
Output: one document with every shipment's status, route and position, ETA history across runs, and a summary.
Pure apart from reading/writing the files in main().
"""

import csv
import json
import re
from datetime import date, datetime
from pathlib import Path

from .carriers import get_carrier
from .compare import FORSINKET, TIDLIGERE, TJEK_MANUELT, compare, parse_date
from .ports import PORTS


_BY_NAME = {name: code for code, (name, _, _) in PORTS.items()}


def _clean_name(name: str | None) -> str:
    return (name or "").split(",")[0].split("(")[0].strip().upper()


def _port(code: str | None, name: str | None, lat=None, lon=None) -> dict | None:
    if not code and not name:
        return None
    code = code or _BY_NAME.get(_clean_name(name))
    if (lat is None or lon is None) and code in PORTS:
        _, lat, lon = PORTS[code]
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        lat = lon = None
    return {"code": code, "name": _clean_name(name) or PORTS.get(code, ("",))[0], "lat": lat, "lon": lon}


def route_cma(item: dict) -> tuple[list[dict], dict | None]:
    """Stops in order (POL, transshipments, POD) and the latest place something actually happened."""
    stops: dict[str, dict] = {}
    position = None
    last_actual = ""
    for e in item.get("events") or []:
        call = e.get("transportCall") or {}
        loc = call.get("location") or {}
        code = loc.get("UNLocationCode") or call.get("UNLocationCode")
        kind = (e.get("carrierSpecificData") or {}).get("shipmentLocationType")
        port = _port(code, loc.get("locationName"), loc.get("latitude"), loc.get("longitude"))
        if kind in ("POL", "PTS", "POD") and port and code not in stops:
            order = {"POL": 0, "PTS": 1, "POD": 2}[kind]
            stops[code] = {**port, "kind": kind, "order": (order, e.get("eventDateTime") or "9999")}
        if e.get("eventClassifierCode") == "ACT" and port and (e.get("eventDateTime") or "") > last_actual:
            last_actual = e["eventDateTime"]
            label = (e.get("carrierSpecificData") or {}).get("internalEventLabel") or ""
            position = {**port, "event": label, "date": last_actual[:10]}
    ordered = sorted(stops.values(), key=lambda s: s.pop("order"))
    return ordered, position


def route_msc(item: dict) -> tuple[list[dict], dict | None]:
    bls = item.get("bill_of_ladings") or []
    if not bls:
        return [], None
    bl = bls[0]
    info = bl.get("GeneralTrackingInfo") or {}
    containers = bl.get("ContainersInfo") or []
    codes = {}
    for c in containers:
        for e in c.get("Events") or []:
            if e.get("Location"):
                codes[e["Location"].upper()] = e.get("UnLocationCode")

    def stop(name, kind):
        port = _port(codes.get((name or "").upper()), name)
        return {**port, "kind": kind} if port else None

    stops = [stop(info.get("PortOfLoad"), "POL")]
    stops += [stop(t, "PTS") for t in info.get("Transshipments") or []]
    stops.append(stop(info.get("PortOfDischarge"), "POD"))

    position = None
    if containers:
        events = [e for e in containers[0].get("Events") or []
                  if "estimated" not in str(e.get("Description", "")).lower() and "intended" not in str(e.get("Description", "")).lower()]
        if events:
            latest = max(events, key=lambda e: e.get("Order", 0))
            port = _port(latest.get("UnLocationCode"), latest.get("Location"))
            if port:
                d = parse_date(latest.get("Date"))
                position = {**port, "event": latest.get("Description", ""), "date": d.isoformat() if d else None}
    return [s for s in stops if s], position


ROUTES = {"CMA": route_cma, "MSC": route_msc}


def build(items: dict[str, dict], baseline: list[dict], previous: dict | None, today: date, threshold: int = 1,
          news: dict | None = None) -> dict:
    previous = previous or {}
    prev_rows = {s["bl"]: s for s in previous.get("shipments", [])}
    shipments = []
    for row in baseline:
        bl = row["BL"].strip()
        carrier = get_carrier(row["Carrier"])
        current = parse_date(row["Current ETA"])
        item = items.get(bl.upper())
        ex = carrier.parse(item) if carrier and item is not None else None
        failed = carrier is not None and ex is None
        new = ex.eta_date if ex and ex.page_state == "ok" else None
        res = compare(supported=carrier is not None, lookup_failed=failed, page_state=ex.page_state if ex else None,
                      new_eta=new, confidence=ex.confidence if ex else None, current_eta=current, threshold=threshold)
        route, position = ROUTES[carrier.code](item) if carrier and item else ([], None)

        history = list(prev_rows.get(bl, {}).get("history", []))
        if new and (not history or history[-1]["eta"] != new.isoformat()):
            history.append({"date": today.isoformat(), "eta": new.isoformat()})
        prev_eta = prev_rows.get(bl, {}).get("new_eta")
        shipments.append({
            "carrier": carrier.name if carrier else row["Carrier"], "bl": bl,
            "current_eta": current.isoformat() if current else None,
            "new_eta": new.isoformat() if new else None,
            "diff_days": res.diff_days, "status": res.status,
            "changed_since_last": bool(prev_eta and new and prev_eta != new.isoformat()),
            "vessel": ex.vessel if ex else None, "pod": ex.pod if ex else None,
            "arrived": bool(ex and ex.arrived),
            "note": ex.note if ex else ("Rederiet returnerede intet" if carrier else "Rederi understøttes ikke"),
            "route": route, "position": position, "history": history,
        })

    linked_news = link_news(news, shipments)
    counts: dict[str, int] = {}
    for s in shipments:
        counts[s["status"]] = counts.get(s["status"], 0) + 1
    runs = [r for r in previous.get("runs", []) if r["date"] != today.isoformat()]
    runs.append({"date": today.isoformat(), "counts": counts})
    return {
        "generated_at": _now_copenhagen().isoformat(),
        "run_date": today.isoformat(),
        "threshold_days": threshold,
        "summary": summarize(shipments),
        "counts": counts,
        "runs": runs[-60:],
        "shipments": shipments,
        "news": linked_news,
    }


ROLE = {"POL": "afgangshavn", "PTS": "omladning", "POD": "destination"}
SEVERITY_ORDER = {"høj": 0, "middel": 1, "lav": 2, "info": 3}
DEPARTED = re.compile(r"depart|loaded on (board|vessel)", re.IGNORECASE)


def link_news(news: dict | None, shipments: list[dict]) -> dict | None:
    """Attach each news item to the shipments whose remaining route passes its ports.

    A port counts for a shipment when it is the port of loading and the shipment is still there,
    or a transshipment/destination the shipment has not arrived at yet.
    """
    if not news:
        return None
    items = []
    for item in news.get("items", []):
        ports = set(item.get("ports") or [])
        affected = []
        for s in shipments:
            if s["arrived"] or not ports:
                continue
            here = (s.get("position") or {}).get("code")
            left_origin = bool(DEPARTED.search((s.get("position") or {}).get("event") or ""))
            stops = s["route"]
            passed = {p.get("code") for p in stops[: next((i for i, p in enumerate(stops) if p.get("code") == here), 0)]}
            for stop in stops:
                code = stop.get("code")
                if code not in ports or code in passed:
                    continue
                if stop["kind"] == "POL" and (here != code or left_origin):
                    continue
                affected.append({"bl": s["bl"], "port": stop["name"], "role": ROLE[stop["kind"]]})
                s.setdefault("risks", []).append({"id": item["id"], "title": item["title"], "severity": item["severity"],
                                                  "port": stop["name"], "role": ROLE[stop["kind"]]})
                break
        items.append({**item, "affected": affected})
    items.sort(key=lambda i: (SEVERITY_ORDER.get(i["severity"], 9), -len(i["affected"])))
    return {"checked_at": news.get("checked_at"), "items": items}


def summarize(shipments: list[dict]) -> str:
    """Plain-Danish default summary. The morning job may replace it with Claude's own briefing."""
    late = sorted([s for s in shipments if s["status"] == FORSINKET], key=lambda s: -(s["diff_days"] or 0))
    early = [s for s in shipments if s["status"] == TIDLIGERE]
    check = [s for s in shipments if s["status"] == TJEK_MANUELT]
    changed = [s for s in shipments if s["changed_since_last"]]
    parts = [f"{len(late)} af {len(shipments)} forsendelser er forsinket i forhold til jeres liste."]
    if late:
        top = ", ".join(f"{s['bl']} (+{s['diff_days']} dage til {s['pod']})" for s in late[:3])
        parts.append(f"Størst: {top}.")
    if check:
        parts.append(f"{len(check)} har endnu ingen ankomstdato og bør tjekkes.")
    if early:
        parts.append(f"{len(early)} kommer tidligere end ventet.")
    if changed:
        parts.append(f"{len(changed)} har fået ny ETA siden sidste kørsel.")
    return " ".join(parts)


def _now_copenhagen() -> datetime:
    """Local Danish time without offset, as the dashboard shows it ("Opdateret kl. HH:MM")."""
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Europe/Copenhagen")).replace(microsecond=0, tzinfo=None)
    except Exception:
        return datetime.now().replace(microsecond=0)


def _load_items(path: Path) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data["items"] if isinstance(data, dict) and "items" in data else data
    return {str(i.get("tracking_number", "")).strip().upper(): i for i in items if isinstance(i, dict)}


def main(raw_files: list[Path], baseline_csv: Path, previous: Path | None, out: Path, summary: str | None,
         today: date | None = None, news: Path | None = None) -> dict:
    items: dict[str, dict] = {}
    for f in raw_files:
        items.update(_load_items(f))
    with baseline_csv.open(encoding="utf-8") as f:
        baseline = [r for r in csv.DictReader(f) if r.get("BL", "").strip()]
    prev = json.loads(previous.read_text(encoding="utf-8")) if previous and previous.exists() else None
    news_doc = json.loads(news.read_text(encoding="utf-8")) if news and news.exists() else None
    doc = build(items, baseline, prev, today or _now_copenhagen().date(), news=news_doc)
    if summary:
        doc["summary"] = summary
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    return doc

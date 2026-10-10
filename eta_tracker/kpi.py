"""'Hvor opstår forsinkelsen': figures built only from data we actually have.

Carriers overwrite their own plans once a leg has happened (CMA's PLN event gets the actual date), so
"departed later than planned" cannot be read from one day's data. What we can measure:
- dwell at transshipment ports (actual arrival -> actual or planned departure),
- delay against the customer's own list, per carrier and destination,
- how often a carrier has moved the ETA (from our own daily history),
- from now on, how each leg's planned date moves between our daily runs (`plan`, kept per shipment).

dashboard/index.html mirrors dwell_* and build_kpis in JavaScript; keep the two in step.
"""

import math
from collections import defaultdict
from datetime import date

from .compare import FORSINKET, TIDLIGERE, UAENDRET, parse_date

LONG_DWELL_DAYS = 7


def _clean(name: str | None) -> str:
    return (name or "").split(",")[0].split("(")[0].strip().upper()


def _days(a: date, b: date) -> int:
    return (b - a).days


def dwell_cma(item: dict, today: date) -> list[dict]:
    """Days each transshipment port held the cargo. `ongoing` when it has arrived but not left yet."""
    calls: dict[str, dict] = defaultdict(dict)
    for e in item.get("events") or []:
        if e.get("eventType") != "TRANSPORT" or not e.get("eventDateTime"):
            continue
        if (e.get("carrierSpecificData") or {}).get("shipmentLocationType") != "PTS":
            continue
        call = e.get("transportCall") or {}
        loc = call.get("location") or {}
        code = loc.get("UNLocationCode") or call.get("UNLocationCode")
        if not code:
            continue
        kind = f'{e.get("transportEventTypeCode")}:{e.get("eventClassifierCode")}'
        stamp = (e.get("eventCreatedDateTime") or "") + e["eventDateTime"]
        prev = calls[code].get(kind)
        if prev is None or stamp > prev[0]:
            calls[code][kind] = (stamp, e["eventDateTime"][:10])
        calls[code]["name"] = _clean(loc.get("locationName"))
    out = []
    for code, c in calls.items():
        arrived = c.get("ARRI:ACT")
        if not arrived:
            continue
        a = date.fromisoformat(arrived[1])
        left = c.get("DEPA:ACT")
        planned = c.get("DEPA:PLN")
        if left:
            d = date.fromisoformat(left[1])
            out.append({"code": code, "name": c["name"], "arrived": a.isoformat(), "departed": d.isoformat(),
                        "days": _days(a, d), "ongoing": False, "planned_departure": None})
        else:
            out.append({"code": code, "name": c["name"], "arrived": a.isoformat(), "departed": None,
                        "days": max(0, _days(a, today)), "ongoing": True,
                        "planned_departure": planned[1] if planned else None})
    return sorted(out, key=lambda s: s["arrived"])


def dwell_msc(item: dict, today: date) -> list[dict]:
    """MSC: each 'Transshipment Discharged' opens a stay, the next 'Transshipment Loaded' closes it.

    Paired in event order rather than by place name, because the box can be discharged at one terminal
    and loaded at a neighbouring one (Port Elizabeth -> Coega). The stay is named after the discharge port.
    """
    bls = item.get("bill_of_ladings") or []
    containers = (bls[0].get("ContainersInfo") or []) if bls else []
    if not containers:
        return []
    events = []
    for e in containers[0].get("Events") or []:
        desc = str(e.get("Description", "")).lower()
        d = parse_date(e.get("Date"))
        if "transshipment" in desc and d and ("discharged" in desc or "loaded" in desc):
            events.append((e.get("Order", 0), d, "in" if "discharged" in desc else "out", e))
    events.sort(key=lambda x: (x[0], x[1]))
    out, open_stay = [], None
    for _, d, kind, e in events:
        if kind == "in":
            if open_stay is None:
                open_stay = {"code": e.get("UnLocationCode"), "name": _clean(e.get("Location")), "arrived": d}
        elif open_stay is not None:
            out.append({**open_stay, "arrived": open_stay["arrived"].isoformat(), "departed": d.isoformat(),
                        "days": _days(open_stay["arrived"], d), "ongoing": False, "planned_departure": None})
            open_stay = None
    if open_stay is not None:
        out.append({**open_stay, "arrived": open_stay["arrived"].isoformat(), "departed": None,
                    "days": max(0, _days(open_stay["arrived"], today)), "ongoing": True, "planned_departure": None})
    return out


DWELL = {"CMA": dwell_cma, "MSC": dwell_msc}


def containers_cma(item: dict) -> list[str]:
    return sorted({str(e["equipmentReference"]).strip().upper() for e in item.get("events") or [] if e.get("equipmentReference")})


def containers_msc(item: dict) -> list[str]:
    bls = item.get("bill_of_ladings") or []
    cs = (bls[0].get("ContainersInfo") or []) if bls else []
    return sorted({str(c["ContainerNumber"]).strip().upper() for c in cs if c.get("ContainerNumber")})


CONTAINERS = {"CMA": containers_cma, "MSC": containers_msc}


def plan_cma(item: dict) -> dict[str, str]:
    """Each leg's current date as the carrier states it today, e.g. {'DEPA:LKCMB': '2026-10-30'}."""
    best: dict[str, tuple[str, str]] = {}
    for e in item.get("events") or []:
        if e.get("eventType") != "TRANSPORT" or not e.get("eventDateTime"):
            continue
        call = e.get("transportCall") or {}
        code = (call.get("location") or {}).get("UNLocationCode") or call.get("UNLocationCode")
        if not code or e.get("transportEventTypeCode") not in ("ARRI", "DEPA"):
            continue
        key = f'{e["transportEventTypeCode"]}:{code}'
        rank = (1 if e.get("eventClassifierCode") == "ACT" else 0, e.get("eventCreatedDateTime") or "")
        if key not in best or rank > best[key][0]:
            best[key] = (rank, e["eventDateTime"][:10])
    return {k: v[1] for k, v in best.items()}


def merge_plan(previous: dict | None, today_plan: dict[str, str], run_date: str) -> dict[str, list]:
    """Per leg, the dates we have seen, one entry per change: {'DEPA:LKCMB': [{'date':..., 'planned':...}, ...]}."""
    merged = {k: list(v) for k, v in (previous or {}).items()}
    for key, planned in today_plan.items():
        seen = merged.setdefault(key, [])
        if not seen or seen[-1]["planned"] != planned:
            seen.append({"date": run_date, "planned": planned})
    return merged


def _avg(xs: list[float]) -> float | None:
    """Mean to one decimal, halves rounded up (as Math.floor(x * 10 + 0.5) / 10 in the page)."""
    return math.floor(sum(xs) / len(xs) * 10 + 0.5) / 10 if xs else None


def build_kpis(shipments: list[dict], since: str | None) -> dict:
    """Aggregates for the 'Forsinkelser' tab. Every figure carries n."""
    compared = [s for s in shipments if s.get("diff_days") is not None and s.get("status") in (FORSINKET, TIDLIGERE, UAENDRET)]
    late = [s for s in compared if s["status"] == FORSINKET]

    def group(key):
        g = defaultdict(list)
        for s in compared:
            g[key(s)].append(s)
        rows = []
        for k, items in g.items():
            lt = [s["diff_days"] for s in items if s["status"] == FORSINKET]
            rows.append({"key": k, "n": len(items), "late": len(lt), "avg_late_days": _avg(lt)})
        return sorted(rows, key=lambda r: (-(r["avg_late_days"] or 0), -r["n"], r["key"]))

    stops = [(s, d) for s in shipments for d in s.get("dwell") or []]
    by_port = defaultdict(list)
    for s, d in stops:
        by_port[(d["code"] or d["name"], d["name"])].append(d)
    ports = sorted(({"code": code, "name": name, "n": len(ds), "avg_days": _avg([d["days"] for d in ds]),
                     "max_days": max(d["days"] for d in ds), "ongoing": sum(d["ongoing"] for d in ds)}
                    for (code, name), ds in by_port.items()), key=lambda r: (-(r["avg_days"] or 0), r["name"]))
    long_stays = sorted(({"bl": s["bl"], "port": d["name"], "days": d["days"], "ongoing": d["ongoing"]}
                         for s, d in stops if d["days"] >= LONG_DWELL_DAYS), key=lambda r: -r["days"])

    moves = defaultdict(list)
    for s in shipments:
        moves[s.get("carrier")].append(max(0, len(s.get("history") or []) - 1))
    eta_moves = sorted(({"carrier": c, "n": len(m), "avg_moves": _avg(m), "moved": sum(1 for x in m if x)}
                        for c, m in moves.items()), key=lambda r: r["carrier"] or "")
    top_moved = sorted(({"bl": s["bl"], "moves": len(s["history"]) - 1} for s in shipments
                        if len(s.get("history") or []) > 1), key=lambda r: (-r["moves"], r["bl"]))[:5]

    legs = [(s["bl"], k, v) for s in shipments for k, v in (s.get("plan") or {}).items()]
    slipped = [{"bl": bl, "leg": k, "first": v[0]["planned"], "now": v[-1]["planned"],
                "days": (date.fromisoformat(v[-1]["planned"]) - date.fromisoformat(v[0]["planned"])).days}
               for bl, k, v in legs if len(v) > 1]
    plan_since = min((v[0]["date"] for _, _, v in legs if v), default=None)

    return {
        "on_time": {"n": len(compared), "late": len(late),
                    "early": sum(1 for s in compared if s["status"] == TIDLIGERE),
                    "on_time": sum(1 for s in compared if s["status"] != FORSINKET),
                    "avg_late_days": _avg([s["diff_days"] for s in late])},
        "by_carrier": group(lambda s: s.get("carrier")),
        "by_destination": group(lambda s: _clean(s.get("pod")) or "–"),
        "dwell": {"n_shipments": len({s["bl"] for s, _ in stops}), "n_stops": len(stops), "ports": ports,
                  "long": long_stays, "threshold_days": LONG_DWELL_DAYS},
        "eta_moves": {"since": since, "by_carrier": eta_moves, "top": top_moved},
        "plan": {"since": plan_since, "n_legs": len(legs), "slipped": sorted(slipped, key=lambda r: -abs(r["days"]))},
    }

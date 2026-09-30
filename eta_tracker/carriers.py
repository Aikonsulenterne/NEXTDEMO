"""Carrier data -> Extraction. Pure functions, no I/O.

Apify actors return each carrier's own tracking data as JSON. The parsers pick the ETA at the port of
discharge (POD). If the data does not have the expected shape, a parser returns None and run.py lets
Claude read the raw JSON instead (docs/ARCHITECTURE.md).
"""

from dataclasses import dataclass
from typing import Callable

from .compare import parse_date
from .extract import Extraction


def _not_found(note: str) -> Extraction:
    return Extraction(page_state="not_found", eta=None, arrived=False, vessel=None, pod=None,
                      confidence="high", note=note)


def _clean(value: str | None) -> str | None:
    return value.strip() if value and value.strip() else None


def parse_msc(item: dict) -> Extraction | None:
    """MSC gives the ETA directly: GeneralTrackingInfo.FinalPodEtaDate (dd/mm/yyyy)."""
    bls = item.get("bill_of_ladings") or []
    if not bls:
        return _not_found("MSC har ingen data for BL'et")
    bl = bls[0]
    info = bl.get("GeneralTrackingInfo") or {}
    containers = bl.get("ContainersInfo") or []

    eta = parse_date(info.get("FinalPodEtaDate"))
    container_etas = sorted({d for d in (parse_date(c.get("PodEtaDate")) for c in containers) if d})
    if container_etas:
        eta = max([eta, container_etas[-1]] if eta else container_etas)  # latest ETA: the one the shipment waits for
    if eta is None:
        return None

    vessel = None
    for container in containers:
        for event in container.get("Events") or []:
            if "estimated time of arrival" in str(event.get("Description", "")).lower() and event.get("Detail"):
                vessel = _clean(event["Detail"][0])
                break
        if vessel:
            break

    pod = _clean(info.get("PortOfDischarge"))
    arrived = bool(bl.get("Delivered"))
    notes = []
    if arrived:
        notes.append("Ankommet")
    notes.append(f"ETA ved {pod}" if pod else "ETA ved POD")
    transshipments = [_clean(t) for t in info.get("Transshipments") or [] if t]
    if transshipments:
        notes.append("via " + ", ".join(transshipments))
    if len(container_etas) > 1:
        notes.append("containere har forskellige ETA'er: " + ", ".join(d.strftime("%d-%m-%Y") for d in container_etas))
    return Extraction(page_state="ok", eta=eta.isoformat(), arrived=arrived, vessel=vessel, pod=pod,
                      confidence="high", note=", ".join(notes))


def parse_cma(item: dict) -> Extraction | None:
    """CMA gives DCSA events. ETA = 'Vessel Arrival' (ARRI) at the location marked POD.
    Actual (ACT) beats planned (PLN); among plans, the most recently updated wins."""
    events = item.get("events") or []
    if not events:
        return _not_found("CMA CGM har ingen data for BL'et")

    arrivals = [
        e for e in events
        if e.get("eventType") == "TRANSPORT" and e.get("transportEventTypeCode") == "ARRI"
    ]
    pod_all = [e for e in arrivals if (e.get("carrierSpecificData") or {}).get("shipmentLocationType") == "POD"]
    pod_arrivals = [e for e in pod_all if e.get("eventDateTime")]
    if not pod_arrivals:
        if pod_all:
            return _pod_not_scheduled(pod_all[0], arrivals)
        return None

    actual = [e for e in pod_arrivals if e.get("eventClassifierCode") == "ACT"]
    if actual:
        chosen = max(actual, key=lambda e: e["eventDateTime"])
    else:
        chosen = max(pod_arrivals, key=lambda e: (e.get("eventCreatedDateTime", ""), e["eventDateTime"]))

    eta = parse_date(chosen["eventDateTime"][:10])  # local date at the port, as the carrier's site shows it
    if eta is None:
        return None
    call = chosen.get("transportCall") or {}
    pod = _clean((call.get("location") or {}).get("locationName"))
    vessel = _clean((call.get("vessel") or {}).get("vesselName"))
    transshipments = sorted({
        _clean((e.get("transportCall") or {}).get("location", {}).get("locationName"))
        for e in events
        if (e.get("carrierSpecificData") or {}).get("shipmentLocationType") == "PTS"
    } - {None})

    arrived = bool(actual)
    notes = ["Ankommet" if arrived else f"ETA ved {pod}" if pod else "ETA ved POD"]
    if transshipments:
        notes.append("via " + ", ".join(transshipments))
    return Extraction(page_state="ok", eta=eta.isoformat(), arrived=arrived, vessel=vessel, pod=pod,
                      confidence="high", note=", ".join(notes))


def _pod_not_scheduled(pod_event: dict, arrivals: list[dict]) -> Extraction:
    """CMA knows the destination but has no date for it yet (onward vessel not planned).
    Tell the user the latest dated stop instead, since the shipment cannot arrive before that."""
    pod = _clean(((pod_event.get("transportCall") or {}).get("location") or {}).get("locationName"))
    dated = [
        e for e in arrivals
        if e.get("eventDateTime") and (e.get("carrierSpecificData") or {}).get("shipmentLocationType") == "PTS"
    ]
    note = f"CMA CGM har endnu ingen dato for ankomst til {pod or 'POD'} (videre skib ikke planlagt)"
    if dated:
        last = max(dated, key=lambda e: e["eventDateTime"])
        where = _clean(((last.get("transportCall") or {}).get("location") or {}).get("locationName"))
        when = parse_date(last["eventDateTime"][:10])
        if when:
            note += f". Når først omladning i {where} {when.strftime('%d-%m-%Y')}"
    return Extraction(page_state="ok", eta=None, arrived=False, vessel=None, pod=pod,
                      confidence="low", note=note)


@dataclass(frozen=True)
class Carrier:
    code: str
    name: str
    actor_setting: str  # Settings attribute holding the Apify actor name
    parse: Callable[[dict], Extraction | None]


CARRIERS = {
    "CMA": Carrier("CMA", "CMA CGM", "actor_cma", parse_cma),
    "MSC": Carrier("MSC", "MSC", "actor_msc", parse_msc),
}
ALIASES = {"CMA CGM": "CMA"}


def get_carrier(code: str) -> Carrier | None:
    key = code.strip().upper()
    return CARRIERS.get(ALIASES.get(key, key))

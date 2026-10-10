import json
from datetime import date
from pathlib import Path

from eta_tracker.kpi import build_kpis, dwell_cma, dwell_msc, merge_plan, plan_cma

FIXTURES = Path(__file__).parent / "fixtures"


def ev(kind, cls, code, name, when, created="2026-09-01T00:00:00", loc_type="PTS"):
    return {"eventType": "TRANSPORT", "transportEventTypeCode": kind, "eventClassifierCode": cls,
            "eventDateTime": when + "T10:00:00", "eventCreatedDateTime": created,
            "carrierSpecificData": {"shipmentLocationType": loc_type},
            "transportCall": {"location": {"UNLocationCode": code, "locationName": name}}}


def test_cma_dwell_done_ongoing_and_not_yet_arrived():
    item = {"events": [
        ev("ARRI", "ACT", "SGSIN", "SINGAPORE", "2026-08-21"), ev("DEPA", "ACT", "SGSIN", "SINGAPORE", "2026-09-07"),
        ev("DEPA", "PLN", "SGSIN", "SINGAPORE", "2026-09-07", created="2026-10-07T00:00:00"),
        ev("ARRI", "ACT", "ESALG", "ALGECIRAS (ALG)", "2026-10-02"), ev("DEPA", "PLN", "ESALG", "ALGECIRAS", "2026-10-19"),
        ev("ARRI", "PLN", "LKCMB", "COLOMBO", "2026-10-25"),
        ev("ARRI", "PLN", "LRMLW", "MONROVIA", "2026-11-07", loc_type="POD"),
    ]}
    d = dwell_cma(item, date(2026, 10, 8))
    assert [(x["name"], x["days"], x["ongoing"]) for x in d] == [("SINGAPORE", 17, False), ("ALGECIRAS", 6, True)]
    assert d[1]["planned_departure"] == "2026-10-19"


def test_msc_dwell_from_transshipment_events():
    item = json.loads((FIXTURES / "msc_MEDUKC776011.json").read_text())
    d = dwell_msc(item, date(2026, 9, 30))
    # trimmed fixture: discharged at Port Elizabeth 20 Sep, not loaded again yet
    assert d == [{"code": "ZAPLZ", "name": "PORT ELIZABETH", "arrived": "2026-09-20", "departed": None,
                  "days": 10, "ongoing": True, "planned_departure": None}]


def test_plan_tracks_leg_changes_between_runs():
    item = {"events": [ev("DEPA", "PLN", "LKCMB", "COLOMBO", "2026-10-30")]}
    p1 = merge_plan(None, plan_cma(item), "2026-10-08")
    item2 = {"events": [ev("DEPA", "PLN", "LKCMB", "COLOMBO", "2026-11-02", created="2026-10-09T00:00:00")]}
    p2 = merge_plan(p1, plan_cma(item2), "2026-10-09")
    p3 = merge_plan(p2, plan_cma(item2), "2026-10-10")
    assert p3["DEPA:LKCMB"] == [{"date": "2026-10-08", "planned": "2026-10-30"}, {"date": "2026-10-09", "planned": "2026-11-02"}]
    k = build_kpis([{"bl": "X", "carrier": "CMA CGM", "status": "Forsinket", "diff_days": 3, "plan": p3, "history": []}], None)
    assert k["plan"]["slipped"] == [{"bl": "X", "leg": "DEPA:LKCMB", "first": "2026-10-30", "now": "2026-11-02", "days": 3}]
    assert k["plan"]["since"] == "2026-10-08"


def test_kpis_counts_carry_n():
    ships = [
        {"bl": "A", "carrier": "MSC", "pod": "MOMBASA, KE", "status": "Forsinket", "diff_days": 10,
         "history": [{"eta": 1}, {"eta": 2}, {"eta": 3}], "dwell": [{"code": "SGSIN", "name": "SINGAPORE", "days": 9, "ongoing": False}]},
        {"bl": "B", "carrier": "MSC", "pod": "MOMBASA", "status": "Uændret", "diff_days": 0, "history": [{"eta": 1}]},
        {"bl": "C", "carrier": "CMA CGM", "pod": "TEMA", "status": "Tjek manuelt", "diff_days": None, "history": []},
    ]
    k = build_kpis(ships, "2026-09-30")
    assert k["on_time"] == {"n": 2, "late": 1, "early": 0, "on_time": 1, "avg_late_days": 10.0}
    assert k["by_destination"][0] == {"key": "MOMBASA", "n": 2, "late": 1, "avg_late_days": 10.0}
    assert k["dwell"]["long"] == [{"bl": "A", "port": "SINGAPORE", "days": 9, "ongoing": False}]
    assert k["eta_moves"]["top"] == [{"bl": "A", "moves": 2}]
    assert {r["carrier"]: r["moved"] for r in k["eta_moves"]["by_carrier"]} == {"MSC": 1, "CMA CGM": 0}

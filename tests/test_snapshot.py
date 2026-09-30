import json
from datetime import date
from pathlib import Path

from eta_tracker.snapshot import build

FIXTURES = Path(__file__).parent / "fixtures"
BASELINE = [
    {"Carrier": "MSC", "BL": "MEDUKC776011", "Current ETA": "2026-10-01"},
    {"Carrier": "CMA", "BL": "COP0305302", "Current ETA": "2026-10-03"},
    {"Carrier": "CMA", "BL": "COP0306236", "Current ETA": "2026-10-14"},
    {"Carrier": "CMA", "BL": "COP0308433", "Current ETA": "2026-10-21"},
]


def items():
    return {n: json.loads((FIXTURES / f).read_text()) for n, f in [
        ("MEDUKC776011", "msc_MEDUKC776011.json"), ("COP0305302", "cma_COP0305302.json"),
        ("COP0306236", "cma_COP0306236.json")]}


def test_build_statuses_routes_and_summary():
    doc = build(items(), BASELINE, None, date(2026, 9, 30))
    by = {s["bl"]: s for s in doc["shipments"]}
    assert by["MEDUKC776011"]["status"] == "Forsinket" and by["MEDUKC776011"]["diff_days"] == 2
    assert [p["name"] for p in by["MEDUKC776011"]["route"]] == ["BUSAN", "COEGA", "MAPUTO"]
    assert by["MEDUKC776011"]["position"]["name"] == "PORT ELIZABETH"  # latest actual event in the trimmed fixture
    assert [p["kind"] for p in by["COP0305302"]["route"]] == ["POL", "PTS", "POD"]
    assert all(p["lat"] is not None for s in doc["shipments"] for p in s["route"])
    assert by["COP0306236"]["status"] == "Tjek manuelt"
    assert by["COP0308433"]["status"] == "Ikke fundet"
    assert doc["counts"] == {"Forsinket": 1, "Uændret": 1, "Tjek manuelt": 1, "Ikke fundet": 1}
    assert doc["summary"].startswith("1 af 4")


def test_history_and_change_flag_across_days():
    day1 = build(items(), BASELINE, None, date(2026, 9, 30))
    moved = items()
    moved["MEDUKC776011"]["bill_of_ladings"][0]["GeneralTrackingInfo"]["FinalPodEtaDate"] = "05/10/2026"
    moved["MEDUKC776011"]["bill_of_ladings"][0]["ContainersInfo"][0]["PodEtaDate"] = "05/10/2026"
    day2 = build(moved, BASELINE, day1, date(2026, 10, 1))
    s = next(x for x in day2["shipments"] if x["bl"] == "MEDUKC776011")
    assert s["changed_since_last"] and s["diff_days"] == 4
    assert s["history"] == [{"date": "2026-09-30", "eta": "2026-10-03"}, {"date": "2026-10-01", "eta": "2026-10-05"}]
    assert [r["date"] for r in day2["runs"]] == ["2026-09-30", "2026-10-01"]
    assert "1 har fået ny ETA" in day2["summary"]

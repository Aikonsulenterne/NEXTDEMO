import copy
import json
from pathlib import Path

import httpx
import pytest

from eta_tracker import apify as apify_mod
from eta_tracker.apify import Apify, ApifyError
from eta_tracker.carriers import get_carrier, parse_cma, parse_msc

FIXTURES = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# --- MSC (real result for MEDUKC776011, checked against msc.com: POD ETA 03/10/2026) ---

def test_msc_real_result():
    ex = parse_msc(load("msc_MEDUKC776011.json"))
    assert ex.page_state == "ok"
    assert ex.eta == "2026-10-03"
    assert ex.pod == "MAPUTO, MZ"
    assert ex.vessel == "MSC SANDY III"
    assert not ex.arrived
    assert "COEGA, ZA" in ex.note


def test_msc_multiple_containers_takes_latest_eta():
    item = load("msc_MEDUKC776011.json")
    containers = item["bill_of_ladings"][0]["ContainersInfo"]
    extra = copy.deepcopy(containers[0])
    extra["PodEtaDate"] = "07/10/2026"
    containers.append(extra)
    ex = parse_msc(item)
    assert ex.eta == "2026-10-07"
    assert "03-10-2026" in ex.note and "07-10-2026" in ex.note


def test_msc_delivered_is_arrived():
    item = load("msc_MEDUKC776011.json")
    item["bill_of_ladings"][0]["Delivered"] = True
    ex = parse_msc(item)
    assert ex.arrived and ex.note.startswith("Ankommet")


def test_msc_unknown_bl_is_not_found():
    ex = parse_msc({"tracking_number": "MEDUX", "bill_of_ladings": []})
    assert ex.page_state == "not_found"


def test_msc_unexpected_shape_falls_back_to_claude():
    item = load("msc_MEDUKC776011.json")
    item["bill_of_ladings"][0]["GeneralTrackingInfo"]["FinalPodEtaDate"] = None
    item["bill_of_ladings"][0]["ContainersInfo"][0]["PodEtaDate"] = "snart"
    assert parse_msc(item) is None


# --- CMA (real result for COP0305302: vessel arrival at POD Mombasa 03-10-2026) ---

def test_cma_real_result_picks_vessel_arrival_at_pod():
    ex = parse_cma(load("cma_COP0305302.json"))
    assert ex.page_state == "ok"
    assert ex.eta == "2026-10-03"  # not the 02-10 truck arrival at the depot
    assert ex.pod == "MOMBASA"
    assert ex.vessel == "HYUNDAI BUSAN"
    assert not ex.arrived
    assert "COLOMBO" in ex.note


def test_cma_newest_plan_wins():
    item = load("cma_COP0305302.json")
    older = copy.deepcopy(item["events"][1])
    older["eventCreatedDateTime"] = "2026-09-01T00:00:00Z"
    older["eventDateTime"] = "2026-09-28T07:00:00+03:00"
    item["events"].append(older)
    assert parse_cma(item).eta == "2026-10-03"


def test_cma_actual_arrival_beats_plan():
    item = load("cma_COP0305302.json")
    actual = copy.deepcopy(item["events"][1])
    actual["eventClassifierCode"] = "ACT"
    actual["eventDateTime"] = "2026-10-05T02:00:00+03:00"
    actual["eventCreatedDateTime"] = "2026-09-01T00:00:00Z"
    item["events"].append(actual)
    ex = parse_cma(item)
    assert ex.eta == "2026-10-05" and ex.arrived and ex.note.startswith("Ankommet")


def test_cma_no_events_is_not_found():
    assert parse_cma({"tracking_number": "COPX", "events": []}).page_state == "not_found"


def test_cma_without_pod_arrival_falls_back_to_claude():
    item = load("cma_COP0305302.json")
    for e in item["events"]:
        e.get("carrierSpecificData", {}).pop("shipmentLocationType", None)
    assert parse_cma(item) is None


def test_get_carrier():
    assert get_carrier(" cma cgm ").code == "CMA"
    assert get_carrier("msc").code == "MSC"
    assert get_carrier("HAPAG") is None


# --- Apify client ---

def fake_post(status=200, payload=None, exc=None):
    calls = []

    def post(url, headers, json, timeout):
        calls.append((url, headers, json))
        if exc:
            raise exc
        return httpx.Response(status, json=payload if payload is not None else [])
    return post, calls


def test_apify_track_maps_items_by_bl(monkeypatch):
    post, calls = fake_post(payload=[{"tracking_number": "cop0305302 ", "events": []}, "junk"])
    monkeypatch.setattr(apify_mod.httpx, "post", post)
    result = Apify("tok").track("user/actor-name", ["COP0305302"])
    assert list(result) == ["COP0305302"]
    url, headers, body = calls[0]
    assert "user~actor-name" in url and headers["Authorization"] == "Bearer tok"
    assert body == {"trackingNumbers": ["COP0305302"]}


@pytest.mark.parametrize("status, message", [(401, "afviste"), (500, "HTTP 500")])
def test_apify_http_errors(monkeypatch, status, message):
    post, _ = fake_post(status=status, payload={"error": "x"})
    monkeypatch.setattr(apify_mod.httpx, "post", post)
    with pytest.raises(ApifyError, match=message):
        Apify("tok").track("a/b", ["X"])


def test_apify_timeout(monkeypatch):
    post, _ = fake_post(exc=httpx.ReadTimeout("slow"))
    monkeypatch.setattr(apify_mod.httpx, "post", post)
    with pytest.raises(ApifyError, match="tide"):
        Apify("tok").track("a/b", ["X"])


def test_apify_requires_token():
    with pytest.raises(ApifyError, match="APIFY_TOKEN"):
        Apify("")


def test_cma_pod_without_date_needs_manual_check_and_says_why():
    ex = parse_cma(load("cma_COP0306236.json"))  # real case: onward vessel from Colombo not planned yet
    assert ex.page_state == "ok" and ex.eta is None and ex.confidence == "low"
    assert "MOMBASA" in ex.note and "COLOMBO 19-10-2026" in ex.note


def test_msc_discharged_without_eta_counts_as_arrived():
    import copy
    item = copy.deepcopy(json.loads((FIXTURES / "msc_MEDUKC776011.json").read_text()))
    bl = item["bill_of_ladings"][0]
    bl["GeneralTrackingInfo"]["FinalPodEtaDate"] = ""
    for c in bl["ContainersInfo"]:
        c["PodEtaDate"] = ""
        c["Events"].insert(0, {"Order": 99, "Date": "04/10/2026", "Description": "Import Discharged from Vessel",
                               "Location": "MAPUTO, MZ", "UnLocationCode": "MZMPM", "Detail": []})
    ex = parse_msc(item)
    assert ex.page_state == "ok" and ex.eta == "2026-10-04" and ex.arrived
    assert ex.note.startswith("Losset i MAPUTO, MZ 04-10-2026")

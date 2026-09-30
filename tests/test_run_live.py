"""End-to-end live run with a fake Apify and no Google Sheet (terminal-only mode)."""

import dataclasses
import json
from pathlib import Path

from eta_tracker import run as run_mod
from eta_tracker.config import load_settings
from eta_tracker.sheet import Shipment

FIXTURES = Path(__file__).parent / "fixtures"


class FakeApify:
    def __init__(self, token, timeout):
        pass

    def track(self, actor, numbers):
        items = {
            "COP0305302": json.loads((FIXTURES / "cma_COP0305302.json").read_text()),
            "MEDUKC776011": json.loads((FIXTURES / "msc_MEDUKC776011.json").read_text()),
        }
        return {n: items[n] for n in numbers if n in items}


def test_live_run_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setattr(run_mod, "Apify", FakeApify)
    monkeypatch.setattr(run_mod, "load_seed", lambda _: [
        Shipment("MSC", "MEDUKC776011", "2026-10-01"),
        Shipment("CMA", "COP0305302", "2026-10-03"),
        Shipment("CMA", "COP0308433", "2026-10-21"),
        Shipment("HAPAG", "HLCU1", "2026-10-01"),
    ])
    settings = dataclasses.replace(
        load_settings(), sheet_id="", apify_token="x", anthropic_api_key="",
        runs_dir=tmp_path / "runs", reveal_delay_seconds=0,
    )
    run_mod.run(settings, limit=None, bls=None, skip_checked=False, replay=False)

    results = json.loads(next((tmp_path / "runs").glob("*/results.json")).read_text())["results"]
    by_bl = {r["bl"]: r for r in results}
    assert (by_bl["MEDUKC776011"]["status"], by_bl["MEDUKC776011"]["diff_days"]) == ("Forsinket", 2)
    assert (by_bl["COP0305302"]["status"], by_bl["COP0305302"]["diff_days"]) == ("Uændret", 0)
    assert by_bl["COP0308433"]["status"] == "Ikke fundet"
    assert by_bl["HLCU1"]["status"] == "Ikke understøttet"
    assert by_bl["COP0305302"]["evidence"].endswith("COP0305302.json")


def test_live_run_apify_down_marks_rows_not_found(tmp_path, monkeypatch):
    class DownApify(FakeApify):
        def track(self, actor, numbers):
            raise run_mod.ApifyError("Ingen forbindelse til Apify")

    monkeypatch.setattr(run_mod, "Apify", DownApify)
    monkeypatch.setattr(run_mod, "load_seed", lambda _: [Shipment("MSC", "MEDUKC776011", "2026-10-01")])
    settings = dataclasses.replace(load_settings(), sheet_id="", apify_token="x", runs_dir=tmp_path / "runs",
                                   reveal_delay_seconds=0)
    run_mod.run(settings, limit=None, bls=None, skip_checked=False, replay=False)
    record = json.loads(next((tmp_path / "runs").glob("*/results.json")).read_text())["results"][0]
    assert record["status"] == "Ikke fundet" and "Apify" in record["note"]

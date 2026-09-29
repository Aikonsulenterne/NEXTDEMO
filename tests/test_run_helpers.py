import json

from eta_tracker.replay import load_best, save_results
from eta_tracker.run import select_shipments
from eta_tracker.sheet import Shipment, safe_text

SHIPMENTS = [
    Shipment("MSC", "MEDUKC776011", "2026-10-01", checked=True),
    Shipment("MSC", "MEDUYJ453487", "2026-09-29"),
    Shipment("CMA", "COP0305302", "2026-10-03"),
    Shipment("CMA", "COP0308433", "2026-10-21", checked=True),
]


def bls(selected):
    return [s.bl for s in selected]


def test_select_all():
    selected, missing = select_shipments(SHIPMENTS, None, False, None)
    assert bls(selected) == bls(SHIPMENTS) and missing == []


def test_select_by_bl_keeps_given_order_and_ignores_case():
    selected, missing = select_shipments(SHIPMENTS, [" cop0305302", "MEDUKC776011 ", "NOPE123"], False, None)
    assert bls(selected) == ["COP0305302", "MEDUKC776011"]
    assert missing == ["NOPE123"]


def test_skip_checked_then_limit():
    selected, _ = select_shipments(SHIPMENTS, None, True, 1)
    assert bls(selected) == ["MEDUYJ453487"]


def test_limit_zero():
    assert select_shipments(SHIPMENTS, None, False, 0)[0] == []


def test_replay_picks_newest_good_result_per_bl(tmp_path):
    save_results(tmp_path / "20260928-080000", "2026-09-28T08:00:00", [
        {"bl": "COP0305302", "status": "Forsinket", "note": "gammel"},
        {"bl": "MEDUKC776011", "status": "Uændret", "note": "kun i gammel kørsel"},
    ])
    save_results(tmp_path / "20260929-080000", "2026-09-29T08:00:00", [
        {"bl": "COP0305302", "status": "Tidligere", "note": "ny"},
        {"bl": "MEDUKC776011", "status": "Ikke fundet", "note": "blokeret"},
    ])
    (tmp_path / "20260930-080000").mkdir()
    (tmp_path / "20260930-080000" / "results.json").write_text("{ broken")

    best = load_best(tmp_path)
    assert best["COP0305302"]["note"] == "ny"
    assert best["MEDUKC776011"]["note"] == "kun i gammel kørsel"


def test_replay_without_runs_dir(tmp_path):
    assert load_best(tmp_path / "missing") == {}


def test_save_results_is_valid_json(tmp_path):
    save_results(tmp_path, "ts", [{"bl": "X", "note": "æøå"}])
    assert json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))["results"][0]["note"] == "æøå"


def test_safe_text_neutralises_formulas():
    assert safe_text("=IMPORTXML(\"x\")") == "'=IMPORTXML(\"x\")"
    assert safe_text("+45 1234") == "'+45 1234"
    assert safe_text("Ankommet") == "Ankommet"
    assert safe_text(-3) == -3


class FakeWorksheet:
    def __init__(self, column_b):
        self.column_b = column_b
        self.updates = []

    def col_values(self, col):
        assert col == 2
        return self.column_b

    def update(self, values, range_name, value_input_option=None):
        self.updates.append((range_name, values))


def fake_sheet(ws):
    from eta_tracker.sheet import Sheet

    sheet = Sheet.__new__(Sheet)
    sheet._worksheet = lambda *a, **k: ws
    sheet.tab_shipments = "Shipments"
    return sheet


def test_write_result_finds_row_by_bl_after_sorting():
    ws = FakeWorksheet(["BL", "COP0305302", "MEDUKC776011 ", "COP0308433"])
    assert fake_sheet(ws).write_result("meduKC776011", ["2026-10-05", 4, "Forsinket", "", "", "", "=evil"])
    assert ws.updates == [("D3:J3", [["2026-10-05", 4, "Forsinket", "", "", "", "'=evil"]])]


def test_write_result_returns_false_when_bl_is_gone():
    ws = FakeWorksheet(["BL", "COP0305302"])
    assert not fake_sheet(ws).write_result("MEDUKC776011", [""] * 7)
    assert ws.updates == []

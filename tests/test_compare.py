from datetime import date, datetime

import pytest

from eta_tracker.compare import (
    FORSINKET,
    IKKE_FUNDET,
    IKKE_UNDERSTOETTET,
    TIDLIGERE,
    TJEK_MANUELT,
    UAENDRET,
    compare,
    parse_date,
)

BASE = date(2026, 10, 10)


def run(**overrides):
    args = dict(
        supported=True,
        lookup_failed=False,
        page_state="ok",
        new_eta=BASE,
        confidence="high",
        current_eta=BASE,
        threshold=1,
    )
    args.update(overrides)
    return compare(**args)


@pytest.mark.parametrize(
    "new_eta, threshold, diff, status",
    [
        (date(2026, 10, 10), 1, 0, UAENDRET),
        (date(2026, 10, 11), 1, 1, FORSINKET),
        (date(2026, 10, 20), 1, 10, FORSINKET),
        (date(2026, 10, 9), 1, -1, TIDLIGERE),
        (date(2026, 10, 12), 3, 2, UAENDRET),
        (date(2026, 10, 13), 3, 3, FORSINKET),
        (date(2026, 10, 8), 3, -2, UAENDRET),
        (date(2026, 10, 7), 3, -3, TIDLIGERE),
    ],
)
def test_thresholds(new_eta, threshold, diff, status):
    result = run(new_eta=new_eta, threshold=threshold)
    assert (result.diff_days, result.status) == (diff, status)


def test_crosses_month_and_year():
    result = run(current_eta=date(2026, 12, 30), new_eta=date(2027, 1, 2))
    assert (result.diff_days, result.status) == (3, FORSINKET)


def test_threshold_below_one_is_treated_as_one():
    assert run(threshold=0).status == UAENDRET


def test_unsupported_carrier_wins_over_everything():
    assert run(supported=False, lookup_failed=True).status == IKKE_UNDERSTOETTET


def test_failed_lookup():
    result = run(lookup_failed=True, new_eta=None)
    assert (result.diff_days, result.status) == (None, IKKE_FUNDET)


@pytest.mark.parametrize("page_state", ["not_found", "blocked", "error", None])
def test_page_state_not_ok_is_not_found(page_state):
    assert run(page_state=page_state).status == IKKE_FUNDET


def test_missing_eta_needs_manual_check():
    result = run(new_eta=None)
    assert (result.diff_days, result.status) == (None, TJEK_MANUELT)


def test_low_confidence_needs_manual_check_but_keeps_diff():
    result = run(confidence="low", new_eta=date(2026, 10, 15))
    assert (result.diff_days, result.status) == (5, TJEK_MANUELT)


def test_medium_confidence_is_trusted():
    assert run(confidence="medium", new_eta=date(2026, 10, 15)).status == FORSINKET


def test_missing_current_eta_needs_manual_check_without_diff():
    result = run(current_eta=None)
    assert (result.diff_days, result.status) == (None, TJEK_MANUELT)


@pytest.mark.parametrize(
    "value, expected",
    [
        ("2026-10-01", date(2026, 10, 1)),
        ("01-10-2026", date(2026, 10, 1)),
        ("01.10.2026", date(2026, 10, 1)),
        ("01/10/2026", date(2026, 10, 1)),
        (" 2026-10-01 ", date(2026, 10, 1)),
        ("2026-10-01T08:00:00", date(2026, 10, 1)),
        (46296, date(2026, 10, 1)),
        (46296.5, date(2026, 10, 1)),
        (date(2026, 10, 1), date(2026, 10, 1)),
        (datetime(2026, 10, 1, 8, 0), date(2026, 10, 1)),
        ("", None),
        (None, None),
        ("snart", None),
        ("2026-02-30", None),
        (0, None),
        (True, None),
    ],
)
def test_parse_date(value, expected):
    assert parse_date(value) == expected

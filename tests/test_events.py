from datetime import date

import pandas as pd

from house_protocol.forecast import events

EMPTY = pd.DataFrame()

SPY = events.EVENTS["spy_drawdown"]
VIX = events.EVENTS["vix_stress"]


def spy_prices(closes):
    days = pd.bdate_range("2026-01-05", periods=len(closes))

    return pd.DataFrame({"date": days, "symbol": "SPY", "adj_close": closes})


def vix_macro(values):
    days = pd.bdate_range("2026-01-05", periods=len(values))

    return pd.DataFrame({"date": days, "series_id": "VIXCLS", "value": values})


def test_drawdown_event_happens():
    prices = spy_prices([100, 100, 100, 90, 95])

    assert events.spy_drawdown_outcome(prices, EMPTY, date(2026, 1, 6), date(2026, 1, 9)) == 1


def test_drawdown_event_does_not_happen():
    prices = spy_prices([100, 100, 101, 100, 102])

    assert events.spy_drawdown_outcome(prices, EMPTY, date(2026, 1, 6), date(2026, 1, 9)) == 0


def test_drawdown_on_the_issue_day_does_not_count():
    prices = spy_prices([100, 90, 100, 100])

    assert events.spy_drawdown_outcome(prices, EMPTY, date(2026, 1, 6), date(2026, 1, 8)) == 0


def test_outcome_is_pending_until_the_data_reaches_the_resolve_date():
    prices = spy_prices([100, 100, 100, 90, 95])

    assert events.spy_drawdown_outcome(prices, EMPTY, date(2026, 1, 6), date(2026, 1, 20)) is None


def test_vix_event_happens_including_exactly_at_the_level():
    macro = vix_macro([15, 25.0, 20, 18])

    assert events.vix_stress_outcome(EMPTY, macro, date(2026, 1, 5), date(2026, 1, 8)) == 1


def test_vix_event_does_not_happen():
    macro = vix_macro([15, 16, 24.9, 18])

    assert events.vix_stress_outcome(EMPTY, macro, date(2026, 1, 5), date(2026, 1, 8)) == 0


def test_vix_outcome_is_pending_without_data():
    assert (
        events.vix_stress_outcome(EMPTY, vix_macro([]), date(2026, 1, 5), date(2026, 1, 8)) is None
    )


def test_registry_has_both_tracks_with_their_horizons():
    assert events.EVENTS["spy_drawdown"].horizon_days == 21
    assert events.EVENTS["vix_stress"].horizon_days == 10

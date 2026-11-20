from datetime import date

import pandas as pd
import pytest

from house_protocol.forecast import baselines
from house_protocol.forecast.events import Event, drawdown_series


def labels(rows):
    # rows: (issued_on, resolves_on, outcome, state)
    return pd.DataFrame(
        [
            {
                "issued_on": pd.Timestamp(i),
                "resolves_on": pd.Timestamp(r),
                "outcome": o,
                "state": s,
            }
            for i, r, o, s in rows
        ],
        columns=baselines.LABEL_COLUMNS,
    )


def test_climatology_ignores_forecasts_not_yet_resolved():
    table = labels(
        [
            ("2026-01-01", "2026-01-10", 1, 0),
            ("2026-01-02", "2026-01-11", 0, 0),
            ("2026-01-03", "2026-02-01", 1, 0),  # resolves after as_of, must be ignored
        ]
    )

    assert baselines.climatology(table, date(2026, 1, 15)) == (1 + 0.5) / (2 + 1)


def test_climatology_with_no_history_is_a_coin_flip():
    assert baselines.climatology(labels([]), date(2026, 1, 15)) == 0.5


def many(state, outcome, count):
    return [("2026-01-01", "2026-01-10", outcome, state)] * count


def test_conditional_follows_its_own_bucket_but_is_shrunk():
    table = labels(many(1, 1, 40) + many(0, 0, 40))
    as_of = date(2026, 2, 1)
    clim = baselines.climatology(table, as_of)

    high = baselines.conditional(table, as_of, 1)
    low = baselines.conditional(table, as_of, 0)

    assert low < clim < high
    assert high < 1.0
    assert low > 0.0


def test_conditional_with_an_unseen_bucket_equals_climatology():
    table = labels(many(0, 1, 10))
    as_of = date(2026, 2, 1)

    assert baselines.conditional(table, as_of, 3) == pytest.approx(
        baselines.climatology(table, as_of)
    )


def test_history_labels_walk_forward():
    days = pd.bdate_range("2026-01-05", periods=6)
    prices = pd.DataFrame(
        {"date": days, "symbol": "SPY", "adj_close": [100, 100, 90, 100, 100, 100]}
    )
    event = Event(
        track="test",
        horizon_days=2,
        question="",
        series=lambda p, m: drawdown_series(p),
        level=0.05,
        edges=(0.02,),
    )

    table = baselines.history_labels(event, prices, pd.DataFrame())

    assert list(table["outcome"]) == [1, 1, 0, 0]
    assert list(table["state"]) == [0, 0, 1, 0]
    assert len(table) == 4  # the last two dates have not resolved yet


def test_current_state_buckets_and_handles_missing_days():
    days = pd.bdate_range("2026-01-05", periods=2)
    series = pd.Series([0.0, 0.10], index=days)
    event = Event("t", 1, "", lambda p, m: series, 0.05, (0.02,))

    assert baselines.current_state(event, series, date(2026, 1, 6)) == 1
    assert baselines.current_state(event, series, date(2026, 1, 10)) is None

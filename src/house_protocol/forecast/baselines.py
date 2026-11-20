# Baseline probabilities, computed only from what was already known on the issue date

from bisect import bisect_right
from datetime import date

import pandas as pd

from house_protocol.alerts.rules import price_series
from house_protocol.forecast.events import Event, reached
from house_protocol.market_calendar import add_trading_days

LABEL_COLUMNS = ["issued_on", "resolves_on", "outcome", "state"]
PRIOR_STRENGTH = 20


def history_labels(event: Event, prices: pd.DataFrame, macro: pd.DataFrame) -> pd.DataFrame:

    series = event.series(prices, macro)
    rows = []

    for issued in price_series(prices, "SPY").index:
        issued_on = issued.date()
        resolves_on = add_trading_days(issued_on, event.horizon_days)
        outcome = reached(series, event.level, issued_on, resolves_on)

        if outcome is None or issued not in series.index:
            continue

        rows.append(
            {
                "issued_on": issued,
                "resolves_on": pd.Timestamp(resolves_on),
                "outcome": outcome,
                "state": bisect_right(event.edges, series.loc[issued]),
            }
        )

    return pd.DataFrame(rows, columns=LABEL_COLUMNS)


def _known(labels: pd.DataFrame, as_of: date) -> pd.DataFrame:
    return labels.loc[labels["resolves_on"] <= pd.Timestamp(as_of)]


def climatology(labels: pd.DataFrame, as_of: date) -> float:
    known = _known(labels, as_of)

    return float((known["outcome"].sum() + 0.5) / (len(known) + 1))


def conditional(labels: pd.DataFrame, as_of: date, state: int) -> float:
    known = _known(labels, as_of)
    same = known.loc[known["state"] == state]
    prior = climatology(labels, as_of)

    return float((same["outcome"].sum() + PRIOR_STRENGTH * prior) / (len(same) + PRIOR_STRENGTH))


def current_state(event: Event, series: pd.Series, as_of: date) -> int | None:
    when = pd.Timestamp(as_of)

    if when not in series.index:
        return None

    return bisect_right(event.edges, series.loc[when])

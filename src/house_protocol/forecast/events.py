# what each forecast asks and how its decided

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

import pandas as pd

from house_protocol.alerts.rules import (
    DRAWDOWN_LEVELS,
    DRAWDOWN_WINDOW,
    VIX_LEVELS,
    macro_series,
    price_series,
)

DRAWDOWN_EDGES = (0.02, 0.04, 0.07)
VIX_EDGES = (15, 20, 25)


def drawdown_series(prices: pd.DataFrame) -> pd.Series:
    # SPY distance below its 52 week high
    spy = price_series(prices, "SPY")

    return 1 - spy / spy.rolling(DRAWDOWN_WINDOW, min_periods=1).max()


def vix_series(macro: pd.DataFrame) -> pd.Series:
    return macro_series(macro, "VIXCLS")


def reached(series: pd.Series, level: float, issued_on: date, resolves_on: date) -> int | None:
    # 1 if the series hit the level on any day after issued_on up to resolves_on, else 0

    start, end = pd.Timestamp(issued_on), pd.Timestamp(resolves_on)

    if series.empty or series.index[-1] < end:
        return None

    window = series[(series.index > start) & (series.index <= end)]

    return int((window >= level).any())


def spy_drawdown_outcome(
    prices: pd.DataFrame, macro: pd.DataFrame, issued_on: date, resolves_on: date
) -> int | None:
    return reached(drawdown_series(prices), DRAWDOWN_LEVELS[0], issued_on, resolves_on)


def vix_stress_outcome(
    prices: pd.DataFrame, macro: pd.DataFrame, issued_on: date, resolves_on: date
) -> int | None:
    return reached(vix_series(macro), VIX_LEVELS[0], issued_on, resolves_on)


@dataclass(frozen=True)
class Event:
    track: str
    horizon_days: int
    question: str
    series: Callable[[pd.DataFrame, pd.DataFrame], pd.Series]
    level: float
    edges: tuple[float, ...]

    def outcome(
        self, prices: pd.DataFrame, macro: pd.DataFrame, issued_on: date, resolves_on: date
    ) -> int | None:
        return reached(self.series(prices, macro), self.level, issued_on, resolves_on)


EVENTS = {
    "spy_drawdown": Event(
        track="spy_drawdown",
        horizon_days=21,
        question="Will SPY close 7% or more below its 52 week high in next 21 days?",
        series=lambda prices, macro: drawdown_series(prices),
        level=DRAWDOWN_LEVELS[1],
        edges=DRAWDOWN_EDGES,
    ),
    "vix_stress": Event(
        track="vix_stress",
        horizon_days=10,
        question="Will the VIX close at or above 25 on any day in the next 10 trading days?",
        series=lambda prices, macro: vix_series(macro),
        level=VIX_LEVELS[1],
        edges=VIX_EDGES,
    ),
}

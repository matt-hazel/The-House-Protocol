# functions


from dataclasses import dataclass

import pandas as pd

WATCH = "watch"
ALERT = "alert"


# watch,alert levels, Heuristics starting points

VIX_LEVELS = (25.0, 30.0)
CREDIT_Z_LEVELS = (1.5, 2.5)
MARKET_Z_LEVELS = (2.0, 3.0)
TICKER_Z_LEVELS = (3.0, 4.0)
DRAWDOWN_LEVELS = (0.07, 0.12)

CREDIT_WINDOW = 252
RETURN_WINDOW = 60
DRAWDOWN_WINDOW = 252

TENSION_Z_LEVELS = (2.0, 3.0)
TENSION_WINDOW = 26  # same weekday, so ~6 months
TENSION_LABELS = {
    "russia_ukraine": "Russia/Ukraine",
    "china_taiwan": "China/Taiwan",
    "middle_east": "Middle East",
}


@dataclass(frozen=True)
class Signal:
    rule_id: str
    tier: str
    message: str
    value: float
    as_of: pd.Timestamp


@dataclass(frozen=True)
class Tension:
    region: str
    label: str
    share: float
    typical: float
    z: float
    as_of: pd.Timestamp

    @property
    def status(self) -> str:
        tier = _tier(self.z, TENSION_Z_LEVELS)

        if tier is None and self.z <= -TENSION_Z_LEVELS[0]:
            return "quieter than usual"

        return {ALERT: "high", WATCH: "elevated"}.get(tier, "normal")


def zscore_latest(series: pd.Series, window: int) -> float | None:
    # Z score of the last value against the window values previous
    # latest value is left out of its own baseline so it cannot dilute itself

    series = series.dropna()

    if len(series) < window + 1:
        return None

    baseline = series.iloc[-window - 1 : -1]
    std = baseline.std()
    if pd.isna(std) or std == 0:
        return None

    return float((series.iloc[-1] - baseline.mean()) / std)


def _tier(value: float, levels: tuple[float, float]) -> str | None:
    watch, alert = levels
    if value >= alert:
        return ALERT

    if value >= watch:
        return WATCH

    return None


def macro_series(macro: pd.DataFrame, series_id: str) -> pd.Series:
    rows = macro.loc[macro["series_id"] == series_id]

    return rows.set_index("date")["value"].sort_index().dropna()


def price_series(price: pd.DataFrame, symbol: str) -> pd.Series:
    rows = price.loc[price["symbol"] == symbol]

    return rows.set_index("date")["adj_close"].sort_index().dropna()


def returns(prices: pd.Series) -> pd.Series:
    return prices / prices.shift(1) - 1


def check_vix(macro: pd.DataFrame) -> list[Signal]:
    series = macro_series(macro, "VIXCLS")
    if series.empty:
        return []

    latest = float(series.iloc[-1])
    tier = _tier(latest, VIX_LEVELS)
    if tier is None:
        return []

    return [Signal("vix_level", tier, f"VIX is {latest:.1f}", latest, series.index[-1])]


def check_yield_curve(macro: pd.DataFrame) -> list[Signal]:
    series = macro_series(macro, "T10Y2Y")

    if series.empty or series.iloc[-1] >= 0:
        return []

    latest = float(series.iloc[-1])

    message = f"Yield curve is inverted: 10y-2y spread is {latest:+.2f}"

    return [Signal("yield_curve", WATCH, message, latest, series.index[-1])]


def check_credit(macro: pd.DataFrame) -> list[Signal]:
    series = macro_series(macro, "BAA10Y")

    z = zscore_latest(series, CREDIT_WINDOW)

    if z is None:
        return []

    tier = _tier(z, CREDIT_Z_LEVELS)

    if tier is None:
        return []

    message = f"Credit spread (Baa-10y) is {series.iloc[-1]:.2f}, z={z:+.1f} vs the past year"

    return [Signal("credit_spread", tier, message, z, series.index[-1])]


def check_market_move(prices: pd.DataFrame) -> list[Signal]:
    rets = returns(price_series(prices, "SPY"))

    z = zscore_latest(rets, RETURN_WINDOW)

    if z is None:
        return []

    tier = _tier(abs(z), MARKET_Z_LEVELS)

    if tier is None:
        return []

    message = f"SPY moved {rets.iloc[-1]:+.1%} today (z={z:+.1f})"

    return [Signal("market_move", tier, message, z, rets.index[-1])]


def check_drawdown(prices: pd.DataFrame) -> list[Signal]:
    series = price_series(prices, "SPY")

    if series.empty:
        return []

    window = series.iloc[-DRAWDOWN_WINDOW:]
    drawdown = 1 - float(window.iloc[-1] / window.max())
    tier = _tier(drawdown, DRAWDOWN_LEVELS)

    if tier is None:
        return []

    message = f"SPY is {drawdown:.1%} below its 52 week high"

    return [Signal("spy_drawdown", tier, message, -drawdown, series.index[-1])]


def check_ticker_shocks(prices: pd.DataFrame) -> list[Signal]:
    signals = []

    for symbol in sorted(prices["symbol"].unique()):
        rets = returns(price_series(prices, symbol))
        z = zscore_latest(rets, RETURN_WINDOW)

        if z is None:
            continue

        tier = _tier(abs(z), TICKER_Z_LEVELS)

        if tier is None:
            continue

        message = f"{symbol} moved {rets.iloc[-1]:+.1%} today (z={z:+.1f})"

        signals.append(Signal(f"ticker_shock:{symbol}", tier, message, z, rets.index[-1]))

    return signals


def evaluate(
    prices: pd.DataFrame, macro: pd.DataFrame, gdelt: pd.DataFrame | None = None
) -> list[Signal]:
    # run every rule, alerts then watches

    signals = [
        *check_vix(macro),
        *check_yield_curve(macro),
        *check_credit(macro),
        *check_market_move(prices),
        *check_drawdown(prices),
        *check_ticker_shocks(prices),
    ]

    if gdelt is not None and not gdelt.empty:
        signals.extend(check_tension(gdelt))

    return sorted(signals, key=lambda s: s.tier != ALERT)


def tension_readings(gdelt: pd.DataFrame) -> list[Tension]:
    # current material conflict share per region

    if gdelt.empty:
        return []

    readings = []

    for region, label in TENSION_LABELS.items():
        rows = gdelt.loc[(gdelt["region"] == region) & (gdelt["events"] > 0)]

        if rows.empty:
            continue

        rows = rows.set_index("day").sort_index()
        share = rows["material_conflict"] / rows["events"]
        same_weekday = share[share.index.day_of_week == share.index[-1].day_of_week]

        z = zscore_latest(same_weekday, TENSION_WINDOW)

        if z is None:
            continue

        typical = float(same_weekday.iloc[-TENSION_WINDOW - 1 : -1].mean())
        readings.append(Tension(region, label, float(share.iloc[-1]), typical, z, share.index[-1]))

    return readings


def check_tension(gdelt: pd.DataFrame) -> list[Signal]:
    signals = []

    for r in tension_readings(gdelt):
        tier = _tier(r.z, TENSION_Z_LEVELS)

        if tier is None:
            continue

        message = (
            f"{r.label}: {r.share:.1%} of events were material conflict, "
            f"z={r.z:+.1f} vs a typical {r.as_of:%A}"
        )

        signals.append(Signal(f"tension:{r.region}", tier, message, r.z, r.as_of))

    return signals

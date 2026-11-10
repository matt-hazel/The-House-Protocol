import pandas as pd
import pytest

from house_protocol.alerts.rules import (
    ALERT,
    WATCH,
    check_credit,
    check_drawdown,
    check_market_move,
    check_ticker_shocks,
    check_vix,
    check_yield_curve,
    evaluate,
    zscore_latest,
    check_tension,
)

END = "2024-06-28"


def macro_frame(series_id: str, values: list[float]) -> pd.DataFrame:
    dates = pd.bdate_range(end=END, periods=len(values))
    return pd.DataFrame({"date": dates, "series_id": series_id, "value": values})


def price_frame(symbol: str, values: list[float]) -> pd.DataFrame:
    dates = pd.bdate_range(end=END, periods=len(values))
    return pd.DataFrame({"date": dates, "symbol": symbol, "adj_close": values})


def prices_from_returns(symbol: str, returns: list[float]) -> pd.DataFrame:
    values, level = [100.0], 100.0
    for r in returns:
        level *= 1 + r
        values.append(level)
    return price_frame(symbol, values)


def wiggle(n: int) -> list[float]:
    """Small alternating daily returns: a calm baseline with some variance."""
    return [0.001 if i % 2 == 0 else -0.001 for i in range(n)]


def test_zscore_excludes_latest_from_baseline():
    series = pd.Series([0.0, 2.0] * 30 + [4.0])

    z = zscore_latest(series, window=60)

    assert 2.9 < z < 3.05


def test_zscore_none_when_history_too_short():
    assert zscore_latest(pd.Series([1.0, 2.0, 3.0]), window=60) is None


def test_zscore_none_when_baseline_is_flat():
    assert zscore_latest(pd.Series([1.0] * 70), window=60) is None


@pytest.mark.parametrize(("latest", "tier"), [(20.0, None), (26.0, WATCH), (31.0, ALERT)])
def test_vix_levels(latest, tier):
    signals = check_vix(macro_frame("VIXCLS", [18.0] * 10 + [latest]))

    assert [s.tier for s in signals] == ([tier] if tier else [])


def test_yield_curve_inverted_is_watch():
    signals = check_yield_curve(macro_frame("T10Y2Y", [0.5] * 5 + [-0.2]))

    assert [(s.rule_id, s.tier) for s in signals] == [("yield_curve", WATCH)]


def test_yield_curve_positive_is_quiet():
    assert check_yield_curve(macro_frame("T10Y2Y", [0.5] * 6)) == []


def test_credit_spike_is_alert():
    values = [2.0, 2.2] * 130 + [3.0]

    signals = check_credit(macro_frame("BAA10Y", values))

    assert [s.tier for s in signals] == [ALERT]


def test_credit_normal_is_quiet():
    values = [2.0, 2.2] * 130 + [2.1]

    assert check_credit(macro_frame("BAA10Y", values)) == []


def test_market_move_crash_is_alert():
    prices = prices_from_returns("SPY", wiggle(70) + [-0.04])

    signals = check_market_move(prices)

    assert [s.tier for s in signals] == [ALERT]
    assert signals[0].value < 0


def test_market_move_calm_is_quiet():
    assert check_market_move(prices_from_returns("SPY", wiggle(71))) == []


@pytest.mark.parametrize(("last", "tier"), [(100.0, None), (92.0, WATCH), (85.0, ALERT)])
def test_drawdown_levels(last, tier):
    signals = check_drawdown(price_frame("SPY", [100.0] * 260 + [last]))

    assert [s.tier for s in signals] == ([tier] if tier else [])


def test_ticker_shock_only_flags_the_mover():
    calm = prices_from_returns("AAA", wiggle(71))
    shock = prices_from_returns("BBB", wiggle(70) + [0.08])
    prices = pd.concat([calm, shock], ignore_index=True)

    signals = check_ticker_shocks(prices)

    assert [s.rule_id for s in signals] == ["ticker_shock:BBB"]


def test_evaluate_is_quiet_on_calm_data():
    prices = prices_from_returns("SPY", wiggle(300))
    macro = pd.concat(
        [
            macro_frame("VIXCLS", [15.0] * 300),
            macro_frame("T10Y2Y", [0.5] * 300),
            macro_frame("BAA10Y", [2.0] * 300),
        ],
        ignore_index=True,
    )

    assert evaluate(prices, macro) == []


def test_evaluate_puts_alerts_before_watches():
    prices = prices_from_returns("SPY", wiggle(70) + [-0.04])
    macro = macro_frame("T10Y2Y", [0.5] * 5 + [-0.2])

    tiers = [s.tier for s in evaluate(prices, macro)]

    assert tiers[0] == ALERT
    assert WATCH in tiers


def gdelt_frame(shares, region="russia_ukraine"):
    days = pd.date_range(end="2026-11-08", periods=len(shares))
    return pd.DataFrame(
        {
            "day": days,
            "region": region,
            "events": 1000,
            "material_conflict": [round(s * 1000) for s in shares],
        }
    )


def calm_shares(n=200):
    return [0.10 + 0.005 * (i % 4) for i in range(n)]


def test_tension_spike_is_alert():
    gdelt = gdelt_frame(calm_shares()[:-1] + [0.30])

    [signal] = check_tension(gdelt)

    assert signal.tier == "alert"
    assert signal.rule_id == "tension:russia_ukraine"
    assert "Russia/Ukraine" in signal.message


def test_tension_normal_day_is_quiet():
    assert check_tension(gdelt_frame(calm_shares())) == []


def test_tension_needs_enough_history():
    assert check_tension(gdelt_frame(calm_shares(100)[:-1] + [0.30])) == []


def test_tension_ignores_the_global_row():
    assert check_tension(gdelt_frame(calm_shares()[:-1] + [0.30], region="global")) == []

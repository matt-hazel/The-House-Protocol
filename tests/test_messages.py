import pandas as pd

from house_protocol.alerts.messages import format_digest, format_signals
from house_protocol.alerts.rules import ALERT, WATCH, Signal

END = "2024-06-28"
DAY = pd.Timestamp(END)


def sig(rule_id, tier, message):
    return Signal(rule_id, tier, message, 1.0, DAY)


def price_frame(symbol, values):
    dates = pd.bdate_range(end=END, periods=len(values))
    return pd.DataFrame({"date": dates, "symbol": symbol, "adj_close": values})


def macro_frame(series_id, values):
    dates = pd.bdate_range(end=END, periods=len(values))
    return pd.DataFrame({"date": dates, "series_id": series_id, "value": values})


def sample_data():
    moves = {
        "SPY": 1.01,
        "AAA": 1.05,
        "BBB": 1.04,
        "CCC": 1.03,
        "DDD": 0.95,
        "EEE": 0.96,
        "FFF": 0.97,
    }
    prices = pd.concat(
        [price_frame(symbol, [100.0, 100.0 * m]) for symbol, m in moves.items()],
        ignore_index=True,
    )
    macro = pd.concat(
        [
            macro_frame("VIXCLS", [15.0, 16.5]),
            macro_frame("T10Y2Y", [0.40, 0.35]),
            macro_frame("BAA10Y", [2.00, 2.10]),
        ],
        ignore_index=True,
    )
    return prices, macro


def test_format_signals_puts_alerts_first():
    text = format_signals([sig("a", WATCH, "watch msg"), sig("b", ALERT, "alert msg")])

    assert text.index("ALERT") < text.index("WATCH")
    assert "- alert msg" in text
    assert "- watch msg" in text


def test_format_signals_empty_is_empty_string():
    assert format_signals([]) == ""


def test_digest_contains_market_and_macro_lines():
    prices, macro = sample_data()

    text = format_digest(prices, macro, [])

    assert "Fri Jun 28" in text
    assert "SPY +1.00%" in text
    assert "VIX: 16.50 (+1.50)" in text
    assert "10y-2y: 0.35 (-0.05)" in text
    assert "No watch or alert conditions." in text


def test_digest_lists_biggest_movers():
    prices, macro = sample_data()

    text = format_digest(prices, macro, [])

    assert "Biggest gains: AAA +5.0%, BBB +4.0%, CCC +3.0%" in text
    assert "Biggest drops: DDD -5.0%, EEE -4.0%, FFF -3.0%" in text


def test_digest_includes_active_signals():
    prices, macro = sample_data()

    text = format_digest(prices, macro, [sig("vix_level", ALERT, "VIX is 31.0")])

    assert "**ALERT**" in text
    assert "- VIX is 31.0" in text
    assert "No watch or alert conditions." not in text

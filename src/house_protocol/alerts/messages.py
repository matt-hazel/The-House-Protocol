# turn signals and market data into dms

import pandas as pd

from house_protocol.alerts.rules import (
    ALERT,
    WATCH,
    Signal,
    macro_series,
    price_series,
    returns,
)

MACRO_LINES = [("VIXCLS", "VIX"), ("T10Y2Y", "10y-2y"), ("BAA10Y", "Baa-10y spread")]


def format_signals(signals: list[Signal]) -> str:
    # group signals under ALERT and WATCH headings

    lines: list[str] = []

    for tier in (ALERT, WATCH):
        group = [s for s in signals if s.tier == tier]
        if group:
            lines.append(f"**{tier.upper()}**")
            lines.extend(f"- {s.message}" for s in group)
            lines.append("")

    return "\n".join(lines).strip()


def _day_moves(prices: pd.DataFrame, as_of: pd.Timestamp) -> list[tuple[str, float]]:
    # (symbol, return) for each ticker that has a bar on as_of
    moves = []

    for symbol in sorted(prices["symbol"].unique()):
        r = returns(price_series(prices, symbol)).dropna()
        if not r.empty and r.index[-1] == as_of:
            moves.append((symbol, float(r.iloc[-1])))

    return sorted(moves, key=lambda m: m[1])


def format_digest(prices: pd.DataFrame, macro: pd.DataFrame, signals: list[Signal]) -> str:
    # daily summary

    spy = price_series(prices, "SPY")
    as_of = spy.index[-1]
    spy_move = returns(spy).iloc[-1]

    lines = [f"**Daily digest, {as_of:%a %b %d}**", ""]
    lines.append(f"SPY {spy_move:+.2%}")

    for series_id, label in MACRO_LINES:
        series = macro_series(macro, series_id)

        if len(series) >= 2:
            lines.append(
                f"{label}: {series.iloc[-1]:.2f} ({series.iloc[-1] - series.iloc[-2]:+.2f})"
            )

    moves = _day_moves(prices, as_of)

    if len(moves) >= 6:
        up = ", ".join(f"{s} {r:+.1%}" for s, r in reversed(moves[-3:]))
        down = ", ".join(f"{s} {r:+.1%}" for s, r in moves[:3])
        lines += ["", f"Biggest gains: {up}", f"Biggest drops: {down}"]

    lines.append("")
    lines.append(format_signals(signals) if signals else "No watch or alert conditions.")

    return "\n".join(lines).strip()

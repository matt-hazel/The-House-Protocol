import pandas as pd

from house_protocol.forecast import ledger
from house_protocol.forecast.report import format_scorecard


def open_row(model, probability):
    return {
        "track": "spy_drawdown",
        "model": model,
        "issued_on": pd.Timestamp("2026-11-20"),
        "horizon_days": 21,
        "resolves_on": pd.Timestamp("2026-12-21"),
        "probability": probability,
        "kind": "live",
        "outcome": pd.NA,
        "resolved_on": pd.NaT,
    }


def test_scorecard_shows_open_forecast_and_empty_scores():
    frame = pd.DataFrame(
        [open_row("climatology", 0.03), open_row("conditional", 0.062)],
        columns=ledger.LEDGER_COLUMNS,
    )
    frame["outcome"] = frame["outcome"].astype("Int64")

    text = format_scorecard(frame)

    assert "7% or more below its 52 week high" in text
    assert "6.2% now, 3.0% base rate" in text
    assert "Live: nothing resolved yet" in text
    assert "Backtest: nothing resolved yet" in text


def test_scorecard_copes_with_an_empty_ledger():
    assert isinstance(format_scorecard(ledger.empty_ledger()), str)

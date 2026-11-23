import pandas as pd
import pytest

from house_protocol.forecast import ledger, scoring


def row(model, issued, probability, outcome, kind="backtest", track="spy_drawdown"):
    return {
        "track": track,
        "model": model,
        "issued_on": pd.Timestamp(issued),
        "horizon_days": 10,
        "resolves_on": pd.Timestamp(issued),
        "probability": probability,
        "kind": kind,
        "outcome": outcome,
        "resolved_on": pd.NaT,
    }


def table(rows):
    frame = pd.DataFrame(rows, columns=ledger.LEDGER_COLUMNS)
    frame["outcome"] = frame["outcome"].astype("Int64")

    return frame


BASE = [
    row("climatology", "2026-01-05", 0.5, 1),
    row("climatology", "2026-01-06", 0.5, 0),
    row("good", "2026-01-05", 0.9, 1),
    row("good", "2026-01-06", 0.1, 0),
]


def test_scorecard_brier_skill_and_effective_n():
    card = scoring.scorecard(table(BASE), "backtest")

    good = card.loc[("spy_drawdown", "good")]
    clim = card.loc[("spy_drawdown", "climatology")]

    assert good["brier"] == pytest.approx(0.01)
    assert clim["brier"] == pytest.approx(0.25)
    assert good["skill"] == pytest.approx(1 - 0.01 / 0.25)
    assert clim["skill"] == pytest.approx(0.0)
    assert good["n"] == 2
    assert good["eff_n"] == pytest.approx(0.2)  # 2 forecasts, 10 day horizon


def test_scorecard_ignores_unresolved_and_other_kinds():
    extra = [
        row("good", "2026-01-07", 0.5, pd.NA),
        row("good", "2026-01-05", 0.9, 1, kind="live"),
    ]

    card = scoring.scorecard(table(BASE + extra), "backtest")

    assert card.loc[("spy_drawdown", "good"), "n"] == 2


def test_calibration_bins_compare_forecast_to_frequency():
    rows = [row("m", f"2026-01-0{day}", 0.03, int(day == 4)) for day in (1, 2, 3, 4)]
    rows.append(row("m", "2026-01-05", 0.6, 1))

    result = scoring.calibration(table(rows), "backtest", "spy_drawdown", "m")

    low, high = result.iloc[0], result.iloc[-1]

    assert low["n"] == 4
    assert low["mean_p"] == pytest.approx(0.03)
    assert low["hit_rate"] == pytest.approx(0.25)
    assert high["n"] == 1
    assert high["hit_rate"] == pytest.approx(1.0)

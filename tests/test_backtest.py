import pandas as pd
import pytest

from house_protocol.forecast import backtest, baselines, ledger
from house_protocol.forecast.events import Event


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


EVENT = Event("test", 2, "", lambda p, m: pd.Series(dtype=float), 0.05, (0.02,))
TABLE = labels(
    [
        ("2026-01-05", "2026-01-07", 0, 0),
        ("2026-01-06", "2026-01-08", 0, 0),
        ("2026-01-09", "2026-01-13", 1, 0),
    ]
)


def test_backtest_rows_use_only_what_was_known_then():
    rows = backtest.backtest_rows(EVENT, TABLE, min_history=0)
    clim = [row for row in rows if row["model"] == "climatology"]

    assert [row["probability"] for row in clim] == [
        pytest.approx(0.5),
        pytest.approx(0.5),
        pytest.approx(0.5 / 3),  # two zeros known, its own outcome of 1 is not
    ]
    assert clim[2]["outcome"] == 1
    assert clim[2]["resolved_on"] == pd.Timestamp("2026-01-13")
    assert all(row["kind"] == "backtest" for row in rows)


def test_backtest_rows_skip_the_warm_up():
    rows = backtest.backtest_rows(EVENT, TABLE, min_history=2)

    assert {row["issued_on"] for row in rows} == {pd.Timestamp("2026-01-09")}


def test_backtest_rows_match_the_ledger_schema():
    rows = backtest.backtest_rows(EVENT, TABLE, min_history=0)

    assert set(rows[0]) == set(ledger.LEDGER_COLUMNS)


def test_run_backtest_is_idempotent_and_marks_rows(tmp_path):
    days = pd.bdate_range("2026-01-05", periods=80)
    pd.DataFrame({"date": days, "symbol": "SPY", "adj_close": 100.0}).to_parquet(
        tmp_path / "prices.parquet", index=False
    )
    pd.DataFrame({"date": days, "series_id": "VIXCLS", "value": 15.0}).to_parquet(
        tmp_path / "macro.parquet", index=False
    )

    backtest.run_backtest(tmp_path, min_history=5)
    first = ledger.load_ledger(tmp_path / "forecasts.parquet")
    backtest.run_backtest(tmp_path, min_history=5)
    second = ledger.load_ledger(tmp_path / "forecasts.parquet")

    assert len(first) > 0
    assert len(second) == len(first)
    assert (first["kind"] == "backtest").all()
    assert first["outcome"].notna().all()

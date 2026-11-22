from datetime import date

import pandas as pd

from house_protocol.forecast import ledger
from house_protocol.forecast.runner import run_forecasts


def write_inputs(data_dir):
    days = pd.bdate_range("2026-01-05", periods=40)
    prices = pd.DataFrame({"date": days, "symbol": "SPY", "adj_close": 100.0})
    macro = pd.DataFrame({"date": days, "series_id": "VIXCLS", "value": 15.0})

    prices.to_parquet(data_dir / "prices.parquet", index=False)
    macro.to_parquet(data_dir / "macro.parquet", index=False)


def test_run_forecasts_issues_once_per_track_and_model(tmp_path):
    write_inputs(tmp_path)

    run_forecasts(tmp_path, date(2026, 3, 2))
    table = ledger.load_ledger(tmp_path / "forecasts.parquet")

    assert len(table) == 4  # two tracks, two models
    assert set(table["track"]) == {"spy_drawdown", "vix_stress"}
    assert (table["issued_on"] == pd.Timestamp("2026-02-27")).all()


def test_run_forecasts_twice_changes_nothing(tmp_path):
    write_inputs(tmp_path)

    run_forecasts(tmp_path, date(2026, 3, 2))
    first = ledger.load_ledger(tmp_path / "forecasts.parquet")
    run_forecasts(tmp_path, date(2026, 3, 2))
    second = ledger.load_ledger(tmp_path / "forecasts.parquet")

    assert len(second) == 4
    assert first["probability"].tolist() == second["probability"].tolist()


def test_run_forecasts_with_no_data_writes_nothing(tmp_path):
    run_forecasts(tmp_path, date(2026, 3, 2))

    assert not (tmp_path / "forecasts.parquet").exists()

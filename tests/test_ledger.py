from datetime import date

import pandas as pd

from house_protocol.forecast import baselines, ledger
from house_protocol.forecast.events import Event

DAYS = pd.bdate_range("2026-01-05", periods=5)
SERIES = pd.Series([0.0, 0.0, 0.10, 0.0, 0.0], index=DAYS)
EVENT = Event("test", 2, "", lambda p, m: SERIES, 0.05, (0.02,))
EMPTY = pd.DataFrame()
NO_LABELS = pd.DataFrame(columns=baselines.LABEL_COLUMNS)


def rows_for(as_of):
    return ledger.forecast_rows(EVENT, NO_LABELS, EMPTY, EMPTY, as_of)


def test_forecast_rows_make_one_open_row_per_model():
    rows = rows_for(date(2026, 1, 5))

    assert {row["model"] for row in rows} == {"climatology", "conditional"}
    assert all(row["probability"] == 0.5 for row in rows)
    assert all(row["resolves_on"] == pd.Timestamp("2026-01-07") for row in rows)
    assert all(row["kind"] == "live" for row in rows)
    assert all(pd.isna(row["outcome"]) for row in rows)


def test_forecast_rows_skip_a_day_with_no_value():
    assert rows_for(date(2026, 1, 10)) == []  # a Saturday


def test_append_new_never_duplicates_or_overwrites():
    rows = rows_for(date(2026, 1, 5))
    first = ledger.append_new(ledger.empty_ledger(), rows)

    changed = [{**row, "probability": 0.99} for row in rows]
    second = ledger.append_new(first, changed)

    assert len(second) == 2
    assert (second["probability"] == 0.5).all()


def test_resolve_fills_closed_windows_and_leaves_open_ones():
    rows = rows_for(date(2026, 1, 5)) + rows_for(date(2026, 1, 8))
    table = ledger.append_new(ledger.empty_ledger(), rows)

    result = ledger.resolve(table, {"test": EVENT}, EMPTY, EMPTY, date(2026, 1, 9))

    done = result[result["issued_on"] == pd.Timestamp("2026-01-05")]
    pending = result[result["issued_on"] == pd.Timestamp("2026-01-08")]

    assert list(done["outcome"]) == [1, 1]
    assert (done["resolved_on"] == pd.Timestamp("2026-01-09")).all()
    assert pending["outcome"].isna().all()


def test_save_and_load_round_trip(tmp_path):
    path = tmp_path / "forecasts.parquet"
    table = ledger.append_new(ledger.empty_ledger(), rows_for(date(2026, 1, 5)))

    ledger.save_ledger(table, path)
    loaded = ledger.load_ledger(path)

    assert list(loaded.columns) == ledger.LEDGER_COLUMNS
    assert len(loaded) == 2
    assert loaded["outcome"].isna().all()


def test_load_ledger_with_no_file_is_empty(tmp_path):
    loaded = ledger.load_ledger(tmp_path / "missing.parquet")

    assert loaded.empty
    assert list(loaded.columns) == ledger.LEDGER_COLUMNS

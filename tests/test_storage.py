import pandas as pd

from house_protocol.storage.parquet import read_table, upsert

KEYS = ["date", "symbol"]


def frame(*rows) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["date", "symbol", "close"])
    df["date"] = pd.to_datetime(df["date"])
    return df


def test_read_table_missing_file_returns_empty(tmp_path):
    assert read_table(tmp_path / "nope.parquet").empty


def test_upsert_creates_file(tmp_path):
    path = tmp_path / "prices.parquet"
    df = frame(("2024-01-02", "SPY", 1.0), ("2024-01-03", "SPY", 2.0))

    upsert(df, path, KEYS)

    pd.testing.assert_frame_equal(read_table(path), df)


def test_upsert_is_idempotent(tmp_path):
    path = tmp_path / "prices.parquet"
    df = frame(("2024-01-02", "SPY", 1.0), ("2024-01-03", "SPY", 2.0))

    upsert(df, path, KEYS)
    upsert(df, path, KEYS)

    result = read_table(path)
    assert len(result) == 2
    pd.testing.assert_frame_equal(result, df)


def test_upsert_overwrites_existing_key(tmp_path):
    path = tmp_path / "prices.parquet"
    upsert(frame(("2024-01-02", "SPY", 1.0)), path, KEYS)

    upsert(frame(("2024-01-02", "SPY", 9.0)), path, KEYS)

    result = read_table(path)
    assert len(result) == 1
    assert result.loc[0, "close"] == 9.0


def test_upsert_appends_new_rows(tmp_path):
    path = tmp_path / "prices.parquet"
    upsert(frame(("2024-01-02", "SPY", 1.0)), path, KEYS)

    upsert(frame(("2024-01-03", "SPY", 2.0), ("2024-01-02", "QQQ", 3.0)), path, KEYS)

    assert len(read_table(path)) == 3


def test_upsert_sorts_by_keys(tmp_path):
    path = tmp_path / "prices.parquet"
    df = frame(("2024-01-03", "SPY", 2.0), ("2024-01-02", "SPY", 1.0))

    upsert(df, path, KEYS)

    result = read_table(path)
    assert list(result["date"]) == sorted(result["date"])


def test_upsert_leaves_no_temp_file(tmp_path):
    path = tmp_path / "prices.parquet"

    upsert(frame(("2024-01-02", "SPY", 1.0)), path, KEYS)

    assert not path.with_suffix(".tmp").exists()

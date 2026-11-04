from datetime import date, datetime, timedelta

import pandas as pd
import pytest

from house_protocol import scheduler
from house_protocol.config import Settings
from house_protocol.scheduler import NY, is_trading_day, latest_date, update_prices
from house_protocol.storage.parquet import upsert


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        (date(2026, 11, 3), True),  # ordinary Tuesday
        (date(2026, 11, 7), False),  # Saturday
        (date(2026, 11, 8), False),  # Sunday
        (date(2026, 11, 26), False),  # Thanksgiving
        (date(2026, 12, 25), False),  # Christmas
        (date(2026, 1, 1), False),  # New Year's Day
        (date(2026, 4, 3), False),  # Good Friday: not federal, market closed
        (date(2026, 10, 12), True),  # Columbus Day: federal, market open
        (date(2026, 11, 11), True),  # Veterans Day: federal, market open
    ],
)
def test_is_trading_day(day, expected):
    assert is_trading_day(day) is expected


def price_frame(symbol: str, day: date) -> pd.DataFrame:
    return pd.DataFrame({"date": [pd.Timestamp(day)], "symbol": [symbol], "close": [1.0]})


def test_latest_date_missing_file(tmp_path):
    assert latest_date(tmp_path / "prices.parquet", "SPY") is None


def test_latest_date_returns_max_for_symbol(tmp_path):
    path = tmp_path / "prices.parquet"
    upsert(price_frame("SPY", date(2024, 1, 2)), path, ["date", "symbol"])
    upsert(price_frame("SPY", date(2024, 1, 5)), path, ["date", "symbol"])
    upsert(price_frame("QQQ", date(2024, 2, 1)), path, ["date", "symbol"])

    assert latest_date(path, "SPY") == date(2024, 1, 5)


def test_latest_date_unknown_symbol(tmp_path):
    path = tmp_path / "prices.parquet"
    upsert(price_frame("SPY", date(2024, 1, 2)), path, ["date", "symbol"])

    assert latest_date(path, "ZZZ") is None


def make_settings(data_dir, key="k") -> Settings:
    return Settings(
        data_dir=data_dir,
        log_level="INFO",
        fred_api_key=None,
        discord_bot_token=None,
        discord_user_id=None,
        tiingo_api_key=key,
    )


@pytest.fixture
def ingest_calls(monkeypatch):
    calls = []
    monkeypatch.setattr(scheduler, "ingest_prices", lambda *a, **kw: calls.append((a, kw)))
    return calls


def test_update_skips_non_trading_day(monkeypatch, tmp_path, ingest_calls):
    monkeypatch.setattr(scheduler, "load_settings", lambda: make_settings(tmp_path))
    monkeypatch.setattr(scheduler, "is_trading_day", lambda d: False)

    update_prices()

    assert ingest_calls == []


def test_update_skips_without_api_key(monkeypatch, tmp_path, ingest_calls):
    monkeypatch.setattr(scheduler, "load_settings", lambda: make_settings(tmp_path, key=None))
    monkeypatch.setattr(scheduler, "is_trading_day", lambda d: True)

    update_prices()

    assert ingest_calls == []


def test_update_skips_when_already_current(monkeypatch, tmp_path, ingest_calls):
    today = datetime.now(NY).date()
    upsert(price_frame("SPY", today), tmp_path / "prices.parquet", ["date", "symbol"])
    monkeypatch.setattr(scheduler, "load_settings", lambda: make_settings(tmp_path))
    monkeypatch.setattr(scheduler, "is_trading_day", lambda d: True)

    update_prices()

    assert ingest_calls == []


def test_update_fetches_when_stale(monkeypatch, tmp_path, ingest_calls):
    monkeypatch.setattr(scheduler, "load_settings", lambda: make_settings(tmp_path))
    monkeypatch.setattr(scheduler, "is_trading_day", lambda d: True)

    update_prices()

    assert len(ingest_calls) == 1
    args, kwargs = ingest_calls[0]
    expected_start = (datetime.now(NY).date() - timedelta(days=scheduler.LOOKBACK_DAYS)).isoformat()
    assert kwargs["start"] == expected_start
    assert args[1] == "k"
    assert args[2] == tmp_path / "prices.parquet"

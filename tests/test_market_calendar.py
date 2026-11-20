from datetime import date

from house_protocol.market_calendar import add_trading_days, is_trading_day


def test_weekends_and_holidays_are_not_trading_days():
    assert not is_trading_day(date(2026, 11, 21))  # Saturday
    assert not is_trading_day(date(2026, 11, 26))  # Thanksgiving
    assert is_trading_day(date(2026, 11, 20))  # Friday


def test_add_trading_days_skips_weekends():
    assert add_trading_days(date(2026, 11, 20), 1) == date(2026, 11, 23)  # Fri to Mon


def test_add_trading_days_skips_holidays():
    assert add_trading_days(date(2026, 11, 25), 1) == date(2026, 11, 27)  # over Thanksgiving
    assert add_trading_days(date(2026, 12, 24), 1) == date(
        2026, 12, 28
    )  # over Christmas and weekend


def test_zero_days_returns_the_start_date():
    assert add_trading_days(date(2026, 11, 20), 0) == date(2026, 11, 20)

# NYSE trading cal helpers


from datetime import date, timedelta

import holidays

NYSE_HOLIDAYS = holidays.NYSE()


def is_trading_day(d: date) -> bool:
    # weekdays that arent nyse holidays
    return d.weekday() < 5 and d not in NYSE_HOLIDAYS


def add_trading_days(start: date, n: int) -> date:
    # date n trading days after start

    day = start

    while n > 0:
        day += timedelta(days=1)

        if is_trading_day(day):
            n -= 1

    return day

import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import holidays
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from house_protocol.config import load_settings
from house_protocol.ingest.tiingo import ingest_prices
from house_protocol.ingest.universe import EQUITY_SYMBOLS
from house_protocol.storage.parquet import read_table

logger = logging.getLogger(__name__)
NY = ZoneInfo("America/New_York")
NYSE_HOLIDAYS = holidays.NYSE()
LOOKBACK_DAYS = 10


def heartbeat() -> None:
    logger.info("alive mi amigo")


def is_trading_day(d: date) -> bool:
    """True only weekdays that are not NYSE holidays"""
    return d.weekday() < 5 and d not in NYSE_HOLIDAYS


def latest_date(path, symbol: str) -> date | None:
    df = read_table(path)

    if df.empty:
        return None

    dates = df.loc[df["symbol"] == symbol, "date"]

    return dates.max().date() if not dates.empty else None


def update_prices() -> None:
    settings = load_settings()
    today = datetime.now(NY).date()

    if not is_trading_day(today):
        logger.info("%s is not a trading day, skipping", today)
        return

    if not settings.tiingo_api_key:
        logger.warning("TIINGO_API_KEY not set, skipping price update")
        return

    path = settings.data_dir / "prices.parquet"
    if (latest_date(path, "SPY") or date.min) >= today:
        logger.info("prices already up to date for %s", today)

        return

    start = (today - timedelta(days=LOOKBACK_DAYS)).isoformat()
    ingest_prices(EQUITY_SYMBOLS, settings.tiingo_api_key, path, start=start)


def main() -> None:
    settings = load_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("starting scheduler, data_dir%s", settings.data_dir)

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        update_prices,
        CronTrigger(
            day_of_week="mon-fri",
            hour="18-23",
            minute="0,30",
            timezone=NY,
        ),
    )
    scheduler.start()


if __name__ == "__main__":
    main()

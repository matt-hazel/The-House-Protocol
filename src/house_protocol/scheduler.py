import logging
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import holidays
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from house_protocol.alerts.runner import run_alerts
from house_protocol.briefing.headlines import ingest_headlines
from house_protocol.briefing.morning import run_briefing
from house_protocol.briefing.sources import FEEDS
from house_protocol.config import load_settings
from house_protocol.ingest.fred import ingest_macro
from house_protocol.ingest.gdelt import ingest_days, missing_days
from house_protocol.ingest.tiingo import ingest_prices
from house_protocol.ingest.universe import EQUITY_SYMBOLS, FRED_SERIES
from house_protocol.storage.parquet import read_table
from house_protocol.storage.dashboard import sync_dashboard
from house_protocol.storage.sql import get_engine

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


def update_macro() -> None:
    settings = load_settings()
    if not settings.fred_api_key:
        logger.warning("FRED_API_KEY not set, skipping update")
        return

    start = (datetime.now(NY).date() - timedelta(days=30)).isoformat()
    ingest_macro(
        FRED_SERIES, settings.fred_api_key, settings.data_dir / "macro.parquet", start=start
    )


def check_alerts() -> None:
    run_alerts(load_settings(), datetime.now(NY).date())


def update_headlines() -> None:
    settings = load_settings()
    ingest_headlines(FEEDS, settings.data_dir / "headlines.parquet")


def send_briefing() -> None:
    run_briefing(load_settings(), datetime.now(NY))


def update_gdelt() -> None:
    settings = load_settings()
    path = settings.data_dir / "gdelt_daily.parquet"
    end = (datetime.now(UTC) - timedelta(days=1)).date()

    days = missing_days(path, end - timedelta(days=7), end)

    if days:
        ingest_days(days, path)
        
        
def sync_db() -> None:
    settings = load_settings()
    engine = get_engine()
    
    try:
        sync_dashboard(settings.data_dir, engine)
        
    finally:
        engine.dispose()


# THIS IS MAIN


def main() -> None:
    settings = load_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("starting scheduler, data_dir=%s", settings.data_dir)

    scheduler = BlockingScheduler(timezone="UTC")

    evening = {"day_of_week": "mon-fri", "hour": "18-23", "timezone": NY}

    scheduler.add_job(update_prices, CronTrigger(minute="0,30", **evening))
    scheduler.add_job(check_alerts, CronTrigger(minute="10,40", **evening))
    scheduler.add_job(
        update_macro, CronTrigger(day_of_week="mon-fri", hour="9,15", minute=0, timezone=NY)
    )
    scheduler.add_job(update_headlines, CronTrigger(hour="*/2", minute=5, timezone=NY))
    scheduler.add_job(
        send_briefing, CronTrigger(hour=7, minute=30, timezone=NY), misfire_grace_time=3600
    )
    scheduler.add_job(update_gdelt, CronTrigger(hour="3-6", minute=15, timezone=NY))
    scheduler.add_job(sync_db, CronTrigger(minute="20,50", timezone=NY))

    scheduler.start()


if __name__ == "__main__":
    main()

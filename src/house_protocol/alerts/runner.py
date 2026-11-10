# Eval rules against data and DM whats new

import logging
from datetime import UTC, date, datetime
from pathlib import Path

from house_protocol.alerts.discord import send_dm
from house_protocol.alerts.messages import format_digest, format_signals
from house_protocol.alerts.rules import evaluate
from house_protocol.alerts.state import load_log, record, select_new
from house_protocol.config import Settings
from house_protocol.storage.parquet import read_table


logger = logging.getLogger(__name__)


def _last_digest(path: Path) -> str | None:
    return path.read_text().strip() if path.exists() else None


def run_alerts(settings: Settings, today: date, now: datetime | None = None) -> None:
    # sends new alerts then daily digest once spy bar lands

    if not (settings.discord_bot_token and settings.discord_user_id):
        logger.warning("Discord credentials not set, skipping alerts")

        return

    prices = read_table(settings.data_dir / "prices.parquet")
    macro = read_table(settings.data_dir / "macro.parquet")
    gdelt = read_table(settings.data_dir / "gdelt_daily.parquet")

    if prices.empty or macro.empty:
        logger.warning("no data yet, skipping alerts")

        return

    spy_latest = prices.loc[prices["symbol"] == "SPY", "date"].max().date()

    if spy_latest < today:
        logger.info("today's bar not in yet, skipping alerts", spy_latest)

        return

    now = now or datetime.now(UTC).replace(tzinfo=None)
    token, user_id = settings.discord_bot_token, settings.discord_user_id
    signals = evaluate(prices, macro, gdelt)

    log_path = settings.data_dir / "alert_log.parquet"
    new = select_new(signals, load_log(log_path), now)

    if new:
        try:
            send_dm(user_id, token, format_signals(new))
        except Exception:
            logger.exception("alert DM failed, will retry")
        else:
            record(new, log_path, now)
            logger.info("sent %d alert(s)", len(new))

    marker = settings.data_dir / "last_digest.txt"

    if _last_digest(marker) != spy_latest.isoformat():
        try:
            send_dm(user_id, token, format_digest(prices, macro, signals))
        except Exception:
            logger.exception("digest dm failed, will retry")
        else:
            marker.write_text(spy_latest.isoformat())
            logger.info("sent digest for %s", spy_latest)

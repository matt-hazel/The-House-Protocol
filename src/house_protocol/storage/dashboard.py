# copy ever parquet table the dash needs

import logging
from pathlib import Path

from sqlalchemy import Engine

from house_protocol.storage.parquet import read_table
from house_protocol.storage.sql import sync_table

logger = logging.getLogger(__name__)


# par file to postgress

TABLES = {
    "prices.parquet": "prices",
    "macro.parquet": "macro",
    "headlines.parquet": "headlines",
    "gdelt_daily.parquet": "gdelt_daily",
    "alert_log.parquet": "alert_log",
}


def sync_dashboard(data_dir: Path, engine: Engine) -> int:
    # returns how many tables were copied

    synced = 0

    for filename, table in TABLES.items():
        df = read_table(data_dir / filename)

        if df.empty:
            logger.info("%s: empty or missing, skip", filename)

            continue

        try:
            sync_table(df, table, engine)

        except Exception:
            logger.exception("%s: sync failed, keeping the old table", table)

            continue

        synced += 1

    return synced

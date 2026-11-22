# daily forecast job, settle what isnt resolved and issue newest forecast(s)

import logging
from datetime import date
from pathlib import Path

from house_protocol.forecast import baselines, ledger
from house_protocol.forecast.events import EVENTS
from house_protocol.storage.parquet import read_table

logger = logging.getLogger(__name__)


def run_forecasts(data_dir: Path, today: date) -> None:
    prices = read_table(data_dir / "prices.parquet")
    macro = read_table(data_dir / "macro.parquet")

    if prices.empty or macro.empty:
        logger.warning("prices or macro missing, skip")

        return

    path = data_dir / "forecasts.parquet"
    table = ledger.load_ledger(path)
    table = ledger.resolve(table, EVENTS, prices, macro, today)
    before = len(table)

    for event in EVENTS.values():
        series = event.series(prices, macro)

        if series.empty:
            continue

        as_of = series.index.max().date()
        labels = baselines.history_labels(event, prices, macro)
        rows = ledger.forecast_rows(event, labels, prices, macro, as_of)
        table = ledger.append_new(table, rows)

    ledger.save_ledger(table, path)
    logger.info("forecasts: %d new, %d total", len(table) - before, len(table))

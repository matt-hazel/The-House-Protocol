# walk forward backtest

import logging
from pathlib import Path

import pandas as pd

from house_protocol.config import load_settings
from house_protocol.forecast import baselines, ledger
from house_protocol.forecast.events import EVENTS, Event
from house_protocol.storage.parquet import read_table

logger = logging.getLogger(__name__)


MIN_HISTORY = 500


def backtest_rows(event: Event, labels: pd.DataFrame, min_history: int = MIN_HISTORY) -> list[dict]:
    # one row per model per past issue date

    rows = []

    for label in labels.itertuples():
        as_of = label.issued_on.date()

        if (labels["resolves_on"] <= label.issued_on).sum() < min_history:
            continue

        probabilities = {
            "climatology": baselines.climatology(labels, as_of),
            "conditional": baselines.conditional(labels, as_of, label.state),
        }

        for model, probability in probabilities.items():
            rows.append(
                {
                    "track": event.track,
                    "model": model,
                    "issued_on": label.issued_on,
                    "horizon_days": event.horizon_days,
                    "resolves_on": label.resolves_on,
                    "probability": probability,
                    "kind": "backtest",
                    "outcome": label.outcome,
                    "resolved_on": label.resolves_on,
                }
            )

    return rows


def run_backtest(data_dir: Path, min_history: int = MIN_HISTORY) -> None:
    prices = read_table(data_dir / "prices.parquet")
    macro = read_table(data_dir / "macro.parquet")

    if prices.empty or macro.empty:
        logger.warning("prices or macro missing, skip")

        return

    path = data_dir / "forecasts.parquet"
    table = ledger.load_ledger(path)
    before = len(table)

    for event in EVENTS.values():
        labels = baselines.history_labels(event, prices, macro)
        table = ledger.append_new(table, backtest_rows(event, labels, min_history))

    ledger.save_ledger(table, path)
    logger.info("backtest: %d new rows, %d total", len(table) - before, len(table))


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    run_backtest(load_settings().data_dir)

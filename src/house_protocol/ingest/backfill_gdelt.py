# one off gdelt history: py -m house_protocol.ingest.backfill_gdelt --years 3


import argparse
import logging
from datetime import UTC, datetime, timedelta

from house_protocol.config import load_settings
from house_protocol.ingest.gdelt import ingest_days, missing_days

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=float, default=3.0, help="how far back to fetch")
    args = parser.parse_args()

    settings = load_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    path = settings.data_dir / "gdelt_daily.parquet"
    end = (datetime.now(UTC) - timedelta(days=1)).date()
    start = end - timedelta(days=round(args.years * 365))

    days = missing_days(path, start, end)
    logger.info("%d days to fetch (%s to %s)", len(days), start, end)
    stored = ingest_days(days, path)
    logger.info("stored %d days", stored)

if __name__ == "__main__":
    main()

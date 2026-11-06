import logging
import argparse

from house_protocol.config import load_settings
from house_protocol.ingest.tiingo import ingest_prices
from house_protocol.ingest.universe import EQUITY_SYMBOLS, FRED_SERIES
from house_protocol.ingest.fred import ingest_macro


def main() -> None:
    parser = argparse.ArgumentParser(description = "Backfill full history")
    parser.add_argument("dataset", choices=["prices","macro"])
    args = parser.parse_args()
    

    settings = load_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.dataset == "prices":
        if not settings.tiingo_api_key:
            raise SystemExit("TIINGO_API_KEY is not set")
        ingest_prices(
            EQUITY_SYMBOLS,
            settings.tiingo_api_key,
            settings.data_dir / "prices.parquet",
        )
    else:
        if not settings.fred_api_key:
            raise SystemExit("FRED_API_KEY is not set")
        ingest_macro(
            FRED_SERIES,
            settings.fred_api_key,
            settings.data_dir / "macro.parquet",
        )



if __name__ == "__main__":
    main()

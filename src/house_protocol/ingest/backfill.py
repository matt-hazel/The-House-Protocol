import logging

from house_protocol.config import load_settings
from house_protocol.ingest.tiingo import ingest_prices
from house_protocol.ingest.universe import EQUITY_SYMBOLS


def main() -> None:
    settings = load_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if not settings.tiingo_api_key:
        raise SystemExit("TIINGO_API_KEY is not set")

    ingest_prices(
        EQUITY_SYMBOLS,
        settings.tiingo_api_key,
        settings.data_dir / "prices.parquet",
    )


if __name__ == "__main__":
    main()

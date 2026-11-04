"""Tiingo end of day price ingestion"""

import logging
import time
from pathlib import Path

import pandas as pd
import requests

from house_protocol.storage.parquet import upsert

logger = logging.getLogger(__name__)


BASE_URL = "https://api.tiingo.com/tiingo/daily"
KEYS = ["date", "symbol"]
COLUMNS = [
    "date",
    "symbol",
    "open",
    "high",
    "low",
    "close",
    "adj_close",
    "volume",
    "div_cash",
    "split_factor",
]

RENAME = {"adjClose": "adj_close", "divCash": "div_cash", "splitFactor": "split_factor"}


def parse_prices(rows: list[dict], symbol: str) -> pd.DataFrame:
    """Tur nTiingo's JSON rows into a frame with stand. schema"""

    if not rows:
        return pd.DataFrame(columns=COLUMNS)

    df = pd.DataFrame(rows).rename(columns=RENAME)
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    df["symbol"] = symbol

    return df[COLUMNS]


def fetch_prices(
    symbol: str,
    api_key: str,
    start: str,
    session: requests.Session,
    retries: int = 3,
) -> list[dict]:
    """Fetches historical price data for a given symbol from the Tiingo API."""

    url = f"{BASE_URL}/{symbol.lower()}/prices"

    for attempt in range(retries):
        resp = session.get(
            url,
            params={"startDate": start, "format": "json"},
            headers={"Authorization": f"Token {api_key}"},
            timeout=30,
        )

        if resp.status_code == 429:
            wait = 5 * 2**attempt
            logger.warning("%s: rate limited, waiting %ss", symbol, wait)
            time.sleep(wait)
            continue
        resp.raise_for_status()

        return resp.json()

    raise RuntimeError(f"Failed to fetch prices for {symbol} after {retries} attempts")


def ingest_prices(
    symbols: list[str], api_key: str, path: Path, start: str = "2000-01-01", pause: float = 1.0
) -> None:
    """Fetch prices for all symbols and upsert into Parquet file at path"""

    session = requests.Session()
    frames = []

    for symbol in symbols:
        try:
            rows = fetch_prices(symbol, api_key, start, session)
        except (requests.RequestException, RuntimeError):
            logger.exception("%s: failed to fetch prices: ", symbol)
            continue

        frames.append(parse_prices(rows, symbol))
        logger.info("%s: fetched %d rows", symbol, len(rows))
        time.sleep(pause)

    if frames:
        upsert(pd.concat(frames, ignore_index=True), path, KEYS)

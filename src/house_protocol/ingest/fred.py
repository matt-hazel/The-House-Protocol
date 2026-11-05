# fred macro and stress series ingest


import logging
from pathlib import Path

import pandas as pd
import requests

from house_protocol.storage.parquet import upsert

logger = logging.getLogger(__name__)


BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
KEYS = ["date", "series_id"]
COLUMNS = ["date", "series_id", "value"]


def parse_observations(rows: list[dict], series_id: str) -> pd.DataFrame:
    # turns fred observ to the standard schema and drops NA

    if not rows:
        return pd.DataFrame(columns=COLUMNS)

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["series_id"] = series_id

    return df.loc[df["value"].notna(), COLUMNS].reset_index(drop=True)


def fetch_observations(
    series_id: str,
    api_key: str,
    start: str,
    session: requests.Session,
) -> list[dict]:
    # Fetches observ for one series from fred

    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start,
    }

    try:
        resp = session.get(BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        # requests embeds the full url

        status = getattr(exc.response, "status_code", None)

        raise RuntimeError(f"{series_id}: Fred request failed, status={status}") from None

    return resp.json()["observations"]


def ingest_macro(
    series_ids: list[str],
    api_key: str,
    path: Path,
    start: str = "2000-01-01",
) -> None:

    # Fetch all series and upsert them into parquet

    session = requests.Session()
    frames = []

    for series_id in series_ids:
        try:
            rows = fetch_observations(series_id, api_key, start, session)
        except RuntimeError as exc:
            logger.error("%s", exc)
            continue

        frames.append(parse_observations(rows, series_id))
        logger.info("%s: fetched %d rows", series_id, len(rows))

    if frames:
        upsert(pd.concat(frames, ignore_index=True), path, KEYS)

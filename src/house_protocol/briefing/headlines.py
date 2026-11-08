# Fetches headlines from sources


import html
import logging
import re
from calendar import timegm
from datetime import UTC, datetime
from pathlib import Path

import feedparser
import pandas as pd
import requests

from house_protocol.briefing.sources import Feed
from house_protocol.storage.parquet import upsert

logger = logging.getLogger(__name__)


USER_AGENT = "HouseProtocol/0.1 (personal project)"
KEYS = ["source", "url"]
COLUMNS = ["source", "url", "title", "summary", "published"]
SUMMARY_LIMIT = 300
TAG = re.compile(r"<[^>]+>")


def clean_text(text: str, limit: int | None = None) -> str:
    # strip html

    text = " ".join(html.unescape(TAG.sub("", text)).split())

    return text[:limit] if limit else text


def parse_feed(content: bytes, source: str) -> list[dict]:
    # turns raw feed into rows

    rows = []

    for entry in feedparser.parse(content).entries:
        title, link = entry.get("title"), entry.get("link")

        if not title or not link:
            continue

        parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        published = datetime.fromtimestamp(timegm(parsed), UTC) if parsed else None

        rows.append(
            {
                "source": source,
                "url": link,
                "title": clean_text(title),
                "summary": clean_text(entry.get("summary", ""), SUMMARY_LIMIT),
                "published": published,
            }
        )

    return rows


def fetch_feed(feed: Feed, session: requests.Session) -> list[dict]:
    try:
        resp = session.get(feed.url, headers={"User-Agent": USER_AGENT}, timeout=30)
        resp.raise_for_status()

    except requests.RequestException as exc:
        status = getattr(exc.response, "status_code", None)

        raise RuntimeError(f"{feed.name}: feed request failed, status={status}") from None

    return parse_feed(resp.content, feed.name)


def ingest_headlines(
    feeds: list[Feed], path: Path, session: requests.Session | None = None
) -> None:
    # Fetch every feed and upsert headlines

    session = session or requests.Session()
    rows = []

    for feed in feeds:
        try:
            fetched = fetch_feed(feed, session)

        except RuntimeError as exc:
            logger.error("%s", exc)

            continue

        rows.extend(fetched)
        logger.info("%s: fetched %d headlines", feed.name, len(fetched))

    if not rows:
        return

    df = pd.DataFrame(rows, columns=COLUMNS)
    df["published"] = pd.to_datetime(df["published"], utc=True)
    upsert(df, path, KEYS)

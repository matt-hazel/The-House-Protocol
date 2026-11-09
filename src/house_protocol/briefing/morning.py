# Assemble morning briefing

import logging
from datetime import datetime, timedelta

import pandas as pd
import requests

from house_protocol.alerts.discord import send_dm
from house_protocol.briefing.cluster import find_clusters, summarize
from house_protocol.briefing.sources import FEEDS, Feed
from house_protocol.briefing.weather import get_weather_text
from house_protocol.config import Settings
from house_protocol.storage.parquet import read_table

logger = logging.getLogger(__name__)


PER_SOURCE = 2
MAX_AGE = timedelta(hours=24)
STORY_WINDOW = timedelta(hours=36)
TOP_STORIES = 5
MIN_TITLE_WORDS = 3


def format_headlines(headlines: pd.DataFrame, now: datetime, feeds: list[Feed] = FEEDS) -> str:
    # latest few headlines per source

    if headlines.empty:
        return ""

    recent = headlines.loc[headlines["published"] >= pd.Timestamp(now) - MAX_AGE]

    lines = ["**Headlines**"]

    for feed in feeds:
        rows = recent.loc[recent["source"] == feed.name].sort_values("published", ascending=False)

        if rows.empty:
            continue

        lines.append(f"__{feed.name}__ ({feed.lean})")
        lines.extend(f"- [{r.title}](<{r.url}>)" for r in rows.head(PER_SOURCE).itertuples())

    return "\n".join(lines) if len(lines) > 1 else ""


def format_top_stories(headlines: pd.DataFrame, now: datetime, feeds: list[Feed] = FEEDS) -> str:
    # biggest stories by indep. outlets
    if headlines.empty:
        return ""

    recent = headlines.loc[headlines["published"] >= pd.Timestamp(now) - STORY_WINDOW]
    recent = recent.loc[recent["title"].str.split().str.len() >= MIN_TITLE_WORDS]

    if recent.empty:
        return ""

    leans = {f.name: f.lean for f in feeds}
    stories = [s for s in summarize(find_clusters(recent), leans) if s["independent"] >= 2]

    lines = ["**Top stories**"]
    for rank, story in enumerate(stories[:TOP_STORIES], start=1):
        lines.append(f"**{rank}.** {story['title']}")
        lines.append(f"Covered by {', '.join(story['sources'])}")

        missing = [f.name for f in feeds if f.name not in story["sources"]]

        if story["independent"] * 2 > len(feeds) and missing:
            lines.append(f"Not covered: {', '.join(missing)}")

    return "\n".join(lines) if len(lines) > 1 else ""


def build_briefing(
    settings: Settings,
    headlines: pd.DataFrame,
    now: datetime,
    session: requests.Session | None = None,
    feeds: list[Feed] = FEEDS,
) -> str:

    # join sections

    try:
        weather = get_weather_text(settings, session)

    except (RuntimeError, requests.RequestException):
        logger.exception("weather section failed, skipping")
        weather = None

    sections = [
        s
        for s in (
            weather,
            format_top_stories(headlines, now, feeds),
            format_headlines(headlines, now, feeds),
        )
        if s
    ]

    if not sections:
        return ""

    return "\n\n".join([f"**Morning briefing, {now:%a %b %d}**", *sections])


def run_briefing(
    settings: Settings, now: datetime, session: requests.Session | None = None
) -> None:
    # send todays briefing

    if not (settings.discord_bot_token and settings.discord_user_id):
        logger.warning("Discord credentials not set")
        return

    marker = settings.data_dir / "last_briefing.txt"

    today = now.date().isoformat()

    if marker.exists() and marker.read_text().strip() == today:
        logger.info("briefing already sent for %s", today)

        return

    headlines = read_table(settings.data_dir / "headlines.parquet")
    text = build_briefing(settings, headlines, now, session)

    if not text:
        logger.warning("briefing has no content, skipping")
        return

    try:
        send_dm(settings.discord_user_id, settings.discord_bot_token, text)

    except Exception:
        logger.exception("briefing DM failed, will retry")

    else:
        marker.write_text(today)
        logger.info("sent briefing for %s", today)

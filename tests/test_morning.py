from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from house_protocol.briefing import morning
from house_protocol.briefing.sources import Feed
from house_protocol.config import Settings

NOW = datetime(2026, 11, 8, 7, 30, tzinfo=ZoneInfo("America/New_York"))
FEEDS_T = [
    Feed("A", "https://a.test/rss", "left", "us"),
    Feed("B", "https://b.test/rss", "right", "us"),
]


def hl(source, name, hours_ago):
    return {
        "source": source,
        "url": f"https://{source.lower()}.test/{name}",
        "title": name,
        "summary": "",
        "published": NOW - timedelta(hours=hours_ago),
    }


def frame(rows):
    df = pd.DataFrame(rows)
    df["published"] = pd.to_datetime(df["published"], utc=True)
    return df


def make_settings(tmp_path, token="t", user="u"):
    return Settings(tmp_path, "INFO", None, token, user, None)


def test_headlines_group_by_source_with_lean_newest_first():
    df = frame([hl("A", "old1", 3), hl("A", "new", 1), hl("A", "mid", 2), hl("B", "b1", 1)])

    text = morning.format_headlines(df, NOW, FEEDS_T)

    assert "__A__ (left)" in text
    assert "__B__ (right)" in text
    assert text.index("[new]") < text.index("[mid]")
    assert "[old1]" not in text  # only two per source
    assert text.index("__A__") < text.index("__B__")


def test_headlines_drop_items_older_than_a_day():
    df = frame([hl("A", "stale", 30), hl("A", "fresh", 2)])

    text = morning.format_headlines(df, NOW, FEEDS_T)

    assert "[fresh]" in text
    assert "[stale]" not in text


def test_headlines_empty_when_nothing_recent():
    assert morning.format_headlines(pd.DataFrame(), NOW, FEEDS_T) == ""
    assert morning.format_headlines(frame([hl("A", "stale", 48)]), NOW, FEEDS_T) == ""


def test_build_briefing_has_both_sections(tmp_path, monkeypatch):
    monkeypatch.setattr(morning, "get_weather_text", lambda settings, session=None: "WEATHER")
    df = frame([hl("A", "story", 1)])

    text = morning.build_briefing(make_settings(tmp_path), df, NOW, feeds=FEEDS_T)

    assert text.startswith("**Morning briefing, Sun Nov 08**")
    assert "WEATHER" in text
    assert "[story]" in text


def test_build_briefing_survives_weather_failure(tmp_path, monkeypatch):
    def boom(settings, session=None):
        raise RuntimeError("weather down")

    monkeypatch.setattr(morning, "get_weather_text", boom)
    df = frame([hl("A", "story", 1)])

    text = morning.build_briefing(make_settings(tmp_path), df, NOW, feeds=FEEDS_T)

    assert "[story]" in text
    assert "WEATHER" not in text


def test_build_briefing_empty_without_content(tmp_path, monkeypatch):
    monkeypatch.setattr(morning, "get_weather_text", lambda settings, session=None: None)

    assert morning.build_briefing(make_settings(tmp_path), pd.DataFrame(), NOW) == ""


def prepare(tmp_path, monkeypatch):
    monkeypatch.setattr(morning, "get_weather_text", lambda settings, session=None: "WEATHER")
    sent = []
    monkeypatch.setattr(morning, "send_dm", lambda user, token, text: sent.append(text))
    return sent


def test_run_briefing_sends_once_per_day(tmp_path, monkeypatch):
    sent = prepare(tmp_path, monkeypatch)
    settings = make_settings(tmp_path)

    morning.run_briefing(settings, NOW)
    morning.run_briefing(settings, NOW)

    assert len(sent) == 1
    assert (tmp_path / "last_briefing.txt").read_text() == "2026-11-08"


def test_run_briefing_sends_again_next_day(tmp_path, monkeypatch):
    sent = prepare(tmp_path, monkeypatch)
    settings = make_settings(tmp_path)

    morning.run_briefing(settings, NOW)
    morning.run_briefing(settings, NOW + timedelta(days=1))

    assert len(sent) == 2


def test_run_briefing_skips_without_credentials(tmp_path, monkeypatch):
    sent = prepare(tmp_path, monkeypatch)

    morning.run_briefing(make_settings(tmp_path, token=None), NOW)

    assert sent == []


def test_failed_send_leaves_no_marker(tmp_path, monkeypatch):
    monkeypatch.setattr(morning, "get_weather_text", lambda settings, session=None: "WEATHER")
    attempts = []

    def boom(user, token, text):
        attempts.append(text)
        raise requests.ConnectionError("discord down")

    monkeypatch.setattr(morning, "send_dm", boom)

    morning.run_briefing(make_settings(tmp_path), NOW)

    assert len(attempts) == 1
    assert not (tmp_path / "last_briefing.txt").exists()

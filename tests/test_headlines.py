from datetime import UTC, datetime

import pytest
import requests

from house_protocol.briefing import headlines
from house_protocol.briefing.sources import FEEDS, LEANS, Feed
from house_protocol.storage.parquet import read_table

RSS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>t</title>
<item><title>First &amp; story</title><link>https://x.test/1</link>
<description>&lt;p&gt;Some &lt;b&gt;summary&lt;/b&gt;   text&lt;/p&gt;</description>
<pubDate>Sat, 07 Nov 2026 12:00:00 GMT</pubDate></item>
<item><title>No link here</title></item>
<item><title>Second</title><link>https://x.test/2</link></item>
</channel></rss>"""


class FakeResponse:
    def __init__(self, content=b"", status=200):
        self.content = content
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError("boom https://secret.test/feed", response=self)


class FakeSession:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get(self, url, headers=None, timeout=None):
        self.calls.append((url, headers))
        return self.responses[url]


GOOD = Feed("Good", "https://good.test/rss", "center", "us")
BAD = Feed("Bad", "https://bad.test/rss", "center", "us")


def test_clean_text_strips_tags_entities_and_whitespace():
    assert headlines.clean_text("<p>Hi &amp;  <b>there</b></p>") == "Hi & there"


def clean_text_case(text):
    return headlines.clean_text(text)


def test_clean_text_truncates():
    assert headlines.clean_text("abcdef", limit=3) == "abc"


def test_parse_feed_skips_entries_without_a_link():
    rows = headlines.parse_feed(RSS, "Good")

    assert [r["url"] for r in rows] == ["https://x.test/1", "https://x.test/2"]


def test_parse_feed_cleans_fields_and_parses_date():
    first, second = headlines.parse_feed(RSS, "Good")

    assert first["source"] == "Good"
    assert first["title"] == "First & story"
    assert first["summary"] == "Some summary text"
    assert first["published"] == datetime(2026, 11, 7, 12, 0, tzinfo=UTC)
    assert second["published"] is None


def test_fetch_feed_sends_user_agent():
    session = FakeSession({GOOD.url: FakeResponse(RSS)})

    rows = headlines.fetch_feed(GOOD, session)

    assert len(rows) == 2
    assert session.calls[0][1]["User-Agent"] == headlines.USER_AGENT


def test_fetch_feed_error_reports_status_and_hides_url():
    session = FakeSession({BAD.url: FakeResponse(status=503)})

    with pytest.raises(RuntimeError) as exc:
        headlines.fetch_feed(BAD, session)

    assert "status=503" in str(exc.value)
    assert "secret.test" not in str(exc.value)


def test_ingest_skips_failed_feed(tmp_path):
    session = FakeSession({GOOD.url: FakeResponse(RSS), BAD.url: FakeResponse(status=500)})
    path = tmp_path / "headlines.parquet"

    headlines.ingest_headlines([BAD, GOOD], path, session)

    assert set(read_table(path)["source"]) == {"Good"}


def test_ingest_writes_nothing_if_all_fail(tmp_path):
    session = FakeSession({BAD.url: FakeResponse(status=500)})
    path = tmp_path / "headlines.parquet"

    headlines.ingest_headlines([BAD], path, session)

    assert not path.exists()


def test_ingest_is_idempotent(tmp_path):
    session = FakeSession({GOOD.url: FakeResponse(RSS)})
    path = tmp_path / "headlines.parquet"

    headlines.ingest_headlines([GOOD], path, session)
    headlines.ingest_headlines([GOOD], path, session)

    assert len(read_table(path)) == 2


def test_feed_config_is_sane():
    names = [f.name for f in FEEDS]

    assert len(names) == len(set(names))
    assert all(f.url.startswith("https://") for f in FEEDS)
    assert all(f.lean in LEANS for f in FEEDS)

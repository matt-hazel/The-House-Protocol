# news feeds

from dataclasses import dataclass

LEANS = {"left", "center-left", "center", "center-right", "right"}


@dataclass(frozen=True)
class Feed:
    name: str
    url: str
    lean: str
    region: str
    note: str = ""


FEEDS = [
    Feed(
        "Washington Post",
        "https://feeds.washingtonpost.com/rss/world",
        "center-left",
        "us",
    ),
    Feed(
        "ABC News",
        "https://abcnews.com/abcnews/internationalheadlines",
        "center-left",
        "us",
    ),
    Feed(
        "AP (via Google News)",
        "https://news.google.com/rss/search?q=site:apnews.com+when:1d&hl=en-US&gl=US&ceid=US:en",
        "center",
        "us",
        note="AP blocks direct access, this is a work around",
    ),
    Feed(
        "NPR",
        "https://feeds.npr.org/1004/rss.xml",
        "center-left",
        "us",
    ),
    Feed(
        "Fox News",
        "https://moxie.foxnews.com/google-publisher/world.xml",
        "right",
        "us",
    ),
    Feed(
        "BBC",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "center",
        "uk",
    ),
    Feed(
        "Al Jazeera",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "center",
        "qatar",
        note="State funded",
    ),
    Feed(
        "Deutsche Welle",
        "https://rss.dw.com/xml/rss-en-world",
        "center",
        "germany",
        note="State funded",
    ),
]

import pytest

from house_protocol.alerts import discord
from house_protocol.alerts.discord import send_dm, split_message


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = str(self._payload)

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.posts = []

    def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        return self.responses.pop(0)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(discord.time, "sleep", lambda seconds: None)


def test_split_short_message_is_one_chunk():
    assert split_message("hello\nworld") == ["hello\nworld"]


def test_split_breaks_on_lines_under_limit():
    text = "\n".join(["x" * 40] * 10)

    chunks = split_message(text, limit=100)

    assert len(chunks) > 1
    assert all(len(c) <= 100 for c in chunks)
    assert "\n".join(chunks) == text


def test_split_hard_splits_a_very_long_line():
    chunks = split_message("y" * 250, limit=100)

    assert [len(c) for c in chunks] == [100, 100, 50]


def test_send_dm_opens_channel_then_posts_message():
    session = FakeSession([FakeResponse(200, {"id": "999"}), FakeResponse(200, {"id": "1"})])

    send_dm("123", "tok", "hi there", session)

    (url1, kw1), (url2, kw2) = session.posts
    assert url1.endswith("/users/@me/channels")
    assert kw1["json"] == {"recipient_id": "123"}
    assert url2.endswith("/channels/999/messages")
    assert kw2["json"] == {"content": "hi there"}
    assert kw2["headers"]["Authorization"] == "Bot tok"


def test_send_dm_sends_one_post_per_chunk(monkeypatch):
    monkeypatch.setattr(discord, "MAX_LEN", 10)
    monkeypatch.setattr(discord, "split_message", lambda text: ["a", "b", "c"])
    session = FakeSession([FakeResponse(200, {"id": "9"})] + [FakeResponse(200, {})] * 3)

    send_dm("123", "tok", "ignored", session)

    assert len(session.posts) == 4


def test_send_dm_retries_once_on_rate_limit():
    session = FakeSession(
        [
            FakeResponse(429, {"retry_after": 0.1}),
            FakeResponse(200, {"id": "9"}),
            FakeResponse(200, {}),
        ]
    )

    send_dm("123", "tok", "hi", session)

    assert len(session.posts) == 3


def test_send_dm_raises_on_api_error():
    session = FakeSession([FakeResponse(403, {"code": 50007})])

    with pytest.raises(RuntimeError, match="403"):
        send_dm("123", "tok", "hi", session)

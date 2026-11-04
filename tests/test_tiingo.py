import pytest
import requests

from house_protocol.ingest import tiingo
from house_protocol.ingest.tiingo import COLUMNS, fetch_prices, ingest_prices, parse_prices
from house_protocol.storage.parquet import read_table

SAMPLE_ROWS = [
    {
        "date": "2024-01-02T00:00:00.000Z",
        "close": 472.65,
        "high": 473.67,
        "low": 470.49,
        "open": 472.16,
        "volume": 123007793,
        "adjClose": 457.6889383476,
        "adjHigh": 458.6766517023,
        "adjLow": 455.597310067,
        "adjOpen": 457.2144485987,
        "adjVolume": 123007793,
        "divCash": 0.0,
        "splitFactor": 1.0,
    },
    {
        "date": "2024-01-03T00:00:00.000Z",
        "close": 468.79,
        "high": 471.19,
        "low": 468.17,
        "open": 470.43,
        "volume": 103585866,
        "adjClose": 453.951121,
        "adjHigh": 456.27,
        "adjLow": 453.33,
        "adjOpen": 455.5,
        "adjVolume": 103585866,
        "divCash": 0.0,
        "splitFactor": 1.0,
    },
]


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else []

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
        self.last_kwargs = {}

    def get(self, url, **kwargs):
        self.calls += 1
        self.last_kwargs = kwargs
        return self.responses.pop(0)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(tiingo.time, "sleep", lambda seconds: None)


def test_parse_prices_schema():
    df = parse_prices(SAMPLE_ROWS, "SPY")

    assert list(df.columns) == COLUMNS
    assert len(df) == 2
    assert (df["symbol"] == "SPY").all()
    assert df["date"].dt.tz is None
    assert df.loc[0, "adj_close"] == pytest.approx(457.6889383476)


def test_parse_prices_empty():
    df = parse_prices([], "SPY")

    assert df.empty
    assert list(df.columns) == COLUMNS


def test_fetch_prices_returns_rows():
    session = FakeSession([FakeResponse(200, SAMPLE_ROWS)])

    rows = fetch_prices("SPY", "abc", "2024-01-01", session)

    assert rows == SAMPLE_ROWS
    assert session.calls == 1


def test_fetch_prices_sends_key_in_header_not_params():
    session = FakeSession([FakeResponse(200, SAMPLE_ROWS)])

    fetch_prices("SPY", "abc", "2024-01-01", session)

    assert session.last_kwargs["headers"] == {"Authorization": "Token abc"}
    assert "abc" not in str(session.last_kwargs["params"])


def test_fetch_prices_retries_on_rate_limit():
    session = FakeSession([FakeResponse(429), FakeResponse(200, SAMPLE_ROWS)])

    rows = fetch_prices("SPY", "abc", "2024-01-01", session)

    assert rows == SAMPLE_ROWS
    assert session.calls == 2


def test_fetch_prices_gives_up_after_retries():
    session = FakeSession([FakeResponse(429)] * 3)

    with pytest.raises(RuntimeError):
        fetch_prices("SPY", "abc", "2024-01-01", session)

    assert session.calls == 3


def test_fetch_prices_raises_on_http_error():
    session = FakeSession([FakeResponse(404)])

    with pytest.raises(requests.HTTPError):
        fetch_prices("NOPE", "abc", "2024-01-01", session)


def test_ingest_skips_failed_symbol(monkeypatch, tmp_path):
    def fake_fetch(symbol, api_key, start, session, retries=3):
        if symbol == "BAD":
            raise RuntimeError("boom")
        return SAMPLE_ROWS

    monkeypatch.setattr(tiingo, "fetch_prices", fake_fetch)
    path = tmp_path / "prices.parquet"

    ingest_prices(["BAD", "SPY"], "abc", path, pause=0)

    assert set(read_table(path)["symbol"]) == {"SPY"}


def test_ingest_writes_nothing_if_all_fail(monkeypatch, tmp_path):
    def fake_fetch(symbol, api_key, start, session, retries=3):
        raise RuntimeError("boom")

    monkeypatch.setattr(tiingo, "fetch_prices", fake_fetch)
    path = tmp_path / "prices.parquet"

    ingest_prices(["SPY"], "abc", path, pause=0)

    assert not path.exists()


def test_ingest_is_idempotent(monkeypatch, tmp_path):
    monkeypatch.setattr(tiingo, "fetch_prices", lambda *args, **kwargs: SAMPLE_ROWS)
    path = tmp_path / "prices.parquet"

    ingest_prices(["SPY"], "abc", path, pause=0)
    ingest_prices(["SPY"], "abc", path, pause=0)

    assert len(read_table(path)) == 2

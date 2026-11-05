import pytest
import requests

from house_protocol.ingest import fred
from house_protocol.ingest.fred import (
    COLUMNS,
    fetch_observations,
    ingest_macro,
    parse_observations,
)
from house_protocol.storage.parquet import read_table

SAMPLE_ROWS = [
    {"date": "2024-01-02", "value": "13.2"},
    {"date": "2024-01-03", "value": "."},
    {"date": "2024-01-04", "value": "13.5"},
]


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {"observations": SAMPLE_ROWS}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError("boom", response=self)


class FakeSession:
    def __init__(self, response=None, error=None):
        self.response = response or FakeResponse()
        self.error = error
        self.last_params = {}

    def get(self, url, **kwargs):
        self.last_params = kwargs["params"]
        if self.error:
            raise self.error
        return self.response


def test_parse_drops_missing_values():
    df = parse_observations(SAMPLE_ROWS, "VIXCLS")

    assert list(df.columns) == COLUMNS
    assert len(df) == 2
    assert df["value"].tolist() == [13.2, 13.5]
    assert (df["series_id"] == "VIXCLS").all()


def test_parse_empty():
    df = parse_observations([], "VIXCLS")

    assert df.empty
    assert list(df.columns) == COLUMNS


def test_fetch_returns_observations_and_sends_start():
    session = FakeSession()

    rows = fetch_observations("VIXCLS", "k", "2024-01-01", session)

    assert rows == SAMPLE_ROWS
    assert session.last_params["observation_start"] == "2024-01-01"
    assert session.last_params["series_id"] == "VIXCLS"


def test_fetch_error_does_not_leak_api_key():
    secret = "SECRET123"
    error = requests.ConnectionError(f"failed for url ...&api_key={secret}")
    session = FakeSession(error=error)

    with pytest.raises(RuntimeError) as excinfo:
        fetch_observations("VIXCLS", secret, "2024-01-01", session)

    assert secret not in str(excinfo.value)
    assert excinfo.value.__suppress_context__


def test_fetch_http_error_reports_status():
    session = FakeSession(response=FakeResponse(status_code=400))

    with pytest.raises(RuntimeError, match="status=400"):
        fetch_observations("BAD", "k", "2024-01-01", session)


def test_ingest_skips_failed_series(monkeypatch, tmp_path):
    def fake_fetch(series_id, api_key, start, session):
        if series_id == "BAD":
            raise RuntimeError("boom")
        return SAMPLE_ROWS

    monkeypatch.setattr(fred, "fetch_observations", fake_fetch)
    path = tmp_path / "macro.parquet"

    ingest_macro(["BAD", "VIXCLS"], "k", path)

    assert set(read_table(path)["series_id"]) == {"VIXCLS"}


def test_ingest_is_idempotent(monkeypatch, tmp_path):
    monkeypatch.setattr(fred, "fetch_observations", lambda *a, **kw: SAMPLE_ROWS)
    path = tmp_path / "macro.parquet"

    ingest_macro(["VIXCLS"], "k", path)
    ingest_macro(["VIXCLS"], "k", path)

    assert len(read_table(path)) == 2

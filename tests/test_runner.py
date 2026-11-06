from datetime import date, datetime

import pandas as pd

from house_protocol.alerts import runner
from house_protocol.config import Settings

TODAY = date(2024, 6, 28)
NOW = datetime(2024, 6, 28, 23, 0)


def make_settings(tmp_path, token="t", user="u"):
    return Settings(tmp_path, "INFO", None, token, user, None)


def write_data(tmp_path, end="2024-06-28"):
    dates = pd.bdate_range(end=end, periods=300)
    prices = pd.DataFrame(
        {"date": dates, "symbol": "SPY", "adj_close": [100.0 + i * 0.1 for i in range(300)]}
    )
    macro = pd.DataFrame({"date": dates, "series_id": "VIXCLS", "value": 40.0})
    prices.to_parquet(tmp_path / "prices.parquet")
    macro.to_parquet(tmp_path / "macro.parquet")


def capture(monkeypatch):
    sent = []
    monkeypatch.setattr(runner, "send_dm", lambda user, token, text: sent.append(text))
    return sent


def test_skips_without_credentials(tmp_path, monkeypatch):
    sent = capture(monkeypatch)
    write_data(tmp_path)

    runner.run_alerts(make_settings(tmp_path, token=None), TODAY, NOW)

    assert sent == []


def test_skips_when_todays_bar_missing(tmp_path, monkeypatch):
    sent = capture(monkeypatch)
    write_data(tmp_path, end="2024-06-27")

    runner.run_alerts(make_settings(tmp_path), TODAY, NOW)

    assert sent == []


def test_sends_alert_and_digest_once(tmp_path, monkeypatch):
    sent = capture(monkeypatch)
    write_data(tmp_path)
    settings = make_settings(tmp_path)

    runner.run_alerts(settings, TODAY, NOW)
    first = len(sent)
    runner.run_alerts(settings, TODAY, NOW)

    assert first == 2  # VIX alert plus the digest
    assert "VIX" in sent[0]
    assert "Daily digest" in sent[1]
    assert len(sent) == first  # second run sends nothing


def test_failed_send_is_not_recorded(tmp_path, monkeypatch):
    write_data(tmp_path)

    def boom(user, token, text):
        raise RuntimeError("discord down")

    monkeypatch.setattr(runner, "send_dm", boom)
    runner.run_alerts(make_settings(tmp_path), TODAY, NOW)

    assert not (tmp_path / "alert_log.parquet").exists()
    assert not (tmp_path / "last_digest.txt").exists()

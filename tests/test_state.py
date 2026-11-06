from datetime import datetime, timedelta

import pandas as pd

from house_protocol.alerts.rules import ALERT, WATCH, Signal
from house_protocol.alerts.state import (
    COOLDOWNS,
    load_log,
    record,
    select_new,
)

NOW = datetime(2024, 6, 28, 22, 0)
DAY = pd.Timestamp("2024-06-28")


def sig(rule_id="vix_level", tier=WATCH, as_of=DAY) -> Signal:
    return Signal(rule_id, tier, "msg", 1.0, as_of)


def log_with(*signals_and_times) -> pd.DataFrame:
    """Build a history frame from (signal, sent_at) pairs."""
    rows = [
        {
            "sent_at": pd.Timestamp(sent_at),
            "rule_id": s.rule_id,
            "tier": s.tier,
            "value": s.value,
            "as_of": s.as_of,
        }
        for s, sent_at in signals_and_times
    ]
    return pd.DataFrame(rows)


def test_everything_is_sent_when_history_is_empty(tmp_path):
    log = load_log(tmp_path / "alerts.parquet")

    assert select_new([sig(), sig("yield_curve")], log, NOW) == [sig(), sig("yield_curve")]


def test_same_rule_same_data_day_is_not_repeated():
    log = log_with((sig(), NOW - timedelta(minutes=30)))

    assert select_new([sig()], log, NOW) == []


def test_new_day_inside_cooldown_is_suppressed():
    log = log_with((sig(as_of=DAY - pd.Timedelta(days=1)), NOW - timedelta(days=1)))

    assert select_new([sig()], log, NOW) == []


def test_new_day_after_cooldown_is_sent():
    sent_at = NOW - COOLDOWNS[WATCH] - timedelta(hours=1)
    log = log_with((sig(as_of=DAY - pd.Timedelta(days=4)), sent_at))

    assert select_new([sig()], log, NOW) == [sig()]


def test_escalation_ignores_cooldown():
    log = log_with((sig(tier=WATCH), NOW - timedelta(hours=1)))

    result = select_new([sig(tier=ALERT)], log, NOW)

    assert [s.tier for s in result] == [ALERT]


def test_de_escalation_inside_cooldown_is_suppressed():
    old_day = DAY - pd.Timedelta(days=1)
    log = log_with((sig(tier=ALERT, as_of=old_day), NOW - timedelta(hours=12)))

    assert select_new([sig(tier=WATCH)], log, NOW) == []


def test_rules_are_tracked_independently():
    log = log_with((sig("vix_level"), NOW - timedelta(minutes=30)))

    result = select_new([sig("vix_level"), sig("yield_curve")], log, NOW)

    assert [s.rule_id for s in result] == ["yield_curve"]


def test_record_then_load_roundtrip(tmp_path):
    path = tmp_path / "alerts.parquet"

    record([sig()], path, NOW)
    log = load_log(path)

    assert len(log) == 1
    assert log.loc[0, "rule_id"] == "vix_level"
    assert select_new([sig()], log, NOW + timedelta(minutes=30)) == []


def test_record_nothing_creates_no_file(tmp_path):
    path = tmp_path / "alerts.parquet"

    record([], path, NOW)

    assert not path.exists()

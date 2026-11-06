# alert history


from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from house_protocol.alerts.rules import ALERT, WATCH, Signal
from house_protocol.storage.parquet import read_table, upsert

COOLDOWNS = {WATCH: timedelta(days=3), ALERT: timedelta(days=1)}
TIER_RANK = {WATCH: 1, ALERT: 2}
LOG_COLUMNS = ["sent_at", "rule_id", "tier", "value", "as_of"]
LOG_KEYS = ["sent_at", "rule_id"]


def load_log(path: Path) -> pd.DataFrame:
    # read alert history

    log = read_table(path)

    return log if not log.empty else pd.DataFrame(columns=LOG_COLUMNS)


def select_new(signals: list[Signal], log: pd.DataFrame, now: datetime) -> list[Signal]:
    # keep only signals that are allowed as of rn

    selected = []

    for signal in signals:
        rows = log.loc[log["rule_id"] == signal.rule_id]

        if rows.empty:
            selected.append(signal)

            continue

        last = rows.sort_values("sent_at").iloc[-1]
        escalated = TIER_RANK[signal.tier] > TIER_RANK[last["tier"]]

        if escalated:
            selected.append(signal)

        elif last["as_of"] == signal.as_of:
            continue

        elif now - last["sent_at"] >= COOLDOWNS[signal.tier]:
            selected.append(signal)

    return selected


def record(signals: list[Signal], path: Path, now: datetime) -> None:
    # append sent signals to history

    if not signals:
        return

    rows = pd.DataFrame(
        [
            {
                "sent_at": pd.Timestamp(now),
                "rule_id": s.rule_id,
                "tier": s.tier,
                "value": s.value,
                "as_of": pd.Timestamp(s.as_of),
            }
            for s in signals
        ],
        columns=LOG_COLUMNS,
    )

    upsert(rows, path, LOG_KEYS)

# Append only forecast ledger, issue forecasts, fill in outcomes

from datetime import date
from pathlib import Path

import pandas as pd

from house_protocol.forecast import baselines
from house_protocol.forecast.events import Event
from house_protocol.market_calendar import add_trading_days


LEDGER_COLUMNS = [
    "track",
    "model",
    "issued_on",
    "horizon_days",
    "resolves_on",
    "probability",
    "kind",
    "outcome",
    "resolved_on",
]

KEY = ["track", "model", "issued_on"]

DATE_COLUMNS = ["issued_on", "resolves_on", "resolved_on"]


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

def _typed(ledger: pd.DataFrame) -> pd.DataFrame:
    # pin the dtypes so an empty ledger, fresh one and one read from disk all look the same
    ledger = ledger.copy()
    
    for column in DATE_COLUMNS:
        ledger[column] = pd.to_datetime(ledger[column])
        
    ledger["outcome"] = ledger["outcome"].astype("Int64")
    
    return ledger


def empty_ledger() -> pd.DataFrame:
    return _typed(pd.DataFrame(columns=LEDGER_COLUMNS))


def load_ledger(path: Path) -> pd.DataFrame:
    if not path.exists():
        return empty_ledger
    
    return _typed(pd.read_parquet(path))


def save_ledger(ledger: pd.DataFrame, path: Path) -> None:
    # write beside the real file then swap, a crash mid write cannot corrupt ledger
    
    temp = path.with_suffix(".tmp")
    ledger.to_parquet(temp, index=False)
    temp.replace(path)
    
    
def forecast_row(
    event: Event,
    labels: pd.DataFrame,
    prices: pd.DataFrame,
    macro: pd.DataFrame,
    as_of: date,
    kind: str = "live",
) -> list[dict]:
    # one row per baseline model for event
    
    state = baselines.current_state(event, event.series(prices, macro), as_of)
    
    if state is None:
        return []
    
    probabilities = {
        "climatology": baselines.climatology(labels, as_of),
        "conditional": baselines.conditional(labels, as_of, state),
    }
    
    resolves_on = add_trading_days(as_of, event.horizon_days)
    
    
    return [
        {
            "track": event.track,
            "model": model,
            "issued_on": pd.Timestamp(as_of),
            "horizon_days": event.horizon_days,
            "resolves_on": pd.Timestamp(resolves_on),
            "probability": probability,
            "kind": kind,
            "outcome": pd.NA,
            "resolved_on": pd.NaT,
        }
        
        for model, probability in probabilities.items()
    ]
    

def append_new(ledger: pd.DataFrame, rows: list[dict]) -> pd.DataFrame:
    # adds only rows whose is not already in ledger
    new = pd.DataFrame(rows, columns=LEDGER_COLUMNS)
    
    if new.empty:
        return ledger
    
    if ledger.empty:
        return _typed(new)
    
    seen = new.merge(ledger[KEY], on=KEY, how="left", indictator=True)
    fresh = new[seen["_merge"].eq("left_only").to_numpy()]
    
    
    return _typed(pd.concat([ledger, fresh], ignore_index=True))


def resolve(
    ledger: pd.DataFrame,
    events: dict[str, Event],
    prices: pd.DataFrame,
    macro: pd.DataFrame,
    as_of: date,
) -> pd.DataFrame:
    # fill in the outcome of every open forecast whose window has now closed
    
    ledger = ledger.copy()
    
    for index, row in ledger[ledger["outcome"].isna()].iterrows():
        outcome = events[row["track"]].outcome(
            prices, macro, row["issued_on"].date(), row["resolves_on"].date()
        )
        
        if outcome is None:
            continue
        
        ledger.loc[index, "outcome"] = outcome
        ledger.loc[index, "resolved_on"] = pd.Timestamp(as_of)
        
        
    return ledger

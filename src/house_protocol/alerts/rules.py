# functions 


from dataclasses import dataclass


import pandas as pd


WATCH = "watch"
ALERT = "alert"


# watch,alert levels, Heuristics starting points

VIX_LEVELS = (25.0, 30.0)
CREDIT_Z_LEVELS = (1.5, 2.5)
MARKET_Z_LEVELS = (2.0,3.0)
TICKER_Z_LEVELS = (3.0,4.0)
DRAWDOWN_LEVELS = (0.07,0.12)

CREDIT_WINDOW = 252
RETURN_WINDOW = 60
DRAWDOWN_WINDOW = 252



@dataclass(frozen=True)
class Signal:
    rule_id: str
    tier: str
    message: str
    value: float
    as_of: pd.Timestamp
        
def zscore_latest(series: pd.Series, window: int) -> float | None:
    # Z score of the last value against the window values previous
    # latest value is left out of its own baseline so it cannot dilute itself
    
    series = series.dropna()
    
    if len(series) < window + 1:
        return None
    
    baseline = series.iloc[-window - 1: -1]
    std = baseline.std()
    if pd.isna(std) or std == 0:
        return None
    
    
    return float((series.iloc[-1] - baseline.mean()) / std)


def _tier(value: float, levels: tuple[float, float]) -> str | None:
    watch, alert = levels
    if value >= alert:
        return ALERT
    
    if value >= watch:
        return WATCH
    
    return None


def _macro_series(macro: pd.DataFrame, series_id: str) -> pd.Series:
    rows = macro.loc[macro["series_id"] == series_id]
    
    return rows.set_index("date")["value"].sort_index().dropna()



def _price_series(price: pd.DataFrame, symbol: str) -> pd.Series:
    rows = price.loc[prices["symbol"] == symbol]
    
    return rows.set_index("date")["adj_close"].sort_index().dropna()


def _returns(prices: pd.Series) -> pd.Series:
    return prices / prices.shift(1) - 1



def check_vix(macro: pd.DataFrame) -> list[Signal]:
    series = _macro_series(macro, "VIXCLS")
    if series.empty:
        return []
    
    latest = float(series.iloc[-1])
    tier = _tier(latest, VIX_LEVELS)
    if tier is None:
        return []
    
    return [Signal("vix_level", tier, f"VIX is {latest:.1f}", latest, series.index[-1])]



def check_yield_curve(macro: pd.DataFrame) -> list[Signal]:
    series = _macro_series(macro, "T10Y2Y")
    
    if series.empty or series.iloc[-1] >= 0:
        return []
    
    latest = float(series.iloc[-1])
    
    message = f"Yield curve is inverted: 10y-2y spread is {latest:+.2f}"
    
    
    return [Signal("yield_curve", WATCH, message, latest, series.index[-1])]
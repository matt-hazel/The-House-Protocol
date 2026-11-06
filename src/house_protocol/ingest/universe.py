"""Tickers tracked via dev dataset"""

EQUITY_SYMBOLS: list[str] = [
    # broad market, rates, au
    "SPY",
    "QQQ",
    "IWM",
    "TLT",
    "GLD",
    # sectors
    "XLE",
    "XLF",
    "XLV",
    "XLI",
    "XLP",
    # agriculture
    "DBA",
    "DE",
    "ADM",
    # large caps
    "AAPL",
    "MSFT",
    "AMZN",
    "NVDA",
    "JPM",
    "XOM",
    "CAT",
    # nuclear
    "URA",
    "URNM",
    "CCJ",
    "CEG",
    "VST",
    "BWXT",
    "SMR",
]


FRED_SERIES: list[str] = [
    "VIXCLS",
    "T10Y2Y",
    "BAMLH0A0HYM2",
    "DGS10",
    "DFF",
    "BAA10Y",
]

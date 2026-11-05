from house_protocol.ingest.universe import EQUITY_SYMBOLS


def test_universe_is_27_unique_valid_tickers():
    assert len(EQUITY_SYMBOLS) == 27
    assert len(set(EQUITY_SYMBOLS)) == len(EQUITY_SYMBOLS)
    for symbol in EQUITY_SYMBOLS:
        assert symbol.isalpha()
        assert symbol.isupper()
        assert len(symbol) <= 5

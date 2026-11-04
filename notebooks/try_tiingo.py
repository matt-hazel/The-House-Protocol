import json
import os

import requests

from house_protocol.ingest.tiingo import fetch_prices, parse_prices

key = os.environ.get("TIINGO_API_KEY")

rows = fetch_prices("SPY", key, "2024-01-01", requests.Session())

print(len(rows), "rows")
print(json.dumps(rows[0], indent = 2))


df = parse_prices(rows, "SPY")
print(df.head())
print(df.dtypes)
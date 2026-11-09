# download one GDELT daily event file and work out its column layout


import io

import pandas as pd
import requests

URL = "https://data.gdeltproject.org/events/20260101.export.CSV.zip"


resp = requests.get(URL, timeout=120)
print("download size:", len(resp.content), "bytes")


df = pd.read_csv(io.BytesIO(resp.content), compression="zip", sep="\t", header=None, dtype=str)
print("rows:", len(df), "columns:", df.shape[1])

print()
print("first event, column by column:")
print(df.iloc[0].to_string())


for col in (28, 29, 51, 53):
    if col < df.shape[1]:
        print(f"\ncolumn {col}, most common values:")
        print(df[col].value_counts().head(12).to_string())

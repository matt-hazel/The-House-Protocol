import pandas as pd

df = pd.read_parquet("data/prices.parquet")

print(df.groupby("symbol")["date"].agg(["min", "max", "count"]))
print("total rows: ", len(df))
print("duplicate keys: ", df.duplicated(["date", "symbol"]).sum())

import pandas as pd

df = pd.read_parquet("data/macro.parquet")
print(df.groupby("series_id")["date"].agg(["min", "max", "count"]))
print("duplicate keys:", df.duplicated(["date", "series_id"]).sum())
print(df.groupby("series_id")["value"].describe()[["min", "mean", "max"]])
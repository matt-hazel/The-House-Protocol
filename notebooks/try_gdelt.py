# Download latest GDELT 2.0 event file


import io

import pandas as pd
import requests

LASTUPDATE = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"


# column position -> name, from gdelt event codebook

COLUMNS = {
    0: "event_id",
    1: "date",
    5: "actor1_code",
    7: "actor1_country",
    15: "actor2_code",
    17: "actor2_country",
    26: "event_code",
    28: "root_code",
    29: "quad_class",
    30: "goldstein",
    31: "num_mentions",
    33: "num_articles",
    34: "avg_tone",
    53: "action_country",
    59: "added",
    60: "source_url",
}

TEXT_COLUMNS = [
    "actor1_code",
    "actor1_country",
    "actor2_code",
    "actor2_country",
    "event_code",
    "root_code",
    "action_country",
]


lines = requests.get(LASTUPDATE, timeout=30).text.splitlines()
url = next(line.split()[-1] for line in lines if line.endswith(".export.CSV.zip"))

print("file: ", url)


resp = requests.get(url, timeout=60)
print("download size:", len(resp.content), "bytes")


df = pd.read_csv(
    io.BytesIO(resp.content),
    compression="zip",
    sep="\t",
    header=None,
    usecols=sorted(COLUMNS),
    names=[COLUMNS[i] for i in sorted(COLUMNS)],
    dtype={name: str for name in TEXT_COLUMNS},
)


print("rows:", len(df))
print(df.head(5).to_string())
print()
print("events per root code:")
print(df["root_code"].value_counts().sort_index().to_string())
print()
print("mean goldstein:", round(df["goldstein"].mean(), 2))
print("mean tone:", round(df["avg_tone"].mean(), 2))
print("share quad_class 3 or 4 (conflict):", round(df["quad_class"].isin([3, 4]).mean(), 3))

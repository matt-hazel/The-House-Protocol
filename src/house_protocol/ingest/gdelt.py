# GDELT 2.0 event files


import io
import re

import pandas as pd

BASE_URL = "https://data.gdeltproject.org/gdeltv2"


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


REGIONS = {
    "russia_ukraine": {"RS", "UP"},
    "china_taiwan": {"CH", "TW"},
    "middle_east": {"IS", "IR", "GZ", "WE", "LE", "SY", "IZ", "YM", "SA", "JO"},
}

VERBAL_CONFLICT = 3  # quad class, threats demands and protests
MATERIAL_CONFLICT = 4  # quad class, force assult fighting
VIOLENT_ROOTS = {"18", "19", "20"}  # assault fight unconventional mass violence


KEYS = ["day", "region"]
DAY_COLUMNS = [
    "day",
    "region",
    "events",
    "verbal_conflict",
    "material_conflict",
    "violent",
    "goldstein_sum",
    "tone_sum",
]

DAY_NAME = re.compile(r"(\d{14})\.export\.CSV\.zip$")


def day_url(when: pd.Timestamp) -> str:
    return f"{BASE_URL}/{when:%Y%m%d%H%M%S}.export.CSV.zip"


def day_time(url: str) -> pd.Timestamp:
    # day timestamp encoded in a file url
    match = DAY_NAME.search(url)
    if not match:
        raise ValueError(f"not a GDELT event file: {url}")

    return pd.to_datetime(match.group(1), format="%Y%m%d%H%M%S")


def parse_events(content: bytes) -> pd.DataFrame:
    # read a zipped, tab sep., headerless event file into named cols

    return pd.read_csv(
        io.BytesIO(content),
        compression="zip",
        sep="\t",
        header=None,
        usecols=sorted(COLUMNS),
        names=[COLUMNS[i] for i in sorted(COLUMNS)],
        dtype={name: str for name in TEXT_COLUMNS},
    )


def aggregate_day(events: pd.DataFrame, when: pd.Timestamp) -> pd.DataFrame:
    # one row per region with counts and sums for this day

    scopes = {"global": events}

    for name, codes in REGIONS.items():
        scopes[name] = events.loc[events["action_country"].isin(codes)]

    rows = [
        {
            "slice": when,
            "region": name,
            "events": len(sub),
            "verbal_conflict": int((sub["quad_class"] == VERBAL_CONFLICT).sum()),
            "material_conflict": int((sub["quad_class"] == MATERIAL_CONFLICT).sum()),
            "violent": int(sub["root_code"].isin(VIOLENT_ROOTS).sum()),
            "goldstein_sum": float(sub["goldstein"].sum()),
            "tone_sum": float(sub["avg_tone"].sum()),
        }
        for name, sub in scopes.items()
    ]

    return pd.DataFrame(rows, columns=DAY_COLUMNS)

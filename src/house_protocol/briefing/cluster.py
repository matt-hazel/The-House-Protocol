# group headlines about the same event


import re

import numpy as np
import pandas as pd

STOPWORDS = frozenset(
    "a an the and or but of in on at to for with by from as is are was were be been it its "
    "this that these those after over into out up down not no new says say said amid more than "
    "about who what when where how why will would could can may has have had he she they their "
    "his her us".split()
)

TOKEN = re.compile(r"[a-z0-9]+")
THRESHOLD = 0.25
SYNDICATED = 0.9


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN.findall(text.lower()) if len(t) > 1 and t not in STOPWORDS]


def tfidf(docs: list[str]) -> np.ndarray:
    # row normalized matrix

    tokenized = [tokenize(d) for d in docs]
    vocab = {w: i for i, w in enumerate(sorted({w for t in tokenized for w in t}))}
    counts = np.zeros((len(docs), len(vocab)))

    for row, words in enumerate(tokenized):
        for w in words:
            counts[row, vocab[w]] += 1

    doc_freq = (counts > 0).sum(axis=0)
    weighted = counts * (np.log((1 + len(docs)) / (1 + doc_freq)) + 1)
    norms = np.linalg.norm(weighted, axis=1, keepdims=True)
    norms[norms == 0] = 1

    return weighted / norms


def _roots(n: int, pairs: np.ndarray) -> list[int]:
    # connected components over pairs

    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in pairs:
        parent[find(a)] = find(b)

    return [find(i) for i in range(n)]


def find_clusters(headlines: pd.DataFrame, threshold: float = THRESHOLD) -> pd.DataFrame:
    # return copy with cluster origin and centrality columns
    # cluster: shared by headlines on same story, -1 if no other source ran it
    # origin: shared by near identical headlines, so a syndicated copy counts once
    # centrality: how typical a headline is of its cluster

    df = headlines.reset_index(drop=True).copy()

    if df.empty:
        df["cluster"] = pd.Series(dtype=int)
        df["origin"] = pd.Series(dtype=int)
        df["centrality"] = pd.Series(dtype=int)

        return df

    matrix = tfidf(df["title"].tolist())
    sim = matrix @ matrix.T
    sources = df["source"].to_numpy()
    cross = np.triu(np.ones_like(sim, dtype=bool), 1) & (sources[:, None] != sources[None, :])

    df["root"] = _roots(len(df), np.argwhere((sim >= threshold) & cross))
    df["origin"] = _roots(len(df), np.argwhere((sim >= SYNDICATED) & cross))

    multi = df.groupby("root")["source"].transform("nunique") >= 2
    df["cluster"] = np.where(multi, df["root"], -1)
    df["centrality"] = 0.0

    for cid in df.loc[df["cluster"] >= 0, "cluster"].unique():
        idx = np.flatnonzero(df["cluster"] == cid)
        df.loc[idx, "centrality"] = sim[np.ix_(idx, idx)].mean(axis=1)

    return df.drop(columns="root")


def _independent(group: pd.DataFrame) -> int:
    # outlets in a story, merging any that ran the same
    
    names = sorted(set(group["source"]))
    index = {name: i for i, name in enumerate(names)}
    pairs = []
    
    
    for _, sources in group.groupby("origin")["source"]:
        first, *rest = sorted(set(sources))
        pairs.extend((index[first], index[other]) for other in rest)
        
        
    return len(set(_roots(len(names), pairs)))



def summarize(clustered: pd.DataFrame, lean_by_source: dict[str, str]) -> list[dict]:
    # one dict per multi source story, widest independent first

    stories = []

    for _, group in clustered.loc[clustered["cluster"] >= 0].groupby("cluster"):
        best = group.sort_values("centrality", ascending=False).iloc[0]
        leans = {lean_by_source[s] for s in group["source"] if s in lean_by_source}

        stories.append(
            {
                "title": best["title"],
                "sources": sorted(set(group["source"])),
                "independent": _independent(group),
                "leans": sorted(leans),
            }
        )

    return sorted(stories, key=lambda s: (-s["independent"], -len(s["sources"]), s["title"]))

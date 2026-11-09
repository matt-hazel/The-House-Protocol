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
from pathlib import Path

import pandas as pd



def read_table(path : Path) -> pd.DataFrame:
    """Read a parquet table from the given path."""
    
    if not path.exists():
        return pd.DataFrame()
    
    return pd.read_parquet(path)


def upsert(df: pd.DataFrame, path: Path, keys: list[str]) -> None:
    """Upsert the given DataFrame into the parquet table at the given path."""
    
    if path.exists():
        return pd.DataFrame()
    
    return pd.read_parquet(path)


def upsert(df: pd.DataFrame, path: Path, keys: list[str]) -> None:
    """ Merge df into Parquet file at path, de-duplicating based on keys"""
    
    combined = pd.concat([read_table(path), df], ignore_index=True)
    
    combined = (combined.drop_duplicates(subset=keys, keep='last').sort_values(keys).reset_index(drop=True))
    
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    combined.to_parquet(temp, index=False)
    temp.replace(path)
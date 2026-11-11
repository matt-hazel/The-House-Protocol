# copy parquet tables into postgres for grafana

import logging
import os
import pandas as pd

from sqlalchemy import Engine, create_engine



logger = logging.getLogger(__name__)



def get_engine(url: str | None = None) -> Engine:
    # DATABASE_URL is .env
    
    url = url or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    
    
    return create_engine(url)



def sync_table(df: pd.DataFrame, name: str, engine: Engine) -> int:
    # replaces whole table
    
    with engine.begin() as conn:
        df.to_sql(name, conn, if_exists="replace", index=False)
    
    
    logger.info("synced %s: %d rows", name, len(df))
    
    
    return len(df)
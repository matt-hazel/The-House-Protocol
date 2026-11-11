import pandas as pd
import pytest
from sqlalchemy import create_engine

from house_protocol.storage import sql


@pytest.fixture
def engine():
    return create_engine("sqlite://")


def test_sync_table_writes_rows(engine):
    df = pd.DataFrame({"day": ["2026-01-01", "2026-01-02"], "value": [1.0, 2.0]})

    assert sql.sync_table(df, "demo", engine) == 2
    assert len(pd.read_sql("select * from demo", engine)) == 2


def test_sync_table_replaces_rather_than_appends(engine):
    df = pd.DataFrame({"value": [1.0, 2.0]})

    sql.sync_table(df, "demo", engine)
    sql.sync_table(df, "demo", engine)

    assert len(pd.read_sql("select * from demo", engine)) == 2


def test_get_engine_requires_a_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        sql.get_engine()

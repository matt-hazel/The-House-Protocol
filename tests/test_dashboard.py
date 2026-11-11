import pandas as pd
import pytest
from sqlalchemy import create_engine

from house_protocol.storage import dashboard


@pytest.fixture
def engine():
    return create_engine("sqlite://")


def write(data_dir, filename):
    pd.DataFrame({"day": ["2026-01-01"], "value": [1.0]}).to_parquet(data_dir / filename)


def test_syncs_each_existing_file(tmp_path, engine):
    write(tmp_path, "prices.parquet")
    write(tmp_path, "macro.parquet")

    assert dashboard.sync_dashboard(tmp_path, engine) == 2
    assert len(pd.read_sql("select * from prices", engine)) == 1
    assert len(pd.read_sql("select * from macro", engine)) == 1


def test_missing_files_are_skipped(tmp_path, engine):
    assert dashboard.sync_dashboard(tmp_path, engine) == 0


def test_one_failing_table_does_not_block_the_others(tmp_path, engine, monkeypatch):
    write(tmp_path, "prices.parquet")
    write(tmp_path, "macro.parquet")
    real = dashboard.sync_table

    def flaky(df, name, eng):
        if name == "prices":
            raise RuntimeError("boom")
        return real(df, name, eng)

    monkeypatch.setattr(dashboard, "sync_table", flaky)

    assert dashboard.sync_dashboard(tmp_path, engine) == 1
    assert len(pd.read_sql("select * from macro", engine)) == 1

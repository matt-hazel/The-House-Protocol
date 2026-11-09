import io
import zipfile

import pandas as pd
import pytest

from house_protocol.ingest import gdelt

WHEN = pd.Timestamp("2026-11-09 22:00:00")


def event(root, quad, goldstein, tone, country, event_id=1):
    """One event row as {column index: value}."""
    return {
        0: event_id,
        26: root + "0",
        28: root,
        29: quad,
        30: goldstein,
        34: tone,
        53: country,
        59: "20261109220000",
    }


def make_zip(events):
    lines = []
    for values in events:
        cells = [""] * 61
        for index, value in values.items():
            cells[index] = str(value)
        lines.append("\t".join(cells))

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("20261109220000.export.CSV", "\n".join(lines))

    return buffer.getvalue()


def sample_events():
    return gdelt.parse_events(
        make_zip(
            [
                event("04", 1, 1.0, 2.0, "US", 1),
                event("14", 3, -2.0, -3.0, "RS", 2),
                event("19", 4, -10.0, -8.0, "UP", 3),
                event("18", 4, -9.0, -6.0, "IS", 4),
            ]
        )
    )


def row(table, region):
    return table.loc[table["region"] == region].iloc[0]


def test_parse_keeps_root_code_leading_zero_and_numeric_types():
    events = gdelt.parse_events(make_zip([event("04", 1, 1.5, -2.0, "US")]))

    assert len(events) == 1
    assert events.loc[0, "root_code"] == "04"
    assert events.loc[0, "goldstein"] == 1.5
    assert events.loc[0, "action_country"] == "US"


def test_aggregate_counts_each_region_separately():
    table = gdelt.aggregate_slice(sample_events(), WHEN)

    assert row(table, "global")["events"] == 4
    assert row(table, "russia_ukraine")["events"] == 2
    assert row(table, "middle_east")["events"] == 1
    assert row(table, "china_taiwan")["events"] == 0


def test_aggregate_splits_conflict_types():
    table = gdelt.aggregate_slice(sample_events(), WHEN)

    ru = row(table, "russia_ukraine")
    assert ru["verbal_conflict"] == 1
    assert ru["material_conflict"] == 1
    assert ru["violent"] == 1


def test_aggregate_sums_goldstein_and_tone():
    table = gdelt.aggregate_slice(sample_events(), WHEN)

    ru = row(table, "russia_ukraine")
    assert ru["goldstein_sum"] == -12.0
    assert ru["tone_sum"] == -11.0


def test_aggregate_quiet_region_still_gets_a_row_of_zeros():
    table = gdelt.aggregate_slice(sample_events(), WHEN)

    ct = row(table, "china_taiwan")
    assert ct["events"] == 0
    assert ct["goldstein_sum"] == 0.0


def test_aggregate_has_one_row_per_region_and_slice_time():
    table = gdelt.aggregate_slice(sample_events(), WHEN)

    assert list(table.columns) == gdelt.SLICE_COLUMNS
    assert set(table["region"]) == {"global", *gdelt.REGIONS}
    assert (table["slice"] == WHEN).all()


def test_slice_url_and_back():
    url = gdelt.slice_url(WHEN)

    assert url == "https://data.gdeltproject.org/gdeltv2/20261109220000.export.CSV.zip"
    assert gdelt.slice_time(url) == WHEN


def test_slice_time_rejects_other_files():
    with pytest.raises(ValueError):
        gdelt.slice_time("https://data.gdeltproject.org/gdeltv2/lastupdate.txt")


def test_regions_are_wellformed_and_do_not_overlap():
    seen = set()
    for name, codes in gdelt.REGIONS.items():
        assert all(len(c) == 2 and c.isupper() for c in codes), name
        assert not (seen & codes), f"{name} overlaps another region"
        seen |= codes

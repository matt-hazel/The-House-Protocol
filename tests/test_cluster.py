import pandas as pd

from house_protocol.briefing import cluster


def frame(rows):
    return pd.DataFrame(rows, columns=["source", "title"])


AMSTERDAM = [
    ("ABC", "Tens of thousands march in Amsterdam pressing Dutch government on Gaza"),
    ("AP", "Tens of thousands march in Amsterdam pressing Dutch government on Gaza"),
    ("BBC", "Huge Amsterdam march demands Dutch government act on Gaza"),
]


def test_same_story_different_words_clusters_and_unrelated_does_not():
    df = frame(
        [
            ("A", "Israeli president taps Eisenkot to form government"),
            ("B", "Eisenkot asked by Israel president to form new government"),
            ("C", "Alcaraz beats Shelton in Paris Masters final"),
        ]
    )

    out = cluster.find_clusters(df)

    assert out.loc[0, "cluster"] == out.loc[1, "cluster"]
    assert out.loc[0, "cluster"] >= 0
    assert out.loc[2, "cluster"] == -1


def test_same_source_headlines_do_not_cluster_on_their_own():
    df = frame(
        [
            ("A", "Israeli president taps Eisenkot to form government"),
            ("A", "Eisenkot asked by Israel president to form new government"),
        ]
    )

    assert (cluster.find_clusters(df)["cluster"] == -1).all()


def test_identical_headlines_share_an_origin():
    out = cluster.find_clusters(frame(AMSTERDAM))

    assert out.loc[0, "origin"] == out.loc[1, "origin"]
    assert out.loc[2, "origin"] != out.loc[0, "origin"]


def test_summary_counts_syndicated_copies_once():
    leans = {"ABC": "center-left", "AP": "center", "BBC": "center"}

    [story] = cluster.summarize(cluster.find_clusters(frame(AMSTERDAM)), leans)

    assert story["sources"] == ["ABC", "AP", "BBC"]
    assert story["independent"] == 2
    assert story["leans"] == ["center", "center-left"]


def test_summary_orders_by_independent_coverage():
    df = frame(
        [
            ("A", "Egypt trains collide killing seven"),
            ("B", "Seven killed as trains collide in Egypt"),
            ("C", "Trains collide in Egypt, seven dead"),
            ("A", "Paraguay former president charged over bank collapse"),
            ("B", "Paraguay ousted president charged bank collapse"),
        ]
    )

    stories = cluster.summarize(cluster.find_clusters(df), {})

    assert [s["independent"] for s in stories] == [3, 2]


def test_empty_frame():
    out = cluster.find_clusters(frame([]))

    assert out.empty
    assert "cluster" in out.columns



def test_one_outlet_with_two_headlines_counts_once():
    df = frame(
        [
            ("AP", "Egypt trains collide killing seven"),
            ("AP", "Seven killed as trains collide in Egypt"),
            ("BBC", "Trains collide in Egypt, seven dead"),
        ]
    )

    [story] = cluster.summarize(cluster.find_clusters(df), {})

    assert story["independent"] == 2

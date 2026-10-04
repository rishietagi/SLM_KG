"""CQ1: Which stage does "trade scheme creation" belong to, and what are its upstream and downstream stages?"""
from retrieve.competency import cq1


def test_trade_scheme_creation_stage_and_neighbours(store, expected):
    e = expected["cq1"]
    result = cq1(store, e["term"])
    assert len(result["rows"]) == 1, result["rows"]
    row = result["rows"][0]
    assert row["activity"] == e["activity"]
    assert row["stage"] == e["stage"]
    assert row["upstream"] == e["upstream"]
    assert row["downstream"] == e["downstream"]
    assert len(result["path"]) == 3

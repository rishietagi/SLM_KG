"""CQ10: Which L2/L3 processes in trade-promotion management enable which activities across stages?"""
from retrieve.competency import cq10


def test_trade_promotion_management_spans_stages(store, expected):
    e = expected["cq10"]
    r = cq10(store, e["area"])
    assert sorted({x["l3_process"] for x in r["rows"]}) == sorted(e["l3"])
    assert sorted({x["stage"] for x in r["rows"]}) == e["stages"]

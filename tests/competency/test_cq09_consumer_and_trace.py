"""CQ9: Which consumer concepts does Stage 10 touch, and what can a complaint be traced back to?"""
from retrieve.competency import cq9


def test_consumer_concepts_and_complaint_trace(store, expected):
    e = expected["cq9"]
    r = cq9(store, e["stage"])
    assert sorted(r["touched"]) == sorted(e["touched"])
    assert len(r["trace"]) == 1
    t = r["trace"][0]
    assert (t["batch"], t["plant"], t["sku"]) == (e["trace"]["batch"], e["trace"]["plant"], e["trace"]["sku"])

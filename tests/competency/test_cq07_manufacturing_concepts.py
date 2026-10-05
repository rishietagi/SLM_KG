"""CQ7: Which product and asset concepts does manufacturing act on, and how do they relate?"""
from retrieve.competency import cq7


def test_manufacturing_concept_subgraph(store, expected):
    e = expected["cq7"]
    r = cq7(store, e["stage"])
    assert r["concepts"] == sorted(e["concepts"])
    got = {(x["from"], x["relationship"], x["to"]) for x in r["rows"]}
    assert {tuple(t) for t in e["must_relate"]} <= got

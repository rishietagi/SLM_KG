"""CQ8: Which ecosystem participants and channels are involved from warehouse to consumer purchase?"""
from retrieve.competency import cq8


def test_ecosystem_from_warehouse_to_purchase(store, expected):
    e = expected["cq8"]
    r = cq8(store, e["first"], e["last"])
    assert sorted(x["concept"] for x in r["rows"]) == sorted(e["concepts"])
    assert {x["kind"] for x in r["rows"]} == {"participant", "channel", "geography"}

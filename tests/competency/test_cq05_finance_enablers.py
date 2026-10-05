"""CQ5: Which L3 processes enable outlet execution activities?"""
from retrieve.competency import cq5


def test_l3_processes_enabling_outlet_execution(store, expected):
    e = expected["cq5"]
    result = cq5(store, e["stage"])
    assert {r["endpoint"] for r in result["rows"]} == set(e["endpoints"])
    # every L3 sits in an L2 group inside an L1 process area
    assert all(r["process_group"] and r["process_area"] for r in result["rows"])
